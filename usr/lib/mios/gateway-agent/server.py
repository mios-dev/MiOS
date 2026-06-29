import asyncio
import json
import logging
import os
import uuid
import time
from typing import Any, Generator, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import httpx

from contextlib import asynccontextmanager
from mcp_client import MiOSMCPClient
from tool_registry import MiOSToolRegistry

import session as session_db

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("mios-gateway-agent")

mcp_client = None
tool_registry = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global mcp_client, tool_registry
    gateway_cfg = _toml_section("gateway")
    mcp_refresh = int(gateway_cfg.get("mcp_refresh_seconds") or 300)
    
    mcp_client = MiOSMCPClient(mcp_refresh_seconds=mcp_refresh)
    await mcp_client.connect()
    
    main_loop = asyncio.get_running_loop()
    tool_registry = MiOSToolRegistry(mcp_client, main_loop)
    
    yield
    
    if mcp_client:
        await mcp_client.close()

app = FastAPI(title="MiOS Gateway Agent Service", lifespan=lifespan)

# ── Config Loader ──
def _toml_section(section: str) -> dict:
    _layers = [
        os.environ.get("MIOS_TOML", "/usr/share/mios/mios.toml"),
        "/etc/mios/mios.toml",
        os.path.expanduser("~/.config/mios/mios.toml")
    ]
    out: dict = {}
    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        for _p in _layers:
            try:
                with open(_p, "rb") as _f:
                    _layer = tomllib.load(_f).get(section) or {}
            except (OSError, tomllib.TOMLDecodeError):
                continue
            if isinstance(_layer, dict):
                out.update(_layer)
    except Exception as e:
        log.warning("Failed to load overlay config section %s: %s", section, e)

    def _xpand(v):
        if isinstance(v, str):
            return os.path.expandvars(v) if "$" in v else v
        if isinstance(v, dict):
            return {k: _xpand(x) for k, x in v.items()}
        if isinstance(v, list):
            return [_xpand(x) for x in v]
        return v
    return _xpand(out)

# ── Health Endpoints ──
@app.get("/health")
@app.get("/v1/cluster/health")
async def health():
    return {"status": "ok", "service": "mios-gateway-agent"}

# ── Models Endpoint ──
@app.get("/v1/models")
async def models():
    ai_cfg = _toml_section("ai")
    available_models = ai_cfg.get("available_models") or ["granite4.1:3b", "granite4.1:30b", "gpt-oss:20b", "nomic-embed-text"]
    
    data = []
    for model_id in available_models:
        data.append({
            "id": model_id,
            "object": "model",
            "created": int(time.time()),
            "owned_by": "system"
        })
    return {"object": "list", "data": data}

# ── Chat Completions Endpoint ──
class ChatCompletionRequest(BaseModel):
    model: Optional[str] = None
    messages: list[dict]
    stream: Optional[bool] = False
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    tools: Optional[list] = None
    metadata: Optional[dict] = None

@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    # Determine session ID
    meta = req.metadata or {}
    session_id = str(meta.get("chat_id") or meta.get("session_id") or "default")
    
    # Load session history from pgvector
    history = await session_db.get_session(session_id)
    
    # Append new incoming messages to session history
    new_incoming = req.messages
    # Avoid duplicating history if messages contain the history already (OpenAI stateless clients)
    # Check if history is already a prefix of incoming messages:
    if len(history) < len(new_incoming):
        # We append only the new turns
        history = history + new_incoming[len(history):]
    else:
        history = new_incoming

    # Save updated session history to pgvector
    await session_db.save_session(session_id, history)

    # Gateway / AI configs
    gateway_cfg = _toml_section("gateway")
    ai_cfg = _toml_section("ai")

    model_id = req.model or gateway_cfg.get("model") or ai_cfg.get("agent_model") or "granite4.1:3b"
    max_steps = gateway_cfg.get("max_steps", 30)

    # Set up OpenAIServerModel pointing at MIOS_AI_ENDPOINT (Unified redirection Law 5)
    # Defaults to localhost orchestrator port :8640
    ai_endpoint = os.environ.get("MIOS_AI_ENDPOINT", "http://localhost:8640/v1")
    
    from smolagents import OpenAIServerModel, ToolCallingAgent
    
    try:
        model = OpenAIServerModel(
            model_id=model_id,
            api_base=ai_endpoint,
            api_key=os.environ.get("MIOS_AI_KEY", "fake")
        )
    except Exception as e:
        log.error("Failed to initialize OpenAIServerModel: %s", e)
        return JSONResponse(status_code=500, content={"error": f"Model init failed: {e}"})

    # Tool loop engine initialization (T-079)
    tools = tool_registry.get_tools() if tool_registry else []
    
    try:
        agent = ToolCallingAgent(
            tools=tools,
            model=model,
            max_steps=max_steps
        )
    except Exception as e:
        log.error("Failed to initialize ToolCallingAgent: %s", e)
        return JSONResponse(status_code=500, content={"error": f"Agent init failed: {e}"})

    # Build ReAct task query from conversation history
    context = ""
    for msg in history[:-1]:
        role = msg.get("role", "")
        content = msg.get("content", "")
        context += f"{role.upper()}: {content}\n"
    
    last_user_text = history[-1].get("content", "")
    task = f"Conversation History:\n{context}\n\nUser request: {last_user_text}"

    # Helper function to generate stream chunks
    def openai_chunk(content: str, finish_reason: Optional[str] = None) -> str:
        chunk = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model_id,
            "choices": [{
                "index": 0,
                "delta": {"content": content} if content else {},
                "finish_reason": finish_reason
            }]
        }
        return f"data: {json.dumps(chunk)}\n\n"

    if req.stream:
        async def stream_generator():
            try:
                # Run the agent stream
                # Note: agent.run() execution blocks synchronous threads, we run it in executor or stream step-by-step
                loop = asyncio.get_running_loop()
                steps = await loop.run_in_executor(None, lambda: list(agent.run(task, stream=True)))
                
                from smolagents.memory import ActionStep
                from smolagents.agents import FinalAnswerStep
                
                final_answer = ""
                for step in steps:
                    if isinstance(step, ActionStep):
                        if step.model_output:
                            yield openai_chunk(step.model_output)
                        if step.tool_calls:
                            for tc in step.tool_calls:
                                yield openai_chunk(f"\n[Calling Tool: {tc.name} with arguments: {tc.arguments}]\n")
                        if step.observations:
                            yield openai_chunk(f"\n[Observation: {step.observations}]\n")
                    elif isinstance(step, FinalAnswerStep):
                        final_answer = step.output
                        yield openai_chunk(f"\nFinal Answer: {step.output}\n", finish_reason="stop")
                
                if final_answer:
                    history.append({"role": "assistant", "content": str(final_answer)})
                    await session_db.save_session(session_id, history)
            except Exception as stream_err:
                log.error("Stream generation error: %s", stream_err)
                yield openai_chunk(f"\n[Agent Error: {stream_err}]\n", finish_reason="error")
            yield "data: [DONE]\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")
    else:
        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, lambda: agent.run(task, stream=False))
            
            # Format completion response
            response = {
                "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model_id,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": str(result)
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            }
            history.append({"role": "assistant", "content": str(result)})
            await session_db.save_session(session_id, history)
            return response
        except Exception as run_err:
            log.error("Agent execution error: %s", run_err)
            return JSONResponse(status_code=500, content={"error": f"Agent loop failed: {run_err}"})

if __name__ == "__main__":
    import uvicorn
    # Load settings to bind host/port
    gateway_cfg = _toml_section("gateway")
    port = int(gateway_cfg.get("port") or 8642)
    uvicorn.run(app, host="0.0.0.0", port=port)
