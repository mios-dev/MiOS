#!/usr/bin/env python3
"""mios-opencode-gateway -- a thin OpenAI /v1 adapter that fronts the
opencode CLI so agent-pipe's [agents.opencode] (:8633/v1) is a REAL
endpoint.

WHY: opencode has NO native OpenAI /v1 server. Its `serve` mode exposes
opencode's OWN OpenAPI on :4096 (for opencode clients), not OpenAI
chat-completions. This shim wraps `opencode run` (single-shot, headless)
and returns an OpenAI chat.completion, so any /v1 caller -- agent-pipe's
multi-agent fan-out (opencode secondary) AND the primary path when refine
picks target_agent=opencode -- can reach it like any other sub-agent.

FOSS + OFFLINE: opencode is configured (opencode.json) for the LOCAL
ollama provider (model ollama/qwen2.5-coder:7b @ http://localhost:11434/v1).
This gateway adds ZERO cloud dependency -- it only spawns the local
opencode binary, which talks to local ollama.

Best-effort by design: opencode's model runs on the dGPU lane, so under
VRAM pressure the run will time out; the gateway then returns an empty
answer so agent-pipe's fan-out drops opencode harmlessly. Streaming
callers get the complete answer as a single content delta + [DONE].

Config (env / SSOT via mios.toml -> service Environment=):
  MIOS_PORT_OPENCODE_GATEWAY  listen port (default 8633)
  MIOS_OPENCODE_BIN           opencode binary (default /usr/local/bin/opencode)
  MIOS_OPENCODE_WORKDIR       scratch cwd for runs (no repo -> Q&A mode)
  MIOS_OPENCODE_TIMEOUT_S     per-run cap (default 90)
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

OPENCODE_BIN = os.environ.get("MIOS_OPENCODE_BIN", "/usr/local/bin/opencode")
WORK_DIR = os.environ.get("MIOS_OPENCODE_WORKDIR",
                          "/var/lib/mios/opencode-gateway/work")
TIMEOUT_S = int(os.environ.get("MIOS_OPENCODE_TIMEOUT_S", "90"))
MODEL_ID = os.environ.get("MIOS_OPENCODE_MODEL", "opencode")
PORT = int(os.environ.get("MIOS_PORT_OPENCODE_GATEWAY", "8633"))

# Strip ANSI/OSC escape sequences opencode's CLI emits.
_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*(?:\x07|\x1b\\)")

app = FastAPI()


def _clean(s: str) -> str:
    return _ANSI.sub("", s or "").strip()


def _last_user(messages: list) -> str:
    for m in reversed(messages or []):
        if isinstance(m, dict) and m.get("role") == "user":
            c = m.get("content")
            if isinstance(c, list):  # OpenAI content-parts shape
                c = " ".join(p.get("text", "") for p in c
                             if isinstance(p, dict))
            return str(c or "")
    return ""


async def _run_opencode(prompt: str) -> str:
    if not prompt.strip():
        return ""
    try:
        os.makedirs(WORK_DIR, exist_ok=True)
    except OSError:
        pass
    try:
        proc = await asyncio.create_subprocess_exec(
            OPENCODE_BIN, "run", prompt,
            cwd=WORK_DIR,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env={**os.environ,
                 "HOME": os.environ.get("HOME", "/root"),
                 "NO_COLOR": "1", "CI": "1"},
        )
    except Exception as e:  # binary missing / not executable
        return f"(opencode unavailable: {e})"
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_S)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        return ""  # timeout -> empty so the fan-out drops opencode
    return _clean(out.decode("utf-8", "replace"))


def _completion(text: str) -> dict:
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": MODEL_ID,
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": text}}],
    }


@app.get("/v1/models")
async def models() -> dict:
    return {"object": "list",
            "data": [{"id": MODEL_ID, "object": "model", "owned_by": "mios"}]}


@app.get("/health")
async def health() -> dict:
    return {"ok": os.path.exists(OPENCODE_BIN), "bin": OPENCODE_BIN}


@app.post("/v1/chat/completions")
async def chat(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": {"message": "invalid JSON body",
                                       "type": "invalid_request_error"}},
                            status_code=400)
    text = await _run_opencode(_last_user(body.get("messages") or []))
    if body.get("stream"):
        async def _gen():
            cid = f"chatcmpl-{uuid.uuid4().hex[:24]}"
            base = {"id": cid, "object": "chat.completion.chunk",
                    "created": int(time.time()), "model": MODEL_ID}
            first = {**base, "choices": [
                {"index": 0,
                 "delta": {"role": "assistant", "content": text}}]}
            yield f"data: {json.dumps(first)}\n\n".encode("utf-8")
            done = {**base, "choices": [
                {"index": 0, "delta": {}, "finish_reason": "stop"}]}
            yield f"data: {json.dumps(done)}\n\n".encode("utf-8")
            yield b"data: [DONE]\n\n"
        return StreamingResponse(_gen(), media_type="text/event-stream")
    return JSONResponse(_completion(text))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
