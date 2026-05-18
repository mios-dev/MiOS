"""'MiOS' Agent Pipe -- standalone FastAPI service.

Operator directive 2026-05-18: "mios discord chats not going through
MiOS-Agent(OWUI) paths when contacting through discord (uses only
MiOS-Hermes and doesn't have the same tool understanding and
environments details now!!!!)"

The router + refine + dispatch + critic + polish chain has historically
lived as an OWUI Pipe class inside webui.db. That makes the chain
EXCLUSIVE to OWUI -- any other gateway (Hermes Discord, future
Slack/Telegram, MCP) talks directly to hermes-agent and gets a less-
aware agent (no router, no critic, no tool dispatch envelope).

This service centralizes the chain at one HTTP endpoint
(http://localhost:8640/v1/chat/completions) so EVERY gateway gets the
same tool surface + critic + SurrealDB state writes. Architecture:

  OWUI                     ──┐
  Hermes Discord gateway   ──┼──> localhost:8640 (agent-pipe)
                             │        │
  (future) Slack/Telegram   ──┘        │
                                       ▼
                              localhost:8642 (hermes-agent)
                                       │
                                       ▼
                              ollama (raw inference)

This file is the SCAFFOLD (step 1 of 5 per the migration plan). The
actual router/refine/critic logic gets ported in subsequent commits;
v0 here is a transparent proxy that just forwards /v1/chat/completions
through to hermes-agent so the deployment shape is provable end-to-end
before the logic migration begins.

Endpoints:
  GET  /health                  -> {"status": "ok", "backend": "<url>"}
  POST /v1/chat/completions     -> proxy to MIOS_AGENT_PIPE_BACKEND
  GET  /v1/models               -> proxy to MIOS_AGENT_PIPE_BACKEND
  POST /v1/embeddings           -> proxy to MIOS_AGENT_PIPE_BACKEND

Per the SSOT chain: every operator-tunable constant sources from
mios.toml -> userenv.sh -> MIOS_* env -> os.environ.get() with a
sensible fallback. No hardcoded literals.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any, AsyncGenerator

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn

# ── Config (SSOT-sourced via env) ──────────────────────────────────
PORT = int(os.environ.get("MIOS_PORT_AGENT_PIPE", "8640"))
BACKEND = os.environ.get("MIOS_AGENT_PIPE_BACKEND",
                         "http://localhost:8642/v1").rstrip("/")
BACKEND_MODEL = os.environ.get("MIOS_AGENT_PIPE_BACKEND_MODEL",
                               "hermes-agent")

# ── Logging ────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[mios-agent-pipe] %(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("mios-agent-pipe")

# ── App ────────────────────────────────────────────────────────────
app = FastAPI(
    title="MiOS Agent Pipe",
    version="0.1.0",
    description=(
        "Gateway-agnostic router + refine + critic chain "
        "fronting hermes-agent."
    ),
)

# Shared httpx AsyncClient -- reused across requests (connection
# pooling). Created lazily on first request so module import is cheap.
_client: httpx.AsyncClient | None = None


async def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=None, write=None, pool=None),
        )
    return _client


# ── Health ─────────────────────────────────────────────────────────
@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": app.version,
        "backend": BACKEND,
        "backend_model": BACKEND_MODEL,
        "port": PORT,
    }


# ── /v1/models (passthrough) ───────────────────────────────────────
@app.get("/v1/models")
async def list_models(request: Request) -> JSONResponse:
    client = await _get_client()
    headers = {k: v for k, v in request.headers.items()
               if k.lower() in ("authorization",)}
    try:
        r = await client.get(f"{BACKEND}/models", headers=headers)
        return JSONResponse(content=r.json(), status_code=r.status_code)
    except httpx.HTTPError as e:
        log.warning("models proxy failed: %s", e)
        return JSONResponse(
            content={"error": {"message": str(e), "type": "backend_error"}},
            status_code=502,
        )


# ── /v1/embeddings (passthrough) ───────────────────────────────────
@app.post("/v1/embeddings")
async def embeddings(request: Request) -> JSONResponse:
    body = await request.body()
    client = await _get_client()
    headers = {k: v for k, v in request.headers.items()
               if k.lower() in ("authorization", "content-type")}
    try:
        r = await client.post(
            f"{BACKEND}/embeddings", content=body, headers=headers,
        )
        return JSONResponse(content=r.json(), status_code=r.status_code)
    except httpx.HTTPError as e:
        log.warning("embeddings proxy failed: %s", e)
        return JSONResponse(
            content={"error": {"message": str(e), "type": "backend_error"}},
            status_code=502,
        )


# ── /v1/chat/completions ───────────────────────────────────────────
# v0 SCAFFOLD: transparent proxy. Subsequent commits will insert the
# router / refine / critic chain here. Keeping the proxy shape now so
# the OWUI shim + Hermes Discord re-route can be wired in parallel
# without waiting for the logic migration to land.
@app.post("/v1/chat/completions")
async def chat_completions(request: Request) -> StreamingResponse:
    try:
        body_bytes = await request.body()
        body = json.loads(body_bytes) if body_bytes else {}
    except json.JSONDecodeError:
        return JSONResponse(
            content={"error": {"message": "invalid JSON body",
                               "type": "invalid_request_error"}},
            status_code=400,
        )

    streaming = bool(body.get("stream", False))
    headers = {k: v for k, v in request.headers.items()
               if k.lower() in ("authorization", "content-type", "accept")}
    headers.setdefault("Content-Type", "application/json")

    if streaming:
        async def _stream() -> AsyncGenerator[bytes, None]:
            client = await _get_client()
            async with client.stream(
                "POST", f"{BACKEND}/chat/completions",
                content=body_bytes, headers=headers,
            ) as r:
                async for chunk in r.aiter_bytes():
                    if chunk:
                        yield chunk
        return StreamingResponse(_stream(), media_type="text/event-stream")

    # Non-streaming: simple JSON roundtrip. Robust to backends that
    # return SSE chunks even when stream=false was requested
    # (operator-observed 2026-05-18: hermes returned a stream body
    # against a stream=false req and the strict r.json() blew up
    # with JSONDecodeError on the empty/event-stream payload).
    client = await _get_client()
    try:
        r = await client.post(
            f"{BACKEND}/chat/completions",
            content=body_bytes, headers=headers,
        )
        # Try strict JSON first; if it fails, pass the raw text + status
        # through. Forwarding the backend status preserves error info.
        try:
            return JSONResponse(content=r.json(), status_code=r.status_code)
        except (json.JSONDecodeError, ValueError):
            return JSONResponse(
                content={
                    "error": {
                        "message": "backend returned non-JSON response",
                        "type": "backend_non_json",
                        "backend_status": r.status_code,
                        "backend_preview": (r.text or "")[:500],
                    }
                },
                status_code=502,
            )
    except httpx.HTTPError as e:
        log.warning("chat/completions proxy failed: %s", e)
        return JSONResponse(
            content={"error": {"message": str(e), "type": "backend_error"}},
            status_code=502,
        )


# ── Entry point ────────────────────────────────────────────────────
def main() -> int:
    log.info("starting on :%d -> backend=%s model=%s",
             PORT, BACKEND, BACKEND_MODEL)
    # uvicorn.run() is blocking; the systemd unit takes care of
    # restart-on-failure.
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="info",
        access_log=False,    # noisy; the SurrealDB writes are the audit trail
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
