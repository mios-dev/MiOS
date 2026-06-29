# AI-hint: In-process asyncio.Queue gateway producer-consumer seam (CONV-02).
# Integrates smolagents.ToolCallingAgent with the unified capreg tool manifest and LiteLLMModel
# pointed locally at MIOS_AI_ENDPOINT (Law 5 compliance). Degrades-open to legacy HTTP via mode="http".
# AI-related: ./server.py, ./mios_dispatcher.py, ./mios_capreg.py, ./test_mios_gateway_queue.py

import asyncio
import os
import time
import uuid
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, List

from smolagents import Tool, ToolCallingAgent, LiteLLMModel

log = logging.getLogger("mios-agent-pipe")

# Global config variables dependency-injected by server.py
_VERB_CATALOG: dict = {}
_recipes: dict = {}
_skills: dict = {}
_trace_span: Any = None

def configure(verb_catalog: dict = None, recipes: dict = None, skills: dict = None, trace_span: Any = None):
    global _VERB_CATALOG, _recipes, _skills, _trace_span
    if verb_catalog is not None:
        _VERB_CATALOG = verb_catalog
    if recipes is not None:
        _recipes = recipes
    if skills is not None:
        _skills = skills
    if trace_span is not None:
        _trace_span = trace_span

@dataclass
class GatewayRequest:
    payload: dict
    fut: asyncio.Future

class GatewayQueue:
    def __init__(self, maxsize: int = 64):
        self.queue = asyncio.Queue(maxsize=maxsize)

    async def put(self, req: GatewayRequest) -> None:
        await self.queue.put(req)

    async def get(self) -> GatewayRequest:
        return await self.queue.get()

    def task_done(self) -> None:
        self.queue.task_done()

    def qsize(self) -> int:
        return self.queue.qsize()

class DispatchTool(Tool):
    def __init__(self, name: str, description: str, inputs: dict, kind: str, main_loop: asyncio.AbstractEventLoop):
        self.name = name
        self.description = description
        self.inputs = inputs
        self.output_type = "string"
        self.kind = kind
        self.main_loop = main_loop
        super().__init__()

    def forward(self, **kwargs) -> str:
        # Resolve the underlying execution coroutine
        if self.kind == "verb":
            from mios_dispatch import dispatch_mios_verb
            coro = dispatch_mios_verb(self.name, kwargs)
        elif self.kind == "recipe":
            from mios_dispatch import dispatch_mios_verb
            rkey = self.name[len("mios_recipe__"):].replace("_", "-")
            coro = dispatch_mios_verb("os_recipe", {"name": rkey, "params": kwargs})
        elif self.kind == "skill":
            from mios_skills import execute_skill
            real = self.name[len("mios_skill__"):]
            coro = execute_skill(real, kwargs)
        else:
            return f"Error: unknown capability kind '{self.kind}'"

        # Execute coroutine on the main event loop from the worker thread
        fut = asyncio.run_coroutine_threadsafe(coro, self.main_loop)
        res = fut.result()
        if isinstance(res, dict):
            return str(res.get("output") or res.get("result") or res)
        return str(res)

def parse_sig(sig: str) -> dict:
    if not sig:
        return {}
    inputs = {}
    for part in sig.split(","):
        part = part.strip()
        if not part:
            continue
        optional = False
        if part.endswith("?"):
            part = part[:-1].strip()
            optional = True
        
        if "=" in part:
            name_part, val_part = part.split("=", 1)
            name = name_part.strip()
            optional = True
        else:
            name = part
            
        name = name.strip('"').strip("'")
        
        param_type = "string"
        lower_name = name.lower()
        if any(x in lower_name for x in ("limit", "count", "timeout", "port", "every", "concurrency", "maxsize")):
            param_type = "integer"
        elif any(x in lower_name for x in ("enable", "force", "success", "active", "dryrun")):
            param_type = "boolean"
            
        inputs[name] = {
            "type": param_type,
            "description": f"Parameter {name}",
            "nullable": optional
        }
    return inputs

def get_tools(ceiling: str = "interactive") -> list:
    from mios_capreg import build_capability_manifest
    manifest = build_capability_manifest(
        _VERB_CATALOG, _recipes, ceiling=ceiling, skills=_skills
    )
    
    tools = []
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.get_event_loop()
        
    for cap in manifest:
        name = cap["name"]
        kind = cap["kind"]
        description = cap.get("description", "")
        
        sig = ""
        if kind == "verb":
            vcfg = _VERB_CATALOG.get(name) or {}
            sig = vcfg.get("sig", "")
        elif kind == "recipe":
            rcfg = _recipes.get(name) or {}
            sig = rcfg.get("sig", "")
            name = f"mios_recipe__{name}"
        elif kind == "skill":
            scfg = _skills.get(name) or {}
            sig = scfg.get("sig", "")
            name = f"mios_skill__{name}"
            
        inputs = parse_sig(sig)
        tools.append(DispatchTool(
            name=name,
            description=description,
            inputs=inputs,
            kind=kind,
            main_loop=loop
        ))
    return tools

def extract_prompt_from_payload(payload: dict) -> str:
    messages = payload.get("messages") or []
    prompt = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            prompt = msg.get("content") or ""
            break
    if not prompt and messages:
        prompt = messages[-1].get("content") or ""
    return prompt

def extract_system_prompt_from_payload(payload: dict) -> Optional[str]:
    messages = payload.get("messages") or []
    for msg in messages:
        if msg.get("role") == "system":
            return msg.get("content")
    return None

class GatewayWorker:
    def __init__(self, tools: list, endpoint: str, model_name: str):
        self.tools = tools
        self.endpoint = endpoint
        self.model_name = model_name
        self._tasks: List[asyncio.Task] = []

    async def run(self, queue: GatewayQueue, concurrency: int = 4) -> None:
        self._tasks = []
        for i in range(concurrency):
            t = asyncio.create_task(self._worker_loop(queue, f"worker-{i}"))
            self._tasks.append(t)
        try:
            await asyncio.gather(*self._tasks)
        except asyncio.CancelledError:
            log.info("GatewayWorker loop cancelled")
            for t in self._tasks:
                t.cancel()
            await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _worker_loop(self, queue: GatewayQueue, worker_id: str) -> None:
        while True:
            try:
                req = await queue.get()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"{worker_id} error getting request: {e}")
                continue

            try:
                # Wrap the worker execution inside a single trace span
                if _trace_span:
                    async with _trace_span("tool_loop", kind="tool_loop"):
                        res = await asyncio.to_thread(self._run_agent, req.payload)
                else:
                    res = await asyncio.to_thread(self._run_agent, req.payload)
                
                if not req.fut.done():
                    req.fut.set_result(res)
            except Exception as e:
                log.exception(f"{worker_id} agent execution failed")
                if not req.fut.done():
                    req.fut.set_exception(e)
            finally:
                queue.task_done()

    def _run_agent(self, payload: dict) -> dict:
        system_prompt = extract_system_prompt_from_payload(payload)
        prompt = extract_prompt_from_payload(payload)
        
        # Strict local enforcement: telemetry off + LiteLLM targeted at local endpoint
        os.environ["LITELLM_TELEMETRY"] = "False"
        
        model = LiteLLMModel(
            model_id="openai/" + self.model_name,
            api_base=self.endpoint,
            api_key="none"
        )
        
        agent = ToolCallingAgent(
            tools=self.tools,
            model=model,
            system_prompt=system_prompt
        )
        
        result = agent.run(prompt)
        
        return {
            "id": "chatcmpl-" + uuid.uuid4().hex[:12],
            "object": "chat.completion",
            "created": int(time.time()),
            "model": self.model_name,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": str(result)
                    },
                    "finish_reason": "stop"
                }
            ]
        }
