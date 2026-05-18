"""'MiOS' Agent Pipe -- standalone FastAPI service.

Step 2 of the migration: ports the router + dispatch + SurrealDB
writes from the OWUI Pipe class into this gateway-agnostic service.

Operator directive 2026-05-18: "mios discord chats not going through
MiOS-Agent(OWUI) paths when contacting through discord (uses only
MiOS-Hermes and doesn't have the same tool understanding and
environments details now!!!!)"

Architecture:

  OWUI                     ──┐
  Hermes Discord gateway   ──┼──> :8640 (this service)
  future Slack/Telegram    ──┘        │
                                       ▼
                              :8642 (hermes-agent)
                                       │
                                       ▼
                              ollama (raw inference)

Endpoints:
  GET  /health                  -> {status, version, backend, port}
  POST /v1/chat/completions     -> Router-classified chain:
                                     action=dispatch -> verb via broker
                                                       -> tool_call envelope
                                     action=chat    -> short-reply
                                     action=agent   -> proxy to backend
                                     (no verdict)   -> proxy to backend
  GET  /v1/models               -> proxy to MIOS_AGENT_PIPE_BACKEND
  POST /v1/embeddings           -> proxy to MIOS_AGENT_PIPE_BACKEND

Per the SSOT chain: every operator-tunable constant sources from
mios.toml -> userenv.sh -> MIOS_* env -> os.environ.get() with
sensible fallbacks. No hardcoded literals.

Skipped vs. the OWUI Pipe (deliberate for this commit; can be Step
2b if Discord needs them):
  * REFINE pass (CPU-LLM rewrite of the user message before forward)
  * CRITIC pass (post-backend verification + re-compose loop)
  * POLISH pass (final-answer cleanup)
  * NARRATION COLLAPSE (OWUI <think> wrapping)
These are quality-bonus features that add latency without changing
the tool-understanding parity Discord needs. They can be ported in
follow-up commits guided by operator feedback.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import shlex
import socket as _socket
import sys
import time
import uuid
from typing import Any, AsyncGenerator, Optional

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

# Router (layer-1 micro-LLM classifier) config.
ROUTER_ENABLED = os.environ.get("MIOS_AGENT_PIPE_ROUTER_ENABLED",
                                "true").lower() not in {"false", "0", "no"}
ROUTER_MODEL = os.environ.get("MIOS_AGENT_PIPE_ROUTER_MODEL", "qwen3:1.7b")
ROUTER_ENDPOINT = os.environ.get(
    "MIOS_AGENT_PIPE_ROUTER_ENDPOINT", "http://localhost:11434"
).rstrip("/")
ROUTER_TIMEOUT_S = int(os.environ.get("MIOS_AGENT_PIPE_ROUTER_TIMEOUT_S", "12"))
ROUTER_MAX_TOKENS = int(os.environ.get("MIOS_AGENT_PIPE_ROUTER_MAX_TOKENS", "200"))

# Launcher broker (unix socket) -- where dispatch verbs run.
LAUNCHER_SOCK = os.environ.get(
    "MIOS_LAUNCHER_SOCK", "/run/mios-launcher/launcher.sock",
)

# ── SurrealDB (cross-cutting agent state) ──────────────────────────
DB_URL = os.environ.get("MIOS_DB_URL", "http://localhost:8000")
DB_USER = os.environ.get("MIOS_DB_USER", "root")
DB_PASS = os.environ.get("MIOS_DB_PASS", "root")
DB_NS = os.environ.get("MIOS_DB_NS", "mios")
DB_DB = os.environ.get("MIOS_DB_DB", "mios")
_DB_AUTH = "Basic " + base64.b64encode(f"{DB_USER}:{DB_PASS}".encode()).decode()
_DB_DOWN_UNTIL: float = 0.0

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
    version="0.2.0",
    description=(
        "Gateway-agnostic router + dispatch + SurrealDB-state chain "
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


# ── SurrealDB writer (port of the OWUI pipe helpers) ───────────────
async def _db_post(sql: str, *, timeout: float = 3.0) -> Optional[list]:
    """Best-effort SurrealDB write/query. Returns the parsed list of
    per-statement results, or None on any error. A 30s backoff after
    each failure prevents per-turn retry storms when the DB is down."""
    global _DB_DOWN_UNTIL
    if not sql or not sql.strip():
        return None
    if time.time() < _DB_DOWN_UNTIL:
        return None
    body = (f"USE NS {DB_NS} DB {DB_DB}; " + sql).encode()
    try:
        async with httpx.AsyncClient(timeout=timeout) as s:
            r = await s.post(
                f"{DB_URL}/sql",
                content=body,
                headers={
                    "Authorization": _DB_AUTH,
                    "Accept": "application/json",
                },
            )
            if r.status_code != 200:
                _DB_DOWN_UNTIL = time.time() + 30
                return None
            return r.json()
    except Exception:
        _DB_DOWN_UNTIL = time.time() + 30
        return None


def _db_create(table: str, fields: dict, *,
               now_fields: tuple = (),
               extra: str = "") -> str:
    """Build `CREATE <table> SET ...` with time::now() for datetime
    fields. SurrealDB 3.0+ rejects plain ISO-Z strings for TYPE
    datetime; canonical pattern is `field = time::now()` literal."""
    parts = [f"{k} = time::now()" for k in now_fields]
    for k, v in fields.items():
        if k in now_fields or v is None:
            continue
        parts.append(f"{k} = {json.dumps(v, default=str)}")
    sql = f"CREATE {table} SET " + ", ".join(parts)
    if extra:
        sql += " " + extra
    return sql + ";"


def _db_fire(coro) -> None:
    """Schedule a DB coroutine fire-and-forget. Streaming responses
    are never delayed by DB writes."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(coro)


# ── Router system prompt (kept in lockstep with the OWUI pipe) ─────
# IMPORTANT: this verb table MUST stay synchronized with the OWUI
# Pipe class's _ROUTER_SYSTEM. Either side advertising verbs the
# other doesn't dispatch causes silent failures. Future Step 2b can
# move the table to a shared yaml file both sides load.
_ROUTER_SYSTEM = (
    "You are the MiOS router (Agentic-OS layer 1). Classify the "
    "user prompt into ONE of three actions and emit JSON ONLY.\n"
    "\n"
    "Actions:\n"
    '  "dispatch": the prompt maps to ONE MiOS verb call. Emit\n'
    '              {"action":"dispatch","tool":"<name>",'
    '"args":{...},"reason":"<short>"}\n'
    '  "chat":     conversational (greeting/thanks/question with\n'
    '              no system effect). Emit\n'
    '              {"action":"chat","reply":"<your reply>"}\n'
    '  "agent":    multi-step / research / unclear / needs\n'
    '              several tools. Emit\n'
    '              {"action":"agent","reason":"<short>"}\n'
    "\n"
    "MiOS verbs available for dispatch. Each verb is tagged WRITE\n"
    "(causes a visible system effect) or READ (returns info only):\n"
    '  [WRITE] open_app(name, position="default", args?, monitor=0)\n'
    '          -- LAUNCH an app/program. Use for "open X" / "launch X" /\n'
    '             "start X" / "run X". position enum:\n'
    '             default / as-is / center / left / right / top /\n'
    '             bottom / top-left / top-right / bottom-left /\n'
    '             bottom-right / maximize\n'
    '  [WRITE] launch_app(name)                -- simpler launch, no position arg\n'
    '  [WRITE] focus_window(title, position="default")\n'
    '          -- bring an OPEN window to front + apply default golden+\n'
    '             16:10-centered geometry (same position enum as open_app).\n'
    '             pass position="as-is" to focus WITHOUT resizing.\n'
    '  [WRITE] move_window(title, position, monitor=0)\n'
    '  [WRITE] close_window(title, mode="graceful")   -- mode: graceful|force\n'
    '  [WRITE] open_url(url, browser?)         -- open a URL in a browser\n'
    '  [READ ] list_windows()                  -- list currently OPEN windows\n'
    '  [READ ] screen_layout()                 -- monitor geometry\n'
    '  [READ ] mios_find(name)                 -- resolve name -> path, no launch\n'
    '  [READ ] mios_apps(filter?)              -- INVENTORY of installed apps, no launch\n'
    '  [READ ] everything_search(query, limit=10, ext?)\n'
    '          -- Windows-side filesystem search via Voidtools Everything CLI.\n'
    '  [READ ] fs_search(query, limit=20, ext?, path?, type?)\n'
    '          -- Linux-side filesystem search (plocate -> locate -> find).\n'
    '  [READ ] system_status()\n'
    '  [READ ] service_status(name)\n'
    '          -- systemctl is-active + status snapshot for a Linux service.\n'
    '  [WRITE] service_restart(name)\n'
    '  [READ ] process_list(filter?, sort="rss", limit=20)\n'
    '  [READ ] container_status(name?)\n'
    '  [WRITE] container_restart(name)\n'
    "\n"
    "Verb-pick priority (most common cases first):\n"
    '  "open X" / "launch X" / "start X" / "run X"  -> open_app(name=X)\n'
    '  "close X"                                    -> close_window(title=X)\n'
    '  "focus X" / "bring X to front" / "switch to X" -> focus_window(title=X)\n'
    '  "move X to <pos>"                            -> move_window(title=X, position=<pos>)\n'
    '  "what apps are installed" / "list apps"      -> mios_apps()\n'
    '  "what windows are open"                      -> list_windows()\n'
    '  "go to <url>" / "visit <url>"                -> open_url(url=<url>)\n'
    "\n"
    "Rules:\n"
    "- `dispatch` only when ONE verb solves it.\n"
    "- A WRITE verb is the right pick whenever the user asks for a\n"
    "  system effect (open/close/focus/move). NEVER pick a READ verb\n"
    "  when the user clearly wants an effect.\n"
    "- Position defaults to \"default\" (golden+16:10 centered); set\n"
    "  explicitly only when the user named a side.\n"
    "- `chat` for greetings, thanks, one-sentence clarification.\n"
    "- `agent` for N>1 tools, web research, install, file editing,\n"
    "  general knowledge questions, conversational follow-through.\n"
    "  MiOS-Agent is both an Agentic-OS AND a generalized AI agent.\n"
    "- Mirror the user's language in `reply` fields.\n"
    "- Output JSON ONLY -- no preamble, no markdown, no commentary."
)


# ── Router (Layer-1 classifier) ────────────────────────────────────
async def classify_intent(user_text: str) -> Optional[dict]:
    """Call the micro-LLM router. Returns the parsed verdict dict
    or None to fall through to backend proxy. Best-effort: any error
    falls through cleanly."""
    if not ROUTER_ENABLED or not user_text or not user_text.strip():
        return None
    payload = {
        "model": ROUTER_MODEL,
        "messages": [
            {"role": "system", "content": _ROUTER_SYSTEM},
            {"role": "user",   "content": user_text[:2000]},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.0,
        "max_tokens": ROUTER_MAX_TOKENS,
        "stream": False,
    }
    url = f"{ROUTER_ENDPOINT}/v1/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=ROUTER_TIMEOUT_S) as s:
            r = await s.post(url, json=payload,
                             headers={"Content-Type": "application/json"})
            if r.status_code != 200:
                return None
            body = r.json()
    except (httpx.HTTPError, asyncio.TimeoutError):
        return None
    except Exception as e:
        log.warning("router unexpected error: %s", e)
        return None
    choices = body.get("choices") or []
    if not choices:
        return None
    content = ((choices[0].get("message") or {}).get("content") or "").strip()
    if not content:
        return None
    content = re.sub(r"^\s*```(?:json)?\s*\n?", "", content)
    content = re.sub(r"\n?```\s*$", "", content)
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict) or "action" not in parsed:
        return None
    # Best-effort SurrealDB event row for the router verdict.
    _db_fire(_db_post(_db_create("event", {
        "source": "mios-agent-pipe",
        "kind": "classify",
        "severity": "info",
        "summary": str(parsed.get("action", "?"))[:120],
        "payload": parsed,
    }, now_fields=("ts",))))
    return parsed


# ── Dispatch (broker socket bridge) ────────────────────────────────
def _build_dispatch_cmd(tool: str, args: dict) -> Optional[str]:
    """Map verb name + args -> the bash command line the launcher
    broker executes. Kept in lockstep with the OWUI pipe's
    _dispatch_mios_verb. Returns None for unknown verbs."""
    env_prefix = ""
    if tool == "open_app":
        name = str(args.get("name", "")).strip()
        position = str(args.get("position", "default")).lower()
        extra_args = args.get("args") or []
        if position and position != "as-is":
            env_prefix = f"MIOS_LAUNCH_POSITION={shlex.quote(position)} "
        if extra_args:
            ea = " ".join(shlex.quote(str(a)) for a in extra_args)
            return f"{env_prefix}mios-windows launch {shlex.quote(name)} {ea}"
        return f"{env_prefix}mios-launch {shlex.quote(name)}"
    if tool == "launch_app":
        return f"mios-launch {shlex.quote(str(args.get('name', '')))}"
    if tool == "focus_window":
        title = shlex.quote(str(args.get("title", "")))
        pos = str(args.get("position", "default")).lower()
        if pos == "as-is":
            return f"mios-window focus {title}"
        return (
            f"mios-window focus {title} && "
            f"MIOS_LAUNCH_POSITION={shlex.quote(pos)} "
            f"mios-window {shlex.quote(pos)} {title}"
        )
    if tool == "move_window":
        title = shlex.quote(str(args.get("title", "")))
        pos = shlex.quote(str(args.get("position", "center")))
        return f"mios-window {pos} {title}"
    if tool == "close_window":
        title = shlex.quote(str(args.get("title", "")))
        mode = "kill" if str(args.get("mode", "graceful")) == "force" else "close"
        return f"mios-window {mode} {title}"
    if tool == "list_windows":
        return "mios-pc-control window-list"
    if tool == "screen_layout":
        return "mios-pc-control screen-layout"
    if tool == "open_url":
        url = shlex.quote(str(args.get("url", "")))
        browser = args.get("browser") or ""
        return f"mios-open-url {url}" + (
            f" {shlex.quote(str(browser))}" if browser else "")
    if tool == "mios_find":
        return f"mios-find {shlex.quote(str(args.get('name', '')))}"
    if tool == "mios_apps":
        f = args.get("filter") or ""
        return "mios-apps" + (f" --filter {shlex.quote(str(f))}" if f else "")
    if tool == "everything_search":
        q = shlex.quote(str(args.get("query", "")))
        n = int(args.get("limit", 10))
        ext = args.get("ext") or ""
        cmd = f"mios-everything -n {n} {q}"
        if ext:
            cmd += f" -ext {shlex.quote(str(ext))}"
        return cmd
    if tool == "fs_search":
        q = shlex.quote(str(args.get("query", "")))
        n = int(args.get("limit", 20))
        ext = args.get("ext") or ""
        path = args.get("path") or ""
        type_filter = args.get("type") or ""
        cmd = f"mios-locate -n {n} {q}"
        if ext:
            cmd += f" -ext {shlex.quote(str(ext))}"
        if path:
            cmd += f" -path {shlex.quote(str(path))}"
        if type_filter in ("f", "d"):
            cmd += f" -type {type_filter}"
        return cmd
    if tool == "system_status":
        return "mios-system-status"
    if tool == "service_status":
        name = shlex.quote(str(args.get("name", "")))
        return (
            f"echo \"=== is-active ===\"; systemctl is-active {name}; "
            f"echo; echo \"=== status ===\"; "
            f"systemctl --no-pager status {name} | head -20"
        )
    if tool == "service_restart":
        name = shlex.quote(str(args.get("name", "")))
        return (
            f"systemctl restart {name} && "
            f"echo \"restarted; is-active=$(systemctl is-active {name})\""
        )
    if tool == "process_list":
        limit = int(args.get("limit", 20))
        sort = str(args.get("sort", "rss")).lower()
        sort_arg = "--sort=-pcpu" if sort == "cpu" else "--sort=-rss"
        filt = str(args.get("filter", "")).strip()
        base = f"ps -eo pid,user,rss,pcpu,comm,args {sort_arg} --no-headers"
        if filt:
            base += f" | grep -i -- {shlex.quote(filt)}"
        return f"{base} | head -{limit}"
    if tool == "container_status":
        filt = str(args.get("name", "")).strip()
        base = "podman ps -a --format '{{.Names}}\\t{{.Status}}\\t{{.Image}}'"
        if filt:
            base += f" | grep -i -- {shlex.quote(filt)}"
        return base
    if tool == "container_restart":
        name = shlex.quote(str(args.get("name", "")))
        return (
            f"podman restart {name} && "
            f"podman ps --filter name={name} "
            f"--format '{{.Names}}\\t{{.Status}}'"
        )
    return None


async def dispatch_mios_verb(tool: str, args: dict) -> dict:
    """Run a single MiOS verb via the launcher broker (unix socket
    /run/mios-launcher/launcher.sock). Returns a structured dict:
    {success, tool, args, output, stderr, exit_code, latency_ms}.
    Uses the broker's CAPTURE_JSON: protocol so stdout/stderr split
    cleanly (operator's "no English in tool_result.output" rule)."""
    cmd = _build_dispatch_cmd(tool, args)
    if cmd is None:
        return {
            "success": False, "tool": tool, "args": args,
            "output": "", "stderr": f"unknown verb {tool!r}",
            "exit_code": -1, "latency_ms": 0,
        }
    if not os.path.exists(LAUNCHER_SOCK):
        return {
            "success": False, "tool": tool, "args": args,
            "output": "", "stderr": f"broker socket missing at {LAUNCHER_SOCK}",
            "exit_code": -1, "latency_ms": 0,
        }
    t0 = time.time()
    try:
        s = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
        s.settimeout(20.0)
        s.connect(LAUNCHER_SOCK)
        s.sendall(("CAPTURE_JSON: " + cmd + "\n").encode())
        chunks: list[bytes] = []
        try:
            while True:
                buf = s.recv(65536)
                if not buf:
                    break
                chunks.append(buf)
        except _socket.timeout:
            pass
        finally:
            s.close()
        raw = b"".join(chunks).decode("utf-8", errors="replace").strip()
        try:
            j = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            j = {}
        latency_ms = int((time.time() - t0) * 1000)
        if not j:
            return {
                "success": False, "tool": tool, "args": args,
                "output": "", "stderr": raw or "broker: empty response",
                "exit_code": -1, "latency_ms": latency_ms,
            }
        exit_code = int(j.get("exit_code", -1))
        return {
            "success": exit_code == 0,
            "tool": tool, "args": args,
            "output": (j.get("stdout") or "")[:6000],
            "stderr": (j.get("stderr") or "")[:2000],
            "exit_code": exit_code,
            "latency_ms": latency_ms,
        }
    except OSError as e:
        return {
            "success": False, "tool": tool, "args": args,
            "output": "", "stderr": f"broker: {e}",
            "exit_code": -1,
            "latency_ms": int((time.time() - t0) * 1000),
        }


# ── SSE chunk builders ─────────────────────────────────────────────
# Encode chat completion deltas in the OpenAI streaming protocol so
# any gateway (OWUI, Hermes Discord, Slack/Telegram, ...) consumes
# the response with its existing OpenAI client. The dispatch fast-
# path emits a single delta containing the structured tool_calls
# envelope as content (rendered as a <details type="tool_calls">
# block markdown can collapse natively).

def _sse_chunk(content: str, *, chat_id: str, model: str,
               role: Optional[str] = None,
               finish_reason: Optional[str] = None,
               mios_status: Optional[dict] = None) -> bytes:
    """Build an OpenAI-streaming SSE chunk. Optional `mios_status`
    field carries pipe-internal phase emits (📡 prompt, 🧭 route,
    🛠️ {tool}, ✅) that translator gateways (OWUI shim, Hermes
    Discord) lift into their native status surfaces. Stock OpenAI
    clients see this as an unknown field and ignore it -- graceful
    degradation."""
    delta: dict[str, Any] = {}
    if role:
        delta["role"] = role
    if content is not None:
        delta["content"] = content
    chunk = {
        "id": chat_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "delta": delta,
            "finish_reason": finish_reason,
        }],
    }
    if mios_status:
        chunk["mios_status"] = mios_status
    return ("data: " + json.dumps(chunk) + "\n\n").encode("utf-8")


def _sse_status(*, chat_id: str, model: str, emoji: str, label: str,
                done: bool = False) -> bytes:
    """Emit a content-empty SSE chunk whose only purpose is the
    `mios_status` field. Standard OpenAI clients see a no-op delta
    + ignore the extra field. Translator gateways pull the phase
    info from `mios_status` and surface it natively (OWUI's
    event_emitter status, Hermes Discord's reactions, etc.)."""
    return _sse_chunk(
        "", chat_id=chat_id, model=model,
        mios_status={"emoji": emoji, "label": label, "done": done},
    )


def _sse_done() -> bytes:
    return b"data: [DONE]\n\n"


# ── Last-user-message extraction ───────────────────────────────────
def _extract_last_user_text(messages: list) -> str:
    for i in range(len(messages) - 1, -1, -1):
        m = messages[i]
        if not isinstance(m, dict):
            continue
        if m.get("role") != "user":
            continue
        c = m.get("content") or ""
        if isinstance(c, list):
            for part in c:
                if isinstance(part, dict) and part.get("type") == "text":
                    return part.get("text", "")
            return ""
        return c if isinstance(c, str) else ""
    return ""


# ── Health ─────────────────────────────────────────────────────────
@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": app.version,
        "backend": BACKEND,
        "backend_model": BACKEND_MODEL,
        "router": {
            "enabled": ROUTER_ENABLED,
            "model": ROUTER_MODEL,
            "endpoint": ROUTER_ENDPOINT,
        },
        "broker_sock": LAUNCHER_SOCK,
        "broker_present": os.path.exists(LAUNCHER_SOCK),
        "db_url": DB_URL,
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


# ── /v1/chat/completions (the chain) ───────────────────────────────
@app.post("/v1/chat/completions")
async def chat_completions(request: Request) -> Any:
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
    messages = body.get("messages") or []
    last_user_text = _extract_last_user_text(messages)
    model = body.get("model") or BACKEND_MODEL
    chat_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"

    # SurrealDB session row -- fire-and-forget; the record id (if
    # the write completes in time) is captured for downstream
    # tool_call rows. Misses are tolerable -- the chain still works
    # if SurrealDB is down (the SurrealDB writer has a 30s backoff).
    session_id: Optional[str] = None
    try:
        resp = await _db_post(_db_create(
            "session",
            {"platform": "mios-agent-pipe",
             "model": model},
            now_fields=("started_at",),
            extra="RETURN id",
        ))
        if isinstance(resp, list) and resp:
            last = resp[-1] or {}
            rows = last.get("result") or []
            if isinstance(rows, list) and rows:
                rid = rows[0].get("id")
                if rid:
                    session_id = str(rid)
    except Exception as e:
        log.debug("session open failed: %s", e)

    # Run the layer-1 router. Verdict possibilities:
    #   {"action":"dispatch","tool":"<name>","args":{...}}
    #   {"action":"chat","reply":"<text>"}
    #   {"action":"agent","reason":"..."}
    verdict = await classify_intent(last_user_text)

    if verdict:
        action = verdict.get("action")

        # ── DISPATCH fast-path ──────────────────────────────────
        if action == "dispatch":
            tool = str(verdict.get("tool", "")).strip()
            args = verdict.get("args") or {}
            if tool:
                result = await dispatch_mios_verb(
                    tool, args if isinstance(args, dict) else {},
                )
                ok = bool(result.get("success"))
                # SurrealDB tool_call row -- write fire-and-forget.
                _row = {
                    "tool": tool,
                    "args": args if isinstance(args, dict) else {},
                    "result_preview": (result.get("output") or "")[:500],
                    "success": ok,
                    "latency_ms": int(result.get("latency_ms", 0)),
                }
                if session_id:
                    _db_fire(_db_post(
                        _db_create("tool_call", _row, now_fields=("ts",)).rstrip(";")
                        + f", session = {session_id};"
                    ))
                else:
                    _db_fire(_db_post(
                        _db_create("tool_call", _row, now_fields=("ts",))
                    ))
                # Build the tool_calls envelope (OpenAI-spec-shaped
                # tool_call + tool_result wrapped in <details> so
                # gateways with markdown rendering get a collapsible
                # block + agents reading the chat history see the
                # canonical structured shape).
                envelope = {
                    "tool_call": {
                        "id": f"call_{int(time.time()*1000)}",
                        "type": "function",
                        "function": {
                            "name": tool,
                            "arguments": args if isinstance(args, dict) else {},
                        },
                    },
                    "tool_result": {
                        "success": ok,
                        "output": (result.get("output") or "")[:2000],
                        "stderr": (result.get("stderr") or "")[:2000],
                        "exit_code": int(result.get("exit_code", -1)),
                    },
                }
                symbol = "✅" if ok else "⚠️"
                rendered = (
                    f"<details type=\"tool_calls\" done=\"true\">\n"
                    f"<summary>{symbol} `{tool}`</summary>\n\n"
                    f"```json\n{json.dumps(envelope, indent=2, default=str)}\n```\n"
                    f"</details>"
                )
                if streaming:
                    async def _stream_dispatch() -> AsyncGenerator[bytes, None]:
                        # Phase markers: prompt -> route -> tool -> done.
                        # Translator gateways pull the emoji/label from
                        # `mios_status` and surface natively (OWUI status
                        # event_emitter, Discord reactions, etc.).
                        yield _sse_status(chat_id=chat_id, model=model,
                                          emoji="📡", label="prompt")
                        yield _sse_status(chat_id=chat_id, model=model,
                                          emoji="🧭", label="route")
                        yield _sse_status(chat_id=chat_id, model=model,
                                          emoji="🛠️", label=tool)
                        yield _sse_chunk("", chat_id=chat_id, model=model,
                                         role="assistant")
                        yield _sse_chunk(rendered, chat_id=chat_id, model=model)
                        yield _sse_status(chat_id=chat_id, model=model,
                                          emoji="✅" if ok else "⚠️",
                                          label=tool, done=True)
                        yield _sse_chunk("", chat_id=chat_id, model=model,
                                         finish_reason="stop")
                        yield _sse_done()
                    return StreamingResponse(_stream_dispatch(),
                                             media_type="text/event-stream")
                # Non-streaming response.
                return JSONResponse(content={
                    "id": chat_id,
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "message": {"role": "assistant", "content": rendered},
                        "finish_reason": "stop",
                    }],
                })

        # ── CHAT fast-path (one-line conversational reply) ──────
        if action == "chat":
            reply = str(verdict.get("reply", "")).strip()
            if reply:
                if streaming:
                    async def _stream_chat() -> AsyncGenerator[bytes, None]:
                        yield _sse_status(chat_id=chat_id, model=model,
                                          emoji="📡", label="prompt")
                        yield _sse_status(chat_id=chat_id, model=model,
                                          emoji="🧭", label="route")
                        yield _sse_chunk("", chat_id=chat_id, model=model,
                                         role="assistant")
                        yield _sse_chunk(reply, chat_id=chat_id, model=model)
                        yield _sse_status(chat_id=chat_id, model=model,
                                          emoji="✅", label="chat", done=True)
                        yield _sse_chunk("", chat_id=chat_id, model=model,
                                         finish_reason="stop")
                        yield _sse_done()
                    return StreamingResponse(_stream_chat(),
                                             media_type="text/event-stream")
                return JSONResponse(content={
                    "id": chat_id,
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "message": {"role": "assistant", "content": reply},
                        "finish_reason": "stop",
                    }],
                })

        # action == "agent" or unrecognized -> fall through to backend.

    # ── AGENT path / fallback -> proxy to backend ──────────────
    headers = {k: v for k, v in request.headers.items()
               if k.lower() in ("authorization", "content-type", "accept")}
    headers.setdefault("Content-Type", "application/json")
    if streaming:
        async def _stream_backend() -> AsyncGenerator[bytes, None]:
            # Phase markers BEFORE the backend stream so the OWUI shim
            # / Discord reactions know the pipe handed off to hermes.
            # The backend's own content chunks pass through unchanged
            # (no mios_status injected mid-stream -- the backend may
            # emit its own tool-call status via tail_watcher or its
            # internal mechanism).
            yield _sse_status(chat_id=chat_id, model=model,
                              emoji="📡", label="prompt")
            yield _sse_status(chat_id=chat_id, model=model,
                              emoji="🧭", label="route")
            yield _sse_status(chat_id=chat_id, model=model,
                              emoji="🧠", label="→ hermes")
            client = await _get_client()
            async with client.stream(
                "POST", f"{BACKEND}/chat/completions",
                content=body_bytes, headers=headers,
            ) as r:
                async for chunk in r.aiter_bytes():
                    if chunk:
                        yield chunk
        return StreamingResponse(_stream_backend(),
                                 media_type="text/event-stream")
    client = await _get_client()
    try:
        r = await client.post(
            f"{BACKEND}/chat/completions",
            content=body_bytes, headers=headers,
        )
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
        log.warning("chat/completions backend proxy failed: %s", e)
        return JSONResponse(
            content={"error": {"message": str(e), "type": "backend_error"}},
            status_code=502,
        )


# ── Entry point ────────────────────────────────────────────────────
def main() -> int:
    log.info("starting on :%d -> backend=%s model=%s "
             "router_enabled=%s router_model=%s",
             PORT, BACKEND, BACKEND_MODEL,
             ROUTER_ENABLED, ROUTER_MODEL)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="info",
        access_log=False,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
