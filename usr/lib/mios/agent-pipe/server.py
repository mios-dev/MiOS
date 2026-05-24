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
import collections
import contextvars
import glob
import json
import logging
import os
import random
import re
import shlex
import socket as _socket
import sys
import time
import uuid
from typing import Any, AsyncGenerator, Optional

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import (HTMLResponse, JSONResponse, Response,
                               StreamingResponse)
import uvicorn

# ── Config (SSOT-sourced via env) ──────────────────────────────────
PORT = int(os.environ.get("MIOS_PORT_AGENT_PIPE", "8640"))
BACKEND = os.environ.get("MIOS_AGENT_PIPE_BACKEND",
                         "http://localhost:8642/v1").rstrip("/")
BACKEND_MODEL = os.environ.get("MIOS_AGENT_PIPE_BACKEND_MODEL",
                               "hermes-agent")

# Micro-LLM (SSOT: mios.toml [ai].micro_model / micro_endpoint, surfaced
# as MIOS_MICRO_MODEL / MIOS_MICRO_ENDPOINT by userenv.sh). This is the
# always-warm (keep_alive=-1) sub-second classifier -- qwen3:0.6b-cpu by
# default. Operator directive 2026-05-20: "we have access to micro-llms
# for fast refinements too" -- so the layer-1 classifier passes (router +
# refine) default to the micro-LLM instead of the heavier qwen3:1.7b that
# was stalling 13-45s on the CPU lane. The bigger PLANNER + POLISH passes
# keep their own (larger) models.
_MICRO_MODEL = os.environ.get("MIOS_MICRO_MODEL", "qwen3:0.6b-cpu")
_MICRO_ENDPOINT = os.environ.get(
    "MIOS_MICRO_ENDPOINT", "http://localhost:11434/v1",
).rstrip("/")
# Callers below append "/v1/chat/completions"; strip a trailing /v1 so we
# don't double it.
_MICRO_BASE = (_MICRO_ENDPOINT[:-3].rstrip("/")
               if _MICRO_ENDPOINT.endswith("/v1") else _MICRO_ENDPOINT)

# Web-search cross-agent concurrency bound (operator 2026-05-22: "SearXNG
# setup to handle the load -- buffer/queue or delayed starts for multi-agent
# dispatches"). When a council/DAG fans out, several agents can call
# web_search at once, and each expands into MIOS_WEB_FANOUT concurrent
# sub-queries -- a thundering herd at the local SearXNG. A global semaphore
# (bulkhead) caps how many web_search dispatches run concurrently; excess
# ones QUEUE on it (the "buffer"). A tiny pre-acquire jitter desynchronises
# simultaneous starts (the "delayed starts"). Total concurrent SearXNG
# queries stay ~= MIOS_WEB_CONCURRENCY * MIOS_WEB_FANOUT.
WEB_CONCURRENCY = int(os.environ.get("MIOS_WEB_CONCURRENCY", "3"))
WEB_DISPATCH_JITTER_S = float(os.environ.get("MIOS_WEB_DISPATCH_JITTER_S", "0.15"))
_web_sem = asyncio.Semaphore(max(1, WEB_CONCURRENCY))
# Cap on CONCURRENTLY-dispatched agents (operator 2026-05-23 "not all agents at
# the same time -- reasonable limit/cap"). Council secondaries + DAG-level
# nodes share this semaphore via _call_agent_complete, so the swarm engages at
# most N agents at once; the rest queue. Also protects the shared model lanes /
# search engines from being overrun (the same burst that degraded web search).
AGENT_CONCURRENCY = int(os.environ.get("MIOS_AGENT_CONCURRENCY", "3"))
_agent_sem = asyncio.Semaphore(max(1, AGENT_CONCURRENCY))

# Router (layer-1 micro-LLM classifier) config.
ROUTER_ENABLED = os.environ.get("MIOS_AGENT_PIPE_ROUTER_ENABLED",
                                "true").lower() not in {"false", "0", "no"}
ROUTER_MODEL = os.environ.get("MIOS_AGENT_PIPE_ROUTER_MODEL", _MICRO_MODEL)
# Router runs the micro-LLM classifier (qwen3:1.7b) on the iGPU lane
# (mios-ollama-igpu at :11435) -- isolates micro-LLM workload from the
# dGPU/CUDA queue so router latency stays sub-second even when big-model
# inference is saturating :11434. Falls back to the CUDA-ollama lane
# if the iGPU instance is down (operator override via the env).
# Light lane (:11435) -- the iGPU/CPU micro-LLM instance, ISOLATED from
# the :11434 big-model queue. Refine/router/polish MUST run here: putting
# the micro classifier on :11434 (operator test 2026-05-20) queued it
# behind big-model inference -> refine 41s, polish 42s. On the light lane
# the warm qwen3:0.6b-cpu answers in ~1-2s regardless of dGPU load.
_LIGHT_LANE = os.environ.get("MIOS_OLLAMA_IGPU_ENDPOINT",
                             "http://localhost:11435").rstrip("/")
ROUTER_ENDPOINT = os.environ.get(
    "MIOS_AGENT_PIPE_ROUTER_ENDPOINT", _LIGHT_LANE
).rstrip("/")
ROUTER_TIMEOUT_S = int(os.environ.get("MIOS_AGENT_PIPE_ROUTER_TIMEOUT_S", "30"))
ROUTER_MAX_TOKENS = int(os.environ.get("MIOS_AGENT_PIPE_ROUTER_MAX_TOKENS", "200"))

# Planner (Phase A.1 -- DAG query decomposition) config. The planner is
# function-calling-tuned + larger than the router; it emits a DAG of
# dispatch verbs when the router classifies a multi-step intent.
# Defaults to qwen2.5-coder:7b on the dGPU/CUDA lane (:11434) -- it
# needs the bigger context + reasoning headroom. Operator can disable
# planner via env (DAG-mode falls back to backend proxy).
PLANNER_ENABLED = os.environ.get(
    "MIOS_AGENT_PIPE_PLANNER_ENABLED", "true",
).lower() not in {"false", "0", "no"}
PLANNER_MODEL = os.environ.get(
    "MIOS_AGENT_PIPE_PLANNER_MODEL", "qwen2.5-coder:7b",
)
PLANNER_ENDPOINT = os.environ.get(
    "MIOS_AGENT_PIPE_PLANNER_ENDPOINT", "http://localhost:11434",
).rstrip("/")
# Decompose substantive single-goal asks into a CONCURRENT multi-agent swarm
# by DEFAULT (operator 2026-05-22: "decompose into sub-tasks" as the default
# swarm mode). For an agent-intent query of >= MIN_WORDS, attempt _plan_swarm:
# if it splits into >=2 independent sub-tasks, they run on DIFFERENT agents /
# lanes concurrently (real division of labour -- the CPU lane does its OWN
# sub-task, not a duplicate) and get synthesised. If the ask is not worth
# splitting, _plan_swarm returns [] and the normal council path handles it, so
# this never hurts trivial queries. MIN_WORDS keeps short ACTION verbs ("open
# steam") off the extra planner call.
# DEFAULT FALSE (operator 2026-05-23 "swarm from first operations / not just
# Hermes"): a plain substantive query should hit the ALL-NODES council first
# (every node weighs in), NOT get pre-split into a thin decompose DAG that
# collapses to 1-2 agents. Decompose still fires for EXPLICIT multi-goal asks
# (refine intent=multi_task), the 🧩 delegate toggle (force_delegate), and
# refine's _multi_step flag -- just not by default on every substantive turn.
SWARM_DECOMPOSE_DEFAULT = os.environ.get(
    "MIOS_SWARM_DECOMPOSE_DEFAULT", "false").lower() not in {"false", "0", "no"}
SWARM_DECOMPOSE_MIN_WORDS = int(
    os.environ.get("MIOS_SWARM_DECOMPOSE_MIN_WORDS", "6"))
# Swarm DECOMPOSER model (operator 2026-05-22). A general 4b instruct model
# via /api/chat (think=False) -- NOT the code model on /v1, which returned
# EMPTY content on the full agent roster. Warm (keep_alive, shared lane).
SWARM_MODEL = os.environ.get("MIOS_SWARM_MODEL", "qwen3.5:4b")
PLANNER_TIMEOUT_S = int(os.environ.get(
    "MIOS_AGENT_PIPE_PLANNER_TIMEOUT_S", "30"))
PLANNER_MAX_TOKENS = int(os.environ.get(
    "MIOS_AGENT_PIPE_PLANNER_MAX_TOKENS", "800"))
PLANNER_MAX_NODES = int(os.environ.get(
    "MIOS_AGENT_PIPE_PLANNER_MAX_NODES", "8"))
PLANNER_REFLEXION_CAP = int(os.environ.get(
    "MIOS_AGENT_PIPE_PLANNER_REFLEXION_CAP", "2"))

# Launcher broker (unix socket) -- where dispatch verbs run.
LAUNCHER_SOCK = os.environ.get(
    "MIOS_LAUNCHER_SOCK", "/run/mios-launcher/launcher.sock",
)

# Backend bearer key. Hermes (and other sub-agents) usually require
# Authorization: Bearer <key>. The OWUI gateway sends the operator's
# session token; direct callers (curl, MCP clients, future Slack/
# Telegram) won't. Loaded from MIOS_AGENT_PIPE_BACKEND_KEY env first,
# then /etc/mios/hermes/api.env's API_SERVER_KEY as the canonical
# fallback. Empty when neither is set -- the proxy still works for
# backends that don't enforce auth.
def _load_backend_key() -> str:
    env_key = os.environ.get("MIOS_AGENT_PIPE_BACKEND_KEY", "").strip()
    if env_key:
        return env_key
    try:
        with open("/etc/mios/hermes/api.env", "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("API_SERVER_KEY="):
                    return line.split("=", 1)[1].strip().strip('"')
    except (OSError, PermissionError):
        pass
    return ""


_BACKEND_KEY = _load_backend_key()

# ── SurrealDB (cross-cutting agent state) ──────────────────────────
DB_URL = os.environ.get("MIOS_DB_URL", "http://localhost:8000")
DB_USER = os.environ.get("MIOS_DB_USER", "root")
DB_PASS = os.environ.get("MIOS_DB_PASS", "root")
DB_NS = os.environ.get("MIOS_DB_NS", "mios")
DB_DB = os.environ.get("MIOS_DB_DB", "mios")
_DB_AUTH = "Basic " + base64.b64encode(f"{DB_USER}:{DB_PASS}".encode()).decode()

# ── Phase C.3 -- Agent Passport (Ed25519 signing) ─────────────────
# Each agent in the stack signs security-relevant SurrealDB writes
# with its Ed25519 private key so every tool_call / firewall_block
# event / skill_invocation row carries a tamper-evident attribution
# header. Verification is OFFLINE: any agent reads the signer's
# public key from /var/lib/mios/agent-passports/<agent>/public.key
# (world-readable) or the SurrealDB agent_keypair table -- no
# external KMS, no online CA.
#
# We import the mios-passport library helpers lazily so a fresh
# deployment without keypairs provisioned yet doesn't crash agent-
# pipe at import time. When ENABLE is true but the agent's private
# key isn't on disk, individual sign calls return None + log a
# warning -- the write still lands but unsigned (operator sees the
# missing-passport state in the configurator HTML "Passport"
# section).
PASSPORT_ENABLE = os.environ.get(
    "MIOS_PASSPORT_ENABLE", "true",
).lower() not in {"false", "0", "no"}
PASSPORT_ALGO = os.environ.get("MIOS_PASSPORT_ALGO", "ed25519")
PASSPORT_KEY_DIR = os.environ.get(
    "MIOS_PASSPORT_KEY_DIR", "/var/lib/mios/agent-passports")
PASSPORT_AGENT_NAME = os.environ.get(
    "MIOS_PASSPORT_AGENT_NAME", "agent-pipe")
PASSPORT_VERIFY_ON_READ = os.environ.get(
    "MIOS_PASSPORT_VERIFY_ON_READ", "false",
).lower() in {"true", "1", "yes"}

# Imported only when the helper is actually exercised so a host
# without python3-cryptography can still run agent-pipe with
# PASSPORT_ENABLE=false.
_passport_priv = None  # cached private key object
_passport_pub_cache: dict[str, Any] = {}
_passport_load_attempted = False


def _passport_canonical_json(obj) -> str:
    """Deterministic JSON encoding -- matches the mios-passport CLI
    exactly so a signature emitted by one path is verifiable by
    the other."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      default=str)


def _passport_op_hash(table: str, fields: dict) -> str:
    """SHA-256 of `table:canonical-json(fields-minus-passport)`.
    Identical algorithm to mios-passport CLI's op_hash so the two
    sides agree on what's being signed."""
    import hashlib
    payload = dict(fields or {})
    payload.pop("passport", None)
    canon = f"{table}:{_passport_canonical_json(payload)}"
    return "sha256:" + hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _passport_load_priv():
    """Best-effort load of this service's Ed25519 private key.
    Returns the key object on success; sets _passport_priv to a
    sentinel False on failure so we don't retry repeatedly."""
    global _passport_priv, _passport_load_attempted
    if _passport_load_attempted:
        return _passport_priv if _passport_priv else None
    _passport_load_attempted = True
    if not PASSPORT_ENABLE:
        _passport_priv = False
        return None
    try:
        from cryptography.hazmat.primitives import serialization
        path = os.path.join(
            PASSPORT_KEY_DIR, PASSPORT_AGENT_NAME, "private.key")
        with open(path, "rb") as f:
            _passport_priv = serialization.load_pem_private_key(
                f.read(), password=None)
        log.info(
            "passport: loaded private key for %s from %s",
            PASSPORT_AGENT_NAME, path)
        return _passport_priv
    except FileNotFoundError:
        log.warning(
            "passport: no private key at %s for agent %s -- "
            "writes will be unsigned until "
            "`mios-passport provision` runs",
            os.path.join(PASSPORT_KEY_DIR, PASSPORT_AGENT_NAME,
                         "private.key"),
            PASSPORT_AGENT_NAME)
        _passport_priv = False
        return None
    except Exception as e:
        log.warning("passport: failed to load private key: %s", e)
        _passport_priv = False
        return None


def _passport_kid() -> str:
    """Read this service's current kid. Defaults to <agent>-v1."""
    path = os.path.join(PASSPORT_KEY_DIR, PASSPORT_AGENT_NAME, "kid")
    try:
        with open(path) as f:
            kid = f.read().strip()
        return kid or f"{PASSPORT_AGENT_NAME}-v1"
    except Exception:
        return f"{PASSPORT_AGENT_NAME}-v1"


def _passport_load_public(agent: str):
    """Resolve an agent's public key. Filesystem first; SurrealDB
    agent_keypair row as the offline fallback so a verifier
    without filesystem access can still validate."""
    if agent in _passport_pub_cache:
        return _passport_pub_cache[agent]
    try:
        from cryptography.hazmat.primitives import serialization
        path = os.path.join(PASSPORT_KEY_DIR, agent, "public.key")
        with open(path, "rb") as f:
            key = serialization.load_pem_public_key(f.read())
        _passport_pub_cache[agent] = key
        return key
    except FileNotFoundError:
        pass
    except Exception as e:
        log.warning("passport: pub key load failed for %s: %s", agent, e)
    return None


def _passport_sign(table: str, fields: dict) -> Optional[dict]:
    """Return a passport envelope for a (table, fields) write, or
    None if signing is disabled / no key available. The envelope is
    safe to attach as `fields["passport"]` -- the op_hash is
    computed over `fields` WITHOUT the passport key (which would be
    circular), so the recipient re-derives the same hash."""
    if not PASSPORT_ENABLE:
        return None
    priv = _passport_load_priv()
    if not priv:
        return None
    try:
        h = _passport_op_hash(table, fields)
        nonce = base64.b64encode(os.urandom(16)).decode("ascii")
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        msg = f"{PASSPORT_AGENT_NAME}\n{ts}\n{nonce}\n{h}".encode("utf-8")
        sig = priv.sign(msg)
        return {
            "agent": PASSPORT_AGENT_NAME,
            "ts": ts,
            "nonce": nonce,
            "op_hash": h,
            "alg": PASSPORT_ALGO,
            "kid": _passport_kid(),
            "sig": base64.b64encode(sig).decode("ascii"),
        }
    except Exception as e:
        log.warning("passport: sign failed for %s: %s", table, e)
        return None


def _passport_verify(envelope: dict,
                     payload_for_hash: Optional[tuple] = None
                     ) -> tuple[bool, str]:
    """Verify a passport envelope. (table, fields) tuple in
    payload_for_hash binds the op_hash check. Same algorithm as
    mios-passport's verify_envelope."""
    if not isinstance(envelope, dict):
        return False, "envelope_not_dict"
    agent = envelope.get("agent")
    ts = envelope.get("ts")
    nonce = envelope.get("nonce")
    declared_hash = envelope.get("op_hash")
    sig_b64 = envelope.get("sig")
    alg = envelope.get("alg", "ed25519")
    if not all([agent, ts, nonce, declared_hash, sig_b64]):
        return False, "envelope_missing_field"
    if alg != "ed25519":
        return False, f"unsupported_alg:{alg}"
    if payload_for_hash is not None:
        table, fields = payload_for_hash
        recomputed = _passport_op_hash(table, fields)
        if recomputed != declared_hash:
            return False, "op_hash_mismatch"
    pub = _passport_load_public(agent)
    if pub is None:
        return False, f"no_public_key:{agent}"
    try:
        from cryptography.exceptions import InvalidSignature
        pub.verify(
            base64.b64decode(sig_b64),
            f"{agent}\n{ts}\n{nonce}\n{declared_hash}".encode("utf-8"),
        )
    except InvalidSignature:
        return False, "invalid_signature"
    except Exception as e:
        return False, f"verify_error:{e}"
    return True, "ok"
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


@app.on_event("startup")
async def _warm_embeddings_in_background() -> None:
    """Build verb + app embeddings as fire-and-forget Tasks at boot.
    First chat turn does NOT block on a 4-5s embed flood; instead the
    /v1/tool-search and /v1/app-search endpoints use substring
    fallback until the warmup completes. Disk-persisted embeddings
    survive restart -- subsequent boots are no-ops.
    Operator-flagged 2026-05-19 "double fail" (TransferEncodingError
    when polish path competed with embed flood on iGPU lane)."""
    async def _warm():
        try:
            await _ensure_verb_embeddings()
        except Exception as e:
            log.warning("verb embed warmup failed: %s", e)
        try:
            await _refresh_app_inventory()
        except Exception as e:
            log.warning("app inventory warmup failed: %s", e)
    asyncio.create_task(_warm())

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
               extra: str = "",
               passport_sign: bool = True) -> str:
    """Build `CREATE <table> SET ...` with time::now() for datetime
    fields. SurrealDB 3.0+ rejects plain ISO-Z strings for TYPE
    datetime; canonical pattern is `field = time::now()` literal.

    Phase C.3 -- when passport_sign=True (the default), attach an
    Ed25519 passport envelope to the record. The passport is
    computed over the canonical-JSON of `fields` (with the
    eventual time::now() values represented as the literal
    "time::now()" sentinel) so a verifier seeing the persisted
    row can re-derive the same op_hash. Failure to sign (key not
    provisioned, crypto error) drops the field silently -- the
    write still lands so security logging never blocks
    observability.

    Pass passport_sign=False to opt out for non-attribution writes
    where the envelope overhead isn't justified (currently: none
    -- every audit-relevant write benefits from attribution)."""
    if passport_sign:
        # Snapshot the fields the verifier will see (the time::now()
        # values get the literal sentinel because that's what the
        # CREATE statement encodes). Keep the order stable.
        hash_fields = {k: "time::now()" for k in now_fields}
        for k, v in fields.items():
            if k in now_fields or v is None:
                continue
            hash_fields[k] = v
        envelope = _passport_sign(table, hash_fields)
        if envelope is not None:
            fields = dict(fields)
            fields["passport"] = envelope
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
    '          -- SEMANTIC position: center / left / right / top-left etc.\n'
    '             For literal pixel coords use position_window(title, x, y).\n'
    '  [WRITE] position_window(title, x, y)\n'
    '          -- Move window to LITERAL (x,y) pixel coords. Use after\n'
    '             screen_layout when the agent has computed exact target.\n'
    '  [WRITE] resize_window(title, width, height)\n'
    '          -- Resize to literal pixel WxH (does NOT move).\n'
    '  [WRITE] minimize_window(title)\n'
    '          -- Hide to taskbar.\n'
    '  [WRITE] maximize_window(title)\n'
    '          -- Maximize to full screen of containing monitor.\n'
    '  [WRITE] restore_window(title)\n'
    '          -- Undo minimize/maximize: return to last normal-state\n'
    '             geometry.\n'
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
    '  [READ ] knowledge_search(query, collection?, top_k=5)\n'
    '          -- Query OWUI knowledge collections (RAG). Hits return\n'
    '             {score, source, snippet} for citation in the reply.\n'
    '             `collection` is a name or id; empty = search all.\n'
    '  [READ ] directory_lookup(query, root?, ext?, kind?, limit=20)\n'
    '          -- Sub-100ms filesystem search via mios-daemon\'s cached\n'
    '             map. Hits return {path, kind, size, mtime, summary,\n'
    '             root_label}. Use this FIRST for "where is foo" -\n'
    '             cheaper than mios-find / everything_search.\n'
    '  [READ ] system_status()\n'
    '  [READ ] service_status(name)\n'
    '          -- systemctl is-active + status snapshot for a Linux service.\n'
    '  [WRITE] service_restart(name)\n'
    '  [READ ] process_list(filter?, sort="rss", limit=20)\n'
    '  [READ ] container_status(name?)\n'
    '  [WRITE] container_restart(name)\n'
    '  [READ ] text_view(path, start?, end?)\n'
    '          -- Read a file (with 1-indexed line numbers) or list a directory.\n'
    '             For Windows-side paths, hit everything_search FIRST to resolve\n'
    "             the exact path -- text_view on a missing path is fast but the\n"
    "             planner shouldn't depend on Everything fallback for the happy path.\n"
    '  [WRITE] text_create(path, content)\n'
    '          -- Create a new file. Refuses /etc, /usr, /boot, /sys, /proc, /dev,\n'
    "             /mnt/c/Windows, /mnt/c/Program Files -- write-protected system paths.\n"
    '  [WRITE] text_str_replace(path, old, new)\n'
    "          -- Exact-match replace. `old` must occur EXACTLY once -- supply\n"
    "             a larger old block if the substring is ambiguous.\n"
    '  [WRITE] text_insert(path, line, content)\n'
    '          -- Insert content AFTER 1-indexed line N (0 = prepend).\n'
    '  [WRITE] powershell_run(script, timeout=30, work_dir?)\n'
    '          -- Execute a PowerShell script on the Windows side. Returns\n'
    "             stdout/stderr/exit_code. High-privilege -- tainted sessions\n"
    "             are refused. Default timeout 30s; script cap 64 KiB.\n"
    '  [READ ] winget_search(query, limit=10)\n'
    '  [READ ] winget_list()\n'
    '  [READ ] winget_show(id)\n'
    '  [WRITE] winget_install(id)\n'
    '  [WRITE] winget_upgrade(id?)         -- id = package id OR --all\n'
    '  [WRITE] winget_uninstall(id)\n'
    '          -- Windows-side package management via winget.exe through\n'
    "             WSL interop. Install/upgrade/uninstall are high-priv.\n"
    '  [READ ] flatpak_search(query, limit=10)\n'
    '  [READ ] flatpak_list()\n'
    '  [READ ] flatpak_show(id)\n'
    '  [WRITE] flatpak_install(id, scope?) -- scope: system|user (default system)\n'
    '  [WRITE] flatpak_upgrade(id?)        -- id = flatpak ref OR --all\n'
    '  [WRITE] flatpak_uninstall(id)\n'
    '          -- Linux-side package management via flatpak CLI. Install/\n'
    "             upgrade/uninstall are high-priv.\n"
    '  [WRITE] os_recipe(name, params?, os?)\n'
    '          -- Run a NAMED, allow-listed OS shell recipe from mios.toml\n'
    '             [recipes.*]. Picks the OS-appropriate template (linux /\n'
    '             windows) and quote-escapes every param before splicing.\n'
    '             `name` is the recipe key (e.g. open-folder,\n'
    '             open-shell-folder, reveal-in-folder, open-control-panel,\n'
    '             open-settings-uri, run-powershell, run-bash, lock-screen,\n'
    '             list-drives, show-network, show-process,\n'
    '             copy-to-clipboard, read-clipboard, toast, shutdown,\n'
    '             reboot). `params` is a dict matching the recipe\'s\n'
    '             declared `args`. `os` is optional ("linux" | "windows");\n'
    '             default = WSL-aware detection.\n'
    '             EXAMPLES:\n'
    '               os_recipe(name="open-folder", params={"path":"/mnt/c/Users"})\n'
    '               os_recipe(name="open-shell-folder", params={"folder":"Desktop"})\n'
    '               os_recipe(name="lock-screen")\n'
    "\n"
    "Verb-pick priority (most common cases first):\n"
    '  "open X" / "launch X" / "start X" / "run X"  -> open_app(name=X)\n'
    '  "close X"                                    -> close_window(title=X)\n'
    '  "focus X" / "bring X to front" / "switch to X" -> focus_window(title=X)\n'
    '  "move X to <pos>"                            -> move_window(title=X, position=<pos>)\n'
    '  "move X to (a,b)" / "X to position (a,b)"    -> position_window(title=X, x=a, y=b)\n'
    '  "resize X to WxH" / "make X WxH"             -> resize_window(title=X, width=W, height=H)\n'
    '  "minimize X" / "hide X"                      -> minimize_window(title=X)\n'
    '  "maximize X" / "fullscreen X"                -> maximize_window(title=X)\n'
    '  "restore X" / "un-minimize X" / "un-maximize X" -> restore_window(title=X)\n'
    '  "find X in winget" / "winget search X"       -> winget_search(query=X)\n'
    '  "install X via winget"                       -> winget_install(id=X)\n'
    '  "what Windows apps are installed"            -> winget_list()\n'
    '  "find X in flathub" / "flatpak search X"     -> flatpak_search(query=X)\n'
    '  "install X via flatpak"                      -> flatpak_install(id=X)\n'
    '  "what flatpaks are installed"                -> flatpak_list()\n'
    "  Platform hint: WIN-only apps (Office, Notepad++, ...) -> winget;\n"
    "  Linux GUI / cross-platform via Flathub      -> flatpak.\n"
    '  "what apps are installed" / "list apps"      -> mios_apps()\n'
    '  "what windows are open"                      -> list_windows()\n'
    '  "go to <url>" / "visit <url>"                -> open_url(url=<url>)\n'
    '  "read X" / "show me X" / "cat X"             -> text_view(path=X)\n'
    '  "write X to <path>" / "save X to <path>"     -> text_create(path=<path>, content=X)\n'
    '  "in <file> replace A with B"                 -> text_str_replace(path=<file>, old=A, new=B)\n'
    '  "run powershell: <script>" / "ps: <script>"  -> powershell_run(script=<script>)\n'
    "  For ANY file/folder reference on the Windows side, use everything_search\n"
    "  FIRST to resolve the exact path -- it's faster than recursing directories.\n"
    "\n"
    "Rules:\n"
    "- `dispatch` only when ONE verb solves it.\n"
    "- A WRITE verb is the right pick whenever the user asks for a\n"
    "  system effect (open/close/focus/move). NEVER pick a READ verb\n"
    "  when the user clearly wants an effect.\n"
    "- Position defaults to \"default\" (golden+16:10 centered); set\n"
    "  explicitly only when the user named a side.\n"
    "- `chat` for greetings, thanks, one-sentence clarification.\n"
    "  REASON -> PLAN -> DELEGATE meta-rule: an 'open / find / install /\n"
    "  launch / use X' intent NEVER routes to `chat`. The downstream\n"
    "  agent has to fan out across discovery surfaces before deciding\n"
    "  if X exists -- pick `agent` so it can do that. Refusing as 'not\n"
    "  installed' without running any probe first is a defect.\n"
    "- `agent` for N>1 tools, web research, install, file editing,\n"
    "  general knowledge questions, conversational follow-through,\n"
    "  ANY 'open / find / install / launch / use' intent.\n"
    "  MiOS-Agent is both an Agentic-OS AND a generalized AI agent.\n"
    "- Write `reply` fields in ENGLISH by default; use another language\n"
    "  only if the user's own message is clearly written in it.\n"
    "- Output JSON ONLY -- no preamble, no markdown, no commentary."
)


# ── Router (Layer-1 classifier) ────────────────────────────────────
async def classify_intent(user_text: str) -> Optional[dict]:
    """Call the micro-LLM router. Returns the parsed verdict dict
    or None to fall through to backend proxy. Best-effort: any error
    falls through cleanly."""
    if not ROUTER_ENABLED or not user_text or not user_text.strip():
        return None
    # ollama /api/chat with think=False: ROUTER_MODEL is a qwen3 micro
    # that ignores /no_think and otherwise dumps its answer into
    # message.reasoning with EMPTY content (operator test 2026-05-20) --
    # which made the router slow (full think pass) and unreliable.
    payload = {
        "model": ROUTER_MODEL,
        "messages": [
            {"role": "system", "content": _ROUTER_SYSTEM},
            {"role": "user",   "content": user_text[:2000]},
        ],
        "think": False,
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": ROUTER_MAX_TOKENS},
    }
    url = f"{ROUTER_ENDPOINT}/api/chat"
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
    # /api/chat shape {"message":{"content"}}; /v1 choices[] fallback.
    msg = body.get("message")
    if not isinstance(msg, dict):
        choices = body.get("choices") or []
        msg = (choices[0].get("message") if choices else {}) or {}
    content = (msg.get("content") or "").strip()
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


# ── Phase D.5 -- Refine / Polish / Agent registry ─────────────────
# Operator directive 2026-05-18: "MiOS-Agent (OWUI) handles the
# question(s) and refactors and reasons the actionable plan for
# other agents -- uses quick models and methods to achieve this
# refinement -- sent to the respective local agents with hints
# (tools, skills, intent, intended outcome) -- processed --
# returned to MiOS-Agent to check success -- refine the final
# answer". And: "Hermes isn't the only sub-agent on the system".
#
# Implementation:
#   * refine_intent(user_text, history) -- always-on quick pass
#     on the iGPU lane (qwen3:1.7b). Output extends the router
#     verdict with intended_outcome + target_agent + hint_tools
#     + hint_skills.
#   * Sub-agent registry sourced from mios.toml [agents.*] via
#     _load_agent_registry(). Refine picks target_agent by role
#     match; falls back to default=true; falls back to first.
#   * delegate_to_agent(name, refined, history) -- proxies to the
#     chosen sub-agent's :port with the refined plan injected as
#     a system-message prefix.
#   * polish_response(raw, refined) -- final-answer cleanup with
#     the same iGPU model. Skipped on dispatch / chat / DAG fast
#     paths (those produce final-shape content directly).
#
# Latency budget (qwen3:1.7b on iGPU): refine ~150-300ms,
# polish ~300-600ms. Trivial-input bypass (greetings, short)
# skips both -- sub-50ms total overhead on the fast path.

REFINE_ENABLED = os.environ.get(
    "MIOS_REFINE_ENABLE", "true",
).lower() not in {"false", "0", "no"}
# Refine CLASSIFIES intent (chat vs agent) -- the decisive routing call.
# The 0.6b/1.7b micros repeatedly mis-called action + web queries as
# chat (operator 2026-05-20: "Check system status" -> fake chat reply;
# "what's trending" -> chat). A more capable general model is worth the
# latency for correct routing; think=False (in refine_intent) stops it
# burning tokens on a reasoning preamble, and the LITE prompt is small
# so the call stays a few seconds even on the shared dGPU lane.
REFINE_MODEL = os.environ.get("MIOS_REFINE_MODEL", "qwen3.5:4b")
REFINE_ENDPOINT = os.environ.get(
    "MIOS_REFINE_ENDPOINT", "http://localhost:11434",
).rstrip("/")
REFINE_TIMEOUT_S = int(os.environ.get("MIOS_REFINE_TIMEOUT_S", "12"))
REFINE_MAX_TOKENS = int(os.environ.get("MIOS_REFINE_MAX_TOKENS", "400"))
REFINE_BYPASS_CHARS = int(os.environ.get("MIOS_REFINE_BYPASS_CHARS", "24"))
# Keep the refine model resident between turns. Cold, qwen3.5:4b takes ~10s to
# load (the silent gap before the first emit); warm it's ~0.4s. It's the same
# 4b that does polish + the 4b executor lane, so this just delays its unload
# during a work session rather than pinning a NEW model. "30m" frees it after
# idle (VRAM-friendly); set -1 to pin, or a shorter value under VRAM pressure.
REFINE_KEEP_ALIVE = os.environ.get("MIOS_REFINE_KEEP_ALIVE", "30m")

POLISH_ENABLED = os.environ.get(
    "MIOS_POLISH_ENABLE", "true",
).lower() not in {"false", "0", "no"}
# Polish PREPARES the final answer (operator 2026-05-20: "Hermes doesn't
# create the final answer EVER -- sub-agent output is only think blocks +
# emits; the final answer is prepared/consolidated/extrapolated, user-
# matched"). So it's the key output step, not a cosmetic pass -- it needs
# a capable + fast model, not the slow 1.7b CPU lane that timed out 45s.
# qwen3.5:4b on the dGPU lane (think=False) consolidates in a few seconds.
POLISH_MODEL = os.environ.get("MIOS_POLISH_MODEL", "qwen3.5:4b")
POLISH_ENDPOINT = os.environ.get(
    "MIOS_POLISH_ENDPOINT", "http://localhost:11434",
).rstrip("/")
POLISH_TIMEOUT_S = int(os.environ.get("MIOS_POLISH_TIMEOUT_S", "15"))
POLISH_MAX_TOKENS = int(os.environ.get("MIOS_POLISH_MAX_TOKENS", "800"))


def _load_agent_registry() -> dict[str, dict]:
    """Parse mios.toml [agents.*] sections into a registry dict.
    Returns {name: {endpoint, model, role, default, strengths}}.
    Read at module load + cached -- operator restarts agent-pipe
    to pick up changes (same pattern as ports/security/...).

    Fallback: when the TOML can't be read or has no [agents.*],
    returns a single hermes entry pointing at MIOS_AGENT_PIPE_
    BACKEND so the legacy path still works."""
    registry: dict[str, dict] = {}
    # LAYERED overlay (operator overlay wins): vendor <- /etc <- ~/.config.
    # A host can set a PRIVATE / per-host agent field -- e.g. the ai-local
    # phone's tailnet `endpoint` -- in /etc/mios/mios.toml WITHOUT baking it
    # into the PUBLIC vendor mios.toml (which ships it empty for privacy).
    # Each [agents.<name>] is merged field-by-field, so an overlay can set just
    # `endpoint` and inherit the rest. Mirrors the firstboot toml-layer reader.
    _base = os.environ.get("MIOS_TOML", "/usr/share/mios/mios.toml")
    _layers = [_base, "/etc/mios/mios.toml",
               os.path.expanduser("~/.config/mios/mios.toml")]
    try:
        try:
            import tomllib  # py311+
        except ImportError:
            import tomli as tomllib  # fallback (Fedora <= py310)
        agents: dict = {}
        for _p in _layers:
            try:
                with open(_p, "rb") as _f:
                    _d = tomllib.load(_f)
            except (OSError, tomllib.TOMLDecodeError):
                continue
            for _n, _cfg in (_d.get("agents") or {}).items():
                if isinstance(_cfg, dict):
                    agents.setdefault(_n, {}).update(_cfg)
        for name, cfg in agents.items():
            if not isinstance(cfg, dict):
                continue
            registry[name] = {
                "endpoint": str(cfg.get("endpoint", "")).rstrip("/"),
                "model":    str(cfg.get("model", name)),
                "role":     str(cfg.get("role", "general")),
                "default":  bool(cfg.get("default", False)),
                "strengths": list(cfg.get("strengths") or []),
                "lane":     str(cfg.get("lane", "")).lower().strip(),
                # fan-out opt-out (default True = eligible as a secondary).
                "fanout":   bool(cfg.get("fanout", True)),
                # CPU-compute twin (operator 2026-05-22: every agent has a
                # Modelfile for both CPU + GPU). When this agent runs as a
                # concurrent fan-out SECONDARY, _call_agent_complete prefers
                # this lane/model so the secondary offloads to the CPU lane
                # and the dGPU stays free for the primary. Empty = single-lane.
                "cpu_endpoint": str(cfg.get("cpu_endpoint", "")).rstrip("/"),
                "cpu_model":    str(cfg.get("cpu_model", "")),
                # health_gate (operator 2026-05-22 "client endpoints join the
                # swarm when they join"): a client-hosted node (e.g. a phone
                # running a local model over Tailscale) that comes and goes.
                # When set, the secondary call uses a SHORT timeout so a
                # sleeping/absent node drops from the merge fast instead of
                # stalling the turn -- auto-join-when-up, auto-drop-when-gone.
                "health_gate":  bool(cfg.get("health_gate", False)),
            }
    except Exception as e:
        log.warning("agent registry load failed: %s; using fallback", e)
    if not registry:
        registry["hermes"] = {
            "endpoint": BACKEND, "model": BACKEND_MODEL,
            "role": "general", "default": True, "strengths": [],
        }
    return registry


_AGENT_REGISTRY = _load_agent_registry()


def _load_dispatch_cfg() -> dict:
    """[dispatch] -- multi-agent concurrent fan-out config (SSOT in
    mios.toml; env override).

    mode (operator 2026-05-22, supersedes the earlier 'a couple, not all'):
      * 'council'   -- EQUAL WEIGHTING: every chat-eligible agent (every
                       [agents.*] without fanout=false, minus the primary)
                       is dispatched CONCURRENTLY each turn, up to
                       fanout_max, regardless of tag relevance. Lane-diverse
                       ordering runs CPU + GPU agents in parallel. This is
                       what stops the Hermes monopoly.
      * 'relevance' -- legacy: score the OTHER agents by skill-tag overlap
                       with the refined plan, engage only the top matches.
    fanout_max<=1 restores exact single-agent behaviour (zero fan-out)."""
    cfg = {"enable": True, "fanout_min": 1, "fanout_max": 2,
           "mode": "relevance"}
    toml_path = os.environ.get("MIOS_TOML", "/usr/share/mios/mios.toml")
    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        with open(toml_path, "rb") as f:
            dd = (tomllib.load(f).get("dispatch") or {})
        cfg["enable"] = bool(dd.get("enable", True))
        cfg["fanout_min"] = max(1, int(dd.get("fanout_min", 1)))
        cfg["fanout_max"] = max(cfg["fanout_min"], int(dd.get("fanout_max", 2)))
        cfg["mode"] = str(dd.get("mode", "relevance")).lower().strip() \
            or "relevance"
    except Exception as e:
        log.warning("dispatch cfg load failed: %s; using defaults", e)
    try:
        cfg["fanout_max"] = max(1, int(
            os.environ.get("MIOS_DISPATCH_FANOUT_MAX", cfg["fanout_max"])))
    except (TypeError, ValueError):
        pass
    cfg["mode"] = os.environ.get("MIOS_DISPATCH_MODE", cfg["mode"]).lower().strip() \
        or "relevance"
    return cfg


_DISPATCH_CFG = _load_dispatch_cfg()


def _agent_lane(cfg: dict) -> str:
    """Resolve an agent's inference lane: 'cpu' (the light iGPU/CPU lane,
    incl. the daemon-agent) or 'gpu' (the heavy dGPU lane). Explicit
    [agents.*].lane wins; otherwise infer from endpoint/model so legacy
    configs still classify. Used to run CPU work CONCURRENTLY with GPU."""
    lane = str(cfg.get("lane", "")).lower().strip()
    if lane in ("cpu", "igpu"):
        return "cpu"
    if lane == "mobile":
        # client-hosted node (phone/tablet on the tailnet) -- a distinct lane
        # so it's lane-diverse vs the local gpu/cpu agents in council fan-out.
        return "mobile"
    if lane == "gpu":
        return "gpu"
    ep = str(cfg.get("endpoint", ""))
    mdl = str(cfg.get("model", "")).lower()
    if ":8644" in ep or ":11435" in ep or "cpu" in mdl:
        return "cpu"
    return "gpu"


def _agent_skill_tags(cfg: dict) -> list[str]:
    """Canonical skill tags for an agent: role + inference lane + declared
    strengths. SINGLE SSOT shared by the A2A AgentCard (publish side ->
    skill.tags) and _pick_fanout_agents (consume side -> routing key) so an
    agent's advertised capabilities and the key the orchestrator routes on
    can never drift. Clean human/agent-facing labels (NOT snake_case-split);
    the router expands sub-tokens for matching internally."""
    tags = {
        str(cfg.get("role", "general")).lower().strip(),
        _agent_lane(cfg),
    }
    for s in (cfg.get("strengths") or []):
        s = str(s).lower().strip()
        if s:
            tags.add(s)
    return sorted(t for t in tags if t)


def _pick_fanout_agents(primary_name: str,
                        refined: Optional[dict],
                        *, force_council: bool = False) -> list:
    """Pick SECONDARY (name, cfg) agents to run CONCURRENTLY alongside the
    chosen primary -- operator 2026-05-21 'a couple at a time' + 'self-
    delegate to CPU concurrently to pending/future GPU operations' + 'make
    sure hermes isn't always the only dispatched agent'. Selection is
    deterministic + language-neutral (NO hardcoded topic map): score each
    OTHER registered agent by role/strengths-token overlap with the refined
    plan, PLUS a concurrency bonus for a CPU-lane agent when the primary
    holds the GPU lane -- that secondary runs in parallel at zero dGPU cost,
    so the CPU lane is always utilised and the primary is never alone.
    Returns [] when fan-out is disabled / capped at 1 / nothing relevant.

    force_council (operator 2026-05-22 SWARM toggle): engage EVERY eligible
    agent (non-primary, not opted out) this turn, bypassing the enable /
    fanout_max / relevance gates entirely -- the manual 'full swarm' override."""

    def _opted_out(c: dict) -> bool:
        # Explicit fan-out opt-out. The telemetry daemon-agent sets this:
        # it ignores the prompt and always returns a system digest, so it
        # would flood chat synthesis. Its own monitoring loop is unaffected.
        return c.get("fanout") is False or \
            str(c.get("fanout", "")).lower() in {"false", "no", "0"}

    if force_council:
        primary_lane = _agent_lane(_AGENT_REGISTRY.get(primary_name) or {})
        swarm = [(name, cfg) for name, cfg in _AGENT_REGISTRY.items()
                 if name != primary_name and not _opted_out(cfg)]
        swarm.sort(key=lambda nc: (
            0 if _agent_lane(nc[1]) != primary_lane else 1, nc[0]))
        return swarm

    if not _DISPATCH_CFG.get("enable") or _DISPATCH_CFG.get("fanout_max", 1) <= 1:
        return []
    want = _DISPATCH_CFG["fanout_max"] - 1

    # COUNCIL mode (operator 2026-05-22 'weigh every agent equally + dispatch
    # multiple concurrently', supersedes 'a couple, not all'): EQUAL WEIGHT --
    # every eligible agent (non-primary, not opted out) runs concurrently
    # each turn, NO relevance gate, so it is never Hermes-only. Order
    # lane-diverse first (a CPU agent parallelises a GPU primary at zero dGPU
    # cost), then by name for determinism. Capped at `want` (fanout_max-1).
    if _DISPATCH_CFG.get("mode") == "council":
        primary_lane = _agent_lane(_AGENT_REGISTRY.get(primary_name) or {})
        council = [
            (name, cfg) for name, cfg in _AGENT_REGISTRY.items()
            if name != primary_name and not _opted_out(cfg)
        ]
        council.sort(key=lambda nc: (
            0 if _agent_lane(nc[1]) != primary_lane else 1, nc[0]))
        # FIRST PASS = ALL nodes (operator 2026-05-23: "every turn dispatches to
        # ALL nodes/endpoints for a first pass/understanding"). Previously
        # capped at fanout_max-1; now every eligible node participates -- the
        # _agent_sem (MIOS_AGENT_CONCURRENCY) bounds how many run AT ONCE, so
        # all nodes contribute without re-creating the engine-overrun burst.
        # MIOS_COUNCIL_MAX caps the roster only as a safety valve (0 = all).
        _cmax = int(os.environ.get("MIOS_COUNCIL_MAX", "0"))
        return council if _cmax <= 0 else council[:_cmax]

    corpus = ""
    if isinstance(refined, dict):
        corpus = " ".join(
            str(refined.get(k, "")) for k in
            ("intended_outcome", "refined_text", "target_agent")).lower()
        for k in ("hint_tools", "hint_skills"):
            v = refined.get(k)
            if isinstance(v, list):
                corpus += " " + " ".join(str(x) for x in v).lower()
    if not corpus.strip():
        return []
    # Word-boundary token set of the intent (NOT substring): the old
    # `tag in corpus` matched 'search' inside 'researching' and similar
    # accidental substrings. Routing on whole words against the A2A skill
    # tags is both more precise and the standard's capability surface.
    corpus_words = set(re.findall(r"[a-z0-9]+", corpus))
    primary_lane = _agent_lane(_AGENT_REGISTRY.get(primary_name) or {})
    scored = []
    for name, cfg in _AGENT_REGISTRY.items():
        if name == primary_name:
            continue
        # Honour the explicit fan-out opt-out (see _opted_out above).
        if _opted_out(cfg):
            continue
        # Route on the agent's A2A skill tags (the SAME _agent_skill_tags
        # SSOT the AgentCard publishes), expanding snake_case sub-tokens for
        # matching so 'web_search' also matches 'web' / 'search'. Match is
        # WORD-BOUNDARY (tag in corpus_words), not substring -- no accidental
        # 'search' inside 'researching'. Card capability == routing key.
        match_tokens: set[str] = set()
        for t in _agent_skill_tags(cfg):
            match_tokens.add(t)
            match_tokens.update(p for p in t.split("_") if p)
        score = len(match_tokens & corpus_words)
        # CPU-lane concurrency bonus: boost an ALREADY-RELEVANT CPU-lane
        # agent (base score>0) when the primary holds the GPU lane, so a
        # genuinely-relevant secondary parallelises at zero dGPU cost.
        # CRITICAL: gated on score>0 -- it only lifts an agent that ALREADY
        # matched the intent, NEVER forces an irrelevant one in. The old
        # "even on weak match" +2 force-engaged the telemetry daemon-agent
        # on EVERY GPU turn, flooding unrelated global system-failure digests
        # (crowdsec / CDP / bouncer) into the answer reasoning on
        # recipe/knowledge queries (operator 2026-05-22 "Complete FAILS").
        # Now the daemon-agent fans out ONLY for system/telemetry intents
        # that match its strengths.
        if score > 0 and primary_lane == "gpu" and _agent_lane(cfg) == "cpu":
            score += 2
        if score > 0:
            scored.append((score, name, cfg))
    scored.sort(key=lambda x: -x[0])
    return [(n, c) for _, n, c in scored[:want]]


async def _call_agent_complete(name, cfg, body, headers, client,
                               *, prefer_cpu: bool = True) -> tuple:
    """Bounded entry point (operator 2026-05-23): concurrent agent dispatches
    -- council secondaries AND DAG-level nodes -- share _agent_sem, so the
    swarm engages at most MIOS_AGENT_CONCURRENCY agents at once; the rest
    queue. No nested agent calls, so no deadlock."""
    async with _agent_sem:
        return await _call_agent_complete_inner(
            name, cfg, body, headers, client, prefer_cpu=prefer_cpu)


async def _call_agent_complete_inner(name: str, cfg: dict, body: dict,
                               headers: dict, client,
                               *, prefer_cpu: bool = True) -> tuple:
    """Best-effort non-streaming /v1 call to a secondary fan-out agent.
    Returns (name, text); text='' -> dropped from the merge. A dead or
    absent endpoint (e.g. opencode :8633 when not served as /v1) just
    yields '' and is skipped, so fan-out degrades to the live agents.

    CPU-lane offload (operator 2026-05-22): a secondary always runs
    CONCURRENTLY with the GPU primary, so if the agent declares a CPU
    twin (cpu_endpoint/cpu_model -> mios-*-cpu Modelfile on :11435) we
    dispatch THAT -- the secondary works on the light iGPU/CPU lane while
    the dGPU stays dedicated to the primary. No twin -> its own endpoint.

    An ollama-lane endpoint (the :11434/:11435 instances, incl. every CPU
    twin) is called via the NATIVE /api/chat with think=False -- the same
    fix refine/polish use: a qwen3 model on the /v1 compat path dumps its
    answer into message.reasoning with EMPTY content (operator 2026-05-20),
    so a /v1 secondary folds in nothing. Custom gateways (opencode :8633,
    hermes :8642) are not ollama -> stay on /v1/chat/completions."""
    # prefer_cpu (fan-out secondaries): offload to the agent's CPU twin so
    # it runs concurrent with the GPU primary. prefer_cpu=False (planner
    # agent-task nodes): use the agent's PRIMARY endpoint/model -- a coding
    # sub-task must hit opencode proper, not a small CPU twin.
    ep = ((cfg.get("cpu_endpoint") if prefer_cpu else "")
          or cfg.get("endpoint") or "").rstrip("/")
    if not ep:
        return name, ""
    _mdl = (cfg.get("cpu_model") if prefer_cpu else "") or cfg.get("model")
    # ollama lanes speak the native API + honour think=False; the bespoke
    # sub-agent servers do not. Detect by the SSOT lane ports.
    _is_ollama = (":11434" in ep) or (":11435" in ep)
    # health-gated client node (mobile / Tailscale-hosted): SHORT timeout so a
    # sleeping/absent node drops from the merge fast instead of stalling.
    _to = 2.5 if cfg.get("health_gate") else None
    try:
        if _is_ollama:
            base = ep[:-3].rstrip("/") if ep.endswith("/v1") else ep
            payload = {
                "model": _mdl or cfg.get("model"),
                "messages": body.get("messages") or [],
                "think": False,
                "stream": False,
            }
            if body.get("max_tokens"):
                payload["options"] = {"num_predict": int(body["max_tokens"])}
            r = await client.post(
                f"{base}/api/chat",
                content=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}, timeout=_to)
            if r.status_code != 200:
                return name, ""
            msg = (r.json().get("message") or {})
            return name, _strip_think_tags(str(msg.get("content") or ""))
        nb = dict(body)
        nb["stream"] = False
        if _mdl:
            nb["model"] = _mdl
        r = await client.post(
            f"{ep}/chat/completions",
            content=json.dumps(nb).encode("utf-8"), headers=headers,
            timeout=_to)
        if r.status_code != 200:
            return name, ""
        ch = (r.json().get("choices") or [])
        msg = (ch[0].get("message") if ch else {}) or {}
        return name, _strip_think_tags(str(msg.get("content") or ""))
    except Exception as e:
        log.info("fanout secondary %s failed: %s", name, e)
        return name, ""


async def _call_agent_stream(name, cfg, body, headers, client, q,
                             *, prefer_cpu: bool = True) -> tuple:
    """Bounded STREAMING sibling of _call_agent_complete (operator
    2026-05-23: a sub-agent's thinking must STREAM into the think blocks
    live, not be collected then flushed last-minute). Streams the
    secondary's output and pushes (name, fragment) onto the shared queue
    `q` as fragments arrive, so the orchestrator interleaves them into the
    reasoning dropdown WHILE the primary streams. Returns (name,
    full_text) -- the SAME contract as _call_agent_complete -- so the
    polish-merge / scratchpad / roster path downstream is unchanged. Dead
    endpoints + errors yield '' (dropped from the merge), identical
    degradation to the non-streaming path. Shares _agent_sem (the swarm
    concurrency cap)."""
    async with _agent_sem:
        return await _call_agent_stream_inner(
            name, cfg, body, headers, client, q, prefer_cpu=prefer_cpu)


async def _call_agent_stream_inner(name: str, cfg: dict, body: dict,
                                   headers: dict, client, q,
                                   *, prefer_cpu: bool = True) -> tuple:
    ep = ((cfg.get("cpu_endpoint") if prefer_cpu else "")
          or cfg.get("endpoint") or "").rstrip("/")
    if not ep:
        return name, ""
    _mdl = (cfg.get("cpu_model") if prefer_cpu else "") or cfg.get("model")
    _is_ollama = (":11434" in ep) or (":11435" in ep)
    _to = 2.5 if cfg.get("health_gate") else None
    parts: list = []

    def _push(frag: str) -> None:
        if frag and q is not None:
            try:
                # Tagged event for the orchestrator's MERGED event queue:
                # ("SF", agent_name, fragment). Distinguishes secondary
                # fragments from the primary's ("PR"/"PT"/"PD") events.
                q.put_nowait(("SF", name, frag))
            except Exception:
                pass

    try:
        if _is_ollama:
            base = ep[:-3].rstrip("/") if ep.endswith("/v1") else ep
            payload = {
                "model": _mdl or cfg.get("model"),
                "messages": body.get("messages") or [],
                "think": False,
                "stream": True,
            }
            if body.get("max_tokens"):
                payload["options"] = {"num_predict": int(body["max_tokens"])}
            async with client.stream(
                    "POST", f"{base}/api/chat",
                    content=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    timeout=_to) as r:
                if r.status_code != 200:
                    return name, ""
                async for line in r.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        obj = json.loads(line)
                    except (json.JSONDecodeError, ValueError):
                        continue
                    frag = ((obj.get("message") or {}).get("content")) or ""
                    if frag:
                        parts.append(frag)
                        _push(frag)
                    if obj.get("done"):
                        break
            return name, _strip_think_tags("".join(parts))
        # Bespoke /v1 gateway (opencode :8633, hermes :8642): SSE stream.
        nb = dict(body)
        nb["stream"] = True
        if _mdl:
            nb["model"] = _mdl
        async with client.stream(
                "POST", f"{ep}/chat/completions",
                content=json.dumps(nb).encode("utf-8"), headers=headers,
                timeout=_to) as r:
            if r.status_code != 200:
                return name, ""
            async for line in r.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except (json.JSONDecodeError, ValueError):
                    continue
                ch = chunk.get("choices") or []
                if not ch:
                    continue
                delta = ch[0].get("delta") or {}
                _content = delta.get("content") or ""
                # Display BOTH the answer + any native reasoning the gateway
                # streams; only the answer content folds into the merge text.
                frag = _content or (delta.get("reasoning_content") or "")
                if _content:
                    parts.append(_content)
                if frag:
                    _push(frag)
        return name, _strip_think_tags("".join(parts))
    except Exception as e:
        log.info("fanout secondary %s (stream) failed: %s", name, e)
        return name, ""


def _load_verb_catalog() -> dict:
    """Parse mios.toml [verbs.*] sections into the canonical verb
    catalog. Each entry: {section, sig, desc, tier, permission, params:
    {<arg>: {type, desc, aliases, enum, default}}}. SSOT for the planner
    prompt + the arg-synonym dispatcher + (future) MCP tools/list."""
    cat: dict = {}
    toml_path = os.environ.get("MIOS_TOML", "/usr/share/mios/mios.toml")
    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
        verbs = data.get("verbs") or {}
        if isinstance(verbs, dict):
            for vname, vcfg in verbs.items():
                if not isinstance(vcfg, dict):
                    continue
                # Reject entries lacking `section` -- the [verbs.*]
                # namespace is shared with the mios-html configurator
                # (build/config/dash/ai/dev/...) which uses the same
                # TOML key for UI button definitions. agent-pipe owns
                # only the entries that carry the agent-verb shape.
                if "section" not in vcfg:
                    continue
                cat[vname] = {
                    "section":    str(vcfg.get("section", "Misc")),
                    "sig":        str(vcfg.get("sig", "")),
                    "desc":       str(vcfg.get("desc", "")),
                    "tier":       str(vcfg.get("tier", "common")),
                    "permission": str(vcfg.get("permission", "read")),
                    "params":     vcfg.get("params") or {},
                    # SSOT command template (P3): when present, the dispatch
                    # builder renders THIS instead of a hardcoded branch.
                    "cmd":        str(vcfg.get("cmd", "") or ""),
                }
    except Exception as e:
        log.warning("verb catalog load failed: %s", e)
    return cat


def _verb_arg_synonyms_from_catalog(cat: dict) -> dict:
    """Project verb catalog's per-arg `aliases` lists into the legacy
    {verb: {arg: [alias,...]}} shape `_arg_with_synonyms` consumes.
    Single SSOT (catalog) -- no separate [verbs.<name>.synonyms] block."""
    syn: dict = {}
    for vname, vcfg in cat.items():
        params = vcfg.get("params") or {}
        if not isinstance(params, dict):
            continue
        for argname, argcfg in params.items():
            if not isinstance(argcfg, dict):
                continue
            aliases = argcfg.get("aliases") or []
            if aliases:
                syn.setdefault(vname, {})[str(argname)] = [str(a) for a in aliases]
    return syn


def _render_verb_catalog(cat: dict, include_rare: bool = False) -> str:
    """Render the verb catalog as the prose block the planner consumes.
    Sections grouped + ordered by first-seen order. Verbs tagged
    tier='rare' are HIDDEN by default -- they remain dispatchable for
    in-flight chains but don't burn planner tokens. Set include_rare=
    True for a full audit."""
    sections: dict[str, list[str]] = {}
    order: list[str] = []
    for vname, vcfg in cat.items():
        if not include_rare and vcfg.get("tier") == "rare":
            continue
        sec = vcfg.get("section", "Misc")
        if sec not in sections:
            sections[sec] = []
            order.append(sec)
        sig = vcfg.get("sig", "")
        desc = vcfg.get("desc", "")
        line = f"  {vname}({sig})".ljust(48) + f"-- {desc}"
        sections[sec].append(line)
    parts: list[str] = []
    for sec in order:
        parts.append(f"  -- {sec} --")
        parts.extend(sections[sec])
        parts.append("")
    return "\n".join(parts).rstrip()


def _load_verb_arg_synonyms() -> dict:
    """Compat shim -- existing callers still hit this name."""
    return _verb_arg_synonyms_from_catalog(_VERB_CATALOG)


_VERB_CATALOG = _load_verb_catalog()
_VERB_ARG_SYNONYMS = _load_verb_arg_synonyms()
_VERB_CATALOG_RENDERED = _render_verb_catalog(_VERB_CATALOG)


def _load_recipe_catalog() -> dict:
    """Parse mios.toml [recipes.*] -> {name: {description, args, permission}}.
    SSOT for the os_recipe verb. Rendered into the planner prompt so EVERY
    recipe is natively discoverable by every agent -- no recipe names baked
    in code (operator 2026-05-21: "ALL agents know to use these functions";
    "no hardcodes unless modelfile/docs"). Add a [recipes.*] block in TOML
    and it appears here + in every consumer automatically (self-iterating)."""
    out: dict = {}
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            return out
    toml_path = os.environ.get("MIOS_TOML", "/usr/share/mios/mios.toml")
    for p in (toml_path, "/etc/mios/mios.toml"):  # /etc overlay wins
        try:
            with open(p, "rb") as f:
                recs = (tomllib.load(f).get("recipes") or {})
        except (OSError, tomllib.TOMLDecodeError):
            continue
        for name, cfg in recs.items():
            if isinstance(cfg, dict):
                out[name] = {
                    "description": str(cfg.get("description", "")),
                    "args": list(cfg.get("args") or []),
                    "permission": str(cfg.get("permission", "read")),
                }
    return out


def _render_recipe_catalog(rec: dict) -> str:
    if not rec:
        return ""
    lines = ["  -- OS recipes (run via os_recipe(name=..., params={...})) --"]
    for name, cfg in rec.items():
        args = ",".join(cfg.get("args") or [])
        perm = cfg.get("permission", "read")
        tag = "" if perm == "read" else f" [{perm}]"
        lines.append(f"  {name}({args})".ljust(34)
                     + f"-- {cfg.get('description', '')}{tag}")
    return "\n".join(lines)


_RECIPE_CATALOG = _load_recipe_catalog()
_RECIPE_CATALOG_RENDERED = _render_recipe_catalog(_RECIPE_CATALOG)


def _render_agent_catalog(registry: dict) -> str:
    """Render the sub-agent roster for the planner so it can route a
    sub-task to the right AGENT (an `agent` node) -- NOT a hardcoded list:
    pulled from _AGENT_REGISTRY (mios.toml [agents.*] SSOT) + the same
    skill tags the A2A card publishes. Lets the planner assign DIFFERENT
    sub-tasks to DIFFERENT agents that then run concurrently."""
    if not registry:
        return ""
    lines = ["  -- sub-agents (delegate a sub-task via an `agent` node) --"]
    for name, cfg in sorted(registry.items()):
        role = str(cfg.get("role", "general"))
        lane = _agent_lane(cfg)
        strengths = ", ".join(str(s) for s in (cfg.get("strengths") or []))
        lines.append(f"  {name}".ljust(24)
                     + f"-- {role} [{lane}]"
                     + (f"; {strengths}" if strengths else ""))
    return "\n".join(lines)


_AGENT_CATALOG_RENDERED = _render_agent_catalog(_AGENT_REGISTRY)


def _arg_with_synonyms(tool: str, canonical: str, args: dict) -> str:
    """Resolve an arg by canonical name first, then by mios.toml-
    declared synonyms for the verb. Returns the first non-empty string
    value found, or '' if none match. SSOT: mios.toml
    [verbs.<tool>.synonyms]."""
    v = args.get(canonical)
    if v is not None and str(v).strip():
        return str(v)
    for alias in (_VERB_ARG_SYNONYMS.get(tool, {}).get(canonical) or []):
        v = args.get(alias)
        if v is not None and str(v).strip():
            return str(v)
    return ""


def _validate_enum_args(tool: str, args: dict) -> Optional[str]:
    """Tool-Manager parameter validation (ref AIOS kernel C 3.7: "validate
    parameters before execution to prevent tool crashes"). Reject a verb
    arg whose value falls outside the enum DECLARED for it in mios.toml
    [verbs.<tool>.params.<arg>.enum], BEFORE the command reaches the
    broker -- previously such values passed through as a stray env var and
    silently misbehaved.

    Conservative + binding-clean: only acts on explicitly-declared enums;
    every other arg passes untouched. The allowed set comes straight from
    the SSOT (no hardcoded English/topic content). Returns an error string
    (which dispatch_mios_verb surfaces in the same shape the planner's
    reflection pass consumes, so it re-issues with a valid value), or None
    when every declared enum is satisfied / the verb is unknown (the
    existing unknown-verb path reports that)."""
    if not isinstance(args, dict) or not args:
        return None
    vcfg = _VERB_CATALOG.get(tool)
    if not vcfg:
        return None
    params = vcfg.get("params")
    if not isinstance(params, dict):
        return None
    for argname, argcfg in params.items():
        if not isinstance(argcfg, dict):
            continue
        enum = argcfg.get("enum")
        if not isinstance(enum, list) or not enum:
            continue
        val = _arg_with_synonyms(tool, str(argname), args)
        if val == "":
            continue  # not supplied -> default applies; not our concern
        allowed = [str(e) for e in enum]
        if val not in allowed:
            return (
                f"verb {tool!r} arg {argname!r}={val!r} is not allowed "
                f"(mios.toml [verbs.{tool}.params.{argname}].enum). "
                f"Re-issue with one of: {allowed}."
            )
    return None


def _pick_agent(role: str) -> tuple[str, dict]:
    """Pick a sub-agent by role match. Order: exact-role -> default
    -> first registered. Returns (name, cfg)."""
    role = (role or "").lower().strip()
    if role:
        for name, cfg in _AGENT_REGISTRY.items():
            if cfg.get("role", "").lower() == role:
                return name, cfg
    for name, cfg in _AGENT_REGISTRY.items():
        if cfg.get("default"):
            return name, cfg
    # Whatever is first.
    name = next(iter(_AGENT_REGISTRY))
    return name, _AGENT_REGISTRY[name]


# Trivial-input bypass regex -- short messages with no question
# mark, no action verb tokens, no path-like or URL-like content.
# These are handled by the existing classify_intent router without
# a separate refine pass. Locale-neutral (the regex matches BY
# SHAPE not by English keyword list -- operator binding rule
# "ABSOLUTELY NO HARDCODED ENGLISH STANDARD Linux and Windows
# Terminologies").
#
# Bypass triggers when:
#   * <= REFINE_BYPASS_CHARS total chars
#   * no `?` (questions ALWAYS get the refine pass)
#   * no `/`, `\`, `:`, `@`, `$`, `~` (paths / refs / hosts)
#   * no digit (commands with numbers / coords are non-trivial)
#   * <= 4 word tokens
_BYPASS_NEGATIVE_CHARS = set("?/\\:@$~")


def _is_trivial_bypass(s: str) -> bool:
    if not s:
        return False
    s = s.strip()
    if not s or len(s) > REFINE_BYPASS_CHARS:
        return False
    if any(c in _BYPASS_NEGATIVE_CHARS for c in s):
        return False
    if any(c.isdigit() for c in s):
        return False
    if len(s.split()) > 4:
        return False
    return True


def _temporal_grounding() -> str:
    """One system-message line giving the agents the current date/time.

    The micros have no clock. Without this, relative dates ("tomorrow",
    "this weekend") were resolved by guessing off whatever dates appeared
    in retrieved text -- operator-flagged: "what's tomorrow at Anime North"
    came back as TODAY's date and three other dates across one answer.
    This grounds the orchestrator's OWN system prompts (refine / polish /
    dispatch); it is NOT a pre_llm_call env-inject into the user message.
    Uses process-local time so "tomorrow" matches the operator's day.
    """
    now = time.localtime()
    tomorrow = time.localtime(time.time() + 86400)
    return (
        "Temporal grounding (resolve every relative date/time against THIS, "
        "never against dates found in retrieved text or training data):\n"
        f"  - Today is {time.strftime('%A, %Y-%m-%d', now)}.\n"
        f"  - Tomorrow is {time.strftime('%A, %Y-%m-%d', tomorrow)}.\n"
        f"  - Current local time: {time.strftime('%H:%M %Z', now)}."
    )


# ─── Per-chat agent scratchpad (rolling cross-agent blackboard) ────────
# operator 2026-05-22: "rolling scratchpad per chat ... an inline log on
# every agent's scratchpad for them ALL to see and use or refer to during
# the chain for checkpoints from other agents." One rolling, capped log PER
# CONVERSATION, keyed by the OpenAI-standard metadata.chat_id the OWUI pipe
# forwards. The orchestrator injects the recent tail into EVERY dispatched
# agent's system context (so each sees the others' checkpoints) and appends
# each agent's contribution back as a checkpoint. In-process + async-safe
# via a contextvar (concurrent council/DAG tasks inherit the key); no new
# deps, fully offline.
SCRATCHPAD_ENABLE = os.environ.get(
    "MIOS_SCRATCHPAD_ENABLE", "true").lower() not in {"false", "0", "no"}
SCRATCHPAD_MAX = int(os.environ.get("MIOS_SCRATCHPAD_MAX", "60"))
SCRATCHPAD_INJECT = int(os.environ.get("MIOS_SCRATCHPAD_INJECT", "12"))
SCRATCHPAD_TTL_S = int(os.environ.get("MIOS_SCRATCHPAD_TTL_S", "3600"))
SCRATCHPAD_SUMMARY_CHARS = int(
    os.environ.get("MIOS_SCRATCHPAD_SUMMARY_CHARS", "280"))
SCRATCHPAD_MAX_CHATS = int(os.environ.get("MIOS_SCRATCHPAD_MAX_CHATS", "256"))
# conv_key -> rolling deque of checkpoint dicts. OrderedDict so the least-
# recently-used conversation evicts when MAX_CHATS is exceeded.
_SCRATCHPADS: "collections.OrderedDict" = collections.OrderedDict()
# Set once per request from the conversation id; read by note/render anywhere
# in the dispatch chain (child asyncio tasks inherit the context at creation).
_conv_key_var: "contextvars.ContextVar" = contextvars.ContextVar(
    "mios_conv_key", default="default")


def _scratchpad_key(body: dict, fallback: str = "default") -> str:
    """Per-chat scratchpad key: the OpenAI-standard metadata.chat_id the OWUI
    pipe forwards, with graceful fallbacks so non-OWUI callers (Discord, raw
    API) still get a stable-per-request blackboard rather than colliding."""
    meta = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}
    return str(meta.get("chat_id") or meta.get("session_id")
               or body.get("chat_id") or fallback)


def _scratchpad_for(key: str) -> "collections.deque":
    dq = _SCRATCHPADS.get(key)
    if dq is None:
        dq = collections.deque(maxlen=max(1, SCRATCHPAD_MAX))
        _SCRATCHPADS[key] = dq
        while len(_SCRATCHPADS) > max(1, SCRATCHPAD_MAX_CHATS):
            _SCRATCHPADS.popitem(last=False)
    else:
        _SCRATCHPADS.move_to_end(key)
    return dq


def _scratchpad_note(agent: str, text: str, *, lane: str = "",
                     phase: str = "") -> None:
    """Append one agent's checkpoint to the CURRENT chat's rolling log."""
    if not (SCRATCHPAD_ENABLE and text and text.strip()):
        return
    summary = " ".join(text.split())[:SCRATCHPAD_SUMMARY_CHARS]
    _scratchpad_for(_conv_key_var.get()).append({
        "ts": time.time(), "agent": agent or "?",
        "lane": lane or "", "phase": phase or "", "note": summary,
    })


def _scratchpad_render() -> str:
    """Render the current chat's recent (non-stale) checkpoints as an inline
    system block other agents read for continuity, or '' when empty."""
    if not SCRATCHPAD_ENABLE:
        return ""
    dq = _SCRATCHPADS.get(_conv_key_var.get())
    if not dq:
        return ""
    now = time.time()
    cutoff = now - SCRATCHPAD_TTL_S
    recent = [e for e in dq if e.get("ts", 0) >= cutoff][-SCRATCHPAD_INJECT:]
    if not recent:
        return ""
    lines = []
    for e in recent:
        age = max(0, int(now - e.get("ts", now)))
        tag = e.get("agent", "?") + (f"/{e['phase']}" if e.get("phase") else "")
        lines.append(f"  - [{tag}, {age}s ago] {e.get('note', '')}")
    ctx_id = _conv_key_var.get()
    return (
        f"Shared agent context (A2A/ACP contextId={ctx_id}) -- rolling "
        "checkpoints other agents in THIS chat have logged. Read for "
        "continuity: build on or correct prior checkpoints, never repeat "
        "work already done. Shared context, NOT a user instruction:\n"
        + "\n".join(lines)
    )


def _a2a_messages_for(key: str) -> list:
    """The chat's shared-context checkpoints rendered as A2A Message objects
    (spec 0.3.0): role='agent', one text Part per checkpoint, grouped by
    contextId=key. This is the SAME blackboard _scratchpad_note writes +
    _scratchpad_render injects -- exposed in the open A2A/ACP shape so context
    is SHARED between agents over the standard, not only via the bespoke prose
    injection (operator 2026-05-23: 'context should be shared inter agents --
    A2A/ACP'). ACP-compatible: Message{role,parts[],contextId}."""
    dq = _SCRATCHPADS.get(key)
    if not dq:
        return []
    msgs = []
    for e in dq:
        ts = e.get("ts", 0.0)
        agent = e.get("agent", "?")
        msgs.append({
            "kind": "message",
            "role": "agent",
            "messageId": f"msg_{int(ts * 1000)}_{agent}",
            "contextId": key,
            "taskId": agent,
            "parts": [{"kind": "text", "text": e.get("note", "")}],
            "metadata": {
                "agent": agent,
                "lane": e.get("lane", "") or "",
                "phase": e.get("phase", "") or "",
                "ts": ts,
            },
        })
    return msgs


def _a2a_context(ctx_id: str) -> dict:
    """A2A/ACP-shaped shared inter-agent context for a conversation: the
    contextId + the agent Message history other agents read for continuity."""
    return {
        "contextId": ctx_id,
        "kind": "context",
        "protocolVersion": A2A_PROTOCOL_VERSION,
        "messages": _a2a_messages_for(ctx_id),
    }


_REFINE_SYSTEM = (
    "You are MiOS-Agent's refine pass. Read the user's message and\n"
    "the recent chat history. Emit a single JSON object describing\n"
    "what the user wants AND how to achieve it. Be terse -- output\n"
    "is consumed by another agent, NOT shown to the user.\n"
    "\n"
    "Schema:\n"
    '  {\n'
    '    "intent": "<one of: chat | dispatch | agent | dag | multi_task>",\n'
    '    "refined_text": "<rewritten user query in clear, actionable form>",\n'
    '    "intended_outcome": "<one short line: what the user expects back>",\n'
    '    "target_agent": "<one of the registered sub-agents -- pick by role>",\n'
    '    "hint_tools":  ["<verb-name-1>", "<verb-name-2>", ...],\n'
    '    "hint_skills": ["<skill-name-1>", ...],\n'
    '    "reply": "<for intent=chat: your reply directly; omit otherwise>",\n'
    '    "tasks": [   // ONLY for intent=multi_task. One entry per\n'
    '                 //   discrete goal the user crammed into one prompt.\n'
    '      {\n'
    '        "title":            "<short imperative -- one line>",\n'
    '        "refined_text":     "<rewritten subtask, agent-ready>",\n'
    '        "intended_outcome": "<what success looks like for THIS task>",\n'
    '        "target_agent":     "<role-matched sub-agent>",\n'
    '        "hint_tools":       ["..."],\n'
    '        "hint_skills":      ["..."],\n'
    '        "priority":         1,  // lower runs first; 1..N\n'
    '        "depends_on":       []  // task indices this one waits for;\n'
    '                                //   empty = runs first / in parallel\n'
    '      }, ...\n'
    '    ],\n'
    '    "tool_cards": [   // OPTIONAL but PREFERRED for intent in\n'
    '                      //   {agent, dag, multi_task}. Per-step\n'
    '                      //   guidance carried INTO the sub-agent\n'
    '                      //   dispatch so it knows WHY each tool is\n'
    '                      //   hinted + what success looks like. Lifts\n'
    '                      //   the planning burden off the worker.\n'
    '      {\n'
    '        "tool":              "<verb-name or skill-name>",\n'
    '        "args_hint":         {"key": "value", ...},\n'
    '        "why":               "<one line: why THIS tool for THIS step>",\n'
    '        "success_predicate": "<short check: how to know it worked>",\n'
    '        "output_used_by":    [<idx-of-step-that-consumes-this>]\n'
    '      }, ...\n'
    '    ]\n'
    '  }\n'
    "\n"
    "REASON -> PLAN -> DELEGATE meta-rule:\n"
    "  An 'open / find / install / launch / use / run / start / show /\n"
    "  reveal X' intent NEVER routes to `chat`. NEITHER does any request\n"
    "  for CURRENT or EXTERNAL information: 'search the web for', 'look\n"
    "  up', 'latest', 'today', 'news', 'recent', \"what's trending\",\n"
    "  prices, weather, scores, or ANY fact not answerable from THIS\n"
    "  conversation alone. Those need the agent's web_search / web_extract\n"
    "  tools -- pick `agent` (or `dag`). Decide local-vs-web by intent: a\n"
    "  file/app on THIS computer -> agent with directory_lookup/\n"
    "  everything_search/fs_search; current world info -> agent with\n"
    "  web_search/web_extract. The downstream agent must fan out across\n"
    "  discovery/search surfaces before deciding -- never refuse or\n"
    "  chat-reply without trying. Refine-time `chat` is RESERVED for\n"
    "  greetings / thanks / single-turn conversational text with NO action\n"
    "  verb AND no external-info need.\n"
    "\n"
    "Intent classification:\n"
    "  chat        -- greeting, thanks, single-turn conversation; no system\n"
    "                 effect needed; emit `reply` and no agent is called.\n"
    "                 NOT for any 'open / find / launch / install / show /\n"
    "                 reveal / run / start <X>' intent -- those need\n"
    "                 tools and must route to `agent` or `dag`.\n"
    "  dispatch    -- maps to ONE MiOS verb; tool + args populated by the\n"
    "                 existing router. Refine just rewrites refined_text.\n"
    "  agent       -- needs a sub-agent for ONE coherent goal. Pick\n"
    "                 target_agent by role:\n"
    "                 * general    (Hermes)        -- broad reasoning + tools\n"
    "                 * coding     (OpenCode)      -- file edits / refactor / git\n"
    "                 * telemetry  (mios-daemon-agent) -- 'what just happened?',\n"
    "                              log/journal tail, recent system activity\n"
    "                              follow-ups. Pinned to 2 cores; always-on.\n"
    "  dag         -- ONE goal broken into multiple dependent steps; the\n"
    "                 planner will decompose. target_agent can be empty.\n"
    "  multi_task  -- the user crammed SEVERAL INDEPENDENT goals into one\n"
    "                 prompt (e.g. 'open chrome AND install vscode AND\n"
    "                 summarize my journal'). Emit a `tasks` array with one\n"
    "                 entry per discrete goal, ordered by priority. The\n"
    "                 dispatcher runs task #1 immediately, queues the rest\n"
    "                 in kanban for sequential execution.\n"
    "\n"
    "RULES:\n"
    "- ALWAYS emit valid JSON. No prose around it.\n"
    "- `hint_tools` lists MiOS verb names you think the agent will need\n"
    "  (open_app, focus_window, text_view, winget_search, ...).\n"
    "- For 'find <X>' / 'where is <X>' / 'show me the <X> file' queries,\n"
    "  ALWAYS hint `directory_lookup` -- sub-100ms DB query against the\n"
    "  mios-daemon cache (~19k indexed entries). Falls back to\n"
    "  `everything_search` (Windows-side live search) or `fs_search`\n"
    "  (Linux-side deep walk) only when the cache misses.\n"
    "- `hint_skills` lists C.2 skill names from the catalog\n"
    "  (open-and-focus, install-flatpak-app, window-tile-side-by-side).\n"
    "- For conversational input (greetings, small talk, single-turn\n"
    "  questions like 'how are you', acknowledgements, thanks):\n"
    "  pick intent=chat AND populate `reply` with a brief, natural\n"
    "  response. Do NOT delegate to a sub-agent. Examples that should\n"
    "  ALWAYS be chat: 'hey', 'hi', 'hello', 'thanks', 'thank you',\n"
    "  'how's it going', 'how are you', 'good morning', 'bye'.\n"
    "  When in doubt about conversational vs. agent: if the user is\n"
    "  not asking for a system action / file / data / code, chat.\n"
    "- multi_task vs dag: dag = ONE goal, dependent steps (e.g. 'install\n"
    "  vscode and open it'). multi_task = SEVERAL goals, independent\n"
    "  (e.g. 'install vscode AND THEN ALSO summarize my journal AND\n"
    "  THEN ALSO post a status to discord'). Three+ unrelated\n"
    "  imperatives joined by `and`/`also`/`then` is the multi_task tell.\n"
    "- multi_task MUST emit `tasks` with >= 2 entries. If you only\n"
    "  find one goal, use intent=agent or intent=dag instead.\n"
    "- RESEARCH-AND-REPORT: when the goal is to GATHER information on one\n"
    "  or more topics and report the findings back IN THE ANSWER (rather\n"
    "  than putting something on the operator's screen), it is research,\n"
    "  not launching. Decompose into one INDEPENDENT research task per\n"
    "  topic so they dispatch CONCURRENTLY (depends_on empty), each\n"
    "  delegated to a web_search-capable sub-agent that fetches + reads\n"
    "  page content via Hermes's native Chrome browsing; finish with a\n"
    "  synthesis step that combines the findings into one report. NEVER\n"
    "  map a 'check / look up / find out <topic>' goal to open_url or to\n"
    "  opening a visible browser window per topic -- open_url only SHOWS a\n"
    "  page the operator explicitly asked to see.\n"
    "- `tool_cards` rationale (ReWOO + MCP-style annotations): the\n"
    "  worker agent (Hermes / OpenCode / daemon-agent) sees ONLY what\n"
    "  you emit. If you list tools in hint_tools but the worker has\n"
    "  no idea WHY each one was hinted, it'll re-derive the plan\n"
    "  itself (slow + error-prone). Per-step `tool_cards` carry the\n"
    "  WHY + the success predicate, so the worker just executes. For\n"
    "  multi-step goals (3+ tool calls), emit tool_cards even when\n"
    "  intent stays `agent` -- they're additive guidance, not a new\n"
    "  intent class. Skip tool_cards for intent=chat or single-step\n"
    "  dispatch (no value vs. cost).\n"
    "- For dag: tool_cards' `output_used_by` lets the worker chain\n"
    "  step outputs (e.g. step 0 lists games -> step 1 web_search\n"
    "  ratings -> step 2 launches winner). Worker substitutes #E0,\n"
    "  #E1 placeholders into args at execute time -- you don't have\n"
    "  to know the runtime values.\n"
    "\n"
    "Length cue (CRITICAL): intent=chat is for SHORT conversational\n"
    "inputs (~ <40 chars: 'hi', 'how are you', 'thanks'). intent=\n"
    "dispatch is for SHORT verb invocations (~ <60 chars: 'open\n"
    "chrome', 'launch steam', 'screenshot'). If the user_text is\n"
    "LONG (>100 chars) it almost certainly describes a multi-step\n"
    "goal -- pick intent=dag (or multi_task for unrelated parallel\n"
    "goals) and decompose. A long-text intent=dispatch is almost\n"
    "always wrong -- the args would have to carry a semantic\n"
    "descriptor (e.g. 'the highest reviewed game I have installed')\n"
    "which the launcher can't resolve to a real app.\n"
    "\n"
    "Arg-concreteness rule: when emitting intent=dispatch, every\n"
    "args value MUST be a concrete identifier (app name, file\n"
    "path, URL, fully-qualified id). NEVER a semantic phrase\n"
    "('highest', 'best', 'the one with X', 'whichever is fastest').\n"
    "If the right value can't be known without first running other\n"
    "tools, pick intent=dag with the lookup as step 0 and the\n"
    "dispatch as a downstream node using #E0 substitution.\n"
)


# Compact "light refine" prompt (operator architecture 2026-05-20: the
# micro just classifies + lightly refines/contextualizes; heavy step
# planning belongs to the planner downstream). The full _REFINE_SYSTEM
# above is ~1500 tokens -> 14-26s prefill on the 0.6b CPU micro AND
# confused its classification (called a web query "chat"). This tight
# version is ~450 tokens -> a few seconds, and the 0.6b classifies the
# same web query correctly (operator test 2026-05-20).
_REFINE_SYSTEM_LITE = (
    "You are MiOS-Agent's refine pass. Read the user's message + recent\n"
    "history and output ONE compact JSON object (no prose).\n"
    "\n"
    "Fields:\n"
    '  "intent": chat | agent | multi_task   (coarse -- the planner\n'
    "    decides single-step vs multi-step downstream)\n"
    '  "refined_text": the request rewritten clearly + actionably\n'
    '  "intended_outcome": one line -- what the user expects back\n'
    '  "target_agent": a registered sub-agent chosen by role\n'
    '  "hint_tools": [verb names from the catalog the agent will need]\n'
    '  "reply": ONLY when intent=chat -- your short direct reply\n'
    '  "tasks": ONLY when intent=multi_task -- one entry per goal\n'
    "\n"
    "Classify by what the request fundamentally NEEDS, never by keywords:\n"
    "  chat = the user only wants conversation; the answer is already\n"
    "    fully contained in ordinary dialogue -- nothing must be looked\n"
    "    up, fetched, computed, or done on the machine. Emit reply.\n"
    "  agent = the user wants something DONE on this computer, or KNOWN\n"
    "    from information not already present in this conversation. The\n"
    "    agent owns the tools (system control, local file search, web\n"
    "    search/extract) and must USE them rather than guess or refuse.\n"
    "  multi_task = the message holds several independent goals; emit a\n"
    "    tasks array (>=2 entries).\n"
    "  Default to agent whenever the request is not purely conversation;\n"
    "  when in doubt between chat and agent, choose agent.\n"
    "\n"
    "GROUNDING (no fabrication): when answering needs information not\n"
    "already in this conversation -- anything external or current the agent\n"
    "would look up rather than already know -- classify it agent so the\n"
    "agent FETCHES it with the matching tool; such facts are never recalled\n"
    "from memory or invented. The agent chooses the tool by purpose, not by\n"
    "keyword. Never address the operator by a personal name they did not\n"
    "give; use no name rather than a guessed one.\n"
    "\n"
    "LANGUAGE: write refined_text, intended_outcome, and reply in ENGLISH\n"
    "by default. Use another language ONLY when the operator's own message\n"
    "is clearly written in that language -- then keep every human-readable\n"
    "value in that ONE language. Never drift to a language the operator did\n"
    "not use. JSON keys + verb/tool names stay as-is (identifiers).\n"
)


async def _quick_chat_reply(user_text: str, history: list = None) -> str:
    """Generate the conversational reply for an intent=chat turn.

    Separate from refine because the JSON classifier reliably tags chat
    but does NOT reliably emit a `reply` field (operator test 2026-05-20:
    greetings classified chat with reply=None -> the turn fell through to
    Hermes, which then tried a nonexistent 'chat' verb). think=False on
    the micro lane; plain prose, GENERATED in the user's language (never
    a canned/hardcoded string)."""
    if not user_text or not user_text.strip():
        return ""
    msgs = [{"role": "system",
             "content": ("You are MiOS AI. Reply to the user directly and "
                         "concisely, in ENGLISH by default -- switch to "
                         "another language ONLY if the user's own message "
                         "is clearly written in it. Never drift to a "
                         "language the user did not use. Plain text only -- "
                         "no tools, no JSON.")}]
    if history:
        for h in history[-2:]:
            if isinstance(h, dict) and h.get("role") in ("user", "assistant"):
                msgs.append({"role": h["role"],
                             "content": str(h.get("content", ""))[:200]})
    msgs.append({"role": "user", "content": user_text[:500]})
    payload = {
        "model": REFINE_MODEL,
        "messages": msgs,
        "think": False,
        "stream": False,
        "options": {"temperature": 0.5, "num_predict": 200},
    }
    try:
        async with httpx.AsyncClient(timeout=REFINE_TIMEOUT_S) as s:
            r = await s.post(f"{REFINE_ENDPOINT}/api/chat", json=payload,
                             headers={"Content-Type": "application/json"})
            if r.status_code != 200:
                return ""
            body = r.json()
    except Exception:
        return ""
    msg = body.get("message") if isinstance(body.get("message"), dict) else {}
    return (msg.get("content") or "").strip()


RAG_ENABLED = os.environ.get(
    "MIOS_AGENT_PIPE_RAG_ENABLED", "true").lower() not in {"false", "0", "no"}
RAG_BIN = os.environ.get("MIOS_RAG_BIN", "/usr/libexec/mios/mios-rag")
RAG_K = int(os.environ.get("MIOS_AGENT_PIPE_RAG_K", "4"))


async def _rag_enrich(query: str) -> str:
    """Enrich stage: pull RAG context from the SurrealDB vector store
    (mios-rag query, nomic-embed + cosine) so EVERY agent/sub-agent turn
    sees relevant MiOS knowledge in-loop (operator 2026-05-20: "RAG in
    the loop for all agents every turn"). Returns a formatted context
    block, or '' on miss/error -- best-effort, never blocks the turn."""
    if not RAG_ENABLED or not query or not query.strip():
        return ""
    try:
        proc = await asyncio.create_subprocess_exec(
            RAG_BIN, "query", query[:500], "--k", str(RAG_K),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL)
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        d = json.loads((out or b"{}").decode("utf-8", "replace") or "{}")
    except Exception as e:
        log.debug("rag enrich skipped: %s", e)
        return ""
    hits = d.get("hits") or []
    lines = [f"- ({h.get('source', '')}) {str(h.get('text', '')).strip()[:320]}"
             for h in hits if isinstance(h, dict) and h.get("text")]
    if not lines:
        return ""
    return ("MiOS knowledge relevant to this request (retrieved; cite/use "
            "if helpful, ignore if not):\n" + "\n".join(lines))


async def refine_intent(user_text: str,
                        history: list = None) -> Optional[dict]:
    """Quick-refine pass. Returns the parsed plan dict or None on
    bypass / error (caller falls through to the legacy router path).

    Bypass: trivial inputs (greetings, single-word commands) skip
    refine entirely. The existing classify_intent router handles
    them with its own chat-reply path in one LLM call -- adding a
    refine pass on top would be wasted latency. Local-compute-aware
    per operator directive 2026-05-18 'fast and efficient for pure
    local compute'."""
    if not REFINE_ENABLED or not user_text or not user_text.strip():
        return None
    # No length-based trivial bypass: it mis-classed short ACTION
    # commands ("Check system status", "Take screenshot", "Open chrome")
    # as chat -> the chat short-circuit then faked a reply without
    # running the tool (operator 2026-05-20). The capable refine model
    # below classifies every non-empty query instead -- greetings still
    # land as intent=chat, real actions as intent=agent.
    # Pull the registered agents into the prompt so the model picks
    # one that actually exists.
    agents_summary = "\n".join(
        f"  - {n}: role={c.get('role','?')} "
        f"strengths={','.join(c.get('strengths') or [])[:80]}"
        for n, c in _AGENT_REGISTRY.items()
    )
    # Thinking is disabled at the API level (think=False on /api/chat
    # below) rather than via the `/no_think` token -- operator test
    # 2026-05-20 proved the qwen3 micros ignore /no_think (modelfile
    # thinking-mode override) and dump the answer into message.reasoning,
    # leaving message.content EMPTY.
    system = (_REFINE_SYSTEM_LITE
              + "\n" + _temporal_grounding()
              + "\nRegistered sub-agents:\n" + agents_summary)
    msgs = [{"role": "system", "content": system}]
    # Last 2 turns of history, tightly capped -- the OWUI pipe already
    # enhances the prompt before it reaches us, so re-feeding long
    # history here just slows the CPU refine (operator 2026-05-20:
    # refine hit 13-45s on a ~1646-char input). Keep it lean.
    if history:
        for h in history[-2:]:
            if isinstance(h, dict) and h.get("role") in ("user", "assistant"):
                msgs.append({"role": h["role"],
                             "content": str(h.get("content", ""))[:200]})
    # Cap the refine input to the TAIL. OWUI's RAG ("Searching Knowledge")
    # rewrites the user turn as "<context...>\n\nQuery: <actual question>"
    # -- the real question is at the END (operator test 2026-05-20 showed a
    # 6207-char user_text for a one-line question; CPU refine scales with
    # length). Keep the last 1500 chars so the question + nearby context
    # survive while latency stays bounded.
    msgs.append({"role": "user", "content": user_text[-1500:]})
    # ollama native /api/chat with think=False: the qwen3 micro then emits
    # the JSON straight to message.content (~0.4s warm) instead of dumping
    # it into message.reasoning with an empty content (the /v1 + /no_think
    # failure mode that made refine default to chat + an empty reply).
    payload = {
        "model": REFINE_MODEL,
        "messages": msgs,
        "think": False,
        "format": "json",
        "stream": False,
        "keep_alive": REFINE_KEEP_ALIVE,
        "options": {"temperature": 0.0,
                    "num_predict": REFINE_MAX_TOKENS},
    }
    url = f"{REFINE_ENDPOINT}/api/chat"
    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=REFINE_TIMEOUT_S) as s:
            r = await s.post(url, json=payload,
                             headers={"Content-Type": "application/json"})
            if r.status_code != 200:
                log.warning("refine: backend %s in %.1fs",
                            r.status_code, time.time() - t0)
                return None
            body = r.json()
    except (httpx.HTTPError, asyncio.TimeoutError) as e:
        log.warning("refine: timeout/http error after %.1fs: %s",
                    time.time() - t0, e)
        return None
    except Exception as e:
        log.warning("refine unexpected error: %s", e)
        return None
    elapsed = time.time() - t0
    # /api/chat shape is {"message": {"content": ...}}; fall back to the
    # /v1 choices[] shape so an endpoint override still parses.
    msg = body.get("message")
    if not isinstance(msg, dict):
        choices = body.get("choices") or []
        msg = (choices[0].get("message") if choices else {}) or {}
    content = (msg.get("content") or "").strip()
    if not content:
        log.warning("refine: %.1fs empty_content", elapsed)
        return None
    # qwen3-style reasoning models sometimes wrap output in
    # <think>...</think> blocks before the JSON. Strip them so
    # the JSON parser sees just the structured plan.
    content = re.sub(r"<think>.*?</think>\s*", "", content,
                     flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r"^\s*```(?:json)?\s*\n?", "", content)
    content = re.sub(r"\n?```\s*$", "", content)
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        log.warning("refine: %.1fs parse_fail: %s; preview=%r",
                    elapsed, e, content[:200])
        return None
    if not isinstance(parsed, dict):
        log.warning("refine: %.1fs not_dict type=%s",
                    elapsed, type(parsed).__name__)
        return None
    log.info("refine: %.1fs intent=%s target=%s",
             elapsed, parsed.get("intent"), parsed.get("target_agent"))
    # Stash routing-metadata onto the envelope so downstream SSE
    # emit sites can surface "refine: 17.7s qwen3:1.7b intent=agent"
    # instead of the bare "refine" label.
    parsed["_elapsed_s"] = round(elapsed, 1)
    parsed["_model"] = REFINE_MODEL
    parsed["_endpoint"] = REFINE_ENDPOINT
    # Chat-classify guard: a small refine model occasionally picks
    # intent=chat for an input that's CLEARLY actionable (literal
    # CLI verb, fully-qualified URL, `mios-*` shim invocation) and
    # fabricates a confirmation `reply` text. Force-promote to
    # dispatch when the user text is shaped like a command or URL.
    # Language-agnostic: keyed off path / scheme prefixes, NOT on
    # any natural-language tokens (operator binding).
    if parsed.get("intent") == "chat":
        _ut = (user_text or "").strip()
        _looks_actionable = (
            _ut.startswith(("mios-", "/", "./", "sudo ", "systemctl ",
                            "podman ", "docker ", "git ", "curl ",
                            "wsl.exe", "powershell.exe", "cmd.exe"))
            or "://" in _ut
        )
        if _looks_actionable:
            log.info(
                "refine: chat promoted to dispatch "
                "(text starts with verb/URL token)")
            parsed["intent"] = "dispatch"
            parsed.pop("reply", None)
    # multi_task sanity: collapse to `agent` if the model produced
    # the multi_task intent with <2 tasks. Avoids surfacing an empty
    # kanban queue when the model was over-eager.
    if parsed.get("intent") == "multi_task":
        tasks = parsed.get("tasks") or []
        if not isinstance(tasks, list) or len(tasks) < 2:
            log.info(
                "refine: multi_task degraded to agent (tasks=%s)",
                len(tasks) if isinstance(tasks, list) else "non-list",
            )
            parsed["intent"] = "agent"
            # Keep the MULTI-STEP signal: refine SAW multiple steps but did
            # not itemise them. The handler hands this to the planner to
            # decompose into a concurrent per-agent DAG (operator 2026-05-22).
            parsed["_multi_step"] = True
            parsed.pop("tasks", None)
    # Long-prompt guard (language-agnostic): a real intent=chat /
    # intent=dispatch input is short (greeting, single verb).
    # When the user_text is >100 chars but the refine model still
    # picked one of those shallow intents, it almost always missed
    # multi-step structure. Promote to `agent` so the worker (or
    # the planner DAG) decomposes properly. Operator-flagged trace:
    # 134-char "find all games; research ratings; launch highest"
    # was classified intent=dispatch with args="highest reviewed
    # game" and the launcher picked Ubisoft as nearest substring.
    _ut = (user_text or "").strip()
    if (parsed.get("intent") in ("chat", "dispatch")
            and len(_ut) > 100):
        log.info(
            "refine: %s promoted to agent (user_text=%d chars > 100)",
            parsed["intent"], len(_ut))
        parsed["intent"] = "agent"
        parsed.pop("reply", None)
    # Arg-shape guard: a dispatch arg value of >3 words is almost
    # certainly a semantic descriptor (e.g. "highest reviewed
    # game", "any browser will do"), not a concrete identifier the
    # launcher can resolve. Promote to agent so the worker
    # disambiguates with tool calls. Language-agnostic: counts
    # whitespace-separated tokens.
    if parsed.get("intent") == "dispatch":
        _args = parsed.get("args") if isinstance(parsed.get("args"), dict) else {}
        _wordy = False
        for v in _args.values():
            if isinstance(v, str) and len(v.strip().split()) > 3:
                _wordy = True
                break
        if _wordy:
            log.info(
                "refine: dispatch promoted to agent "
                "(arg value contained a multi-word semantic phrase)")
            parsed["intent"] = "agent"
    # Best-effort event row.
    _db_fire(_db_post(_db_create("event", {
        "source": "mios-agent-pipe",
        "kind": "refine",
        "severity": "info",
        "summary": str(parsed.get("intent", "?"))[:120],
        "payload": parsed,
    }, now_fields=("ts",))))
    return parsed


def _shadow_queue_tasks(tasks: list[dict],
                        session_id: Optional[str]) -> list[dict]:
    """Write one kanban_shadow row per refined multi-task entry.
    Returns the same list augmented with `hermes_task_id` so the
    dispatcher + polish can refer to each row by id.

    The shadow rows give every agent in the stack a single
    SurrealDB-visible queue without coupling to Hermes's SQLite
    schema. Hermes (or whichever sub-agent picks up a task) syncs
    its native kanban entry back via the existing sync path."""
    if not isinstance(tasks, list) or not tasks:
        return []
    out: list[dict] = []
    for i, t in enumerate(tasks):
        if not isinstance(t, dict):
            continue
        # Stable id so the same task in a retried request collapses
        # onto the same shadow row (UNIQUE INDEX on hermes_task_id).
        tid = (
            "mt-"
            + (session_id or "anon")[:12].replace(":", "")
            + "-"
            + f"{i:02d}"
        )
        title = str(t.get("title") or t.get("refined_text") or "")[:200]
        # First task -> in_progress; rest -> todo. The dispatcher
        # immediately runs index 0, so its status reflects that.
        status = "in_progress" if i == 0 else "todo"
        prio = t.get("priority")
        prio_str = str(prio) if prio is not None else None
        row = {
            "hermes_task_id": tid,
            "title": title,
            "status": status,
            "priority": prio_str,
            "tags": ["multi_task", "agent-pipe-refined"],
        }
        _db_fire(_db_post(
            _db_create("kanban_shadow", row, now_fields=("synced_at",))
        ))
        out.append({**t, "hermes_task_id": tid, "status": status})
    _db_fire(_db_post(_db_create("event", {
        "source": "mios-agent-pipe",
        "kind": "multi_task_queued",
        "severity": "info",
        "summary": f"queued {len(out)} tasks from refine",
        "payload": {"task_ids": [t["hermes_task_id"] for t in out],
                    "titles": [t.get("title", "") for t in out]},
    }, now_fields=("ts",))))
    return out


def _multi_task_preamble(queued: list[dict],
                         active_idx: int = 0) -> str:
    """Render a short user-facing preamble surfacing what's in the
    queue. Goes at the TOP of the polished reply so the operator
    sees the queue state up front (and the polished response for
    the active task comes immediately below)."""
    if not queued or len(queued) < 2:
        return ""
    active = queued[active_idx]
    others = [t for i, t in enumerate(queued) if i != active_idx]
    lines = [
        f"**Queued {len(queued)} tasks from your message.**",
        f"Starting now: _{active.get('title','(untitled)')}_",
        "",
        "Queued for follow-up (run `mios continue` or just say "
        "'next task'):",
    ]
    for t in others:
        lines.append(f"  - {t.get('title','(untitled)')}")
    lines.append("")
    return "\n".join(lines)


_POLISH_SYSTEM = (
    # LANGUAGE RULE FIRST + the word "polish" is deliberately AVOIDED in this
    # prompt: a multilingual base (qwen3.5:4b) primes on the homonym
    # "polish" -> the Polish LANGUAGE and emits Polish for English input
    # (operator 2026-05-22, reproduced on the bare base). State the
    # language target up front and never name the task "polish".
    "Write your answer in ENGLISH. Use another language ONLY if the\n"
    "operator's ORIGINAL message (in the user turn) is itself clearly\n"
    "written in that language -- then reply in that ONE language only.\n"
    "Never add a translation, never switch language mid-reply, and never\n"
    "drift to a language the operator did not use.\n"
    "\n"
    "You are MiOS-Agent's final-answer pass. The raw answer below came\n"
    "from a sub-agent. Your job: produce the FINAL user-facing response by\n"
    "re-shaping that draft to match the intended outcome -- nothing more.\n"
    "Be tight. Add no new content, do not editorialise, do not attribute\n"
    "the answer to the agent. Strip internal-reasoning leaks (thought /\n"
    "reasoning / plan lines, tool-call envelopes, thinking blocks).\n"
    "\n"
    "OUTPUT ONLY THE ANSWER TEXT. No preamble, no meta-commentary about\n"
    "reformatting, no restating the question, no thinking\n"
    "blocks, no answer-label header. The operator sees your output\n"
    "verbatim, so any preamble reads as if the assistant answered twice.\n"
    "Start directly with the answer.\n"
    "\n"
    "NEVER NARRATE YOUR OWN PROCESS. The operator sees only the answer\n"
    "itself -- never commentary about the draft, the tool history, what\n"
    "the response 'should' do, nor any analysis or strategy header.\n"
    "\n"
    "SYNTHESIS: build the answer from the information actually present in\n"
    "the draft and tool results. If a usable answer is already there,\n"
    "never undercut it with a claim that the data is unavailable or the\n"
    "request cannot be met -- contradicting your own content is a defect.\n"
    "Read the request by its evident intent and answer with what the\n"
    "information supports.\n"
    "\n"
    "NO NON-ANSWERS (operator-binding): NEVER reply that something 'could\n"
    "not be provided because no tools were invoked' or that no data was\n"
    "gathered. That is a dead-end failure, not an answer. A greeting or\n"
    "open-ended turn -- 'how's it going', 'get me up to speed', 'what's\n"
    "new' -- is CONVERSATIONAL: answer it naturally and warmly from the\n"
    "draft (the sub-agents' replies ARE your material). If the operator\n"
    "wants live specifics not in hand, give what you do have and OFFER the\n"
    "concrete next step ('I can pull your live system status / recent\n"
    "activity -- want it?') -- never a flat refusal. This does NOT loosen\n"
    "the side-effect rules below: still never CLAIM an action happened\n"
    "without its tool -- but 'I haven't done X yet; want me to?' is a real\n"
    "answer, while 'X could not be provided because no tool ran' is not.\n"
    "\n"
    "WEB GROUNDING (anti-fabrication): for any factual claim drawn from a\n"
    "web_search / web_extract result, state ONLY what the fetched results\n"
    "actually say. If the results do NOT cover part of the question, say so\n"
    "plainly -- do NOT fill the gap from memory and do NOT invent specifics\n"
    "(dates, etymologies, origins, names, numbers). Attach a citation [n]\n"
    "ONLY to the source that actually supports that claim; NEVER reuse one\n"
    "source's number for an unrelated claim. An honest 'the search didn't\n"
    "cover X' beats a confident fabrication.\n"
    "\n"
    "ONE ANSWER: when several sub-agent drafts are present, MERGE them into a\n"
    "single clean reply -- dedupe, drop repetition, reconcile conflicts. Do\n"
    "NOT concatenate the agents' separate takes or repeat a point once per\n"
    "agent.\n"
    "\n"
    "GROUND TRUTH: the tool_result.success field in the tool history is\n"
    "authoritative for what actually happened. Decide first whether this\n"
    "turn's tools succeeded. When every relevant result is success=true\n"
    "(or stdout shows the window was presented to the operator), the turn\n"
    "succeeded: report it plainly. Do not invent a failure and do not\n"
    "distrust a confirmed success. Surface a failure ONLY when a result\n"
    "is actually success=false, or the history carries a repeat-call halt\n"
    "marker -- and then do it cleanly: quote the failing tool's stderr\n"
    "verbatim, name the verb and its args, and give one concrete next\n"
    "step, as a plain statement to the operator. Misreading success as\n"
    "failure is as serious a defect as the reverse. A launched / opened /\n"
    "started claim is valid only when a matching result is success=true;\n"
    "drop any success the history does not back and report what actually\n"
    "happened instead.\n"
    "\n"
    "INVOKED-TOOL CHECK: the user turn may list 'Tools the agent ACTUALLY\n"
    "invoked this turn'. A claim that a SIDE-EFFECTING action completed --\n"
    "sent, posted, delivered, messaged, launched, opened, created, saved,\n"
    "installed, deleted, scheduled -- is valid ONLY if a tool that plausibly\n"
    "performs it is in that invoked list. If the draft asserts such an action\n"
    "but NO matching tool was invoked (or the invoked list is empty), the\n"
    "action did NOT happen: do NOT repeat the false claim. Instead say plainly\n"
    "what was actually produced, or that the action could not be completed --\n"
    "and, if a required detail is missing (e.g. no destination configured),\n"
    "name it. A fabricated 'done' is a serious defect.\n"
    "\n"
    "LOCALE: language is governed by the rule at the very top (English by\n"
    "default). Never pass through foreign-locale text leaked from the\n"
    "draft's reasoning. Keep every measurement in the units the tool\n"
    "results returned; never silently convert a figure.\n"
    "\n"
    "NO FABRICATION: never introduce a fact, name, figure, date, or claim\n"
    "that is not already in the draft or the tool results. If the draft\n"
    "addresses the operator by a personal name the request did not supply,\n"
    "REMOVE the name -- never invent or guess an identity. If the draft\n"
    "asserts an external/current fact with no tool result behind it, do\n"
    "not present it as confirmed; keep only what the tools returned.\n"
    "\n"
    "SOURCE LINKS: when the tool results carry source URLs, surface them\n"
    "verbatim so the operator can verify; never invent, alter, or guess a\n"
    "URL, and never attach one to a claim the results do not support.\n"
    "\n"
    "VERBATIM TOKENS: copy every path, URL, id, port, tag, size, or\n"
    "percentage from the draft character-for-character. Never re-tokenise,\n"
    "spell-correct, or 'fix' such a token; if you cannot read one, omit\n"
    "its line rather than guess.\n"
    "\n"
    "Output the polished answer ONLY -- no prose around it, no JSON.\n"
)


async def _inline_satisfaction_check(
    session_id: Optional[str], refined: Optional[dict],
    *,
    agent_tools_called: Optional[list] = None,
    agent_answered: Optional[bool] = None,
) -> Optional[dict]:
    """CONFIRMATION ENGINE (operator 2026-05-22). Run a synchronous
    Definition-of-Done check on THIS turn and emit a
    user_query_(un)satisfied event for the current session. mios-daemon's
    async loop ticks every 30s and only sees PRIOR turns; without this
    inline check, polish never knows whether the current turn actually
    succeeded and can't ground-truth the wrapped reply against it.

    Two signal sources, in priority order:
      1. tool_call rows agent-pipe recorded this turn (dispatch / DAG
         fast-paths write these) -> AND-fold their success fields.
      2. The agent-path signals `agent_tools_called` (verb names the
         sub-agent invoked inside its OWN tool-loop, captured from the
         stream) + `agent_answered` (the sub-agent produced a non-empty
         final answer). Under unify-on a verb like mios-os-control runs
         INSIDE Hermes, so agent-pipe records NO tool_call row for it --
         "no rows" then means the agent handled the turn, NOT that it
         failed. Treating that as `no_tools_seen -> unsatisfied` was the
         false-negative that made polish report failure on a succeeded
         verb and made the critic re-litigate a done answer (the
         "succeeds early then reports failed" bug). A delivered answer
         is DoD-met: the turn is DONE. Whether the ACTION inside it
         succeeded is then carried by the agent's own answer + any
         recorded rows -- polish relays a failure the agent states, but
         is no longer told the whole turn failed.

    Returns the emitted verdict dict {kind, payload} or None when
    there is nothing to judge. The agent-path caller uses the returned
    kind to HALT the chain (skip the critic re-pass) on a confirmed
    success. Best-effort: any DB hiccup returns None instead of
    failing the turn."""
    if not session_id or not isinstance(refined, dict):
        return None
    intent = str(refined.get("intent") or "").strip()
    intended = str(refined.get("intended_outcome") or "")[:200]
    # Fetch this turn's tool_calls (since the refine row was
    # written). Use a generous 5-min lookback that comfortably
    # covers a slow refine + sub-agent loop. `ts` MUST be in the
    # projection: SurrealDB 3.x rejects an ORDER BY on a field that
    # isn't selected ("Missing order idiom `ts`") with an HTTP 400,
    # which made _db_post return None (and trip a 30s DB backoff) --
    # the check then always bailed once a real session_id existed.
    sql = (
        f"SELECT ts, tool, args, result_preview, success, "
        f"exit_code, latency_ms FROM tool_call "
        f"WHERE session = {session_id} "
        f"  AND ts > time::now() - 5m "
        f"ORDER BY ts ASC;"
    )
    try:
        r = await _db_post(sql)
    except Exception:
        return None
    if not r:
        return None
    rows = (r[-1] or {}).get("result") or []
    if not isinstance(rows, list):
        return None
    # AND-fold (same logic shape as mios-daemon._emit_satisfaction
    # but inline). For intent=chat no tools is expected = satisfied.
    if not rows:
        if intent == "chat":
            verdict = {
                "kind": "user_query_satisfied",
                "reason": "chat_no_tools_expected",
            }
        elif agent_answered:
            # Agent path: the sub-agent ran its own tool-loop (results
            # internal to it -> no agent-pipe tool_call row) and
            # delivered an answer. Turn is DONE = DoD-met. Record which
            # verbs it invoked for the audit trail.
            verdict = {
                "kind": "user_query_satisfied",
                "reason": "agent_answer_delivered",
                "agent_tools": [str(t) for t in (agent_tools_called or [])],
            }
        else:
            # No recorded tools AND no agent answer: a genuine no-op
            # (empty backend reply / dead endpoint).
            verdict = {
                "kind": "user_query_unsatisfied",
                "reason": "no_tools_seen",
            }
    else:
        failed: list[dict] = []
        for tc in rows:
            if not bool(tc.get("success")):
                failed.append({
                    "tool": tc.get("tool"),
                    "exit_code": tc.get("exit_code"),
                    "stderr_preview": (
                        tc.get("result_preview") or "")[:200],
                })
        if not failed:
            verdict = {
                "kind": "user_query_satisfied",
                "tools_checked": len(rows),
                "all_succeeded": True,
            }
        else:
            verdict = {
                "kind": "user_query_unsatisfied",
                "tools_checked": len(rows),
                "failed_tools": failed,
            }
    # STRUCTURAL action-claim validation (P5; the operator's "LIE"):
    # language-agnostic -- NO action-word lists. If the refined PLAN intended a
    # WRITE-permission action (intent=agent/multi_task + a write-permission verb
    # in hint_tools) but NOT ONE write-permission verb was actually invoked this
    # turn (neither in the agent's own tool-loop nor a recorded successful
    # dispatch), the side-effecting action did NOT happen -> flag it so polish's
    # INVOKED-TOOL CHECK has an authoritative structural signal and won't let a
    # fabricated "done" stand. Conservative (fires only on ZERO write verbs) so
    # it never false-flags a turn that legitimately acted; hint_tools are
    # suggestions, hence we test the write-PERMISSION class, not the exact verb.
    try:
        if intent in ("agent", "multi_task"):
            def _is_write_verb(v) -> bool:
                return str((_VERB_CATALOG.get(str(v)) or {})
                           .get("permission", "")).lower() == "write"
            _write_hinted = sorted({
                str(h) for h in ((refined or {}).get("hint_tools") or [])
                if _is_write_verb(h)})
            if _write_hinted:
                _invoked = {str(t) for t in (agent_tools_called or [])}
                _invoked |= {str(tc.get("tool")) for tc in rows
                             if tc.get("success")}
                if not any(_is_write_verb(t) for t in _invoked):
                    verdict["write_action_unmet"] = {
                        "hinted": _write_hinted,
                        "reason": "plan_intended_write_action_none_invoked",
                    }
    except Exception:
        pass
    kind = verdict["kind"]
    summary = f"{kind}: {intent or '?'} ({intended[:60]})"
    body = {
        "refine_intent": intent,
        "intended_outcome": intended,
        "source": "mios-agent-pipe-inline",
        **verdict,
    }
    # Write synchronously so polish's subsequent query picks it
    # up as the most-recent verdict for this session.
    try:
        await _db_post(_db_create("event", {
            "source": "mios-agent-pipe",
            "kind": kind,
            "severity": "info" if kind == "user_query_satisfied" else "warn",
            "summary": summary,
            "payload": body,
        }, now_fields=("ts",)))
    except Exception:
        pass
    return {"kind": kind, "payload": body}


async def _recent_satisfaction_verdicts(limit: int = 3) -> list[dict]:
    """Pull recent mios-daemon satisfaction verdicts (Phase E.1).
    These are post-hoc audit rows the daemon emits every ~30s based
    on AND-folding tool_call outcomes against refine intent. Polish
    uses them to ground the response in CROSS-TURN truth -- if the
    operator's previous query was flagged unsatisfied, the next
    response shouldn't paraphrase it as having worked."""
    sql = (
        "SELECT ts, kind, summary, payload FROM event "
        "WHERE kind = 'user_query_satisfied' "
        "   OR kind = 'user_query_unsatisfied' "
        "ORDER BY ts DESC LIMIT " + str(int(limit)) + ";"
    )
    r = await _db_post(sql)
    if not r:
        return []
    rows = (r[-1] or {}).get("result") or []
    return rows if isinstance(rows, list) else []


def _format_satisfaction_block(rows: list[dict]) -> str:
    if not rows:
        return ""
    parts = [
        "Recent satisfaction verdicts from mios-daemon "
        "(MOST AUTHORITATIVE ground truth -- daemon AND-folds raw "
        "signals across multiple sources):"
    ]
    for row in rows:
        kind = row.get("kind", "")
        summary = (row.get("summary") or "")[:120]
        marker = "✓ satisfied" if kind == "user_query_satisfied" else "✗ UNSATISFIED"
        parts.append(f"  {marker}: {summary}")
        payload = row.get("payload") or {}
        if kind == "user_query_unsatisfied":
            reason = payload.get("reason")
            failed = payload.get("failed_tools") or []
            if reason:
                parts.append(f"    reason: {reason}")
            for f in failed[:3]:
                parts.append(
                    f"    failed: {f.get('tool')} exit={f.get('exit_code')} "
                    f"err={(f.get('stderr_preview') or '')[:80]}"
                )
        # Structural action-claim flag (P5): surfaced for ANY verdict (a turn
        # can be "satisfied" by an answer yet still have skipped a planned
        # side-effecting action). Gives polish's INVOKED-TOOL CHECK an explicit,
        # authoritative signal not to let a fabricated "done" stand.
        wau = payload.get("write_action_unmet")
        if isinstance(wau, dict) and wau.get("hinted"):
            parts.append(
                "    NOTE: the plan intended a side-effecting action ("
                + ", ".join(str(h) for h in wau["hinted"][:4])
                + ") but NO such action actually ran this turn -- do NOT claim "
                "it was done; state plainly that it was not performed.")
    return "\n".join(parts)


async def _recent_tool_history(session_id: Optional[str],
                               limit: int = 6) -> list[dict]:
    """Pull the most recent tool_call rows for this session so polish
    has ground-truth on what actually happened. Returns oldest-first
    so the prompt reads chronologically."""
    if not session_id:
        return []
    sql = (
        f"SELECT ts, tool, args, success, "
        f"result_preview, exit_code "
        f"FROM tool_call WHERE session = {session_id} "
        f"ORDER BY ts DESC LIMIT {int(limit)};"
    )
    r = await _db_post(sql)
    if not r:
        return []
    rows = (r[-1] or {}).get("result") or []
    # Reverse for chronological order in the prompt.
    return list(reversed(rows))


def _format_tool_history(rows: list[dict]) -> str:
    if not rows:
        return ""
    parts = ["Tool history (chronological; CHECK THIS BEFORE WRITING):"]
    for i, row in enumerate(rows, 1):
        tool = row.get("tool", "?")
        args = row.get("args") or {}
        ok = row.get("success")
        exit_code = row.get("exit_code")
        preview = (row.get("result_preview") or "")[:300]
        ok_label = "ok" if ok else (
            f"FAILED (exit={exit_code})" if ok is False else "?")
        parts.append(
            f"  [{i}] {tool}({json.dumps(args, default=str)[:120]}) "
            f"-> {ok_label}"
        )
        if preview.strip():
            parts.append(f"      result: {preview}")
    return "\n".join(parts)


# Reasoning-tag variants different models leak: qwen3 <think>, plus
# <thinking>/<thought>/<reasoning>/<reflection>/<scratchpad> seen from
# other backends. Tag-based stripping only -- STRUCTURAL, no English
# content matching, so the NO-HARDCODED-ENGLISH binding holds.
_THINK_TAGS = r"think|thinking|thought|reasoning|reflection|scratchpad"
_THINK_BLOCK_RE = re.compile(
    rf"<({_THINK_TAGS})\b[^>]*>.*?</\1>\s*", re.DOTALL | re.IGNORECASE)
_THINK_UNCLOSED_RE = re.compile(
    rf"<({_THINK_TAGS})\b[^>]*>.*$", re.DOTALL | re.IGNORECASE)
_THINK_ORPHAN_RE = re.compile(
    rf"</?({_THINK_TAGS})\b[^>]*>\s*", re.IGNORECASE)
_THINK_OPENERS = ("<think", "<thought", "<reason", "<reflect", "<scratch")
_THINK_CAP_RE = re.compile(
    rf"<({_THINK_TAGS})\b[^>]*>(.*?)</\1>", re.DOTALL | re.IGNORECASE)
_THINK_CAP_UNCLOSED_RE = re.compile(
    rf"<({_THINK_TAGS})\b[^>]*>(.*)$", re.DOTALL | re.IGNORECASE)


def _split_think_tags(text: str) -> tuple[str, str]:
    """Split model output into (reasoning, answer).

    Operator 2026-05-19: 'there SHOULD be thinking -- as a dropdown' AND
    'thinking bleeding into the final response makes it look like it
    answered twice'. The fix is to CAPTURE the <think>-family reasoning
    (so it can go in a collapsed dropdown) instead of discarding it, and
    return the answer with the reasoning removed (clean main reply).
    Handles closed + unclosed + orphan tags across the qwen3 <think> and
    <thinking>/<thought>/<reasoning>/<reflection>/<scratchpad> variants.
    Tag-based only -- structural, no English content matching."""
    if not text:
        return "", text
    low = text.lower()
    if not any(t in low for t in _THINK_OPENERS):
        return "", text
    thoughts: list[str] = []

    def _cap(m: "re.Match") -> str:
        thoughts.append((m.group(2) or "").strip())
        return ""
    answer = _THINK_CAP_RE.sub(_cap, text)
    m = _THINK_CAP_UNCLOSED_RE.search(answer)
    if m:
        thoughts.append((m.group(2) or "").strip())
        answer = _THINK_CAP_UNCLOSED_RE.sub("", answer)
    answer = _THINK_ORPHAN_RE.sub("", answer).strip()
    reasoning = "\n\n".join(t for t in thoughts if t).strip()
    return reasoning, answer


def _strip_think_tags(text: str) -> str:
    """Back-compat: return only the answer (reasoning discarded). Use
    _split_think_tags when the reasoning should be KEPT for a dropdown."""
    return _split_think_tags(text)[1]


# ── Knowledge storage ─────────────────────────────────────────────
# Operator pipeline spec 2026-05-23: "...present to user as final answer
# and STORE all gained knowledge in all relevant global databases".
# Persisted fire-and-forget so a write NEVER delays or breaks the
# streamed answer the operator already has. SSOT toggle/table/cap via
# env (mirrors every other MIOS_* tunable; document in mios.toml).
KNOWLEDGE_STORE_ENABLED = os.environ.get(
    "MIOS_KNOWLEDGE_STORE", "true").strip().lower() not in ("0", "false", "no")
KNOWLEDGE_TABLE = (os.environ.get("MIOS_KNOWLEDGE_TABLE", "knowledge").strip()
                   or "knowledge")
KNOWLEDGE_ANSWER_MAX = int(
    os.environ.get("MIOS_KNOWLEDGE_ANSWER_MAX", "8000") or 8000)
# Knowledge RECALL (operator 2026-05-23: read the store back). The query is
# embedded at WRITE time (nomic-embed via the existing _embed_one) so recall is
# a cheap cosine over recent rows, threshold-gated so only genuinely-relevant
# prior answers inject. Reuses the verb tool-search embedding infra. This is
# recall of prior ANSWERS, NOT env detection -> compatible with the
# no-context-injection rule (which is env-detection-only).
KNOWLEDGE_RECALL_ENABLED = os.environ.get(
    "MIOS_KNOWLEDGE_RECALL", "true").strip().lower() not in ("0", "false", "no")
KNOWLEDGE_RECALL_K = int(os.environ.get("MIOS_KNOWLEDGE_RECALL_K", "3") or 3)
KNOWLEDGE_RECALL_CANDIDATES = int(
    os.environ.get("MIOS_KNOWLEDGE_RECALL_CANDIDATES", "60") or 60)
KNOWLEDGE_RECALL_MIN_SCORE = float(
    os.environ.get("MIOS_KNOWLEDGE_RECALL_MIN_SCORE", "0.62") or 0.62)
_KNOWLEDGE_URL_RE = re.compile(r"https?://[^\s\"'<>)\]]+")


def _knowledge_sources(tool_history: Optional[list]) -> list:
    """Compact, auditable source list for a stored answer: the verbs the
    turn invoked + any URLs they touched (web_search / web_extract args +
    result previews). A recalled answer then carries WHERE it came from
    instead of being an unattributed assertion."""
    srcs: list = []
    seen: set = set()
    for r in tool_history or []:
        if not isinstance(r, dict):
            continue
        tool = str(r.get("tool") or "").strip()
        if tool and tool not in seen:
            seen.add(tool)
            srcs.append({"type": "tool", "ref": tool,
                         "success": bool(r.get("success"))})
        blob = (json.dumps(r.get("args") or {}, default=str) + " "
                + str(r.get("result_preview") or ""))
        for u in _KNOWLEDGE_URL_RE.findall(blob):
            u = u.rstrip(".,);")
            if u and u not in seen:
                seen.add(u)
                srcs.append({"type": "url", "ref": u})
    return srcs[:24]


def _store_knowledge(*, query: str, answer: str,
                     session_id: Optional[str],
                     tool_history: Optional[list] = None) -> None:
    """Persist a finished Q+A (with derived sources + a query embedding for
    recall) to the global knowledge table, fire-and-forget. NEVER raises -- a
    storage failure must not affect the answer the operator already received."""
    if not KNOWLEDGE_STORE_ENABLED:
        return
    q = (query or "").strip()
    a = (answer or "").strip()
    if not q or not a:
        return
    _db_fire(_store_knowledge_task(
        q[:2000], a[:KNOWLEDGE_ANSWER_MAX],
        session_id, _knowledge_sources(tool_history)))


async def _store_knowledge_task(q: str, a: str,
                                session_id: Optional[str],
                                sources: list) -> None:
    """Embed the question (so recall is a cheap cosine) then write the row.
    Embedding is best-effort: a miss just stores the row without `emb` -- still
    persisted + auditable, just not semantically recallable."""
    try:
        row = {"q": q, "answer": a, "sources": sources}
        if KNOWLEDGE_RECALL_ENABLED:
            emb = await _embed_one(q)
            if emb:
                row["emb"] = emb
        sql = _db_create(KNOWLEDGE_TABLE, row, now_fields=("ts",))
        if session_id:
            sql = sql.rstrip(";") + f", session = {session_id};"
        await _db_post(sql)
    except Exception as e:
        log.warning("knowledge store skipped: %s", e)


async def _recall_knowledge(query: str) -> str:
    """Semantic recall of PRIOR stored answers relevant to `query`: embed the
    query, cosine it against the query-embeddings of recent knowledge rows,
    return the top-K above a threshold as an injectable context block (or '' on
    miss). Best-effort, never blocks the turn -- the read half of the
    store/recall loop (operator 2026-05-23). Recalled answers are framed as
    PRIOR/own knowledge that may be outdated, never as fresh ground truth."""
    if not (KNOWLEDGE_RECALL_ENABLED and query and query.strip()):
        return ""
    try:
        qv = await _embed_one(query)
        if not qv:
            return ""
        # NOTE: this SurrealDB build requires the ORDER BY field to be in the
        # SELECT projection ("Missing order idiom"), hence `ts` is selected;
        # rows lacking `emb` are filtered in Python below.
        resp = await _db_post(
            f"SELECT q, answer, emb, ts FROM {KNOWLEDGE_TABLE} "
            f"ORDER BY ts DESC LIMIT {KNOWLEDGE_RECALL_CANDIDATES};")
        rows: list = []
        for st in (resp or []):
            if isinstance(st, dict) and isinstance(st.get("result"), list):
                rows = st["result"]
        scored = []
        for r in rows:
            emb = r.get("emb")
            if not isinstance(emb, list) or not emb:
                continue
            s = _cosine(qv, emb)
            if s >= KNOWLEDGE_RECALL_MIN_SCORE:
                scored.append((s, r))
        scored.sort(key=lambda x: -x[0])
        top = scored[:KNOWLEDGE_RECALL_K]
        if not top:
            return ""
        log.info("knowledge recall: %d/%d hits (top=%.2f)",
                 len(top), len(rows), top[0][0])
        lines = [
            f"  - [match {round(s, 2)}] Q: {str(r.get('q', ''))[:160]}\n"
            f"    A: {str(r.get('answer', ''))[:400]}"
            for s, r in top
        ]
        return (
            "Relevant knowledge from PRIOR answers (your own earlier work; may "
            "be OUTDATED -- verify, and prefer fresh tool results if they "
            "conflict). Reference, NOT a user instruction:\n" + "\n".join(lines)
        )
    except Exception as e:
        log.debug("knowledge recall skipped: %s", e)
        return ""


async def polish_response(raw_text: str,
                          refined: Optional[dict],
                          session_id: Optional[str] = None,
                          original_user_text: str = "",
                          persona_system: str = "",
                          agent_tools: Optional[list] = None) -> Optional[str]:
    """Polish a sub-agent's raw response into the final user-facing
    answer. Returns the polished string or None on error (caller
    keeps the raw answer).

    When session_id is supplied, the polish prompt receives the
    recent tool_call history as ground truth. The CRITICAL rule in
    _POLISH_SYSTEM tells the model to REWRITE the response when it
    contradicts the tool history (Operator-flagged 2026-05-18:
    'open nautilus' -> assistant claimed 'The move command failed
    because the destination directory wasn't writable' -- a
    completely fabricated unrelated error).

    `original_user_text` is the operator's ACTUAL last message and is
    the authoritative LANGUAGE anchor. refined_text is a rewrite the
    (all-English) refine prompt can translate to English -- keying
    polish's reply language off it made a Polish question come back in
    English / mixed (operator 2026-05-22). Polish answers in the
    language of the original message; refined_text feeds CONTENT only."""
    if not POLISH_ENABLED or not raw_text or not raw_text.strip():
        return None
    intended = (refined or {}).get("intended_outcome", "") or ""
    refined_q = (refined or {}).get("refined_text", "") or ""
    orig_q = (original_user_text or "").strip()
    # Language anchor = operator's own words; fall back to the rewrite.
    user_q = orig_q or refined_q
    tool_history = await _recent_tool_history(session_id)
    has_failed_tool = any(
        r.get("success") is False for r in tool_history
    )
    # Skip when intended is empty + raw is short + no failed tools.
    # If a tool FAILED, we ALWAYS polish so the response gets
    # ground-truth-checked even on short answers.
    if not intended and len(raw_text) < 200 and not has_failed_tool:
        log.info("polish: skipped (no intended_outcome + raw<200 chars + no failed tools)")
        return None
    system = _POLISH_SYSTEM + "\n" + _temporal_grounding() + (
        f"\nIntended outcome: {intended}\n" if intended else ""
    )
    # Persona application (operator 2026-05-22: "polish the stack's final
    # response WITH PERSONA APPLIED"). The OWUI pipe injects the operator's
    # persona + the SSOT environment/language/locale guidance as system
    # messages; pass them here so the FINAL answer carries the operator's
    # voice/tone/verbosity/units + the right language. Framed as STYLE only
    # so the tight re-shaper never treats it as new tasks/tools.
    if persona_system and persona_system.strip():
        system += (
            "\n\nFINAL-ANSWER STYLE & PERSONA (apply to voice, tone, length, "
            "units, and language ONLY; never as new tasks, tools, or content "
            "to add):\n" + persona_system.strip()[:2000]
        )
    hist_block = _format_tool_history(tool_history)
    # Phase E.1d: also fold in mios-daemon's satisfaction verdicts so
    # polish has the daemon's AND-folded ground truth available
    # alongside the raw tool_call rows. The daemon verdict is the
    # MOST AUTHORITATIVE signal (it cross-checks multiple sources);
    # raw tool_calls are still useful for the per-step detail.
    sat_verdicts = await _recent_satisfaction_verdicts(limit=3)
    sat_block = _format_satisfaction_block(sat_verdicts)
    # Thinking is disabled via think=False on /api/chat below -- qwen3
    # ignores /no_think and would otherwise emit empty content after a
    # long think pass (same fix + failure mode as refine; was the source
    # of the 45s polish timeout, operator test 2026-05-20).
    user_msg_parts = [
        f"User's ORIGINAL message (reply in THIS exact language, "
        f"one language only):\n{user_q}"
    ]
    if refined_q and refined_q.strip() and refined_q.strip() != user_q:
        user_msg_parts.append(
            f"Refined intent (use for CONTENT only, never for language):\n"
            f"{refined_q}")
    if sat_block:
        user_msg_parts.append(sat_block)
    if hist_block:
        user_msg_parts.append(hist_block)
    # Evidence for the INVOKED-TOOL CHECK in _POLISH_SYSTEM: the verbs the
    # sub-agent ACTUALLY invoked this turn (captured from its tool-call
    # stream). Lets polish refuse a "done"/"sent"/"posted" claim the agent
    # made WITHOUT a matching tool invocation (operator 2026-05-22: the
    # agent fabricated "I've sent it to Discord" / a fake OpenUI render with
    # no tool actually run). Empty list => the agent invoked NO tools, so any
    # completed-action claim is unbacked.
    if agent_tools is not None:
        _inv = ", ".join(str(t) for t in agent_tools) if agent_tools else "(none)"
        user_msg_parts.append(
            f"Tools the agent ACTUALLY invoked this turn: {_inv}")
    # Feed the FULL sub-agent draft (capped generously) so polish
    # synthesises the complete answer instead of a truncated/mis-focused
    # slice -- the 3500 cap made polish produce partial answers + "no
    # data" contradictions of a summary it couldn't fully see (operator
    # 2026-05-20). The polish now runs on the fast 4b dGPU lane, so 8000
    # chars is cheap.
    user_msg_parts.append(f"Raw answer from sub-agent:\n{raw_text[:8000]}")
    user_msg = "\n\n".join(user_msg_parts)
    payload = {
        "model": POLISH_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user_msg},
        ],
        "think": False,
        "stream": False,
        "options": {"temperature": 0.0,
                    "num_predict": POLISH_MAX_TOKENS},
    }
    url = f"{POLISH_ENDPOINT}/api/chat"
    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=POLISH_TIMEOUT_S) as s:
            r = await s.post(url, json=payload,
                             headers={"Content-Type": "application/json"})
            if r.status_code != 200:
                log.warning("polish: backend %s in %.1fs",
                            r.status_code, time.time() - t0)
                return None
            body = r.json()
    except (httpx.HTTPError, asyncio.TimeoutError) as e:
        log.warning("polish: timeout/http error after %.1fs: %s",
                    time.time() - t0, e)
        return None
    except Exception as e:
        log.warning("polish unexpected error: %s", e)
        return None
    log.info("polish: %.1fs", time.time() - t0)
    # /api/chat shape {"message":{"content"}}; /v1 choices[] fallback.
    msg = body.get("message")
    if not isinstance(msg, dict):
        choices = body.get("choices") or []
        msg = (choices[0].get("message") if choices else {}) or {}
    polished = (msg.get("content") or "").strip()
    if not polished:
        return None
    # Store the finished Q+A (with sources) to the global knowledge table.
    # Fire-and-forget -- the answer is already returned regardless.
    _store_knowledge(query=user_q, answer=polished,
                     session_id=session_id, tool_history=tool_history)
    return polished


def _casual_agent_label(target_name: str) -> str:
    """Map registered sub-agent name -> casual MiOS-convention label
    for SSE status emission + dropdown summaries. Operator binding:
    surface labels stay generic ('sub-agent' / role), the specific
    daemon name lives in event payloads + journal, not in the chat
    UI. Same agent can be renamed via mios.toml [agents.*] without
    leaking the old name to the operator's screen."""
    cfg = _AGENT_REGISTRY.get(target_name) or {}
    role = str(cfg.get("role") or "").strip().lower()
    if role:
        return f"{role}-agent"
    return "sub-agent"


def _build_agent_hint(refined: dict, target_name: str) -> str:
    """Render a compact system-message prefix from a refined plan.
    Injected at the head of `messages` when proxying to a sub-
    agent so the agent receives MiOS-Agent's intent + suggested
    tools/skills/outcome -- NOT as free-form prose, but as a
    structured marker block the agent's own system prompt can
    parse.

    Format kept tight (~150-250 tokens) so even a 4K-context
    micro-model has plenty of room for the conversation itself.
    """
    intent = str(refined.get("intent") or "").strip()
    outcome = str(refined.get("intended_outcome") or "").strip()
    refined_text = str(refined.get("refined_text") or "").strip()
    tools = refined.get("hint_tools") or []
    skills = refined.get("hint_skills") or []
    lines = [
        "# MiOS-Agent refined plan (consume + act; do NOT echo to user)",
        f"target_agent: {target_name}",
    ]
    if intent:
        lines.append(f"intent: {intent}")
    if outcome:
        lines.append(f"intended_outcome: {outcome}")
    if refined_text:
        lines.append(f"refined_query: {refined_text[:400]}")
    if tools:
        lines.append("hint_tools: " + ", ".join(str(t) for t in tools[:8]))
    if skills:
        lines.append("hint_skills: " + ", ".join(str(s) for s in skills[:8]))
    # GLOBAL tool access (operator 2026-05-23: "all agents have all access to
    # all tools/skills/recipes globally"). The hints above are SUGGESTIONS,
    # not limits -- state it explicitly so an agent never assumes it's scoped
    # to the hinted subset. Compact (no full-catalog dump -- keeps the micro
    # context budget) + reinforces act-don't-narrate.
    lines.append(
        "tool_access: GLOBAL -- hint_tools/hint_skills are SUGGESTIONS, not "
        "limits; you may invoke ANY MiOS tool / skill / recipe. Acting "
        "(install / post / fetch / run / open) REQUIRES a real tool_call, "
        "never narration.")
    # Per-step tool cards (ReWOO + MCP-style annotations). Carries
    # the WHY + the success predicate INTO the sub-agent so it
    # doesn't have to re-derive the plan. Cap at 8 cards so we
    # stay under ~250 tokens total even for rich plans.
    cards = refined.get("tool_cards") or []
    if isinstance(cards, list) and cards:
        lines.append("tool_cards:")
        for i, c in enumerate(cards[:8]):
            if not isinstance(c, dict):
                continue
            tool = str(c.get("tool") or "").strip()
            why = str(c.get("why") or "").strip()[:160]
            succ = str(c.get("success_predicate") or "").strip()[:160]
            consumed = c.get("output_used_by") or []
            args_hint = c.get("args_hint")
            line = f"  - [{i}] tool={tool}"
            if args_hint:
                # Render compactly; sub-agent re-parses as JSON.
                try:
                    line += f" args={json.dumps(args_hint, separators=(',', ':'))[:200]}"
                except (TypeError, ValueError):
                    pass
            if why:
                line += f" why={why}"
            if succ:
                line += f" success={succ}"
            if consumed:
                line += f" output_used_by={consumed}"
            lines.append(line)
    return "\n".join(lines)


# ── Phase C.2 -- Skill catalog SSOT knobs ─────────────────────────
# Mirror of the mios-skills CLI's env reads. Centralised here so a
# single source-of-truth deploys to BOTH the CLI miner AND the
# agent-pipe /skills/* execution surface every other agent in the
# stack consumes.
SKILLS_ENABLED = os.environ.get(
    "MIOS_SKILLS_ENABLE", "true",
).lower() not in {"false", "0", "no"}
SKILLS_MIN_LENGTH = int(os.environ.get("MIOS_SKILLS_MIN_LENGTH", "2"))
SKILLS_MAX_LENGTH = int(os.environ.get("MIOS_SKILLS_MAX_LENGTH", "8"))
SKILLS_MIN_SUPPORT = int(os.environ.get("MIOS_SKILLS_MIN_SUPPORT", "3"))
SKILLS_WINDOW_HOURS = int(os.environ.get("MIOS_SKILLS_WINDOW_HOURS", "168"))
SKILLS_AUTO_PROMOTE_THRESHOLD = float(os.environ.get(
    "MIOS_SKILLS_AUTO_PROMOTE_THRESHOLD", "0.85"))


# ── Phase C.1 -- Personal Knowledge Graph lookup ──────────────────
# Resolves operator-set noun phrases ("my browser", "the dev VM")
# to concrete app_install rows via the SurrealDB graph (alias ->
# resolves_to -> app_install). Used by the planner + dispatch to
# disambiguate phrases that would otherwise force the LLM to guess.

async def kg_lookup(phrase: str) -> Optional[dict]:
    """Look up a phrase in the operator's PKG. Returns the first
    matching app_install record as a dict, or None if no match.
    Tries alias first (operator-defined shortcuts), then a fuzzy
    short_name match on app_install."""
    if not phrase:
        return None
    p = phrase.strip().lower().replace("'", "''")
    if not p:
        return None
    # Stage 1a: alias EXACT-match (highest precedence). Operator
    # configured "my browser" -> X, this returns X directly.
    sql = (
        f"SELECT phrase, "
        f"->resolves_to->app_install.{{id, short_name, app_id, "
        f"source, label, launch_hint}} AS apps "
        f"FROM alias WHERE phrase = '{p}' LIMIT 1;"
    )
    r = await _db_post(sql)
    if r:
        rows = (r[-1] or {}).get("result") or []
        for row in rows:
            apps = row.get("apps") or []
            if apps:
                return {"source": "alias",
                        "phrase": row.get("phrase"),
                        "app": apps[0]}
    # Stage 1b: alias contains match (fuzzy fallback).
    sql = (
        f"SELECT phrase, "
        f"->resolves_to->app_install.{{id, short_name, app_id, "
        f"source, label, launch_hint}} AS apps "
        f"FROM alias "
        f"WHERE string::contains(phrase, '{p}') "
        f"   OR string::contains('{p}', phrase) "
        f"LIMIT 3;"
    )
    r = await _db_post(sql)
    if r:
        rows = (r[-1] or {}).get("result") or []
        for row in rows:
            apps = row.get("apps") or []
            if apps:
                return {"source": "alias",
                        "phrase": row.get("phrase"),
                        "app": apps[0]}
    # Stage 2: direct app_install short_name fuzzy match.
    sql = (
        f"SELECT id, short_name, app_id, source, label, launch_hint "
        f"FROM app_install "
        f"WHERE string::contains(short_name, '{p}') "
        f"   OR string::contains('{p}', short_name) "
        f"LIMIT 1;"
    )
    r = await _db_post(sql)
    if r:
        rows = (r[-1] or {}).get("result") or []
        if rows:
            return {
                "source": "app_install",
                "phrase": phrase,
                "app": rows[0],
            }
    return None


# ── Phase C.2 -- skill catalog helpers ────────────────────────────
# Cross-agent skill execution surface. Every other agent in the
# MiOS stack (MiOS-Hermes, MiOS-OpenCode, future MCP clients) reads
# skills via the SurrealDB skill table directly OR via this
# service's /skills/* endpoints -- they MUST converge on the same
# dispatch path so a skill run produces the same firewall checks,
# taint propagation, and tool_call audit rows regardless of which
# agent initiated it. No agent-specific behaviour anywhere.

_PARAM_TOKEN_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")


def _skill_render_args(args: dict, params: dict) -> dict:
    """Substitute $-tokens in skill step args using the params map.
    Pure helper -- the skill body holds the template, the params
    dict holds the concrete operator-supplied values.

    Operator-supplied params override mined defaults. Missing
    params leave the $-token literal (so the dispatch errors
    visibly instead of silently swallowing the gap)."""
    out: dict = {}
    for k, v in (args or {}).items():
        if isinstance(v, str):
            def _sub(m: re.Match) -> str:
                key = m.group(1)
                if key in params and params[key] is not None:
                    return str(params[key])
                return m.group(0)
            out[k] = _PARAM_TOKEN_RE.sub(_sub, v)
        else:
            out[k] = v
    return out


async def _skill_fetch(name: str) -> Optional[dict]:
    """Read one skill row by name. Returns the row dict (with body
    + status fields) or None if not found."""
    if not name:
        return None
    sql = (
        f"SELECT id, name, body, status, source, version, "
        f"description, support, confidence "
        f"FROM skill WHERE name = {json.dumps(name)} LIMIT 1;"
    )
    r = await _db_post(sql)
    if not r:
        return None
    rows = (r[-1] or {}).get("result") or []
    return rows[0] if rows else None


async def _skill_list(*, status: str = "promoted",
                      source: Optional[str] = None,
                      limit: int = 200) -> list[dict]:
    where = []
    if status and status != "all":
        where.append(f"status = {json.dumps(status)}")
    if source and source != "all":
        where.append(f"source = {json.dumps(source)}")
    clause = " AND ".join(where) if where else "true"
    sql = (
        f"SELECT name, description, body, source, status, "
        f"support, confidence, version "
        f"FROM skill WHERE {clause} "
        f"ORDER BY name LIMIT {int(limit)};"
    )
    r = await _db_post(sql)
    if not r:
        return []
    return (r[-1] or {}).get("result") or []


async def _skill_invocation_open(skill_id: str,
                                 params: dict,
                                 session_id: Optional[str]) -> Optional[str]:
    """Open a skill_invocation row; returns the new row id (or
    None if the DB write failed). The caller closes the row via
    _skill_invocation_close with ended_at + success.

    Hand-built CREATE -- _db_create json.dumps-quotes every value,
    but SurrealDB 3.0+ requires record<...> references UNQUOTED
    (`skill = skill:abc123`, not `skill = "skill:abc123"`). The
    quoted form produces a coerce error response that the caller
    can't interpret as success."""
    parts = [
        "started_at = time::now()",
        f"skill = {skill_id}",
        f"params = {json.dumps(params or {})}",
    ]
    if session_id:
        parts.append(f"session = {session_id}")
    # Phase C.3: passport. Same algorithm as _db_create -- include
    # the record-ref strings (skill_id, session_id) in the hash so
    # tampering with the attribution links re-derives a different
    # op_hash on verify.
    hash_fields = {
        "started_at": "time::now()",
        "skill": skill_id,
        "params": params or {},
    }
    if session_id:
        hash_fields["session"] = session_id
    envelope = _passport_sign("skill_invocation", hash_fields)
    if envelope is not None:
        parts.append(f"passport = {json.dumps(envelope)}")
    sql = "CREATE skill_invocation SET " + ", ".join(parts) + " RETURN AFTER;"
    r = await _db_post(sql)
    if not r:
        return None
    last = r[-1] or {}
    if last.get("status") != "OK":
        return None
    rows = last.get("result") or []
    if not isinstance(rows, list) or not rows:
        return None
    first = rows[0]
    if not isinstance(first, dict):
        return None
    return first.get("id")


async def _skill_invocation_close(inv_id: Optional[str],
                                  success: bool) -> None:
    if not inv_id:
        return
    sql = (
        f"UPDATE {inv_id} SET ended_at = time::now(), "
        f"success = {str(bool(success)).lower()};"
    )
    await _db_post(sql)


async def _skill_attribute_tool_call(inv_id: Optional[str],
                                     tool_call_id: Optional[str],
                                     step_index: int) -> None:
    """RELATE the tool_call back to the skill_invocation so the
    miner subtracts skill-emitted runs from future candidate
    populations (Phase C.2 closes the loop on its own output)."""
    if not inv_id or not tool_call_id:
        return
    sql = (
        f"RELATE {inv_id}->emitted->{tool_call_id} "
        f"SET step_index = {int(step_index)};"
    )
    await _db_post(sql)


async def execute_skill(name: str, params: dict, *,
                        session_id: Optional[str] = None) -> dict:
    """Run a skill by name. Returns the same envelope shape an
    execute_dag run returns -- success, steps[], failures[],
    aborted -- so every gateway in the stack consumes skill output
    with identical code.

    The skill body steps are mapped 1:1 to dispatch_mios_verb calls;
    each tool_call row produced is attributed to the skill via
    RELATE skill_invocation->emitted->tool_call. The Phase B.3
    firewall, Phase A.3 taint chain, and Phase A.1 reflexion cap
    all apply unchanged because we route through the same
    dispatch_mios_verb the planner uses."""
    if not SKILLS_ENABLED:
        return {"success": False,
                "skill": name,
                "error": "skills_disabled",
                "steps": [],
                "failures": ["skills disabled via MIOS_SKILLS_ENABLE"]}
    row = await _skill_fetch(name)
    if not row:
        return {"success": False, "skill": name,
                "error": "not_found", "steps": [], "failures": []}
    if row.get("status") != "promoted":
        return {"success": False, "skill": name,
                "error": "not_promoted",
                "status": row.get("status"),
                "steps": [], "failures": []}
    body = row.get("body") or {}
    steps = body.get("steps") or []
    if not steps:
        return {"success": False, "skill": name,
                "error": "empty_body", "steps": [], "failures": []}
    # Execution mode -- "sequence" (default) halts on first FAILURE;
    # "try-each" halts on first SUCCESS. The latter is the generic
    # primitive resilience skills need (try variant A, then B, then
    # C, ... succeed when any one lands). Operator directive 2026-
    # 05-18 "no hardcoded fallbacks -- ALL TOOLS AND SKILLS to solve
    # for this": the engine extension is generic infrastructure;
    # specific fallback orderings live in individual skill bodies.
    mode = str(body.get("mode") or "sequence").lower()
    inv_id = await _skill_invocation_open(
        row.get("id"), params or {}, session_id)
    # expand_from: a step annotated with {"expand_from": "<param>",
    # "bind_as": "<token>"} fans out into one step per element of
    # the named array param, binding `$<token>` to each value. Used
    # by try-each skills to walk an arbitrary list (e.g. browser
    # fallback chain) without hardcoding the list in the skill. The
    # expansion happens here so the rest of the engine (logging,
    # event emission, invocation_close) sees a flat step list.
    expanded: list[dict] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        ef = step.get("expand_from")
        if not ef:
            expanded.append(step)
            continue
        ba = step.get("bind_as") or "item"
        seq = (params or {}).get(ef)
        if not isinstance(seq, list) or not seq:
            # No values to expand -> skip the step. Counts as a
            # silent no-op rather than a missing-params failure;
            # try-each callers can still resolve on a later step.
            continue
        for v in seq:
            inst = {k: w for k, w in step.items()
                    if k not in ("expand_from", "bind_as")}
            inst_params = {**(params or {}), ba: v}
            inst["args"] = _skill_render_args(
                inst.get("args") or {}, inst_params)
            inst["_expanded_from"] = ef
            inst["_bound_value"] = v
            expanded.append(inst)
    steps = expanded
    results: list[dict] = []
    failures: list[str] = []
    for idx, step in enumerate(steps):
        verb = (step or {}).get("verb") or ""
        raw_args = (step or {}).get("args") or {}
        # Already-rendered args from expand_from pass through; raw
        # args (literal step) still need rendering. Detect by
        # presence of the _expanded_from marker.
        if step.get("_expanded_from"):
            rendered = raw_args
        else:
            rendered = _skill_render_args(raw_args, params or {})
        # Detect un-substituted $-tokens (operator forgot a param).
        leftover = [
            v for v in rendered.values()
            if isinstance(v, str) and _PARAM_TOKEN_RE.search(v)
        ]
        if leftover:
            failures.append(
                f"step {idx} ({verb}): missing params {leftover}")
            results.append({"step": idx, "verb": verb,
                            "success": False,
                            "error": "missing_params",
                            "leftover": leftover})
            # Halt -- can't dispatch with un-bound tokens.
            await _skill_invocation_close(inv_id, success=False)
            return {"success": False, "skill": name, "steps": results,
                    "failures": failures, "aborted": True}
        r = await dispatch_mios_verb(
            verb, rendered, session_id=session_id)
        results.append({
            "step": idx, "verb": verb, "args": rendered,
            "success": bool(r.get("success", False)),
            "exit_code": r.get("exit_code"),
            "output": r.get("output", "")[:400],
            "stderr": r.get("stderr", "")[:400],
            "tainted": r.get("tainted", False),
            "taint_reason": r.get("taint_reason", ""),
        })
        # Attribute the tool_call to this invocation. The
        # dispatch_mios_verb path emits the tool_call row itself;
        # we re-query to find the most recent matching row and
        # RELATE it. Best-effort; the audit chain isn't load-bearing
        # for skill correctness, just for miner-side dedup.
        if session_id:
            q = (
                f"SELECT id, ts FROM tool_call "
                f"WHERE session = {session_id} "
                f"  AND tool = {json.dumps(verb)} "
                f"ORDER BY ts DESC LIMIT 1;"
            )
            qr = await _db_post(q)
            if qr:
                tc_rows = (qr[-1] or {}).get("result") or []
                if tc_rows:
                    await _skill_attribute_tool_call(
                        inv_id, tc_rows[0].get("id"), idx)
        step_ok = bool(r.get("success", False))
        if mode == "try-each":
            # try-each: halt on first SUCCESS. A failed step records
            # the failure and continues; a successful step closes the
            # skill as a win (any-of-N semantics).
            if step_ok:
                await _skill_invocation_close(inv_id, success=True)
                await _db_post(
                    f"UPDATE {row.get('id')} SET last_used_at = time::now();")
                await _db_post(_db_create("event", {
                    "source": "agent-pipe",
                    "kind": "skill_run",
                    "severity": "info",
                    "summary": f"{name} ok at step {idx} (try-each)",
                    "payload": {"skill": name, "winning_step": idx,
                                "mode": "try-each",
                                "steps_attempted": idx + 1},
                }, now_fields=("ts",)))
                return {"success": True, "skill": name, "steps": results,
                        "failures": failures, "aborted": False,
                        "winning_step": idx, "mode": "try-each"}
            # Failure under try-each: record + keep going. Only halt
            # when we run out of steps below (the for-loop falls out).
            failures.append(
                f"step {idx} ({verb}): "
                f"exit={r.get('exit_code')} "
                f"stderr={r.get('stderr','')[:200]}")
            continue
        # mode == "sequence" (default).
        if not step_ok:
            failures.append(
                f"step {idx} ({verb}): "
                f"exit={r.get('exit_code')} "
                f"stderr={r.get('stderr','')[:200]}")
            # Stop on first failure -- operator can re-run with
            # corrected params instead of cascading half-state.
            await _skill_invocation_close(inv_id, success=False)
            await _db_post(_db_create("event", {
                "source": "agent-pipe",
                "kind": "skill_run",
                "severity": "warn",
                "summary": f"{name} failed at step {idx}",
                "payload": {"skill": name, "step": idx,
                            "verb": verb,
                            "stderr": r.get("stderr", "")[:300]},
            }, now_fields=("ts",)))
            return {"success": False, "skill": name, "steps": results,
                    "failures": failures, "aborted": True}
    # Loop fell off the end. For try-each that means every step
    # failed (no win); for sequence that means every step succeeded.
    if mode == "try-each":
        await _skill_invocation_close(inv_id, success=False)
        await _db_post(_db_create("event", {
            "source": "agent-pipe",
            "kind": "skill_run",
            "severity": "warn",
            "summary": f"{name} exhausted (try-each)",
            "payload": {"skill": name, "mode": "try-each",
                        "steps_attempted": len(steps)},
        }, now_fields=("ts",)))
        return {"success": False, "skill": name, "steps": results,
                "failures": failures, "aborted": True,
                "mode": "try-each"}
    await _skill_invocation_close(inv_id, success=True)
    # Update last_used_at on the skill row for the configurator UI.
    await _db_post(
        f"UPDATE {row.get('id')} SET last_used_at = time::now();")
    await _db_post(_db_create("event", {
        "source": "agent-pipe",
        "kind": "skill_run",
        "severity": "info",
        "summary": f"{name} ok ({len(steps)} steps)",
        "payload": {"skill": name, "steps_run": len(steps)},
    }, now_fields=("ts",)))
    return {"success": True, "skill": name, "steps": results,
            "failures": [], "aborted": False}


def _skill_to_openai_tool(row: dict) -> dict:
    """Render one skill row as an OpenAI function-tool schema.
    Hermes + OpenCode consume this dump verbatim so their tool
    surface auto-extends every time the operator promotes a skill --
    no code changes per skill on either client."""
    name = row.get("name") or ""
    description = row.get("description") or f"MiOS skill {name}"
    body = row.get("body") or {}
    params = body.get("params") or []
    properties = {
        p: {"type": "string",
            "description": f"value for ${p}"} for p in params
    }
    return {
        "type": "function",
        "function": {
            "name": f"mios_skill__{re.sub(r'[^A-Za-z0-9_]', '_', name)}",
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": params,
            },
        },
        "x-mios-skill": name,
    }


# ── Phase B.1 -- Deliberative Collective Intelligence (DCI) vocab ─
# 14 typed epistemic acts (Habermas-rooted, DCI paper arxiv
# 2603.11781). Replaces unstructured agent debate -- which the
# paper showed degrades vs isolated reasoning -- with grammatical
# typed acts grouped into 6 functional families. Each act is a
# first-class object the agent emits as structured JSON; the
# orchestrator (Phase B.2) deliberates by passing acts between
# personas, preserving tensions, and converging via DCI-CF.
#
# Phase B.1 scope (this commit): vocabulary + schema + a single-
# persona post-dispatch critic helper that writes an event row
# tagged kind=dci_act. NOT yet the 4-persona convergent flow --
# that's B.2. This gives Phase B.1 immediate operator-visible
# value (post-dispatch critic verdicts in the audit log) without
# the latency of running the full deliberation loop on every
# chat turn.

DCI_ENABLED = os.environ.get("MIOS_AGENT_PIPE_DCI_ENABLED",
                              "true").lower() not in {"false", "0", "no"}
DCI_MODEL = os.environ.get("MIOS_AGENT_PIPE_DCI_MODEL", "qwen2.5-coder:7b")
DCI_ENDPOINT = os.environ.get(
    "MIOS_AGENT_PIPE_DCI_ENDPOINT", "http://localhost:11434",
).rstrip("/")
DCI_TIMEOUT_S = int(os.environ.get("MIOS_AGENT_PIPE_DCI_TIMEOUT_S", "20"))
DCI_MAX_TOKENS = int(os.environ.get("MIOS_AGENT_PIPE_DCI_MAX_TOKENS", "400"))

# The 14 acts organized by family. Each family corresponds to a
# distinct cognitive function in collective deliberation; missing
# a family in a multi-round flow is what the DCI paper identifies
# as the failure mode for unstructured debate ("sycophantic
# convergence", "groupthink", "fragmentation"). Kept identical to
# the paper so future B.2 / B.3 references stay grounded.
DCI_ACTS: dict[str, dict] = {
    # Orienting: problem framing + scope.
    "frame":         {"family": "orienting",   "intent": "establish the problem definition"},
    "clarify":       {"family": "orienting",   "intent": "request or supply clarification"},
    "reframe":       {"family": "orienting",   "intent": "restate the problem with a shifted lens"},
    # Generative: expanding the option space.
    "propose":       {"family": "generative",  "intent": "offer a candidate solution / hypothesis"},
    "extend":        {"family": "generative",  "intent": "build on an existing proposal"},
    "spawn":         {"family": "generative",  "intent": "open a new line of inquiry"},
    # Critical: assumption testing + risk.
    "ask":           {"family": "critical",    "intent": "request evidence / probe an assumption"},
    "challenge":     {"family": "critical",    "intent": "contest a claim with a counter-argument"},
    # Integrative: synthesis + memory.
    "bridge":        {"family": "integrative", "intent": "connect two distinct ideas"},
    "synthesize":    {"family": "integrative", "intent": "merge disparate views into a coherent whole"},
    "recall":        {"family": "integrative", "intent": "surface prior context / decisions"},
    # Epistemic: belief state + confidence.
    "ground":        {"family": "epistemic",   "intent": "anchor a claim to verifiable evidence"},
    "update":        {"family": "epistemic",   "intent": "revise a prior belief in light of new info"},
    # Decisional: closure.
    "recommend":     {"family": "decisional",  "intent": "advance a specific action / decision"},
}

DCI_ACT_NAMES = sorted(DCI_ACTS.keys())

# JSON Schema for OpenAI structured-output constraint. The model
# MUST emit exactly this shape; anything else is a parse error.
# `confidence` is a 0.0-1.0 scalar so downstream can sort by it
# (e.g. Phase B.2's tension tracker promotes high-confidence
# CHALLENGE acts over low-confidence ones).
DCI_ACT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "act":        {"type": "string", "enum": DCI_ACT_NAMES,
                       "description": "Which of the 14 DCI epistemic acts you are emitting."},
        "content":    {"type": "string",
                       "description": "Free-form payload, 1-3 sentences. Mirror the chat language."},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0,
                       "description": "0.0 = highly uncertain; 1.0 = certain."},
        "targets":    {"type": "array", "items": {"type": "string"},
                       "description": "Optional list of prior act-ids this act addresses (Phase B.2 tension tracking)."},
    },
    "required": ["act", "content", "confidence"],
}


# Single-persona critic prompt for Phase B.1. The "Challenger"
# archetype focuses on the critical family (ask / challenge) +
# epistemic family (ground / update). Phase B.2 swaps in the
# full Framer / Explorer / Challenger / Integrator quartet.
_DCI_CRITIC_SYSTEM = (
    "You are a DCI Challenger agent (Deliberative Collective\n"
    "Intelligence, arxiv 2603.11781). Examine the operator's prompt\n"
    "and the agent's tool_result envelope. Emit ONE typed epistemic\n"
    "act as structured JSON. No free-form prose.\n"
    "\n"
    "Available acts (pick ONE):\n"
    + "\n".join(f"  - {a}: {info['intent']} (family: {info['family']})"
                for a, info in sorted(DCI_ACTS.items())) +
    "\n\n"
    "Output schema (JSON ONLY):\n"
    '  {"act":"<one of the 14>",\n'
    '   "content":"<1-3 sentences in the chat language>",\n'
    '   "confidence":<0.0-1.0>,\n'
    '   "targets":[<optional act-ids you address>]}\n'
    "\n"
    "Heuristic for picking an act (Challenger persona):\n"
    "- If the agent's result looks WRONG / unjustified -> challenge\n"
    "  with a specific counter-argument.\n"
    "- If a step seems UNJUSTIFIED -> ask for evidence.\n"
    "- If the result is well-grounded -> ground (acknowledge +\n"
    "  cite the evidence).\n"
    "- If the result OBSOLETES a prior decision -> update.\n"
    "- If unsure -> ask (low confidence is fine; emit it as a\n"
    "  number).\n"
    "\n"
    "Write any text in ENGLISH by default (another language only if the\n"
    "user's own message is clearly in it). Output JSON ONLY -- no preamble,\n"
    "no markdown."
)


# ── Phase B.2 -- DCI-CF convergent flow (4 personas) ──────────────
# Replaces the single-persona B.1 Challenger with the full
# Deliberative Collective Intelligence convergent-flow algorithm:
# 4 archetypal delegates (Framer / Explorer / Challenger /
# Integrator) iterate a bounded loop against a shared workspace,
# always emitting a structured decision packet on exit (per
# arxiv 2603.11781 §3.4: the algorithm is guaranteed-bounded; even
# if convergence fails after R_max rounds, the Integrator emits a
# fallback packet with minority report + reopen triggers).
#
# All 4 personas role-play on the SAME local qwen2.5-coder:7b
# instance -- DCI paper §5.2 ablation showed single-model
# role-playing matches true multi-model diversity on most tasks,
# and the latency budget on a workstation rules out 4 distinct
# model instances anyway.
#
# B.2 scope (this commit): opt-in via env knob + on-demand
# /dci/deliberate endpoint. The flow does NOT fire automatically
# on every dispatch (the cheap B.1 Challenger covers that audit
# trail). Operator enables this when they want the heavy 4-persona
# deliberation -- e.g. for ambiguous, high-stakes, or
# operator-flagged turns.

DCI_FLOW_ENABLED = os.environ.get(
    "MIOS_AGENT_PIPE_DCI_FLOW_ENABLED", "false",
).lower() not in {"false", "0", "no"}
DCI_FLOW_R_MAX = int(os.environ.get("MIOS_AGENT_PIPE_DCI_FLOW_R_MAX", "3"))
DCI_FLOW_TIMEOUT_S = int(os.environ.get(
    "MIOS_AGENT_PIPE_DCI_FLOW_TIMEOUT_S", "20"))

# Per-persona allowed-act sets. Hard constraint at validation
# time so single-model role-play doesn't collapse all four personas
# onto the same act (operator-observed first-run regression
# 2026-05-18: every persona emitted `ground` on an unambiguous
# success envelope -- correct individually but no deliberative
# value as a 4-persona flow). The Integrator retains the broadest
# set since its job is synthesis + decision.
_PERSONA_ALLOWED_ACTS: dict[str, set] = {
    "framer":     {"frame", "clarify", "reframe"},
    "explorer":   {"propose", "extend", "spawn"},
    "challenger": {"ask", "challenge"},
    "integrator": {"bridge", "synthesize", "recall",
                   "ground", "update", "recommend"},
}

# Per-persona system prompts. Each is a SPECIALIZATION of the
# generic critic prompt -- focuses the model on a specific act
# family while preserving access to the full 14-act vocabulary
# (the persona "constrains tendency, not capability" per DCI
# §4.1). The shared structural-output schema (DCI_ACT_SCHEMA from
# B.1) is reused -- one schema, four prompts.

def _persona_prompt(role: str, role_desc: str, allowed_acts: set) -> str:
    """Build a hard-constraint persona prompt: MUST emit one of the
    listed acts, with each act's intent inline so the model picks
    the right one for its cognitive role."""
    allowed_lines = "\n".join(
        f"  - {a}: {DCI_ACTS[a]['intent']}"
        for a in sorted(allowed_acts)
    )
    return (
        f"You are the DCI {role} persona (arxiv 2603.11781).\n"
        f"Your job: {role_desc}\n"
        "\n"
        "You MUST emit EXACTLY ONE act from this list. Any other\n"
        "act will be REJECTED and your contribution to this round\n"
        "will be lost:\n"
        f"{allowed_lines}\n"
        "\n"
        "Write the content in ENGLISH by default (another language only if\n"
        "the operator's own message is clearly in it). Output JSON ONLY shaped:\n"
        '  {"act":"<name>","content":"<1-3 sentences>",'
        '"confidence":<0-1>,"targets":[]}\n'
        "No preamble, no markdown, no commentary."
    )


_DCI_FRAMER_SYSTEM = _persona_prompt(
    "Framer",
    "establish the problem scope + clarify ambiguity. Read the "
    "operator's prompt + the envelope and decide what we're really "
    "deciding about.",
    _PERSONA_ALLOWED_ACTS["framer"],
)

_DCI_EXPLORER_SYSTEM = _persona_prompt(
    "Explorer",
    "expand the option space. What alternative paths or framings has "
    "the Framer missed? What is the second-best option here?",
    _PERSONA_ALLOWED_ACTS["explorer"],
)

_DCI_CHALLENGER_SYSTEM = _persona_prompt(
    "Challenger",
    "interrogate the proposals + the envelope. What evidence is "
    "thin? What assumption looks shaky? Pick the most consequential "
    "weak point and contest it -- or ask for evidence if it's "
    "ambiguous.",
    _PERSONA_ALLOWED_ACTS["challenger"],
)

_DCI_INTEGRATOR_SYSTEM = _persona_prompt(
    "Integrator",
    "synthesize the Framer / Explorer / Challenger contributions "
    "into a coherent next step. When their views diverge, EXPLICITLY "
    "name the tension in your `content` -- do NOT paper over "
    "disagreement. On the final round emit `recommend` to close.",
    _PERSONA_ALLOWED_ACTS["integrator"],
)

_DCI_PERSONAS = [
    ("framer",     _DCI_FRAMER_SYSTEM),
    ("explorer",   _DCI_EXPLORER_SYSTEM),
    ("challenger", _DCI_CHALLENGER_SYSTEM),
    ("integrator", _DCI_INTEGRATOR_SYSTEM),
]


async def _dci_call_persona(
    persona_name: str,
    system_prompt: str,
    user_text: str,
    workspace: dict,
) -> Optional[dict]:
    """One persona round: gives the persona the workspace state +
    asks for ONE typed act. Returns the parsed act dict (with
    persona name appended) or None on any error."""
    workspace_summary = json.dumps(workspace, indent=2, default=str)[:3000]
    user_msg = (
        f"OPERATOR PROMPT:\n{user_text[:1500]}\n\n"
        f"CURRENT WORKSPACE STATE:\n{workspace_summary}\n\n"
        f"You are the {persona_name}. Emit ONE typed epistemic act now:"
    )
    payload = {
        "model": DCI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_msg},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.0,
        "max_tokens": DCI_MAX_TOKENS,
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=DCI_FLOW_TIMEOUT_S) as s:
            r = await s.post(
                f"{DCI_ENDPOINT}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            if r.status_code != 200:
                return None
            body = r.json()
    except (httpx.HTTPError, asyncio.TimeoutError):
        return None
    except Exception as e:
        log.warning("dci flow %s error: %s", persona_name, e)
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
    if not isinstance(parsed, dict):
        return None
    act = parsed.get("act")
    if act not in DCI_ACTS:
        return None
    # Per-persona constraint: reject acts outside the persona's
    # allowed set. Forces deliberative diversity vs single-model
    # mode-collapse.
    allowed = _PERSONA_ALLOWED_ACTS.get(persona_name, set(DCI_ACTS.keys()))
    if act not in allowed:
        log.info("dci %s emitted %s (not in family); rejecting",
                 persona_name, act)
        return None
    try:
        parsed["confidence"] = max(0.0, min(1.0, float(parsed.get("confidence", 0.5))))
    except (TypeError, ValueError):
        parsed["confidence"] = 0.5
    parsed["persona"] = persona_name
    parsed["family"] = DCI_ACTS[act]["family"]
    return parsed


async def run_dci_flow(
    user_text: str,
    envelope: dict,
    *,
    session_id: Optional[str] = None,
    r_max: Optional[int] = None,
) -> dict:
    """Run the DCI-CF convergent flow on (user_text, envelope).
    Returns a structured deliberation result:
      {decision: <Integrator's final recommend act>,
       rounds: [[act_per_persona, ...], ...],
       dissents: [<tension acts>],
       converged: bool}
    Always returns -- the bounded loop guarantees termination."""
    if r_max is None:
        r_max = DCI_FLOW_R_MAX
    # Initialize the shared workspace. DCI paper §3.2 prescribes 6
    # sections; we collapse to 5 for the v1 implementation.
    workspace: dict = {
        "user_prompt":  user_text[:600],
        "envelope":     {
            "tool":    (envelope.get("tool_call") or {}).get("function", {}).get("name"),
            "args":    (envelope.get("tool_call") or {}).get("function", {}).get("arguments"),
            "success": (envelope.get("tool_result") or {}).get("success"),
            "output":  ((envelope.get("tool_result") or {}).get("output") or "")[:500],
        },
        "frames":       [],    # Framer acts
        "proposals":    [],    # Explorer acts
        "challenges":   [],    # Challenger acts
        "syntheses":    [],    # Integrator non-final acts
    }
    rounds: list = []
    decision: Optional[dict] = None
    for r_idx in range(1, r_max + 1):
        round_acts = []
        for persona_name, system_prompt in _DCI_PERSONAS:
            act = await _dci_call_persona(
                persona_name, system_prompt, user_text, workspace,
            )
            if not act:
                continue
            round_acts.append(act)
            # Route the act into the workspace section based on family.
            family = act.get("family", "")
            if family == "orienting":
                workspace["frames"].append(act)
            elif family == "generative":
                workspace["proposals"].append(act)
            elif family == "critical":
                workspace["challenges"].append(act)
            elif family in ("integrative", "epistemic"):
                workspace["syntheses"].append(act)
            elif family == "decisional":
                # Final-form recommend -- capture as the decision.
                decision = act
            # Per-act SurrealDB event (reuse B.1's tagging).
            severity = "warn" if act["act"] in ("challenge", "ask") and act["confidence"] >= 0.7 else "info"
            _db_fire(_db_post(_db_create("event", {
                "source": "mios-agent-pipe",
                "kind": "dci_act",
                "severity": severity,
                "summary": f"r{r_idx}/{persona_name}/{act['act']} ({act['confidence']:.2f})",
                "payload": {
                    "round": r_idx,
                    "persona": persona_name,
                    "act": act["act"],
                    "family": act["family"],
                    "confidence": act["confidence"],
                    "content": (act.get("content") or "")[:500],
                    "targets": act.get("targets") or [],
                    "session": session_id,
                },
            }, now_fields=("ts",))))
        rounds.append(round_acts)
        # Early-exit if the Integrator emitted a recommend.
        if decision is not None:
            break
    # If no recommend was emitted, force one last Integrator round.
    if decision is None:
        forced = await _dci_call_persona(
            "integrator",
            _DCI_INTEGRATOR_SYSTEM + (
                "\n\nIMPORTANT: This is the FINAL round. You MUST "
                "emit `recommend` as your act -- not `synthesize`, "
                "not `bridge`. The workspace has reached R_max; "
                "the deliberation MUST close with a decision."
            ),
            user_text, workspace,
        )
        if forced and forced.get("act") == "recommend":
            decision = forced
    converged = decision is not None
    # Dissent extraction: high-confidence challenges/asks that
    # were never resolved by a subsequent recommend/synthesize.
    dissents = [
        a for a in workspace["challenges"]
        if a.get("confidence", 0.0) >= 0.7
    ]
    for d in dissents:
        # Awaited (not fire-and-forget) so downstream consumers
        # querying right after run_dci_flow returns see the rows.
        await _db_post(_db_create("event", {
            "source": "mios-agent-pipe",
            "kind": "dissent",
            "severity": "warn",
            "summary": f"unresolved {d['act']} ({d['confidence']:.2f})",
            "payload": {
                "persona": d.get("persona"),
                "content": (d.get("content") or "")[:500],
                "session": session_id,
            },
        }, now_fields=("ts",)))
    # Final decision packet -- always returned, even on
    # convergence failure (fallback uses the most-recent synthesis
    # if Integrator couldn't be coerced into a recommend).
    if decision is None and workspace["syntheses"]:
        decision = dict(workspace["syntheses"][-1])
        decision["fallback"] = True
    return {
        "decision": decision,
        "rounds": rounds,
        "dissents": dissents,
        "converged": converged,
        "rounds_used": len(rounds),
        "workspace": {
            "frames":     len(workspace["frames"]),
            "proposals":  len(workspace["proposals"]),
            "challenges": len(workspace["challenges"]),
            "syntheses":  len(workspace["syntheses"]),
        },
    }


# Phase B.3 -- conditional B.2 trigger.
# When the cheap B.1 Challenger emits a HIGH-CONFIDENCE
# `challenge` or `ask` (>= DCI_FLOW_TRIGGER_CONF), automatically
# fire the heavy B.2 4-persona convergent flow. If the flow then
# surfaces unresolved dissent, write a tainted tool_call row so
# the operator's NEXT dispatch in the same session gets refused by
# the Semantic Firewall. The whole chain runs fire-and-forget so
# the operator's reply isn't delayed.
#
# Operator-tunable threshold (default 0.7 -- matches the dissent
# extraction threshold used in run_dci_flow).
DCI_FLOW_TRIGGER_CONF = float(os.environ.get(
    "MIOS_AGENT_PIPE_DCI_FLOW_TRIGGER_CONF", "0.7"))

# Critic->refiner (ref AIOS B.1 / OS-Copilot executor-critic-refiner).
# ENABLED BY DEFAULT, but fires AS NEEDED: only on the HEAVY agent path,
# only for substantive answers (>= MIN_CHARS), and only re-invokes when
# the DCI critic raises a high-confidence challenge/ask (a genuinely
# contested/complex resolution). Simple/short answers and the entire
# mios-os-control DISPATCH fast path skip it -> CPU usecases stay fast,
# GPU/heavy answers earn the quality loop. Bounded; falls back to the
# original answer on any error. Operator 2026-05-19: "DCI fires as needed
# for more complex resolutions" -- this is that gate.
CRITIC_REFINE_ENABLED = os.environ.get(
    "MIOS_AGENT_PIPE_CRITIC_REFINE", "1") not in ("0", "false", "False", "")
CRITIC_REFINE_MAX = int(os.environ.get(
    "MIOS_AGENT_PIPE_CRITIC_REFINE_MAX", "1"))
CRITIC_REFINE_MIN_CHARS = int(os.environ.get(
    "MIOS_AGENT_PIPE_CRITIC_REFINE_MIN_CHARS", "500"))


async def _critic_refine_agent(
    raw: str,
    user_text: str,
    refined: Optional[dict],
    session_id: Optional[str],
    *,
    client,
    target_endpoint: str,
    headers: dict,
    base_body: dict,
) -> str:
    """Critic->refiner for the HEAVY agent path (ref AIOS B.1 / OS-Copilot
    executor-critic-refiner). Run the DCI critic on the buffered agent
    answer; if it raises a high-confidence challenge/ask (a genuinely
    contested/complex resolution), re-invoke the backend ONCE with the
    critic's concern so the answer is revised, then return the revision.

    Fires AS NEEDED: short/simple answers (< CRITIC_REFINE_MIN_CHARS) and
    the mios-os-control dispatch fast path never reach here, so CPU
    usecases stay fast; GPU/heavy answers earn the loop. Bounded by
    CRITIC_REFINE_MAX; returns the ORIGINAL answer on any error or when
    the critic is satisfied (the common case)."""
    if not (CRITIC_REFINE_ENABLED and DCI_ENABLED):
        return raw
    if not raw or len(raw) < CRITIC_REFINE_MIN_CHARS:
        return raw
    envelope = {
        "intent": (refined or {}).get("intent", "agent"),
        "answer": raw[:4000],
        "user_text": (user_text or "")[:1000],
    }
    try:
        act = await dci_critic_pass(user_text, envelope, session_id=session_id)
    except Exception as e:
        log.warning("critic-refine: critic pass failed: %s", e)
        return raw
    if not act or not (
            act.get("act") in ("challenge", "ask")
            and float(act.get("confidence", 0.0)) >= DCI_FLOW_TRIGGER_CONF):
        return raw  # critic satisfied -> answer stands (common case)
    concern = str(act.get("content") or "").strip()[:600]
    if not concern:
        return raw
    refine_body = dict(base_body)
    refine_body["stream"] = False
    refine_body["messages"] = list(refine_body.get("messages") or []) + [
        {"role": "assistant", "content": raw},
        {"role": "user", "content":
            f"A reviewer raised this concern about your answer: {concern}\n"
            f"Revise your answer to fully address it. Be correct and "
            f"concise; do not mention this review."},
    ]
    out = raw
    for _ in range(max(1, CRITIC_REFINE_MAX)):
        try:
            r = await client.post(
                f"{target_endpoint}/chat/completions",
                content=json.dumps(refine_body).encode("utf-8"),
                headers=headers,
            )
            if r.status_code != 200:
                break
            j = r.json()
            ch = j.get("choices") or []
            new = (str((ch[0].get("message") or {}).get("content") or "")
                   if ch else "")
            if new.strip():
                out = new
                _emit_session_event({
                    "source": "mios-agent-pipe",
                    "kind": "critic_refine",
                    "severity": "info",
                    "summary": (f"refined on {act.get('act')} "
                                f"conf={act.get('confidence')}"),
                    "payload": {"concern": concern[:200]},
                }, session_id)
                break
        except Exception as e:
            log.warning("critic-refine: re-invoke failed: %s", e)
            break
    return out


async def critic_then_maybe_flow(
    user_text: str,
    envelope: dict,
    *,
    session_id: Optional[str] = None,
) -> None:
    """Chain B.1 critic -> conditional B.2 flow. Fire-and-forget
    via _db_fire so the dispatch reply isn't delayed.

    Phase B.3 flow:
      1. Run dci_critic_pass (single-persona Challenger).
      2. If the act is in (challenge, ask) AND confidence is high,
         escalate to run_dci_flow (4 personas, bounded loop).
      3. If the flow surfaces unresolved dissent, write a tainted
         tool_call row keyed to the session so any subsequent
         high-privilege verb in this session gets firewalled.
    """
    if not (DCI_ENABLED or DCI_FLOW_ENABLED):
        return
    # Stage 1: B.1 critic.
    act = await dci_critic_pass(user_text, envelope, session_id=session_id)
    if not act:
        return
    # Conditional escalation to B.2.
    if (act.get("act") in ("challenge", "ask")
            and act.get("confidence", 0.0) >= DCI_FLOW_TRIGGER_CONF):
        # Sentinel raised; fire the B.2 jury. Cap rounds at 2 for
        # the auto-trigger path (operator can still hit /dci/
        # deliberate manually for the full R_max=3 budget).
        result = await run_dci_flow(
            user_text, envelope,
            session_id=session_id, r_max=2,
        )
        # If the flow surfaced unresolved dissent, write a tainted
        # tool_call row so the Semantic Firewall blocks subsequent
        # high-privilege verbs in this session.
        #
        # NB: this write is AWAITED (not fire-and-forget). The
        # firewall pre-check on the operator's NEXT dispatch needs
        # to see this row -- if we fire-and-forget it, a sub-second
        # follow-up dispatch from the operator could land BEFORE
        # the write completes and slip past the firewall (operator-
        # observed race 2026-05-18: the dissent row didn't show up
        # in the SurrealDB readback because the loop returned before
        # the pending writes settled).
        if result.get("dissents") and session_id:
            taint_row = {
                "tool": "dci_dissent",
                "args": {
                    "dissent_count": len(result["dissents"]),
                    "trigger_act": act["act"],
                    "trigger_conf": act["confidence"],
                },
                "result_preview": (
                    f"DCI flow surfaced {len(result['dissents'])} "
                    f"unresolved dissent(s) -- session tainted"
                ),
                "success": False,
                "latency_ms": 0,
                "tainted": True,
                "taint_reason": (
                    f"dci_dissent:{len(result['dissents'])}_"
                    f"unresolved_after_r{result.get('rounds_used',0)}"
                ),
            }
            await _db_post(
                _db_create("tool_call", taint_row, now_fields=("ts",)).rstrip(";")
                + f", session = {session_id};"
            )


# Pydantic-free request shape for /dci/deliberate -- accept raw
# JSON so the operator can curl-test on the fly without writing a
# client.

async def dci_critic_pass(
    user_text: str,
    envelope: dict,
    *,
    session_id: Optional[str] = None,
) -> Optional[dict]:
    """Post-dispatch critic: invokes the DCI Challenger persona on
    the (user_text, envelope) pair and emits ONE typed epistemic
    act. Returns the parsed act dict, or None on any error.

    Fire-and-forget at the caller's discretion -- the chat reply is
    already rendered by the time this runs. SurrealDB event row
    written automatically (kind=dci_act, source=mios-agent-pipe).
    """
    if not DCI_ENABLED or not user_text:
        return None
    # Compact envelope for the critic prompt -- keep latency low
    # by passing just the structured tool_call + tool_result, not
    # the full rendered <details> block.
    compact = {
        "tool":       (envelope.get("tool_call") or {}).get("function", {}).get("name"),
        "args":       (envelope.get("tool_call") or {}).get("function", {}).get("arguments"),
        "success":    (envelope.get("tool_result") or {}).get("success"),
        "output":    ((envelope.get("tool_result") or {}).get("output") or "")[:600],
        "stderr":    ((envelope.get("tool_result") or {}).get("stderr") or "")[:200],
        "exit_code":  (envelope.get("tool_result") or {}).get("exit_code"),
    }
    user_msg = (
        f"OPERATOR PROMPT:\n{user_text[:1500]}\n\n"
        f"AGENT ENVELOPE:\n{json.dumps(compact, indent=2, default=str)}\n\n"
        "Emit ONE typed epistemic act now:"
    )
    payload = {
        "model": DCI_MODEL,
        "messages": [
            {"role": "system", "content": _DCI_CRITIC_SYSTEM},
            {"role": "user",   "content": user_msg},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.0,
        "max_tokens": DCI_MAX_TOKENS,
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=DCI_TIMEOUT_S) as s:
            r = await s.post(
                f"{DCI_ENDPOINT}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            if r.status_code != 200:
                return None
            body = r.json()
    except (httpx.HTTPError, asyncio.TimeoutError):
        return None
    except Exception as e:
        log.warning("dci_critic unexpected error: %s", e)
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
    if not isinstance(parsed, dict):
        return None
    act = parsed.get("act")
    if act not in DCI_ACTS:
        return None
    # Normalize + cap confidence.
    try:
        parsed["confidence"] = max(0.0, min(1.0, float(parsed.get("confidence", 0.5))))
    except (TypeError, ValueError):
        parsed["confidence"] = 0.5
    family = DCI_ACTS[act]["family"]
    # SurrealDB event row -- tag with the act + family for later
    # analytics (e.g. SELECT * FROM event WHERE kind='dci_act' AND
    # payload.act='challenge' to find what the critic challenged).
    severity = "warn" if act in ("challenge", "ask") and parsed["confidence"] >= 0.7 else "info"
    row = {
        "source":  "mios-agent-pipe",
        "kind":    "dci_act",
        "severity": severity,
        "summary": f"{family}/{act} ({parsed['confidence']:.2f})",
        "payload": {
            "act":         act,
            "family":      family,
            "confidence":  parsed.get("confidence"),
            "content":     (parsed.get("content") or "")[:600],
            "targets":     parsed.get("targets") or [],
            "session":     session_id,
        },
    }
    _db_fire(_db_post(_db_create("event", row, now_fields=("ts",))))
    return parsed


# ── Phase A.3 -- taint-aware memory + Semantic Firewall stub ─────
# When a verb fetches or exposes the agent to untrusted external
# content (current scope: open_url to a non-allowlisted domain;
# future: web_extract, knowledge_search hitting a third-party RAG
# doc, etc.), tag the tool_call row with tainted=true. Taint
# propagates within a session: any subsequent tool_call inherits
# tainted=true if ANY prior tool_call in the same session was
# tainted. High-privilege verbs are refused while taint is set --
# the Semantic Firewall stub. Refusals emit an event row
# {source=agent-pipe, kind=firewall_block, severity=high}.

# Verbs that perform a SYSTEM-AFFECTING action and must NOT run
# when the session is tainted. service_restart / container_restart
# touch the operator's host services; pc_type / pc_key / pc_click
# inject input into Win32 windows (could enter credentials if
# tainted content prompted it).
_HIGH_PRIVILEGE_VERBS = {
    "service_restart",
    "container_restart",
    "pc_type",
    "pc_key",
    "pc_click",
    # text_create / str_replace / insert are WRITE class -- a
    # tainted session could craft them to drop a payload anywhere
    # the agent has write access to.
    "text_create",
    "text_str_replace",
    "text_insert",
    # powershell_run executes arbitrary Windows-side script with
    # the operator's interop context. Single most dangerous verb
    # in the catalog -- always firewall-gated.
    "powershell_run",
    # Window-state verbs (D.3 PC-control template). All cause a
    # visible system effect -- a tainted session moving operator
    # windows or hiding them counts as the kind of thing the
    # firewall should refuse until the operator clears the chain.
    "minimize_window",
    "maximize_window",
    "restore_window",
    "resize_window",
    "position_window",
    # Package management WRITE verbs (D.4). install / upgrade /
    # uninstall on either platform can land arbitrary code on the
    # operator's machine -- tainted sessions are refused.
    "winget_install",
    "winget_upgrade",
    "winget_uninstall",
    "flatpak_install",
    "flatpak_upgrade",
    "flatpak_uninstall",
}

# Domains that are part of the operator's own infrastructure -- a
# verb opening these is NOT a taint source. Anything else
# constitutes a "we exposed the agent to untrusted external state"
# event and the tool_call gets tainted=true (the URL itself didn't
# return content, but the operator's screen now shows external
# content the agent might subsequently react to).
#
# Phase B.3 -- list now sources from mios.toml [security].allowlist_hosts
# via the userenv.sh slot map (MIOS_SECURITY_ALLOWLIST_HOSTS, CSV).
# Compiled-in defaults are the fallback when the env isn't set --
# they MUST match the mios.toml seed so a fresh deployment with no
# overrides still allows the canonical local-MiOS hosts.
_DEFAULT_ALLOWLIST_HOSTS = {
    "localhost", "127.0.0.1", "::1",
    "host.containers.internal",
    "mios-ollama", "mios-open-webui", "mios-hermes", "mios-surrealdb",
    "mios-forge", "mios-searxng", "mios-code-server",
}
_env_allowlist = os.environ.get("MIOS_SECURITY_ALLOWLIST_HOSTS", "").strip()
if _env_allowlist:
    _ALLOWLIST_HOSTS = {
        h.strip().lower() for h in _env_allowlist.split(",") if h.strip()
    }
else:
    _ALLOWLIST_HOSTS = set(_DEFAULT_ALLOWLIST_HOSTS)


def _is_external_url(url: str) -> bool:
    """Return True if the URL points OUTSIDE the operator's own
    infrastructure (i.e. a taint source). Best-effort host parse;
    anything ambiguous defaults to External (fail-safe)."""
    if not url or not isinstance(url, str):
        return False
    try:
        from urllib.parse import urlparse
        host = (urlparse(url).hostname or "").lower()
        if not host:
            return False
        if host in _ALLOWLIST_HOSTS:
            return False
        # Treat *.local + *.lan + plain hostnames (no dots) as internal.
        if host.endswith((".local", ".lan", ".internal")):
            return False
        if "." not in host:
            return False
        return True
    except Exception:
        return True  # fail-safe: ambiguous = treat as external


def _classify_verb_taint(tool: str, args: dict) -> tuple[bool, str]:
    """Decide whether a verb's OWN execution introduces taint.
    Returns (tainted, reason)."""
    if tool == "open_url":
        url = str((args or {}).get("url", ""))
        if _is_external_url(url):
            return True, f"external_open_url:{url[:80]}"
    # powershell_run output reflects Windows-side execution state
    # the agent didn't author -- treat as taint so subsequent high-
    # privilege verbs in the same session get firewall-checked.
    if tool == "powershell_run":
        return True, "powershell_output"
    # text_view of a system path (or any path under the write-
    # denied prefixes) reads content the agent didn't author, so
    # downstream high-priv verbs should be firewall-gated. The
    # denied-prefix list is the same one mios-text-edit uses for
    # write protection, mirrored here so the agent-pipe doesn't
    # need to shell out to look it up.
    if tool == "text_view":
        path = str((args or {}).get("path", ""))
        for prefix in (
            "/etc/", "/usr/", "/boot/", "/sys/", "/proc/", "/dev/",
            "/mnt/c/Windows/", "/mnt/c/Program Files/",
            "/mnt/c/Program Files (x86)/",
        ):
            if path.startswith(prefix):
                return True, f"text_view_system:{prefix}"
    return False, ""


async def _session_is_tainted(session_id: Optional[str]) -> tuple[bool, str]:
    """Look up whether the session has ANY prior tainted tool_call.
    Returns (tainted, reason_chain) where reason_chain summarises
    the upstream taint sources for the firewall event."""
    if not session_id:
        return False, ""
    # SurrealDB 3.0+ requires ORDER BY fields to be in the SELECT
    # projection -- include `ts` even though we don't use it past the
    # ordering (parse error otherwise: "Missing order idiom `ts` in
    # statement selection").
    sql = (
        f"SELECT ts, tool, taint_reason FROM tool_call "
        f"WHERE session = {session_id} AND tainted = true "
        f"ORDER BY ts ASC LIMIT 5;"
    )
    r = await _db_post(sql)
    if not r:
        return False, ""
    rows = (r[-1] or {}).get("result") or []
    if not rows:
        return False, ""
    chain = "; ".join(
        f"{row.get('tool','?')}:{row.get('taint_reason','')}"
        for row in rows
    )
    return True, chain[:300]


# ── Planner system prompt (Phase A.1 DAG decomposition) ───────────
# Function-calling-shaped prompt for qwen2.5-coder:7b. Emits a DAG
# of dispatch verbs WHEN the user's intent is multi-step. Returns
# {"action": "decompose", "nodes": [...]}. Each node has a unique
# id, a tool, args, and a list of node-id deps (parents). Empty
# nodes list = "I can't decompose this; fall through to backend".
#
# IMPORTANT: this prompt MUST stay in lockstep with the dispatch
# verb table in _build_dispatch_cmd. A planner emitting a verb the
# dispatcher doesn't know causes silent failures.

_PLANNER_SYSTEM = (
    "You are the MiOS planner (Agentic-OS DAG decomposition layer).\n"
    "The user's prompt has been classified as multi-step. Your job is\n"
    "to emit a DAG of MiOS dispatch verbs that, executed in topological\n"
    "order, fulfills the user's intent. Emit JSON ONLY.\n"
    "\n"
    "REASON -> PLAN -> DELEGATE meta-rule:\n"
    "  For any 'open / find / install / use / launch X' intent, the\n"
    "  FIRST DAG layer is ALWAYS a PARALLEL FAN-OUT of every relevant\n"
    "  inventory / search verb from the verb catalog below (deps=[]).\n"
    "  The action verb depends on ALL of them (deps=[n1,n2,...]) so it\n"
    "  runs only after probes complete. Never emit a single-node DAG\n"
    "  that goes straight to the action without the fan-out first --\n"
    "  the downstream agent has to be able to choose the right target,\n"
    "  and choosing requires evidence from MULTIPLE surfaces (Windows-\n"
    "  side index, Linux-side inventory, package managers, cached FS\n"
    "  map). A single refusal turn that declares something absent\n"
    "  without running any probe first is a defect.\n"
    "\n"
    "Output shape (EXACT):\n"
    '{"action":"decompose",\n'
    ' "summary": "<one-line plan in user\'s language>",\n'
    ' "nodes": [\n'
    '   {"id":"n1","tool":"<verb>","args":{...},"deps":[]},\n'
    '   {"id":"n2","tool":"<verb>","args":{...},"deps":["n1"]},\n'
    '   {"id":"n3","agent":"<sub-agent>","prompt":"<sub-task>","deps":[]},\n'
    '   ...\n'
    ' ]}\n'
    "\n"
    "TWO node kinds -- pick per sub-task:\n"
    "  * a `tool` node runs ONE MiOS dispatch verb (direct OS action /\n"
    "    probe; from the verb catalog below).\n"
    "  * an `agent` node DELEGATES a self-contained sub-task to a named\n"
    "    sub-agent (from the sub-agent roster below) -- use it when the\n"
    "    sub-task needs an agent's own reasoning + tool-loop (code work ->\n"
    "    the coding agent; open-ended research/synthesis -> a general\n"
    "    agent; a quick second opinion / summary -> the cpu reasoner).\n"
    "    `prompt` is the sub-task in the user's language; it MAY contain\n"
    "    #E<id> refs to upstream outputs (substituted at run time).\n"
    "ROUTE DIFFERENT sub-tasks to DIFFERENT agents and give independent\n"
    "ones deps=[] so they run CONCURRENTLY (the executor runs every node\n"
    "whose deps are satisfied in parallel). Weigh the whole roster -- do\n"
    "not funnel everything to one agent. Reserve agent nodes for sub-tasks\n"
    "a single verb cannot cover; do not wrap a plain verb in an agent node.\n"
    "\n"
    "If you cannot decompose into AT LEAST 2 dispatchable nodes, emit\n"
    '{"action":"decompose","summary":"","nodes":[]} so the chain falls\n'
    "through to the backend sub-agent (Hermes / OpenCode / etc.) which\n"
    "has tool-calling + web access itself.\n"
    "\n"
    "ReWOO-style forward refs: an arg can reference an upstream node's\n"
    "stdout via `#E<node-id>` or `#E<node-id>.<field>`. The dispatcher\n"
    "substitutes the actual output at execute time, so you don't have\n"
    "to know the runtime value when planning. Two ref forms:\n"
    "\n"
    "  #E<id>          smart-extract a single useful field from the\n"
    "                  upstream output (handles JSON / NDJSON / plain\n"
    "                  text; picks `name` / `launch` / `title` / `id`\n"
    "                  / `path` in that order). Use when you don't\n"
    "                  care which field, just want THE useful value.\n"
    "\n"
    "  #E<id>.<field>  extract a NAMED field from the upstream's JSON\n"
    "                  output. PREFERRED when you know which field you\n"
    "                  need -- avoids ambiguity if the model picks the\n"
    "                  wrong default field.\n"
    "\n"
    "Example A -- list games, pick winner, launch:\n"
    '  {"id":"n1","tool":"mios_apps","args":{"filter":"games"},"deps":[]},\n'
    '  {"id":"n2","tool":"web_search","args":{"query":"highest rated of: #En1.description"},"deps":["n1"]},\n'
    '  {"id":"n3","tool":"open_app","args":{"name":"#En1.name"},"deps":["n1","n2"]}\n'
    "\n"
    "Example B -- find a file then open it (PREFER this over mios-find\n"
    "for `find X` / `where is X` -- directory_lookup is ~100x faster):\n"
    '  {"id":"n1","tool":"directory_lookup","args":{"query":"<X>","kind":"file","limit":1},"deps":[]},\n'
    '  {"id":"n2","tool":"text_view","args":{"path":"#En1.path"},"deps":["n1"]}\n'
    "\n"
    "NEVER paste the raw `#E<id>` value into a launcher arg without\n"
    "thought -- mios_apps + directory_lookup return NDJSON-like results\n"
    "(one record per hit), so a bare #En1 in open_app(name=#En1) would\n"
    "substitute only the FIRST hit's smart-extracted field. If you want\n"
    "a specific record's specific field, use #En1.<field> to pull it\n"
    "explicitly (.name / .app_id / .path / .launch / .description).\n"
    "\n"
    "CRITICAL: the action verb's target NAME comes from the PROBE'S\n"
    "OUTPUT (#En1.app_id / #En1.short_name / #En1.name), NEVER from\n"
    "the probe verb's OWN name:\n"
    "  WRONG -- launch_app(name='mios_apps')   <-- emits the probe verb name\n"
    "  WRONG -- launch_app(name='mios-apps')   <-- same defect with hyphen\n"
    "  RIGHT -- launch_app(name='#En1.app_id') <-- ref the discovered app\n"
    "If you cannot decompose 'find X then launch X' into ref-substitution,\n"
    "emit empty nodes and let the backend sub-agent handle it -- never\n"
    "fall back to launching the discovery tool itself.\n"
    "\n"
    "Available verbs (SSOT: mios.toml [verbs.*]; renderer reads it at\n"
    "boot, no English baked in this file). Use EXACT name + args shape\n"
    "-- the dispatcher rejects unknown verbs:\n"
    "\n"
    + _VERB_CATALOG_RENDERED + "\n\n"
    + _RECIPE_CATALOG_RENDERED + "\n\n"
    "Sub-agent roster for `agent` nodes (SSOT: mios.toml [agents.*]; use\n"
    "the EXACT name -- the executor rejects unknown agents):\n"
    "\n"
    + _AGENT_CATALOG_RENDERED + "\n\n"
    "Common patterns (study these before emitting):\n"
    "\n"
    "  open + position:\n"
    "    n1 open_app(name=X) -> n2 focus_window(title=X) -> n3 position_window(title=X, x=A, y=B)\n"
    "\n"
    "  open + write file (NO more pc_type+pc_key; use text_create):\n"
    "    n1 text_create(path=P, content=C) -> n2 text_view(path=P)\n"
    "\n"
    "  flatpak launch with health check:\n"
    "    n1 flatpak_preflight(id=X) -> n2 open_app(name=X)\n"
    "    (preflight halts on broken sandbox; agent surfaces real error)\n"
    "\n"
    "  inventory + filter (e.g. 'show me my browsers'):\n"
    "    n1 mios_apps(filter='browser') -> n2 (chain only when narrowing further)\n"
    "\n"
    "  install + launch:\n"
    "    n1 winget_search(query=X) -> n2 winget_install(id=X) -> n3 open_app(name=X)\n"
    "    n1 flatpak_search(query=X) -> n2 flatpak_install(id=X) -> n3 open_app(name=X)\n"
    "\n"
    "  tile two windows:\n"
    "    n1 position_window(title=L, x=0, y=0) -> n2 resize_window(title=L, ...)\n"
    "    n3 position_window(title=R, x=HW, y=0) -> n4 resize_window(title=R, ...)\n"
    "\n"
    "When NOT to decompose (return empty nodes):\n"
    "- Web research / 'find reviews of X' / 'what's the best Y' -- the backend\n"
    "  sub-agent owns web_search/web_extract; no broker verb covers it.\n"
    "- Pure conversational / explanation requests -- those are chat, not DAG.\n"
    "- Multi-source synthesis where the planner can't fix the source list\n"
    "  upfront -- delegate to the backend sub-agent.\n"
    "- BUT for inventory + research + action like 'find my games, look up\n"
    "  reviews, launch the best': emit the INVENTORY step (n1 mios_apps())\n"
    "  + leave the research+launch to follow-up turns guided by the backend.\n"
    "\n"
    "Rules:\n"
    "- Linearize when possible: each node depends only on its predecessor.\n"
    "- Cap your DAG at " + str(PLANNER_MAX_NODES) + " nodes.\n"
    "- Output JSON ONLY -- no preamble, no markdown, no commentary."
)


async def decompose_intent(user_text: str) -> Optional[dict]:
    """Call the planner LLM to emit a DAG of dispatch verbs for a
    multi-step user intent. Returns the parsed dict, or None on
    error / unparseable response.

    Short-prompt skip: short inputs (heuristic: <60 chars, <=10
    whitespace-separated tokens) almost always map to a SINGLE
    dispatch verb, not a multi-step plan. Return None so the chain
    falls through to the backend single-dispatch path -- mios-launch
    resolves the verb directly. The planner used to over-decompose
    these into 2-step DAGs whose ReWOO substitution then misfired
    on NDJSON-emitting tools."""
    if not PLANNER_ENABLED or not user_text or not user_text.strip():
        return None
    _ut = user_text.strip()
    if len(_ut) < 60 and len(_ut.split()) <= 10:
        log.info("planner: short-prompt skip (%d chars, %d words)",
                 len(_ut), len(_ut.split()))
        return None
    payload = {
        "model": PLANNER_MODEL,
        "messages": [
            {"role": "system", "content": _PLANNER_SYSTEM},
            {"role": "user",   "content": user_text[:4000]},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.0,
        "max_tokens": PLANNER_MAX_TOKENS,
        "stream": False,
    }
    url = f"{PLANNER_ENDPOINT}/v1/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=PLANNER_TIMEOUT_S) as s:
            r = await s.post(url, json=payload,
                             headers={"Content-Type": "application/json"})
            if r.status_code != 200:
                return None
            body = r.json()
    except (httpx.HTTPError, asyncio.TimeoutError):
        return None
    except Exception as e:
        log.warning("planner unexpected error: %s", e)
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
    if not isinstance(parsed, dict) or "nodes" not in parsed:
        return None
    nodes = parsed.get("nodes") or []
    if not isinstance(nodes, list) or len(nodes) < 2:
        return None
    if len(nodes) > PLANNER_MAX_NODES:
        nodes = nodes[:PLANNER_MAX_NODES]
        parsed["nodes"] = nodes
    # Validate each node: an `agent` node must name a registered sub-agent
    # + carry a prompt; a `tool` node must resolve to a known verb. A mixed
    # DAG (some agents, some verbs) is fine.
    for n in nodes:
        if not isinstance(n, dict) or "id" not in n:
            return None
        if n.get("agent"):
            if str(n["agent"]) not in _AGENT_REGISTRY:
                log.info("planner emitted unknown agent %r; discarding DAG",
                         n.get("agent"))
                return None
            if not str(n.get("prompt") or "").strip():
                log.info("planner agent node %r missing prompt; discarding",
                         n.get("id"))
                return None
            continue
        if "tool" not in n:
            return None
        if _build_dispatch_cmd(str(n["tool"]), n.get("args") or {}) is None:
            log.info("planner emitted unknown verb %r; discarding DAG",
                     n.get("tool"))
            return None
    return parsed


def _topological_order(nodes: list[dict]) -> list[dict]:
    """Return nodes in dependency order. Unknown / cyclic deps fall
    back to declaration order so we never hang."""
    by_id = {n.get("id"): n for n in nodes if isinstance(n, dict)}
    visited: set = set()
    out: list = []
    def visit(nid):
        if nid in visited or nid not in by_id:
            return
        visited.add(nid)
        for d in (by_id[nid].get("deps") or []):
            visit(d)
        out.append(by_id[nid])
    for n in nodes:
        visit(n.get("id"))
    return out


def _dag_levels(nodes: list[dict]) -> list[list[dict]]:
    """Group nodes into concurrent execution LEVELS (Kahn layering): each
    level is the set of not-yet-run nodes whose deps are ALL already
    satisfied, so every node in a level can run CONCURRENTLY. A level only
    starts after all earlier levels finish, preserving topological order
    (so ReWOO #E<id> refs resolve). Cyclic / dangling deps degrade to one
    forced node per round (declaration order) so the DAG never hangs --
    same safety stance as _topological_order."""
    by_id = {n.get("id"): n for n in nodes
             if isinstance(n, dict) and "id" in n}
    remaining = [n for n in nodes if isinstance(n, dict) and "id" in n]
    done: set = set()
    levels: list[list[dict]] = []
    while remaining:
        ready = [n for n in remaining
                 if all((d in done) or (d not in by_id)
                        for d in (n.get("deps") or []))]
        if not ready:  # cycle / dangling dep -- force progress, no hang
            ready = [remaining[0]]
        levels.append(ready)
        ready_ids = {n.get("id") for n in ready}
        done |= ready_ids
        remaining = [n for n in remaining if n.get("id") not in ready_ids]
    return levels


_REFLECT_SYSTEM = (
    "You are MiOS-Agent's single-step reflection pass. A planner\n"
    "emitted a multi-step plan; one step's dispatch FAILED. Read the\n"
    "failed step + the captured error + the surrounding plan, and\n"
    "emit ONE corrected step as JSON. Do NOT re-plan the whole\n"
    "chain. Do NOT add commentary. Just the correction.\n"
    "\n"
    "Output shape (EXACT):\n"
    '{"tool": "<verb>", "args": {...}, "rationale": "<one line>"}\n'
    "\n"
    "Rules:\n"
    "- Keep the same node id if possible; downstream nodes may have\n"
    "  #E<id> refs to it.\n"
    "- If the failure was 'unknown verb', pick a different verb that\n"
    "  does the same thing (open_app vs launch_app, etc.).\n"
    "- If the failure was 'missing arg', add the arg.\n"
    "- If the failure was 'tool returned exit 2 with stderr X', look\n"
    "  at stderr for the actual cause + adjust args (a path that\n"
    "  doesn't exist, a flag the tool doesn't accept, a query that\n"
    "  needs quoting differently).\n"
    "- If the failure looks irrecoverable from a single-step swap,\n"
    "  emit {\"tool\":\"\",\"args\":{},\"rationale\":\"unfixable\"} and\n"
    "  the dispatcher will abort the chain.\n"
)


def _emit_session_event(fields: dict, session_id: Optional[str]) -> None:
    """Write an `event` row, linked to the session when known so the
    Reflexion buffer (_recent_reflections) can query it back per-session.
    Mirrors execute_dag's tool_call session-linking convention."""
    sql = _db_create("event", fields, now_fields=("ts",))
    if session_id:
        sql = sql.rstrip().rstrip(";") + f", session = {session_id};"
    _db_fire(_db_post(sql))


async def _recent_reflections(session_id: Optional[str],
                              limit: int = 4) -> list[dict]:
    """Reflexion episodic buffer (ref AIOS B.3 / Shinn et al. 2023): pull
    recent `reflect_corrected` events for THIS session so a fresh
    reflection can REUSE a prior fix instead of re-deriving it. The audit
    flagged these rows as write-only -- this is the missing read side.
    Best-effort: returns [] on any DB miss so reflection never blocks."""
    if not session_id:
        return []
    sql = (
        f"SELECT summary, ts FROM event "
        f"WHERE kind = 'reflect_corrected' AND session = {session_id} "
        f"ORDER BY ts DESC LIMIT {int(limit)};"
    )
    r = await _db_post(sql)
    if not r:
        return []
    rows = (r[-1] or {}).get("result") or []
    return rows if isinstance(rows, list) else []


async def reflect_on_step_failure(
    failed_node: dict,
    failed_result: dict,
    plan_context: dict,
    session_id: Optional[str] = None,
) -> Optional[dict]:
    """ReWOO-style reflection: route a failed DAG step back to the
    SAME small refine model with the failure context and ask for a
    single corrected step. Returns {tool, args, rationale} dict
    or None on timeout/empty.

    Distinct from the retry-same-args loop (PLANNER_REFLEXION_CAP):
    that retries transient errors; this REPLACES the args/tool when
    the failure is structural (wrong verb, missing arg, wrong path).
    Three-stage Reflect/Call/Final pipeline -- caller bounds the
    number of reflection turns to 1, so a stubborn failure surfaces
    as a real error instead of looping (per the published
    Structured Reflection termination contract)."""
    if not REFINE_ENABLED:
        return None
    failed_tool = failed_node.get("tool", "?")
    failed_args = failed_node.get("args") or {}
    error_preview = (
        (failed_result.get("stderr") or "")[:400]
        or (failed_result.get("error") or "")[:400]
        or (failed_result.get("output") or "")[:400]
        or "(empty)"
    )
    exit_code = failed_result.get("exit_code", "?")
    plan_summary = str(plan_context.get("summary") or "")[:200]
    # Reflexion read-back (ref AIOS B.3): prior corrections in this session
    # inform the new fix instead of re-deriving from scratch. Best-effort;
    # empty when there are none / no session. Feeds the REFLECTION prompt
    # (an internal pass), NOT the first-turn user message -- so it stays
    # clear of the NO-context-injection binding (which targets env auto-
    # injection into the user prompt).
    prior_hint = ""
    _prior = await _recent_reflections(session_id)
    if _prior:
        _lines = [f"  - {str(p.get('summary') or '').strip()}"
                  for p in _prior if str(p.get("summary") or "").strip()]
        if _lines:
            prior_hint = ("\nPrior fixes this session (reuse the pattern if "
                          "it matches this failure):\n" + "\n".join(_lines))
    user_msg = (
        f"Plan summary: {plan_summary}\n"
        f"Failed step: tool={failed_tool} "
        f"args={json.dumps(failed_args, separators=(',', ':'))[:300]}\n"
        f"Exit code: {exit_code}\n"
        f"Stderr/error: {error_preview}"
        f"{prior_hint}\n"
        "/no_think"
    )
    payload = {
        "model": REFINE_MODEL,
        "messages": [
            {"role": "system", "content": _REFLECT_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        "think": False,
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 400},
    }
    url = f"{REFINE_ENDPOINT}/api/chat"
    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=REFINE_TIMEOUT_S) as s:
            r = await s.post(url, json=payload,
                             headers={"Content-Type": "application/json"})
            if r.status_code != 200:
                log.warning("reflect: backend %s in %.1fs",
                            r.status_code, time.time() - t0)
                return None
            body = r.json()
    except (httpx.HTTPError, asyncio.TimeoutError) as e:
        log.warning("reflect: timeout/http after %.1fs: %s",
                    time.time() - t0, e)
        return None
    except Exception as e:
        log.warning("reflect unexpected error: %s", e)
        return None
    elapsed = time.time() - t0
    # /api/chat shape {"message":{"content"}}; /v1 choices[] fallback.
    msg = body.get("message")
    if not isinstance(msg, dict):
        choices = body.get("choices") or []
        msg = (choices[0].get("message") if choices else {}) or {}
    content = (msg.get("content") or "").strip()
    if not content:
        log.warning("reflect: %.1fs empty_content", elapsed)
        return None
    content = re.sub(r"<think>.*?</think>\s*", "", content,
                     flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r"^\s*```(?:json)?\s*\n?", "", content)
    content = re.sub(r"\n?```\s*$", "", content)
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        log.warning("reflect: %.1fs parse_fail: %s preview=%r",
                    elapsed, e, content[:200])
        return None
    if not isinstance(parsed, dict):
        return None
    new_tool = str(parsed.get("tool") or "").strip()
    if not new_tool:
        log.info("reflect: %.1fs marked unfixable", elapsed)
        _emit_session_event({
            "source": "mios-agent-pipe",
            "kind": "reflect_unfixable",
            "severity": "warn",
            "summary": f"reflection declined: {failed_tool}",
            "payload": {
                "failed_node": failed_node,
                "failed_result_preview": error_preview,
                "rationale": parsed.get("rationale", "")[:200],
                "elapsed_s": round(elapsed, 1),
            },
        }, session_id)
        return None
    log.info("reflect: %.1fs corrected tool=%s -> %s",
             elapsed, failed_tool, new_tool)
    _emit_session_event({
        "source": "mios-agent-pipe",
        "kind": "reflect_corrected",
        "severity": "info",
        "summary": f"{failed_tool} -> {new_tool}",
        "payload": {
            "failed_node": failed_node,
            "failed_result_preview": error_preview,
            "corrected": parsed,
            "elapsed_s": round(elapsed, 1),
        },
    }, session_id)
    return parsed


_EK_REF_RE = re.compile(r"#E([A-Za-z0-9_]+)")


_EK_FIELD_REF_RE = re.compile(r"#E([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)")


# ── Tool-output sanitizer (structural; binding-compliant) ──────────
# The reference flags tool-result prompt-injection as the "most
# underrated risk": tool stdout is untrusted and re-enters BOTH the
# ReWOO #E<id> arg substitution AND the polish-prompt preview. A
# content denylist ("ignore previous instructions", ...) would be
# HARDCODED ENGLISH -- forbidden by operator binding -- so we instead
# do STRUCTURAL neutralisation that carries no English/topic content:
#   * ANSI/CSI escape sequences (terminal-control spoofing),
#   * Unicode bidi overrides + isolates (Trojan-Source CVE-2021-42574,
#     used to make displayed text differ from logical order),
#   * C0 control chars except tab/newline/CR.
# This complements the provenance-taint Semantic Firewall (which blocks
# the tainted->high-privilege ESCALATION path); together they cover both
# the escalation and the prompt/arg-spoofing vectors without an English
# classifier. BOM (U+FEFF) stripped too -- it has no place mid-stream.
_ANSI_CSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
_BIDI_OVERRIDE_RE = re.compile("[‪-‮⁦-⁩﻿]")


def _sanitize_tool_text(s: str) -> str:
    """Strip terminal-control + bidi-override + C0 control chars from
    untrusted tool output before it re-enters an arg or a prompt.
    Structural only -- preserves tab/newline/CR and all printable
    content -- so it neither classifies by English keyword nor mangles
    legitimate Unicode (emoji ZWJ sequences are left intact)."""
    if not s:
        return s
    s = _ANSI_CSI_RE.sub("", s)
    s = _BIDI_OVERRIDE_RE.sub("", s)
    return "".join(ch for ch in s if ch >= " " or ch in "\t\n\r")


def _smart_extract_from_jsonish(payload: str) -> str:
    """Pull the most-useful single field out of a JSON-ish blob so a
    ReWOO bare `#E<id>` ref doesn't paste the whole multi-line dump
    into a downstream arg. Trace failure: mios_apps returns NDJSON
    (one app per line). #En1 substituted the FULL stdout into
    open_app(name=...), producing args like
    `{"category":"linux-flatpak","name":"devel",...}\\n{"...":"..."}\\n`
    which mios-launch can't resolve to anything.

    Resolution order:
      1. Single JSON object -> prefer `name`, then `launch`, then
         `title`, then `id`, then `path`, then first string field.
      2. NDJSON (one object per line) -> use the FIRST object's
         best field via the same rule.
      3. Not JSON -> return the first line, capped at 1024 chars
         (matches the prior naive behavior for plain-text upstream)."""
    s = _sanitize_tool_text((payload or "").strip())
    if not s:
        return ""
    # Try a single JSON object first.
    try:
        obj = json.loads(s)
        if isinstance(obj, dict):
            for k in ("name", "launch", "title", "id", "path"):
                v = obj.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()[:1024]
            for v in obj.values():
                if isinstance(v, str) and v.strip():
                    return v.strip()[:1024]
        elif isinstance(obj, list) and obj:
            first = obj[0]
            if isinstance(first, str):
                return first.strip()[:1024]
            if isinstance(first, dict):
                for k in ("name", "launch", "title", "id", "path"):
                    v = first.get(k)
                    if isinstance(v, str) and v.strip():
                        return v.strip()[:1024]
    except (json.JSONDecodeError, ValueError):
        pass
    # NDJSON: try the first line.
    first_line = s.splitlines()[0].strip()
    if first_line.startswith("{") and first_line.endswith("}"):
        try:
            obj = json.loads(first_line)
            if isinstance(obj, dict):
                for k in ("name", "launch", "title", "id", "path"):
                    v = obj.get(k)
                    if isinstance(v, str) and v.strip():
                        return v.strip()[:1024]
        except (json.JSONDecodeError, ValueError):
            pass
    # Plain text fallback: first non-empty line, capped.
    return first_line[:1024]


def _substitute_ek_refs(args: dict, results_by_id: dict) -> dict:
    """ReWOO-style substitution: replace `#E<node-id>` tokens in arg
    values with the captured stdout of the upstream node. Two forms
    supported:

      #E<id>            -> smart-extract a single useful field from
                           the upstream output (handles JSON objects
                           + NDJSON streams; falls back to first line
                           for plain text). Caps at 1024 chars.
      #E<id>.<field>    -> extract a NAMED field from the upstream
                           JSON output. Use this when the planner
                           knows which field it needs (e.g.,
                           open_app(name='#En1.launch') to use the
                           launch line from a mios_apps row).

    Per ReWOO (Xu et al. 2023): the planner emits #E<id> placeholders
    and the worker substitutes them with actual outputs at execute
    time. Removes the per-step LLM re-plan that other frameworks
    need.

    Only handles string args (the common case for shell verbs).
    Object / list args pass through unchanged."""
    if not args:
        return args
    out: dict = {}
    for k, v in args.items():
        if isinstance(v, str) and "#E" in v:
            # Field-ref form #E<id>.<field> -- replace first since
            # the bare-ref regex also matches.
            def _sub_field(m: re.Match) -> str:
                ref, field = m.group(1), m.group(2)
                r = results_by_id.get(ref)
                if not r:
                    return m.group(0)
                payload = r.get("output") or ""
                try:
                    obj = json.loads(payload)
                except (json.JSONDecodeError, ValueError):
                    # Try first line as JSON.
                    first = (payload.strip().splitlines() or [""])[0]
                    try:
                        obj = json.loads(first)
                    except (json.JSONDecodeError, ValueError):
                        return m.group(0)
                if isinstance(obj, list) and obj:
                    obj = obj[0]
                if isinstance(obj, dict):
                    val = obj.get(field)
                    if isinstance(val, str):
                        return val[:1024]
                return m.group(0)
            v = _EK_FIELD_REF_RE.sub(_sub_field, v)
            # Bare-ref form #E<id> -- now smart-extract instead of
            # pasting the whole blob.
            def _sub_bare(m: re.Match) -> str:
                ref = m.group(1)
                r = results_by_id.get(ref)
                if not r:
                    return m.group(0)
                payload = r.get("output") or ""
                return _smart_extract_from_jsonish(payload)
            out[k] = _EK_REF_RE.sub(_sub_bare, v)
        else:
            out[k] = v
    return out


def _action_hash(tool: str, args: dict) -> str:
    """Stable identity of a (verb, resolved-args) dispatch for the
    in-run loop/dedup guard. Structural only -- verb name + sorted
    args -- so it carries no English/topic content (NO-HARDCODED-
    ENGLISH binding)."""
    try:
        canon = json.dumps(args or {}, sort_keys=True,
                           separators=(",", ":"), ensure_ascii=False,
                           default=str)
    except (TypeError, ValueError):
        canon = repr(args)
    return f"{tool}\x00{canon}"


# ── Concurrent dispatch single-flight (anti-swarm-duplication) ─────────
# Agentic-OS idempotency / single-flight pattern: when a fan-out (council /
# swarm / same-level DAG) has several CONCURRENT nodes that independently
# decide to run the SAME (verb, resolved-args) -- e.g. two same-level DAG
# nodes both calling winget_install(VLC), or two agents both web_search-ing
# the same query -- collapse them to ONE broker execution and share the
# result, instead of firing the side effect N times. Closes the gap the
# per-DAG seen_actions guard leaves open (it only dedupes ACROSS levels;
# same-level concurrent nodes both fire -- see _execute_dag_node).
#
# Structural key only (_action_hash -> verb + sorted args; NO hardcoded
# English) scoped to the conversation (the _conv_key_var contextvar, which
# concurrent council/DAG tasks inherit at creation). IN-FLIGHT ONLY: the
# entry is cleared the moment the first call completes, so a legitimate
# SEQUENTIAL repeat re-runs fresh (no stale cache -> reads stay live, and we
# never replay an old result for a genuinely later request). MiOS spec:
# reuses _action_hash + emits the existing `action_repeat_dedup` event.
# Ref: docs/agentic-standards-roadmap.md (standard tool-loop + idempotency).
DISPATCH_DEDUP = os.environ.get(
    "MIOS_DISPATCH_DEDUP", "true").lower() not in {"false", "0", "no"}
# (conv_key \x00 action_hash) -> in-flight Future holding the shared result.
_dispatch_inflight: dict[str, "asyncio.Future"] = {}


def _emit_dispatch_dedup_event(tool: str, args: dict,
                               session_id: Optional[str]) -> None:
    """Audit the single-flight collapse as the same `action_repeat_dedup`
    event the DAG cross-level guard emits -- one observability shape for both
    dedup paths (MiOS spec)."""
    try:
        _db_fire(_db_post(_db_create("event", {
            "source": "mios-agent-pipe",
            "kind": "action_repeat_dedup",
            "severity": "info",
            "summary": f"single-flight collapse: {tool}",
            "payload": {"tool": tool, "mode": "concurrent_single_flight"},
        }, now_fields=("ts",))))
    except Exception:
        pass


async def _execute_dag_node(node: dict, results_by_id: dict,
                            seen_actions: dict, dag_summary: str,
                            session_id: Optional[str], client) -> dict:
    """Execute ONE DAG node -- an `agent` delegation OR a `tool` verb --
    and return its node_result (standard tool_call shape + node_id + _act).
    READS the shared maps (a snapshot of completed levels) but does NOT
    mutate them; execute_dag merges results after each level so concurrent
    same-level nodes never race on writes. ReWOO #E<id> refs in args (verb)
    or in the prompt (agent) resolve against the completed-level outputs."""
    nid = str(node.get("id", "?"))
    # ---- agent-delegation node: route a sub-task to a named sub-agent ----
    if node.get("agent"):
        aname = str(node.get("agent"))
        acfg = _AGENT_REGISTRY.get(aname) or {}
        prompt = _substitute_ek_refs(
            {"_p": str(node.get("prompt") or "")}, results_by_id).get("_p", "")
        _act = _action_hash(f"agent:{aname}", {"prompt": prompt})
        _prior = seen_actions.get(_act)
        if _prior is not None:
            d = dict(_prior)
            d["node_id"] = nid
            d["repeat_of"] = _prior.get("node_id")
            return d
        t0 = time.time()
        # Inject the rolling scratchpad so this node sees checkpoints from
        # earlier DAG levels (sequential levels -> level N reads level N-1).
        _node_msgs: list = []
        _sp_block = _scratchpad_render()
        if _sp_block:
            _node_msgs.append({"role": "system", "content": _sp_block})
        _node_msgs.append({"role": "user", "content": prompt})
        body = {"model": acfg.get("model") or aname,
                "messages": _node_msgs,
                "max_tokens": 800}
        hdrs = {"Content-Type": "application/json"}
        # prefer_cpu=False -> the agent's PRIMARY endpoint/model (a coding
        # sub-task must hit opencode proper, not its CPU twin).
        _, text = await _call_agent_complete(
            aname, acfg, body, hdrs, client, prefer_cpu=False)
        text = (text or "").strip()
        # Fallback: a stream-only gateway (the Hermes server) returns empty
        # on a non-streaming call. If the agent has an ollama CPU twin, use
        # it -- it answers a self-contained sub-task non-streaming cleanly.
        # opencode has no twin -> keeps hitting its real coder model.
        if not text and acfg.get("cpu_endpoint") and acfg.get("cpu_model"):
            _, text = await _call_agent_complete(
                aname, acfg, body, hdrs, client, prefer_cpu=True)
            text = (text or "").strip()
        return {
            "success": bool(text),
            "output": text,
            "latency_ms": int((time.time() - t0) * 1000),
            "tool": f"agent:{aname}",
            "args": {},
            "node_id": nid,
            "_act": _act,
        }
    # ---- verb node: ONE MiOS dispatch verb via the broker ----------------
    tool = str(node.get("tool", "")).strip()
    args = _substitute_ek_refs(node.get("args") or {}, results_by_id)
    # Action-hash dedup guard: a duplicate (verb, resolved-args) already run
    # in an EARLIER level reuses the prior result (structural hash only --
    # NO-HARDCODED-ENGLISH binding). Same-level dupes may both run (the
    # snapshot has no in-level writes); that is a rare, harmless extra call.
    _act = _action_hash(tool, args)
    _prior = seen_actions.get(_act)
    if _prior is not None:
        d = dict(_prior)
        d["node_id"] = nid
        d["repeat_of"] = _prior.get("node_id")
        d["_act"] = _act
        return d
    attempt = 0
    # Phase A.3: forward session_id so the firewall pre-check sees taint.
    last_result = await dispatch_mios_verb(tool, args, session_id=session_id)
    if not last_result.get("success"):
        # ReWOO single-step reflection: one corrected re-dispatch before
        # the transient-retry loop (bounded, so a stubborn failure surfaces
        # as a real error instead of looping).
        correction = await reflect_on_step_failure(
            {"id": nid, "tool": tool, "args": args}, last_result,
            {"summary": dag_summary}, session_id=session_id)
        if correction and correction.get("tool"):
            tool = str(correction.get("tool", tool))
            args = _substitute_ek_refs(
                correction.get("args") or {}, results_by_id)
            last_result = await dispatch_mios_verb(
                tool, args, session_id=session_id)
    while not last_result.get("success") and attempt < PLANNER_REFLEXION_CAP:
        attempt += 1
        await asyncio.sleep(0.5)
        last_result = await dispatch_mios_verb(tool, args, session_id=session_id)
    res = dict(last_result)
    res["node_id"] = nid
    res["tool"] = tool
    res["args"] = args if isinstance(args, dict) else {}
    res["attempts"] = attempt
    res["_act"] = _act
    return res


def _record_dag_node_row(res: dict, session_id: Optional[str]) -> None:
    """Persist a DAG node's dispatch as a session-linked tool_call row so
    the confirmation engine + critics see the propagation/taint chain.
    Logs an action_repeat_dedup event when the node reused a prior result."""
    if res.get("repeat_of"):
        _db_fire(_db_post(_db_create("event", {
            "source": "mios-agent-pipe",
            "kind": "action_repeat_dedup",
            "severity": "info",
            "summary": f"node {res.get('node_id')} == {res.get('repeat_of')} "
                       f"({res.get('tool')})",
            "payload": {"tool": res.get("tool"), "node_id": res.get("node_id"),
                        "repeat_of": res.get("repeat_of")},
        }, now_fields=("ts",))))
        return
    _row = {
        "tool": res.get("tool", ""),
        "args": res.get("args") if isinstance(res.get("args"), dict) else {},
        "result_preview": _sanitize_tool_text(res.get("output") or "")[:500],
        "success": bool(res.get("success")),
        "latency_ms": int(res.get("latency_ms", 0)),
        "tainted": bool(res.get("tainted")),
        "taint_reason": (res.get("taint_reason") or "") or None,
    }
    sql = _db_create("tool_call", _row, now_fields=("ts",))
    if session_id:
        sql = sql.rstrip().rstrip(";") + f", session = {session_id};"
    _db_fire(_db_post(sql))


async def execute_dag(dag: dict, *, session_id: Optional[str],
                      event_q: "Optional[asyncio.Queue]" = None) -> dict:
    """Execute the DAG in concurrent topological LEVELS: every node whose
    deps are satisfied runs in PARALLEL (asyncio.gather), so independent
    sub-tasks -- including agent-delegation nodes routed to DIFFERENT sub-
    agents -- run concurrently across the CPU + GPU lanes (operator
    2026-05-22: "separate prompts per refinement step -> sub-agents ...
    concurrent Compute"). A level only starts once all earlier levels
    finish, so ReWOO #E<id> refs always resolve. Reflexion-retries failed
    verb nodes; fail-fast when a level has an unrecoverable failure.
    Returns aggregate {success, node_results[], summary}."""
    levels = _dag_levels(dag.get("nodes") or [])
    summary = dag.get("summary", "")
    results: list[dict] = []
    results_by_id: dict[str, dict] = {}
    seen_actions: dict[str, dict] = {}
    all_ok = True
    client = await _get_client()
    for level in levels:
        # Endpoint emitters: announce each node in this level as it ENGAGES
        # (a level's nodes run concurrently). The streaming wrapper turns
        # these queue items into live per-node SSE statuses (operator
        # 2026-05-22). No queue (non-streaming) -> no-op.
        if event_q is not None:
            for n in level:
                event_q.put_nowait(("engage", n, None))
        level_res = await asyncio.gather(*[
            _execute_dag_node(n, results_by_id, seen_actions, summary,
                              session_id, client)
            for n in level
        ], return_exceptions=True)
        for node, res in zip(level, level_res):
            nid = str(node.get("id", "?"))
            if isinstance(res, BaseException):
                res = {"success": False, "node_id": nid,
                       "tool": str(node.get("tool") or
                                   (f"agent:{node.get('agent')}"
                                    if node.get("agent") else "")),
                       "args": {}, "output": f"node {nid} raised: {res}"}
            results.append(res)
            _record_dag_node_row(res, session_id)
            # Post this node's outcome as a checkpoint so the NEXT level's
            # nodes (and other agents in the chain) read it from the scratchpad.
            _scratchpad_note(
                res.get("tool") or f"agent:{node.get('agent') or '?'}",
                str(res.get("output") or ""), phase="dag")
            if event_q is not None:
                event_q.put_nowait(("done", node, res))
            if res.get("success"):
                results_by_id[nid] = res
                if res.get("_act"):
                    seen_actions[res["_act"]] = res
            else:
                all_ok = False
        # Fail-fast: don't launch a level that depends on a failed one.
        if not all_ok:
            break
    if event_q is not None:
        event_q.put_nowait(None)  # sentinel: DAG complete, drainer can stop
    return {
        "success": all_ok,
        "summary": summary,
        "nodes_total": len(dag.get("nodes") or []),
        "nodes_executed": len(results),
        "node_results": results,
    }


async def _execute_dag_emitting(dag: dict, *, session_id: Optional[str],
                                chat_id: str, model: str):
    """Run execute_dag while LIVE-yielding per-node endpoint emitter bytes
    (operator 2026-05-22: "endpoint emitters for each ai endpoint/node").
    Yields ("event", sse_bytes) as each DAG node ENGAGES + finishes, then a
    final ("result", dag_result). Agent nodes carry their registry endpoint /
    lane / model; verb nodes show 'verb · <tool>'. The 0.25s poll lets the
    drainer notice the DAG finishing even if the sentinel is lost to an
    unexpected raise -- then `await task` re-raises it (parity with a plain
    `await execute_dag`)."""
    q: "asyncio.Queue" = asyncio.Queue()
    task = asyncio.create_task(
        execute_dag(dag, session_id=session_id, event_q=q))
    while True:
        try:
            item = await asyncio.wait_for(q.get(), timeout=0.25)
        except asyncio.TimeoutError:
            if task.done():
                break
            continue
        if item is None:  # sentinel
            break
        kind, node, res = item
        aname = node.get("agent")
        if aname:
            name = str(aname)
            cfg = _AGENT_REGISTRY.get(aname) or {}
        else:
            name = str(node.get("tool") or "node")
            cfg = {"lane": "verb", "model": str(node.get("tool") or "")}
        if kind == "engage":
            yield ("event", _node_status(chat_id=chat_id, model=model,
                                         name=name, cfg=cfg, state="engage",
                                         context=_node_context(node)))
        else:
            ok = bool(isinstance(res, dict) and res.get("success"))
            yield ("event", _node_status(chat_id=chat_id, model=model,
                                         name=name, cfg=cfg,
                                         state="ok" if ok else "down"))
    dag_result = await task
    yield ("result", dag_result)


def _agent_dag_from_tasks(tasks: list) -> dict:
    """Build a CONCURRENT per-agent DAG from refine's multi_task array:
    one agent node per independent task, routed to the task's target_agent
    (a registry key as-is, else role-matched via _pick_agent, else the
    default agent), all deps=[] so they run in PARALLEL. This is refine's
    OWN decomposition -- each sub-task already carries a target_agent hint
    -- so no extra planner LLM call is needed. Realises the operator's
    "separate prompts per refinement step -> sub-agents ... concurrent
    Compute" directly. Returns {summary, nodes}."""
    nodes: list = []
    for i, t in enumerate(tasks):
        if not isinstance(t, dict):
            continue
        prompt = str(t.get("refined_text") or t.get("title") or "").strip()
        if not prompt:
            continue
        tgt = str(t.get("target_agent") or "").strip()
        aname = tgt if tgt in _AGENT_REGISTRY else _pick_agent(tgt)[0]
        nodes.append({"id": f"t{i + 1}", "agent": aname,
                      "prompt": prompt, "deps": []})
    summary = "; ".join(str(t.get("title") or "")[:60]
                        for t in tasks if isinstance(t, dict))[:200]
    return {"summary": summary, "nodes": nodes}


_SWARM_SYSTEM = (
    "You are the MiOS SWARM planner. Split the user's request into INDEPENDENT "
    "sub-tasks that can run in PARALLEL, and assign each to the best sub-agent "
    "from the roster below. This is multi-agent delegation -- weigh the whole "
    "roster, route by each agent's strengths, do not funnel everything to one.\n"
    "\n"
    "Emit JSON ONLY (no prose, no markdown):\n"
    '{"subtasks":[{"agent":"<exact roster name>","task":"<self-contained sub-task '
    'in the user\'s language>"}, ...]}\n'
    "\n"
    "Rules:\n"
    "- Use EXACT agent names from the roster; the executor rejects unknown ones.\n"
    "- Spread the work: prefer a DIFFERENT agent for each sub-task. Reuse an "
    "agent only when no other agent's strengths fit that sub-task.\n"
    "- 2 to 4 sub-tasks. Each must be SELF-CONTAINED -- the assigned agent sees "
    "ONLY its own task string, not the others.\n"
    "- Independent only: do NOT emit sub-tasks that depend on each other's output "
    "(they run concurrently).\n"
    "- If the request is genuinely single-step / not worth splitting, emit "
    '{"subtasks":[]} and the caller handles it normally.\n'
    "\n"
    "Sub-agent roster:\n"
    + _AGENT_CATALOG_RENDERED
)


async def _plan_swarm(user_text: str) -> list:
    """Dedicated SWARM decomposer (operator 2026-05-22 'AI SWARM', Layer B):
    a narrowly-scoped planner call that splits a request into independent
    {agent, task} assignments for CONCURRENT dispatch. More reliable at
    emitting AGENT assignments than the general verb-DAG planner (which
    skews toward verb nodes). Returns task dicts shaped for
    _agent_dag_from_tasks ({target_agent, refined_text, title}), or []."""
    if not PLANNER_ENABLED or not user_text or not user_text.strip():
        return []
    # /api/chat with think=False -- the proven-reliable path refine uses. The
    # /v1 + response_format path returned EMPTY content for the full agent
    # roster (operator 2026-05-22 trace: "swarm planner raw (len=0)"). Use the
    # general SWARM_MODEL (not the code model) and read native message.content.
    _base = (PLANNER_ENDPOINT[:-3].rstrip("/")
             if PLANNER_ENDPOINT.endswith("/v1") else PLANNER_ENDPOINT)
    payload = {
        "model": SWARM_MODEL,
        "messages": [
            {"role": "system", "content": _SWARM_SYSTEM},
            {"role": "user", "content": user_text[:4000]},
        ],
        "think": False,
        "format": "json",
        "stream": False,
        "keep_alive": REFINE_KEEP_ALIVE,
        "options": {"temperature": 0.0, "num_predict": PLANNER_MAX_TOKENS},
    }
    try:
        async with httpx.AsyncClient(timeout=PLANNER_TIMEOUT_S) as s:
            r = await s.post(f"{_base}/api/chat", json=payload,
                             headers={"Content-Type": "application/json"})
            if r.status_code != 200:
                return []
            body = r.json()
    except (httpx.HTTPError, asyncio.TimeoutError):
        return []
    except Exception as e:
        log.warning("swarm planner error: %s", e)
        return []
    content = ((body.get("message") or {}).get("content") or "").strip()
    log.debug("swarm planner raw (len=%d): %.400s", len(content), content)
    if not content:
        return []
    content = re.sub(r"<think>.*?</think>\s*", "", content,
                     flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r"^\s*```(?:json)?\s*\n?", "", content)
    content = re.sub(r"\n?```\s*$", "", content)
    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, ValueError):
        return []
    subs = parsed.get("subtasks") if isinstance(parsed, dict) else None
    if not isinstance(subs, list):
        return []
    tasks: list = []
    for s in subs:
        if not isinstance(s, dict):
            continue
        task = str(s.get("task") or "").strip()
        agent = str(s.get("agent") or "").strip()
        if not task:
            continue
        tasks.append({"target_agent": agent, "refined_text": task,
                      "title": task[:60]})
    return tasks


async def _respond_agent_dag(dag: dict, refined: Optional[dict], *,
                             streaming: bool, chat_id: str, model: str,
                             session_id: Optional[str], last_user_text: str,
                             persona_system: str):
    """Execute a per-agent DAG concurrently and SYNTHESISE the agents'
    outputs into ONE polished answer (multi_task -> parallel sub-agents).
    The per-node audit envelope rides the reasoning channel; the polished
    synthesis is the operator-facing answer -- same answer/dropdown split
    as the agent + council paths. Streaming emits LIVE per-node endpoint
    statuses (operator 2026-05-22) as the DAG runs, before the synthesis."""

    async def _synthesise(dag_result: dict) -> tuple:
        """Post-DAG: build the audit envelope + the polished synthesis."""
        merged = "\n\n".join(
            f"[{n.get('tool', 'agent')}]:\n{(n.get('output') or '').strip()}"
            for n in dag_result.get("node_results", [])
            if (n.get("output") or "").strip())
        env = {"dag": {"summary": dag.get("summary", ""),
                       "nodes_total": dag_result.get("nodes_total", 0),
                       "nodes_executed": dag_result.get("nodes_executed", 0),
                       "success": dag_result.get("success", False)},
               "nodes": dag_result.get("node_results", [])}
        symbol = "✅" if dag_result.get("success") else "⚠️"
        envelope = (f"<details type=\"tool_calls\" done=\"true\">\n"
                    f"<summary>{symbol} agents · {env['dag']['nodes_total']} "
                    f"parallel</summary>\n\n"
                    f"```json\n{json.dumps(env, indent=2, default=str)}\n```\n"
                    f"</details>")
        polished = ""
        if merged.strip():
            polished_raw = await polish_response(
                merged, refined, session_id=session_id,
                original_user_text=last_user_text,
                persona_system=persona_system)
            polished = _strip_think_tags(polished_raw) if polished_raw else ""
        main = polished.strip() or _strip_think_tags(merged)
        return envelope, main

    if streaming:
        async def _gen() -> AsyncGenerator[bytes, None]:
            yield _sse_status_phase(chat_id=chat_id, model=model,
                                    phase="prompt")
            yield _sse_status_phase(chat_id=chat_id, model=model, phase="plan")
            # LIVE per-node endpoint emitters as the synthesis DAG executes
            # (same 🛰️/✅/💤 vocabulary as the council + primary paths).
            dag_result: dict = {}
            async for _k, _p in _execute_dag_emitting(
                    dag, session_id=session_id, chat_id=chat_id, model=model):
                if _k == "event":
                    yield _p
                else:
                    dag_result = _p
            envelope, main = await _synthesise(dag_result)
            yield _sse_reasoning(envelope + "\n", chat_id=chat_id, model=model)
            yield _sse_chunk("", chat_id=chat_id, model=model, role="assistant")
            async for _ab in _stream_answer(main, chat_id=chat_id, model=model):
                yield _ab
            yield _sse_status_phase(
                chat_id=chat_id, model=model,
                phase="dag_done" if dag_result.get("success")
                else "dag_done_warn", done=True)
            yield _sse_chunk("", chat_id=chat_id, model=model,
                             finish_reason="stop")
            yield _sse_done()
        return StreamingResponse(_gen(), media_type="text/event-stream")

    dag_result = await execute_dag(dag, session_id=session_id)
    _envelope, main = await _synthesise(dag_result)
    return JSONResponse(content={
        "id": chat_id, "object": "chat.completion",
        "created": int(time.time()), "model": model,
        "choices": [{"index": 0,
                     "message": {"role": "assistant", "content": main},
                     "finish_reason": "stop"}],
    })


# ── Dispatch (broker socket bridge) ────────────────────────────────
_TEMPLATE_PH_RE = re.compile(r"\{([a-zA-Z_]\w*)(?:(=|\?|!)([^}]*))?\}")


class _TemplateAbort(Exception):
    """Intentional render abort: a REQUIRED {arg!} placeholder was empty, so the
    whole template renders to None (the caller falls back / surfaces an error).
    Distinct from a real render error so it isn't logged as a failure."""


def _template_to_cmd(tool: str, template: str, args: dict) -> Optional[str]:
    """Render an SSOT verb command template (mios.toml [verbs.*].cmd) into the
    bash line the broker runs (P3: retire hardcoded dispatch branches into the
    catalog). Placeholder forms (all values resolved via _arg_with_synonyms,
    then shlex-quoted):
      {arg}          required -- substituted in place (empty -> '').
      {arg!}         REQUIRED-or-abort -- if empty the WHOLE template renders to
                     None (replaces a hardcoded `if not arg: return None` guard).
      {arg=default}  default used when the arg is absent/empty. If `default`
                     starts with `$`, it is an ENV default `$ENVVAR:fallback`:
                     the value comes from os.environ[ENVVAR] (or `fallback` when
                     unset) -- e.g. {fanout=$MIOS_WEB_FANOUT:2}.
      {arg?FLAG}     OPTIONAL -- emits nothing when absent; else a
                     LEADING-space-prefixed " FLAG <value>" (or just " <value>"
                     when FLAG is empty). Author places NO literal space before
                     an optional placeholder, so an absent optional leaves no
                     double-space (no fragile whitespace-collapsing needed).
    A template with no placeholders renders to its literal. Deliberately
    MINIMAL -- verbs needing conditional/recursive/base64 logic keep their code
    branch (the builder falls through when no `cmd` is set). Returns the rendered
    command, or None on render error (caller falls back to the hardcoded branch)."""
    try:
        def _sub(m: "re.Match") -> str:
            name, op, rest = m.group(1), m.group(2), m.group(3)
            val = _arg_with_synonyms(tool, name, args)
            sval = "" if val is None else str(val)
            if op == "!":
                # REQUIRED: empty -> abort the whole render (-> None).
                if not sval.strip():
                    raise _TemplateAbort(name)
                return shlex.quote(sval)
            if op == "?":
                if not sval.strip():
                    return ""
                flag = (rest or "").strip()
                q = shlex.quote(sval)
                return f" {flag} {q}" if flag else f" {q}"
            if op == "=" and not sval.strip():
                dflt = rest if rest is not None else ""
                # ENV default: `$ENVVAR:fallback` -- the one place a verb default
                # legitimately comes from the host env (e.g. web_search fanout).
                if dflt.startswith("$"):
                    envname, _sep, fallback = dflt[1:].partition(":")
                    dflt = os.environ.get(envname, fallback)
                return shlex.quote(str(dflt))
            return shlex.quote(sval)
        rendered = _TEMPLATE_PH_RE.sub(_sub, template).strip()
        return rendered or None
    except _TemplateAbort:
        return None
    except Exception as e:
        log.warning("verb template render failed for %s: %s", tool, e)
        return None


def _build_dispatch_cmd(tool: str, args: dict) -> Optional[str]:
    """Map verb name + args -> the bash command line the launcher
    broker executes. Kept in lockstep with the OWUI pipe's
    _dispatch_mios_verb. Returns None for unknown verbs."""
    # SSOT command template takes precedence (P3): a verb with a `cmd` in
    # mios.toml renders via the catalog; verbs without one fall through to the
    # hardcoded branches below. Incremental migration -> zero regression.
    _tmpl = (_VERB_CATALOG.get(tool) or {}).get("cmd")
    if _tmpl:
        _rendered = _template_to_cmd(tool, _tmpl, args)
        if _rendered:
            return _rendered
    env_prefix = ""
    if tool == "open_app":
        name = _arg_with_synonyms(tool, "name", args).strip()
        # Path-shaped arg: extract basename (planner sometimes emits
        # `path="/usr/bin/nautilus"` instead of `name="nautilus"`).
        # Operator-flagged 2026-05-19. The basename extract is purely
        # structural -- no English keyword list, just FS path semantics.
        if name and ("/" in name or "\\" in name):
            base = os.path.basename(name.rstrip("/\\")) or name
            # Strip .exe / .desktop suffixes so step-5 alias resolver
            # gets a clean short-name.
            for suf in (".exe", ".desktop", ".lnk"):
                if base.lower().endswith(suf):
                    base = base[: -len(suf)]
                    break
            name = base
        if not name:
            return None
        # Defensive: planner sometimes emits `launch_app(name=<verb>)`
        # where <verb> is the PROBE TOOL NAME (e.g. "mios-apps",
        # "mios_apps") instead of the discovered target. Reject so
        # the agent surfaces a clear error + re-plans, instead of
        # launching the probe tool. Normalised key matches the verb
        # catalog after underscore/hyphen folding. Operator-flagged
        # 2026-05-19.
        norm = name.lower().replace("-", "_").rstrip("s")
        if norm in _VERB_CATALOG or norm.rstrip("_") in {
            v.replace("-", "_").rstrip("s") for v in _VERB_CATALOG
        }:
            return None
        position = str(args.get("position", "default")).lower()
        extra_args = args.get("args") or []
        if position and position != "as-is":
            env_prefix = f"MIOS_LAUNCH_POSITION={shlex.quote(position)} "
        if extra_args:
            ea = " ".join(shlex.quote(str(a)) for a in extra_args)
            return f"{env_prefix}mios-windows launch {shlex.quote(name)} {ea}"
        return f"{env_prefix}mios-launch {shlex.quote(name)}"
    if tool == "launch_app":
        name = _arg_with_synonyms(tool, "name", args).strip()
        if name and ("/" in name or "\\" in name):
            base = os.path.basename(name.rstrip("/\\")) or name
            for suf in (".exe", ".desktop", ".lnk"):
                if base.lower().endswith(suf):
                    base = base[: -len(suf)]
                    break
            name = base
        if not name:
            return None
        # Same probe-tool-name defensive check as open_app.
        norm = name.lower().replace("-", "_").rstrip("s")
        if norm in _VERB_CATALOG or norm.rstrip("_") in {
            v.replace("-", "_").rstrip("s") for v in _VERB_CATALOG
        }:
            return None
        return f"mios-launch {shlex.quote(name)}"
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
    # close_window migrated to SSOT [verbs.close_window].cmd "mios-window close
    # {title}" (P3). Graceful-only by operator decision 2026-05-23: the old
    # `mode=force -> mios-window kill` path was BROKEN (no `kill` subcommand)
    # AND contradicted the 2026-05-17 no-force-kill directive (window-close in
    # mios-pc-control.ps1: never Stop-Process/taskkill -- a force-kill once
    # self-terminated hermes-agent). The `mode` enum stays for compatibility
    # but every mode closes gracefully via WM_CLOSE.
    # ── Window-state verbs (Phase D.3 -- PC-control template) ──
    # All five wrap `mios-window <subcmd>` which resolves the title
    # pattern to an hwnd internally; the agent only needs to supply
    # a substring match. Title patterns are quoted via shlex so
    # spaces / special chars in window titles ("Task Manager",
    # "VS Code - foo.py") survive the broker round-trip.
    if tool == "resize_window":
        title = shlex.quote(str(args.get("title", "")))
        w = int(args.get("width", 0))
        h = int(args.get("height", 0))
        if w <= 0 or h <= 0:
            return None
        return f"mios-window resize {title} {w} {h}"
    # move_window / position_window / minimize_window / maximize_window /
    # restore_window migrated to SSOT [verbs.*].cmd templates (P3); they
    # dispatch via the catalog-template check at the top of this function.
    # close_window (mode enum) + resize_window (w/h>0 guard) stay as code.
    # app_search + tool_search migrated to SSOT [verbs.*].cmd templates (P3)
    # using the {query!} required-or-None form -- the template aborts to None
    # when query is empty, replacing the old `if not q: return None` guard, and
    # {limit=5} renders the int default. They dispatch via the catalog-template
    # check at the top of this function.
    # ── os_recipe (SSOT-driven OS shell verb) ──
    # Generic dispatcher to mios-os-recipe; the recipe NAME + its arg
    # contract live in mios.toml [recipes.*]. agent-pipe doesn't know
    # which recipes exist -- it just forwards. Operator binding
    # 2026-05-18: "RECIPES" + "harden the OS Control tools/skills".
    if tool == "os_recipe":
        name = _arg_with_synonyms(tool, "name", args).strip()
        if not name:
            return None
        params = args.get("params") or {}
        if not isinstance(params, dict):
            params = {}
        # Splice key=value pairs after the recipe name; mios-os-recipe
        # quote-escapes each substituted value before splicing into
        # the recipe template.
        kv_args = " ".join(
            f"{shlex.quote(str(k))}={shlex.quote(str(v))}"
            for k, v in params.items()
        )
        target_os = str(args.get("os") or "").strip().lower()
        os_flag = f"--os {shlex.quote(target_os)} " if target_os in ("linux", "windows") else ""
        return f"mios-os-recipe --json {os_flag}{shlex.quote(name)} {kv_args}".strip()
    # ── pkg (unified package verb -- collapses 13 winget_* / flatpak_*
    # verbs into one). Routes by (action, backend) to the existing
    # winget / flatpak shims. backend="auto" picks winget when id looks
    # like Publisher.AppId, flatpak otherwise -- the LLM is encouraged
    # to be explicit. Operator-flagged 2026-05-19: "consolidate
    # redundant" -- legacy winget_*/flatpak_* verbs kept tier='rare'
    # for in-flight chains; this is the canonical path.
    if tool == "pkg":
        action = str(args.get("action") or "").strip().lower()
        backend = str(args.get("backend") or "auto").strip().lower()
        pid = _arg_with_synonyms(tool, "id", args).strip()
        query = _arg_with_synonyms(tool, "query", args).strip()
        if backend == "auto":
            # winget if id contains a dot AND no slash (Publisher.AppId
            # vs flatpak's org.foo.Bar/x86_64/stable). Bias toward
            # flatpak when only running on the Linux surface (no .exe
            # context). Default winget for unambiguous installs.
            ref = pid or query
            backend = "flatpak" if ("/" in ref or ref.startswith("org.")) else "winget"
        if backend not in ("winget", "flatpak"):
            return None
        # Route to the underlying verb name + delegate to its branch
        # below (no logic duplication).
        legacy = {
            "search":     f"{backend}_search",
            "list":       f"{backend}_list",
            "show":       f"{backend}_show",
            "install":    f"{backend}_install",
            "upgrade":    f"{backend}_upgrade",
            "uninstall":  f"{backend}_uninstall",
            "preflight":  "flatpak_preflight",  # winget has no analog
        }.get(action)
        if not legacy:
            return None
        # Re-shape args to match the legacy verb's expected keys.
        forwarded = dict(args)
        if action == "search" and query:
            forwarded["query"] = query
        if pid:
            forwarded["id"] = pid
        return _build_dispatch_cmd(legacy, forwarded)
    # ── Package management (Phase D.4 -- winget + flatpak surfaces) ──
    # Both shims emit JSON envelopes by default; agent-pipe surfaces
    # the JSON straight back to the gateway. WRITE verbs (install /
    # upgrade / uninstall) are firewall-gated.
    # ALL winget_* + flatpak_* verbs migrated to SSOT [verbs.*].cmd templates
    # (P3). The two upgrade verbs + flatpak_install took the HELPER-CONTRACT
    # path: the conditional logic lives in the helper, not dispatch --
    #   * mios-winget/mios-flatpak `upgrade`: no-arg / "all" / --all = all.
    #   * mios-flatpak `install <id> [scope]`: the helper's _resolve_scope owns
    #     the system/user -> --system/--user mapping + default-scope fallback
    #     (the old dispatch's scope branch + its dead --system/--user matches
    #     are gone; the scope enum is validated pre-dispatch, so only
    #     system/user/empty reach the helper, which resolves them).
    # open_url / mios_find / mios_apps / everything_search / flatpak_preflight
    # are migrated to SSOT [verbs.*].cmd templates (P3); they dispatch via the
    # catalog-template check at the top of this function (incl. the {arg?FLAG}
    # optional-flag form for --filter / -ext / the optional browser arg).
    # web_search migrated to the SSOT [verbs.web_search].cmd template (P3):
    # "mios-web-search -n {limit=5} --fanout {fanout=$MIOS_WEB_FANOUT:2} {query}".
    # The {fanout=$MIOS_WEB_FANOUT:2} ENV-default form preserves the old
    # os.environ.get("MIOS_WEB_FANOUT","2") fallback + the per-call `fanout`
    # override; the helper does the query fan-out (K concurrent sub-queries +
    # RRF merge) + grounds on REAL fetched data so the model never fabricates.
    # discord_send migrated to the SSOT [verbs.discord_send].cmd template (P3):
    # "mios-discord-send {content}{channel?--channel}". It stays a REAL dispatched
    # verb -> a real tool_call -> truthful result (the model can't narrate a fake
    # "posted to Discord"); the command literal + token/default-channel handling
    # live in the mios-discord-send helper, not here.
    # Discovery verbs knowledge_search / directory_lookup / fs_search migrated
    # to SSOT [verbs.*].cmd templates (P3); they dispatch via the catalog-
    # template check at the top of this function (optional-flag form for
    # --collection / --root / --ext / --kind / -ext / -path / -type, with the
    # int-default {top_k=5}/{limit=20}). The catalog path also resolves the
    # declared aliases (q/text, name/filename/term) the old raw args.get(...)
    # ignored. NB: fs_search.type enum is f/d/l but mios-locate only acts on
    # f/d and ignores any other -type, so the template emitting `-type l`
    # (which the old branch dropped) is harmless -- identical net behavior.
    # app_search / tool_search stay as code: their `if not query: return None`
    # guard is input validation the minimal template syntax can't express
    # (an empty query would otherwise dispatch a degenerate search).
    # System-category verbs (system_logs, process_list, container_status,
    # container_restart, service_status, service_restart) migrated to SSOT
    # [verbs.*].cmd templates (P3). They delegate to the mios-sysview /
    # mios-restart / mios-os-recipe helpers, which already OWN the journalctl /
    # ps / podman literals AND arg normalisation -- mios-sysview lowercases
    # level/sort + defaults lines/limit itself -- so the old dispatch-side
    # .lower()/int-coercion were redundant; the catalog path also resolves the
    # declared aliases (service/unit/container/from/window/n) the old raw
    # args.get(...) ignored.
    # NOTE: disk-usage is intentionally NOT a verb -- it is a [recipes.disk-usage]
    # recipe (command in mios.toml SSOT) reached via os_recipe(name="disk-usage").
    # Operator 2026-05-21: no command literals baked in code; capabilities live
    # as native tools/skills/recipes.
    # ── PC-input verbs (Phase A.1 -- needed for DAG chains like
    # open_app -> focus_window -> pc_type -> pc_key Ctrl+S) ──
    # pc_type migrated to SSOT [verbs.pc_type].cmd ("mios-pc-control type {text}");
    # the catalog path also resolves its content/input aliases. pc_key (combo
    # "+" -> key-combo conditional) + pc_click (int coords + button enum-clamp)
    # stay as code.
    if tool == "pc_key":
        key = str(args.get("key", "")).strip()
        # Modifier combos -> key-combo; single keys -> key.
        if "+" in key:
            return f"mios-pc-control key-combo {shlex.quote(key)}"
        return f"mios-pc-control key {shlex.quote(key)}"
    if tool == "pc_click":
        x = int(args.get("x", 0))
        y = int(args.get("y", 0))
        button = str(args.get("button", "left")).lower()
        if button not in ("left", "right", "middle"):
            button = "left"
        return f"mios-pc-control click {x} {y} {button}"
    # ── Native text-editor verbs (replaces pc_type+pc_key save chain) ──
    # Bodies may contain shell metacharacters + multiline content;
    # stage them in /tmp via the broker-side mktemp + base64 so the
    # bash command line stays sane and broker output parsing isn't
    # tripped by literal newlines in the args.
    # text_view migrated to SSOT [verbs.text_view].cmd (P3):
    # "mios-text-edit view {path}{start?--start}{end?--end}". The optional-flag
    # form maps the old `is not None` checks exactly (start=0 still emits
    # --start 0) and is safer than the old int(start) -- an empty start string
    # crashed the old branch, the template emits nothing. Its base64-staging
    # siblings (text_create / text_insert / text_str_replace) stay as code.
    if tool == "text_create":
        path = shlex.quote(str(args.get("path", "")))
        body_b64 = base64.b64encode(
            str(args.get("content", "")).encode("utf-8")).decode()
        # Pipe content via stdin (-) -- avoids the argv length limit
        # and any quoting weirdness with newlines / embedded quotes.
        return (
            f"echo {shlex.quote(body_b64)} | base64 -d "
            f"| mios-text-edit create {path} --content -"
        )
    if tool == "text_str_replace":
        path = shlex.quote(str(args.get("path", "")))
        old_b64 = base64.b64encode(
            str(args.get("old", "")).encode("utf-8")).decode()
        new_b64 = base64.b64encode(
            str(args.get("new", "")).encode("utf-8")).decode()
        # Stage both blocks as files via two echo+base64 hops so
        # mios-text-edit's @-file args read them cleanly.
        return (
            "_old=$(mktemp); _new=$(mktemp); "
            f"echo {shlex.quote(old_b64)} | base64 -d > $_old; "
            f"echo {shlex.quote(new_b64)} | base64 -d > $_new; "
            f"mios-text-edit str_replace {path} --old @$_old --new @$_new; "
            "_rc=$?; rm -f $_old $_new; exit $_rc"
        )
    if tool == "text_insert":
        path = shlex.quote(str(args.get("path", "")))
        line = int(args.get("line", 0))
        body_b64 = base64.b64encode(
            str(args.get("content", "")).encode("utf-8")).decode()
        return (
            f"echo {shlex.quote(body_b64)} | base64 -d "
            f"| mios-text-edit insert {path} --line {line} --content -"
        )
    # ── Native PowerShell execution (Windows-side bash analogue) ──
    if tool == "powershell_run":
        script = str(args.get("script", ""))
        if not script.strip():
            return None
        timeout = int(args.get("timeout", 30))
        work_dir = str(args.get("work_dir", "")).strip()
        script_b64 = base64.b64encode(script.encode("utf-8")).decode()
        cmd = (
            f"echo {shlex.quote(script_b64)} | base64 -d "
            f"| mios-powershell --timeout {timeout} --json"
        )
        if work_dir:
            cmd += f" --work-dir {shlex.quote(work_dir)}"
        cmd += " -"
        return cmd
    return None


async def _dispatch_bounded(
    tool: str, args: dict, *,
    session_id: Optional[str] = None,
) -> dict:
    """Bulkhead layer. web_search dispatches share a global concurrency
    semaphore so a council/DAG fan-out -- each call itself expanding into
    MIOS_WEB_FANOUT concurrent sub-queries -- can't stampede the local
    SearXNG; excess calls QUEUE here, with a small pre-acquire jitter to
    stagger simultaneous starts. All other verbs pass straight through."""
    _t = re.sub(r"\(.*?\)\s*$", "", str(tool or "").strip()).strip().strip("`'\"")
    if _t == "web_search":
        if WEB_DISPATCH_JITTER_S > 0:
            await asyncio.sleep(random.uniform(0, WEB_DISPATCH_JITTER_S))
        async with _web_sem:
            return await _dispatch_mios_verb_inner(
                tool, args, session_id=session_id)
    return await _dispatch_mios_verb_inner(tool, args, session_id=session_id)


async def dispatch_mios_verb(
    tool: str, args: dict, *,
    session_id: Optional[str] = None,
) -> dict:
    """Public dispatch entry point, wrapping the bulkhead with a conversation-
    scoped concurrent SINGLE-FLIGHT guard (anti-swarm-duplication; see
    _dispatch_inflight). Concurrent identical (verb, resolved-args) dispatches
    in the same conversation collapse to ONE broker execution + share the
    result, so a side effect never fires N times across a fan-out. In-flight
    only -> sequential repeats re-run fresh."""
    if not DISPATCH_DEDUP:
        return await _dispatch_bounded(tool, args, session_id=session_id)
    _a = args if isinstance(args, dict) else {}
    key = f"{_conv_key_var.get()}\x00{_action_hash(str(tool), _a)}"
    fut = _dispatch_inflight.get(key)
    if fut is not None:
        # An identical dispatch is already in flight in this conversation --
        # await it and reuse its result instead of firing the verb again.
        try:
            shared = await asyncio.shield(fut)
        except Exception:
            shared = None
        if isinstance(shared, dict):
            _emit_dispatch_dedup_event(str(tool), _a, session_id)
            dd = dict(shared)
            dd["deduped"] = True
            return dd
        # Shared result unusable -> fall through and run normally.
    loop = asyncio.get_running_loop()
    fut = loop.create_future()
    # Synchronous claim (no await between get + set) so a concurrent task
    # either sees no future and becomes the leader, or sees this one and
    # follows -- never two leaders for the same key.
    _dispatch_inflight[key] = fut
    try:
        res = await _dispatch_bounded(tool, args, session_id=session_id)
        if not fut.done():
            fut.set_result(res)
        return res
    except Exception as e:
        if not fut.done():
            fut.set_result({
                "success": False, "tool": tool,
                "args": _a, "output": "",
                "stderr": f"dispatch error: {e}", "exit_code": -1,
                "latency_ms": 0,
            })
        raise
    finally:
        _dispatch_inflight.pop(key, None)


async def _dispatch_mios_verb_inner(
    tool: str, args: dict, *,
    session_id: Optional[str] = None,
) -> dict:
    """Run a single MiOS verb via the launcher broker (unix socket
    /run/mios-launcher/launcher.sock). Returns a structured dict:
    {success, tool, args, output, stderr, exit_code, latency_ms,
     tainted, taint_reason}. Uses the broker's CAPTURE_JSON: protocol
    so stdout/stderr split cleanly.

    Phase A.3: Semantic Firewall stub -- when a high-privilege verb
    is dispatched and the session has ANY upstream tainted tool_call,
    the dispatch is REFUSED (not even sent to the broker) and an
    event row is emitted (kind=firewall_block, severity=high).
    Taint of the dispatched verb itself is computed from
    _classify_verb_taint AND inherited from session state."""
    # Normalise the verb name: capable models (qwen3.5:4b) format tool
    # names as function calls -> "system_status()", which then misses
    # the catalog (operator 2026-05-20). Strip a trailing "(...)" and
    # surrounding whitespace/quotes so the catalog lookup is robust to
    # however a model phrased the name.
    tool = re.sub(r"\(.*?\)\s*$", "", str(tool or "").strip()).strip().strip("`'\"")
    # ── Firewall pre-check for high-privilege verbs ──
    if tool in _HIGH_PRIVILEGE_VERBS and session_id:
        is_tainted, chain = await _session_is_tainted(session_id)
        if is_tainted:
            _db_fire(_db_post(_db_create("event", {
                "source": "agent-pipe",
                "kind": "firewall_block",
                "severity": "high",
                "summary": f"refused {tool} (tainted session)",
                "payload": {
                    "tool": tool, "args": args,
                    "taint_chain": chain,
                },
            }, now_fields=("ts",))))
            return {
                "success": False, "tool": tool, "args": args,
                "output": "",
                "stderr": f"firewall_block: {tool} refused -- "
                          f"upstream taint: {chain}",
                "exit_code": -1, "latency_ms": 0,
                "tainted": True,
                "taint_reason": f"firewall_block:{chain[:200]}",
            }

    # Tool-Manager enum validation (ref AIOS C 3.7): reject out-of-enum
    # args BEFORE the broker. The structured error feeds the planner's
    # reflection pass, which re-issues the step with a valid value.
    _enum_err = _validate_enum_args(tool, args)
    if _enum_err is not None:
        return {
            "success": False, "tool": tool, "args": args,
            "output": "", "stderr": _enum_err,
            "exit_code": -1, "latency_ms": 0,
        }
    cmd = _build_dispatch_cmd(tool, args)
    if cmd is None:
        # Distinguish "no such verb" from "verb known but args rejected"
        # so the planner can see WHICH layer failed + re-plan. Operator-
        # flagged 2026-05-19: "launch_app(path=...) -> unknown verb"
        # error was misleading -- the verb existed but the dispatcher
        # rejected because (a) `name` wasn't populated via any alias
        # (now also accepts `path`), or (b) the proposed target name
        # equals a known verb (defensive check).
        if tool in _VERB_CATALOG:
            v = _VERB_CATALOG[tool]
            required = [n for n, c in (v.get("params") or {}).items()
                        if isinstance(c, dict) and "default" not in c]
            stderr = (
                f"verb {tool!r} known but dispatch rejected: "
                f"args={list(args.keys())} required={required} "
                f"(check arg names; paths get auto-basenamed; "
                f"name equal to a known verb is refused as a defensive "
                f"check against planner emitting the probe tool name as "
                f"the launch target)"
            )
        else:
            stderr = (
                f"unknown verb {tool!r} (not in [verbs.*] catalog "
                f"of mios.toml; visible verbs: "
                f"{sorted(_VERB_CATALOG.keys())[:10]}...)"
            )
        return {
            "success": False, "tool": tool, "args": args,
            "output": "", "stderr": stderr,
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
        # 60s broker timeout: flatpak cold-launches (epiphany / chromedev
        # via WSLg compositor + portal handshake) routinely take 25-45s
        # to first paint. Prior 20s cap fired Broken Pipe on the broker
        # side, surfaced as "broker: empty response" to the agent.
        # Operator-flagged 2026-05-19. Tunable via env.
        s.settimeout(float(os.environ.get("MIOS_BROKER_TIMEOUT_S", "60")))
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
        # Compute taint for this verb's OWN execution (e.g. open_url
        # to an external host marks the result as tainted).
        v_tainted, v_reason = _classify_verb_taint(tool, args)
        return {
            "success": exit_code == 0,
            "tool": tool, "args": args,
            "output": (j.get("stdout") or "")[:6000],
            "stderr": (j.get("stderr") or "")[:2000],
            "exit_code": exit_code,
            "latency_ms": latency_ms,
            "tainted": v_tainted,
            "taint_reason": v_reason,
        }
    except OSError as e:
        return {
            "success": False, "tool": tool, "args": args,
            "output": "", "stderr": f"broker: {e}",
            "exit_code": -1,
            "latency_ms": int((time.time() - t0) * 1000),
            "tainted": False,
            "taint_reason": "",
        }


# ── SSE chunk builders ─────────────────────────────────────────────
# Encode chat completion deltas in the OpenAI streaming protocol so
# any gateway (OWUI, Hermes Discord, Slack/Telegram, ...) consumes
# the response with its existing OpenAI client. The dispatch fast-
# path emits a single delta containing the structured tool_calls
# envelope as content (rendered as a <details type="tool_calls">
# block markdown can collapse natively).

def _sse_chunk(content: Optional[str], *, chat_id: str, model: str,
               role: Optional[str] = None,
               finish_reason: Optional[str] = None,
               mios_status: Optional[dict] = None,
               reasoning: Optional[str] = None) -> bytes:
    """Build an OpenAI-streaming SSE chunk. `reasoning` populates the
    standard `delta.reasoning_content` field (OpenAI/OpenRouter/DeepSeek
    convention) -- OWUI renders it as a native Thinking dropdown and
    strict clients (Firefox Smart Window) ignore it, showing only the
    clean `content` answer. Optional `mios_status` carries pipe-internal
    phase emits (👂 prompt, 🧭 route, 🛠️ tool, ✅) that translator gateways
    lift into their native status surfaces; stock clients ignore it."""
    delta: dict[str, Any] = {}
    if role:
        delta["role"] = role
    if reasoning is not None:
        delta["reasoning_content"] = reasoning
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


def _sse_reasoning(text: str, *, chat_id: str, model: str) -> bytes:
    """Stream a reasoning delta via the standard delta.reasoning_content
    field (no `<details>`-in-content hack). OWUI shows it as a native
    Thinking dropdown; strict OpenAI clients (Firefox Smart Window) ignore
    it and render only the final `content` answer -- which is what makes
    the visible reply clean + generative and kills <think> leaks."""
    return _sse_chunk(None, chat_id=chat_id, model=model, reasoning=text)


# Phase keys -> humanistic casual labels for the SSE status strip.
# MiOS is for non-technical users; the strip should read like the
# system is THINKING and DOING, not like a debugger output. Model
# names, timings, arg JSONs, intent labels stay in the SurrealDB
# event payloads for debug -- they NEVER reach the visible strip.
#
# Add a phase key here when wiring a new emit site instead of
# inlining label strings -- keeps the operator-visible voice
# consistent across every dispatch path.
def _load_status_labels() -> dict:
    """Phase -> (emoji, label) for the SSE status strip. Personable
    defaults here; each phase is OVERRIDABLE from mios.toml
    [owui.status_phases.<phase>] = { emoji = "..", label = ".." } so the
    operator tunes MiOS-Agent's voice without touching code (SSOT; no
    hardcoded UI strings locked in the hot path). Operator 2026-05-19:
    'better emitters / more detailed and personable'."""
    # EMOJI ONLY -- no hardcoded English narrative, no TOML label map.
    # Operator 2026-05-20: "nothing hardcoded -- pure streamed +
    # generative". The chip is the emoji plus any GENERATIVE `detail` the
    # emit site passes (the actual verb / refined intent / plan); the rich
    # agent-path activity comes from the live hermes-tail stream in the
    # OWUI pipe. Emojis are locale-neutral glyphs, not English strings.
    return {
        "prompt":         ("👂", ""),
        "refine":         ("✨", ""),
        "route":          ("🧭", ""),
        "plan":           ("🗺️", ""),
        "agent_target":   ("🤖", ""),
        "tool":           ("🛠️", ""),
        "tool_done":      ("✅", ""),
        "tool_done_warn": ("😅", ""),
        "chat":           ("💬", ""),
        "chat_done":      ("✅", ""),
        "dag_done":       ("✅", ""),
        "dag_done_warn":  ("😅", ""),
        "reflect":        ("🤔", ""),
        "subagent_done":  ("✅", ""),
    }


_HUMAN_LABELS = _load_status_labels()


def _sse_status_phase(*, chat_id: str, model: str, phase: str,
                      done: bool = False,
                      detail: Optional[str] = None) -> bytes:
    """Humanistic-label variant of _sse_status. Looks up the phase
    in _HUMAN_LABELS, emits the casual label + emoji. `detail` is
    optional and should ALSO be human-facing prose (e.g. "for 22
    seconds", "almost there") -- NOT a model id / args JSON /
    intent token. If you find yourself wanting to thread technical
    info through here, log it to the event table instead."""
    emoji, label = _HUMAN_LABELS.get(phase, ("·", phase))
    return _sse_status(chat_id=chat_id, model=model, emoji=emoji,
                       label=label, done=done, detail=detail)


def _sse_status(*, chat_id: str, model: str, emoji: str, label: str,
                done: bool = False, detail: Optional[str] = None) -> bytes:
    """Emit a content-empty SSE chunk whose only purpose is the
    `mios_status` field. Standard OpenAI clients see a no-op delta
    + ignore the extra field. Translator gateways pull the phase
    info from `mios_status` and surface it natively (OWUI's
    event_emitter status, Hermes Discord's reactions, etc.).

    Prefer _sse_status_phase() for new emit sites -- it picks the
    canonical humanistic label from _HUMAN_LABELS. This raw form
    stays available for one-off cases where the phase mapping
    doesn't fit."""
    payload = {"emoji": emoji, "label": label, "done": done}
    if detail:
        d = str(detail).strip()
        if d:
            payload["detail"] = d[:80]
            # Append to label for clients that only render `label`.
            payload["label"] = f"{label}  {d[:80]}"
    return _sse_chunk(
        "", chat_id=chat_id, model=model,
        mios_status=payload,
    )


def _node_context(node: dict) -> str:
    """SHORT, operator-facing description of what a DAG node is DOING -- the
    active step's CONTEXT (operator 2026-05-23: "emits should show actual steps
    relevant to the current active step's context"). Derived from the node's
    OWN data -- an agent node's sub-task, or a verb node's key arg -- NOT the
    internal model/endpoint (which read as a leak). No LLM call, no hardcoded
    topic text: it's the step's literal intent."""
    if not isinstance(node, dict):
        return ""
    if node.get("agent"):
        return str(node.get("prompt") or node.get("task") or "").strip()[:64]
    args = node.get("args") or {}
    if isinstance(args, dict):
        for _k in ("query", "id", "name", "path", "url", "title", "unit",
                   "text", "content", "script"):
            _v = args.get(_k)
            if _v:
                return f"{_k}={str(_v)[:48]}"
        for _v in args.values():
            if _v:
                return str(_v)[:48]
    return ""


def _node_status(*, chat_id: str, model: str, name: str, cfg: dict,
                 state: str, context: str = "") -> bytes:
    """Per-endpoint live emitter (operator 2026-05-22: "endpoint emitters for
    each ai endpoint/node"). One status event naming an AI node as the chain
    ENGAGES it / it RESPONDS / goes silent. `context` (operator 2026-05-23) is
    a short description of the node's CURRENT STEP -- its sub-task or the verb
    arg -- so the emit reflects the active step's context, not just a glyph.
    The lane/model/endpoint internals stay OUT (they read as a leak); context
    is the WHAT (operator-facing), not the HOW (plumbing)."""
    emoji = {"engage": "🛰️", "ok": "✅", "down": "💤"}.get(state, "🛰️")
    return _sse_status(chat_id=chat_id, model=model, emoji=emoji,
                       label=str(name), detail=str(context or "")[:80])


async def _stream_answer(text: str, *, chat_id: str, model: str):
    """Yield the final answer in small character-exact chunks so OWUI renders
    it progressively (live 'typing') instead of one end-of-turn burst -- the
    "thinking prints then switches to the refined copy" jolt (operator
    2026-05-22). Pacing is bounded so long answers stream in ~1.2s, not slower.
    Char-slicing preserves the text byte-for-byte (markdown/code intact)."""
    if not text:
        return
    size = int(os.environ.get("MIOS_ANSWER_CHUNK_CHARS", "48"))
    chunks = [text[i:i + size] for i in range(0, len(text), max(1, size))]
    delay = min(0.03, 1.2 / max(1, len(chunks)))
    for ch in chunks:
        yield _sse_chunk(ch, chat_id=chat_id, model=model)
        if delay:
            await asyncio.sleep(delay)


def _sse_done() -> bytes:
    return b"data: [DONE]\n\n"


# Hermes-tail -> live checkpoint status. During the buffered sub-agent
# call the agent-pipe would otherwise send bare ': keepalive' COMMENT
# lines (no data) while it waits -- OWUI then renders nothing until the
# very end (operator 2026-05-20: "emitters haven't worked once; thinking
# + emits only mass-print at the end"). Emitting a REAL mios_status data
# chunk on each checkpoint, sourced from the AI's actual latest tool
# step, forces the emit to flush + stream live instead of dumping at the
# end -- the "checkpoint/status interrupt" the operator asked for.
_TAIL_KIND_EMOJI = {
    "max_retries":    "❌",
    "invalid_tool":   "⚠️",
    "retry":          "↻",
    "delegate_spawn": "🚀",
    "synthesis":      "🔀",
    "subagent_done":  "✅",
    "tool_call":      "🛠️",
}
_HERMES_TAIL_PATH = os.environ.get(
    "MIOS_HERMES_TAIL_PATH", "/var/lib/mios/hermes-tail/latest.json")


def _tail_latest_status(seen_ts: float, *, chat_id: str,
                        model: str) -> tuple[Optional[bytes], float]:
    """If the hermes-tail holds an event newer than seen_ts, return its
    mios_status SSE chunk (emoji + generative detail) and the advanced
    ts; otherwise (None, seen_ts). Best-effort -- any read/parse error
    just yields no chunk."""
    try:
        with open(_HERMES_TAIL_PATH) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, ValueError):
        return None, seen_ts
    newest = None
    new_ts = seen_ts
    for ev in data.get("events", []):
        ts = ev.get("ts", 0)
        if ts > new_ts:
            new_ts = ts
            newest = ev
    if newest is None:
        return None, seen_ts
    emoji = _TAIL_KIND_EMOJI.get(str(newest.get("kind", "")), "·")
    detail = str(newest.get("detail", "")).strip()
    return (_sse_status(chat_id=chat_id, model=model, emoji=emoji,
                        label="", done=False, detail=detail), new_ts)


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
@app.get("/v1/verbs")
async def list_verbs(include_rare: bool = False) -> JSONResponse:
    """Render [verbs.*] as JSON-Schema tool specs. Same SSOT that
    drives the planner catalog. Consumed by mios-mcp-server (for
    MCP `tools/list`) and any external tooling that wants the
    canonical verb shape."""
    tools = []
    for vname, vcfg in _VERB_CATALOG.items():
        if not include_rare and vcfg.get("tier") == "rare":
            continue
        props: dict = {}
        required: list[str] = []
        for argname, argcfg in (vcfg.get("params") or {}).items():
            if not isinstance(argcfg, dict):
                continue
            spec: dict = {
                "type": argcfg.get("type", "string"),
                "description": argcfg.get("desc", ""),
            }
            if argcfg.get("enum"):
                spec["enum"] = list(argcfg["enum"])
            if "default" in argcfg:
                spec["default"] = argcfg["default"]
            else:
                required.append(argname)
            props[argname] = spec
        tools.append({
            "name": vname,
            "description": vcfg.get("desc", ""),
            "inputSchema": {
                "type": "object",
                "properties": props,
                "required": required,
                "additionalProperties": False,
            },
            "annotations": {
                "section": vcfg.get("section", ""),
                "tier": vcfg.get("tier", "common"),
                "readOnlyHint": vcfg.get("permission") == "read",
                "permission": vcfg.get("permission", "read"),
            },
        })
    return JSONResponse({"tools": tools})


def _verb_to_openai_tool(vname: str, vcfg: dict) -> dict:
    """Render one [verbs.*] entry as an OpenAI function-tool schema --
    the SAME `{type:function, function:{name,description,parameters}}`
    shape Hermes/OpenCode already consume from /skills/openai-tools (see
    _skill_to_openai_tool). Tool name == the bare verb name, so a returned
    tool_call executes verbatim via POST /v1/dispatch {tool, args} (the
    launcher-broker path the MCP server also uses). No name mangling ->
    discover here, execute there, one contract."""
    props: dict = {}
    required: list[str] = []
    for argname, argcfg in (vcfg.get("params") or {}).items():
        if not isinstance(argcfg, dict):
            continue
        spec: dict = {
            "type": argcfg.get("type", "string"),
            "description": argcfg.get("desc", ""),
        }
        if argcfg.get("enum"):
            spec["enum"] = list(argcfg["enum"])
        if "default" in argcfg:
            spec["default"] = argcfg["default"]
        else:
            required.append(argname)
        props[argname] = spec
    return {
        "type": "function",
        "function": {
            "name": vname,
            "description": vcfg.get("desc", ""),
            "parameters": {
                "type": "object",
                "properties": props,
                "required": required,
                "additionalProperties": False,
            },
        },
        # Routing/UX hints (x- namespaced; ignored by strict OpenAI clients).
        "x-mios-verb": vname,
        "x-mios-permission": vcfg.get("permission", "read"),
        "x-mios-section": vcfg.get("section", ""),
    }


@app.get("/v1/verbs/openai-tools")
async def list_verbs_openai_tools(include_rare: bool = False) -> JSONResponse:
    """The MiOS verb catalog projected into the OpenAI `tools=` array shape.

    The OpenAI-shape twin of /v1/verbs (which serves the MCP `inputSchema`
    shape for mios-mcp-server). Hermes already carries the full MiOS verb +
    skill surface alongside its own built-in tools, so this is NOT how
    Hermes gets its tools. It exists so any STRICT OpenAI tool-loop client
    that lacks the MiOS plugin -- an external /v1 caller, OpenCode in a
    tools= mode, an A2A/ACP peer -- can be handed the verb surface in the
    standard shape and call it via POST /v1/dispatch {tool,args} (same
    launcher-broker path the MCP server uses). One SSOT (_VERB_CATALOG),
    three projections: MCP (/v1/verbs), OpenAI tools (here), A2A skills
    (the agent card). Discover here, execute at /v1/dispatch."""
    tools = [
        _verb_to_openai_tool(vname, vcfg)
        for vname, vcfg in _VERB_CATALOG.items()
        if include_rare or vcfg.get("tier") != "rare"
    ]
    return JSONResponse({"tools": tools, "count": len(tools)})


# ── A2A Agent Card (Agent2Agent discovery surface) ────────────────────
# Agentic-standards roadmap Phase 4. A2A (Agent2Agent, now under the
# Linux Foundation Agentic-AI Foundation) is the peer-discovery standard
# that complements MCP: MCP advertises TOOLS (mios-mcp-server -> /v1/verbs),
# A2A advertises AGENTS + their high-level SKILLS. Serving the card from
# the SAME SSOT (mios.toml [agents.*]) the fan-out router already reads
# makes the roster a STANDARD, machine-discoverable surface -- the
# foundation for replacing _pick_fanout_agents' bespoke strength-token
# scoring with spec capability-matching, and for any external A2A client
# (or a future MiOS orchestrator) to enumerate the stack's agents.
#
# LOCAL-ONLY, same as mios-mcp-server: this describes the on-host MiOS
# agent stack; it does not register the agent with any cloud directory.
# Served at the A2A well-known path + a /v1 convenience alias. Generated,
# never hardcoded -- skills come from the live registry, the verb count
# from the live catalog, identity from the FastAPI app + PORT.
A2A_PROTOCOL_VERSION = os.environ.get("MIOS_A2A_PROTOCOL_VERSION", "0.3.0")


def _build_agent_card() -> dict:
    """Render the A2A AgentCard from MiOS SSOT (no hardcoded skills).

    Each mios.toml [agents.*] entry becomes one A2A skill: id=agent name,
    tags=its strengths, description from role+lane. This is exactly the
    data _pick_fanout_agents scores, now exposed in the open standard."""
    base = f"http://localhost:{PORT}"
    skills = []
    for name, cfg in _AGENT_REGISTRY.items():
        role = str(cfg.get("role", "general"))
        lane = _agent_lane(cfg)
        # Shared SSOT: same tags the fan-out router (_pick_fanout_agents)
        # keys on, so advertised capability == routing key.
        tags = _agent_skill_tags(cfg)
        desc_bits = [f"{role} agent on the {lane} inference lane"]
        if cfg.get("default"):
            desc_bits.append("primary/default orchestrator")
        if cfg.get("strengths"):
            desc_bits.append(
                "strengths: " + ", ".join(str(s) for s in cfg["strengths"]))
        skills.append({
            "id": name,
            "name": f"{name} ({role})",
            "description": "; ".join(desc_bits),
            "tags": tags,
            "inputModes": ["text/plain", "application/json"],
            "outputModes": ["text/plain"],
        })
    # The agent speaks the OpenAI Chat Completions API (this server's /v1
    # surface); tool execution is the co-located MCP server. Advertise both
    # so a discovering peer knows how to actually drive MiOS.
    return {
        "protocolVersion": A2A_PROTOCOL_VERSION,
        "name": os.environ.get("MIOS_A2A_AGENT_NAME", "MiOS Agent"),
        "description": app.description,
        "version": app.version,
        # Primary service URL: the OpenAI-compatible chat surface.
        "url": f"{base}/v1",
        "preferredTransport": "OpenAI",
        "provider": {
            "organization": "MiOS",
            "url": os.environ.get(
                "MIOS_REPO_URL", "https://github.com/mios-dev/MiOS"),
        },
        "capabilities": {
            # SSE streaming on /v1/chat/completions.
            "streaming": True,
            "pushNotifications": False,
            # SurrealDB-backed session/tool-call history.
            "stateTransitionHistory": True,
            # Inter-agent shared context as A2A/ACP Message history grouped
            # by contextId, served at /a2a/contexts/{contextId} (operator
            # 2026-05-23: "context should be shared inter agents -- A2A/ACP").
            "contextSharing": True,
        },
        "defaultInputModes": ["text/plain", "application/json", "image/png"],
        "defaultOutputModes": ["text/plain"],
        "skills": skills,
        # Non-spec extension block: where to actually reach the surfaces.
        # Namespaced under x- so strict A2A validators ignore it.
        "x-mios": {
            "openai_chat_completions": f"{base}/v1/chat/completions",
            "mcp_server": "mios-mcp-server (stdio JSON-RPC 2.0, spec "
                          "2025-06-18; tool catalog via this server's "
                          "/v1/verbs)",
            "verb_catalog_size": len(_VERB_CATALOG),
            "discovery": {
                "tools": f"{base}/v1/verbs",
                "tool_search": f"{base}/v1/tool-search",
                "context": f"{base}/a2a/contexts/{{contextId}}",
                "health": f"{base}/health",
            },
        },
    }


@app.get("/.well-known/agent-card.json")
async def a2a_agent_card() -> JSONResponse:
    """A2A AgentCard at the spec well-known path."""
    return JSONResponse(_build_agent_card())


@app.get("/.well-known/agent.json")
async def a2a_agent_card_legacy() -> JSONResponse:
    """Legacy A2A well-known path (pre-0.3 clients)."""
    return JSONResponse(_build_agent_card())


@app.get("/v1/agent-card")
async def a2a_agent_card_alias() -> JSONResponse:
    """Convenience alias under /v1 for clients that don't probe
    the well-known path."""
    return JSONResponse(_build_agent_card())


@app.get("/a2a/contexts/{context_id}")
async def a2a_context_get(context_id: str) -> JSONResponse:
    """A2A/ACP shared inter-agent context: the conversation's blackboard
    rendered as A2A Message history grouped by contextId (operator 2026-05-23:
    "context should be shared inter agents -- A2A/ACP"). Any A2A/ACP-aware
    agent or client reads the shared context by contextId here, in the open
    standard shape, instead of relying only on the bespoke prose injection.
    LOCAL-ONLY, like the rest of the A2A surface."""
    return JSONResponse(_a2a_context(context_id))


@app.get("/v1/contexts/{context_id}")
async def a2a_context_get_v1(context_id: str) -> JSONResponse:
    """/v1 convenience alias for the A2A shared context."""
    return JSONResponse(_a2a_context(context_id))


# ── /v1/tool-search (progressive disclosure / RAG-MCP) ────────────────
# Cosine-over-nomic-embed-text retrieval over the visible verb catalog.
# Embeddings computed lazily on first request, cached in-memory until
# agent-pipe restart (catalog is tiny: ~30 verbs at ~768-dim each).
# Operator binding 2026-05-19: "compact, minimal, efficient" + per
# RAG-MCP paper (arXiv 2505.03275): top-k retrieval halves prompt
# tokens + triples selection accuracy for verb counts > 30.
_VERB_EMBED_MODEL = os.environ.get(
    "MIOS_VERB_EMBED_MODEL", "nomic-embed-text")
_VERB_EMBED_URL = os.environ.get(
    "MIOS_VERB_EMBED_URL", "http://localhost:11435/api/embeddings")
_VERB_EMBEDDINGS: dict[str, list[float]] = {}
_VERB_EMBEDDINGS_LOCK = asyncio.Lock()


async def _embed_one(text: str) -> Optional[list[float]]:
    """Single-vector embed via Ollama /api/embeddings. Returns None on
    failure (caller falls back to substring match)."""
    if not text or not text.strip():
        return None
    client = await _get_client()
    try:
        r = await client.post(
            _VERB_EMBED_URL,
            content=json.dumps({
                "model": _VERB_EMBED_MODEL,
                "prompt": text,
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        if r.status_code != 200:
            return None
        data = r.json()
        v = data.get("embedding")
        if isinstance(v, list) and v:
            return [float(x) for x in v]
    except Exception as e:
        log.warning("embed call failed: %s", e)
    return None


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    import math
    return dot / (math.sqrt(na) * math.sqrt(nb))


async def _ensure_verb_embeddings() -> None:
    """Compute embeddings for tier=core+common verbs. Persisted to
    /var/lib/mios/agent-env/verb-embeddings.json -- restart doesn't
    re-flood the embed lane. Hidden by lock."""
    async with _VERB_EMBEDDINGS_LOCK:
        if _VERB_EMBEDDINGS:
            return
        # First try disk.
        cached = _load_persisted_embeddings(_VERB_EMBED_PERSIST)
        if cached:
            for vname, vcfg in _VERB_CATALOG.items():
                if vcfg.get("tier") == "rare":
                    continue
                vec = cached.get(vname)
                if isinstance(vec, list) and vec:
                    _VERB_EMBEDDINGS[vname] = [float(x) for x in vec]
        # Fill gaps (new verbs not in cache).
        rebuilt = False
        for vname, vcfg in _VERB_CATALOG.items():
            if vcfg.get("tier") == "rare":
                continue
            if vname in _VERB_EMBEDDINGS:
                continue
            text = f"{vname}: {vcfg.get('desc','')}".strip()
            vec = await _embed_one(text)
            if vec:
                _VERB_EMBEDDINGS[vname] = vec
                rebuilt = True
        if rebuilt:
            _save_persisted_embeddings(_VERB_EMBED_PERSIST, _VERB_EMBEDDINGS)
        log.info("verb embeddings ready: %d entries (rebuilt=%s)",
                 len(_VERB_EMBEDDINGS), rebuilt)


@app.get("/v1/tool-search")
async def tool_search(query: str = "", limit: int = 5) -> JSONResponse:
    """Find verbs in the catalog by natural-language query.
    Returns top-k {name, sig, desc, score}. Embeddings cached after
    first request."""
    if not query.strip():
        return JSONResponse({"hits": [], "error": "empty query"})
    await _ensure_verb_embeddings()
    qvec = await _embed_one(query)
    hits: list[dict] = []
    if qvec and _VERB_EMBEDDINGS:
        scored = [
            (_cosine(qvec, vec), vname)
            for vname, vec in _VERB_EMBEDDINGS.items()
        ]
        scored.sort(reverse=True)
        for score, vname in scored[: max(1, min(20, int(limit or 5)))]:
            v = _VERB_CATALOG.get(vname) or {}
            hits.append({
                "name":  vname,
                "sig":   v.get("sig", ""),
                "desc":  v.get("desc", ""),
                "tier":  v.get("tier", ""),
                "score": round(float(score), 4),
            })
    else:
        # Embedding unavailable -- substring fallback over name+desc.
        q = query.lower()
        for vname, vcfg in _VERB_CATALOG.items():
            if vcfg.get("tier") == "rare":
                continue
            blob = f"{vname} {vcfg.get('desc','')}".lower()
            if q in blob:
                hits.append({
                    "name":  vname,
                    "sig":   vcfg.get("sig", ""),
                    "desc":  vcfg.get("desc", ""),
                    "tier":  vcfg.get("tier", ""),
                    "score": 1.0,
                })
            if len(hits) >= int(limit or 5):
                break
    return JSONResponse({"hits": hits, "query": query, "embedded": bool(qvec)})


# ── /v1/app-search (semantic over the mios-apps inventory) ───────────
# Embeds every (name + description) record from `mios-apps --json` once,
# refreshes when the cache file mtime moves. Cosine-rank queries against
# the embeddings.
#
# PERSISTENCE: embeddings spill to disk under /var/lib/mios/agent-env/
# so an agent-pipe restart doesn't trigger a 4-5s blocking rebuild of
# 319 sequential embed calls (which floods the iGPU lane + causes
# concurrent chat SSE streams to time out with TransferEncodingError).
# Operator-flagged 2026-05-19 "double fail" trace.
#
# WARMUP: build runs as a background Task at startup -- requests during
# warmup get the substring fallback so they never block on embeddings.
_APP_EMBEDDINGS: dict[str, dict] = {}   # key -> {vec, record}
_APP_INV_MTIME: float = 0.0
_APP_INV_LOCK = asyncio.Lock()
_APP_INV_CACHE_FILE = os.environ.get(
    "MIOS_APP_INV_CACHE",
    "/var/lib/mios/agent-env/apps-inventory.ndjson",
)
_APP_EMBED_PERSIST = os.environ.get(
    "MIOS_APP_EMBED_PERSIST",
    "/var/lib/mios/agent-env/apps-embeddings.json",
)
_VERB_EMBED_PERSIST = os.environ.get(
    "MIOS_VERB_EMBED_PERSIST",
    "/var/lib/mios/agent-env/verb-embeddings.json",
)


def _load_persisted_embeddings(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_persisted_embeddings(path: str, data: dict) -> None:
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, path)
    except OSError as e:
        log.warning("embedding persist failed: %s -> %s", path, e)


async def _refresh_app_inventory(force: bool = False) -> None:
    """Re-run `mios-apps --json` if the cache is stale (>5min) or
    missing, parse the NDJSON, embed any new records. Existing
    records reuse persisted embeddings. Persisted to disk so a
    restart doesn't trigger a 4-5s blocking embed flood."""
    global _APP_INV_MTIME
    async with _APP_INV_LOCK:
        # First load: hydrate from disk if available.
        if not _APP_EMBEDDINGS:
            cached = _load_persisted_embeddings(_APP_EMBED_PERSIST)
            if isinstance(cached, dict):
                for k, v in cached.items():
                    if (isinstance(v, dict) and isinstance(v.get("vec"), list)
                            and isinstance(v.get("record"), dict)):
                        _APP_EMBEDDINGS[k] = {
                            "vec": [float(x) for x in v["vec"]],
                            "record": v["record"],
                        }
        try:
            st = os.stat(_APP_INV_CACHE_FILE)
            age = time.time() - st.st_mtime
            need_refresh = force or age > 300
        except OSError:
            need_refresh = True
        if need_refresh:
            try:
                os.makedirs(os.path.dirname(_APP_INV_CACHE_FILE), exist_ok=True)
                proc = await asyncio.create_subprocess_exec(
                    "/usr/libexec/mios/mios-apps", "--json",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
                with open(_APP_INV_CACHE_FILE, "wb") as f:
                    f.write(stdout)
            except Exception as e:
                log.warning("mios-apps inventory refresh failed: %s", e)
                return
        # Parse + embed any new entries.
        try:
            with open(_APP_INV_CACHE_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except OSError:
            return
        seen_keys: set[str] = set()
        added = 0
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = f"{rec.get('category','')}::{rec.get('name','')}::{rec.get('launch','')}"
            seen_keys.add(key)
            if key in _APP_EMBEDDINGS:
                continue
            blob = f"{rec.get('name','')}: {rec.get('description','')}".strip()
            vec = await _embed_one(blob)
            if vec:
                _APP_EMBEDDINGS[key] = {"vec": vec, "record": rec}
                added += 1
        # Drop entries whose key disappeared (app uninstalled / inventory shrank).
        stale = [k for k in _APP_EMBEDDINGS if k not in seen_keys]
        for k in stale:
            _APP_EMBEDDINGS.pop(k, None)
        if added or stale:
            _save_persisted_embeddings(_APP_EMBED_PERSIST, _APP_EMBEDDINGS)
            log.info("app inventory: +%d new / -%d stale = %d total",
                     added, len(stale), len(_APP_EMBEDDINGS))
        try:
            _APP_INV_MTIME = os.stat(_APP_INV_CACHE_FILE).st_mtime
        except OSError:
            pass


@app.get("/v1/app-search")
async def app_search(query: str = "", limit: int = 5) -> JSONResponse:
    """Semantic search over the installed-app inventory. Returns top-k
    {category, name, description, launch, score}."""
    if not query.strip():
        return JSONResponse({"hits": [], "error": "empty query"})
    await _refresh_app_inventory()
    qvec = await _embed_one(query)
    hits: list[dict] = []
    if qvec and _APP_EMBEDDINGS:
        scored = [
            (_cosine(qvec, entry["vec"]), entry["record"])
            for entry in _APP_EMBEDDINGS.values()
        ]
        scored.sort(reverse=True, key=lambda x: x[0])
        for score, rec in scored[: max(1, min(20, int(limit or 5)))]:
            hits.append({**rec, "score": round(float(score), 4)})
    else:
        # Embedding unavailable -- substring fallback over name + desc.
        q = query.lower()
        for entry in _APP_EMBEDDINGS.values():
            rec = entry["record"]
            blob = f"{rec.get('name','')} {rec.get('description','')}".lower()
            if q in blob:
                hits.append({**rec, "score": 1.0})
            if len(hits) >= int(limit or 5):
                break
    return JSONResponse({
        "hits": hits, "query": query,
        "embedded": bool(qvec),
        "inventory_size": len(_APP_EMBEDDINGS),
    })


@app.post("/v1/dispatch")
async def dispatch_verb(body: dict) -> JSONResponse:
    """Dispatch a single MiOS verb. Body: {tool, args, session_id?}.
    Returns the same {success, output, stderr, exit_code, latency_ms,
    tainted, taint_reason} envelope as the DAG executor. Used by
    mios-mcp-server for MCP `tools/call`."""
    tool = str(body.get("tool", "")).strip()
    args = body.get("args") or {}
    if not isinstance(args, dict):
        args = {}
    session_id = body.get("session_id")
    result = await dispatch_mios_verb(tool, args, session_id=session_id)
    return JSONResponse(result)


# ── MiOS Portal (operator 2026-05-22: "web portal that hosts links to each
#    service with stats") ───────────────────────────────────────────────
# The service catalog is AUTO-DISCOVERED from the Quadlet `openInBrowser`
# labels (SSOT -- the same URLs Podman Desktop uses) + the host Cockpit
# service. No hardcoded service list. agent-pipe runs INSIDE the WSL VM
# alongside the services, so it health-checks them over localhost (no CORS,
# no portproxy/firewall hop) and reports live up/down + latency. Tiles link
# to the tailnet host:port so a peer can open them. PUBLIC_HOST is the
# Tailscale MagicDNS name (override via MIOS_PUBLIC_HOST). Tiles link to
# https://<name>:<port> -- valid HTTPS provided by `tailscale serve
# --tls-terminated-tcp=<port>` per service (the cert is bound to this name,
# so the NAME, not the IP, is used; clients need MagicDNS).
PORTAL_PUBLIC_HOST = os.environ.get("MIOS_PUBLIC_HOST", "mios.taildd86d0.ts.net")


def _discover_portal_services() -> list[dict]:
    """Scan the Quadlet *.container files for io.podman_desktop.openInBrowser
    labels -> {name, port, local health URL}. Adds the host Cockpit service.
    Deduped by port, sorted by name. SSOT: the quadlet labels, not a list."""
    svcs: list[dict] = []
    seen: set[str] = set()
    for d in ("/etc/containers/systemd", "/usr/share/containers/systemd"):
        for f in sorted(glob.glob(os.path.join(d, "*.container"))):
            title = url = cname = ""
            try:
                for line in open(f, encoding="utf-8", errors="replace"):
                    s = line.strip()
                    if "openInBrowser=" in s:
                        url = s.split("openInBrowser=", 1)[1].strip()
                    elif "image.title=" in s:
                        title = s.split("image.title=", 1)[1].strip()
                    elif s.startswith("ContainerName="):
                        cname = s.split("=", 1)[1].strip()
            except OSError:
                continue
            m = re.search(r"(https?)://[^:/]+:(\d+)(/\S*)?", url)
            if not m:
                continue
            scheme, port, path = m.group(1), m.group(2), (m.group(3) or "/")
            if port in seen:
                continue
            seen.add(port)
            name = (title or os.path.basename(f).replace(".container", ""))
            name = name.replace("mios-", "").replace("-", " ").strip().title()
            if not cname:
                cname = os.path.basename(f).replace(".container", "")
            svcs.append({"name": name, "port": int(port), "path": path,
                         "container_name": cname,
                         "local": f"{scheme}://127.0.0.1:{port}{path}"})
    # Host services (not Quadlets, so no openInBrowser label): read their
    # ports from mios.toml [ports] SSOT. {toml key: (display name, scheme)}.
    host_svcs = {"cockpit": ("Cockpit", "https"),
                 "ttyd_bash": ("Terminal · Bash", "http"),
                 "ttyd_powershell": ("Terminal · PowerShell", "http")}
    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore
        ports = tomllib.load(open(
            os.environ.get("MIOS_TOML", "/usr/share/mios/mios.toml"),
            "rb")).get("ports") or {}
    except Exception:
        ports = {}
    for key, (label, scheme) in host_svcs.items():
        p = ports.get(key)
        if not p or str(p) in seen:
            continue
        seen.add(str(p))
        svcs.append({"name": label, "port": int(p), "path": "/",
                     "container_name": "",
                     "local": f"{scheme}://127.0.0.1:{p}/"})
    svcs.sort(key=lambda s: s["name"].lower())
    return svcs


_PORTAL_SERVICES = _discover_portal_services()


def _host_stats() -> dict:
    """Cheap host telemetry from /proc (no psutil dependency)."""
    out: dict[str, Any] = {"cpu": os.cpu_count()}
    try:
        out["host"] = open("/proc/sys/kernel/hostname").read().strip()
    except OSError:
        pass
    try:
        out["load"] = open("/proc/loadavg").read().split()[:3]
    except OSError:
        pass
    try:
        mi: dict[str, int] = {}
        for line in open("/proc/meminfo"):
            k, _, v = line.partition(":")
            if v:
                mi[k.strip()] = int(v.split()[0])
        tot, avail = mi.get("MemTotal", 0), mi.get("MemAvailable", 0)
        if tot:
            out["mem_used_pct"] = round((tot - avail) * 100 / tot)
            out["mem_total_gb"] = round(tot / 1048576, 1)
    except (OSError, ValueError):
        pass
    try:
        out["uptime_s"] = int(float(open("/proc/uptime").read().split()[0]))
    except (OSError, ValueError):
        pass
    return out


_PODMAN_PS_SNAPSHOT = os.environ.get(
    # World-readable shared path (root:root 755 dir, 0644 file) so every
    # non-root reader -- portal, container_status verb, operator SSH/Termius
    # shell -- can read the rootful-container snapshot. Was under the 0750
    # agent-pipe state dir, invisible to everyone but mios-agent-pipe.
    "MIOS_PODMAN_PS_SNAPSHOT", "/var/lib/mios/podman-ps.json")


async def _podman_ps() -> dict:
    """Best-effort host-port -> {container,state,image} map from podman.
    Returns {} on any failure (podman absent / no perms) so the portal
    degrades to health-only without erroring.

    PREFERS the root-written snapshot at MIOS_PODMAN_PS_SNAPSHOT: this service
    runs hardened + non-root and CANNOT reach the rootful /run/podman socket
    (/run/podman is 0700 root:root), so a direct `podman ps` here sees an empty
    rootless context -> "podman present but no containers" (operator 2026-05-23).
    mios-podman-ps.timer refreshes the snapshot every ~15s. Falls back to a
    direct `podman ps` for unrestricted/rootless-visible deployments."""
    data = None
    try:
        with open(_PODMAN_PS_SNAPSHOT, "rb") as _f:
            data = json.loads(_f.read() or b"[]")
    except Exception:
        data = None
    if data is None:
        try:
            proc = await asyncio.create_subprocess_exec(
                "podman", "ps", "-a", "--format", "json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL)
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=4.0)
            data = json.loads(out or b"[]")
        except Exception:
            return {"port": {}, "name": {}}
    by_port: dict[int, dict] = {}
    by_name: dict[str, dict] = {}
    for c in data if isinstance(data, list) else []:
        names = c.get("Names") or []
        info = {"container": (names[0] if names else (c.get("Id") or "")[:12]),
                "state": str(c.get("State", "")).lower(),
                "image": c.get("Image", "")}
        # by NAME -- the only match for HOST-NETWORKED containers (most MiOS
        # services), which report no published Ports in `podman ps`.
        for nm in names:
            by_name[str(nm)] = info
        for p in (c.get("Ports") or []):
            hp = p.get("host_port") if isinstance(p, dict) else None
            if hp:
                by_port[int(hp)] = info
    return {"port": by_port, "name": by_name}


@app.get("/portal/stats")
async def portal_stats() -> JSONResponse:
    """Live server-side health of every discovered MiOS service + host
    stats + best-effort container state. Self-signed backends checked
    insecurely. The single source the dashboard polls."""
    pmap = await _podman_ps()

    async def _check(svc: dict, client) -> dict:
        t0 = time.time()
        ok = False
        try:
            r = await client.get(svc["local"])
            ok = r.status_code < 500
        except Exception:
            ok = False
        cinfo = (pmap["port"].get(svc["port"])
                 or pmap["name"].get(svc.get("container_name", ""), {}))
        return {"name": svc["name"], "port": svc["port"], "ok": ok,
                "ms": int((time.time() - t0) * 1000),
                "internal": svc["local"],
                "container": cinfo.get("container", ""),
                "state": cinfo.get("state", ""),
                "image": cinfo.get("image", ""),
                "url": f"https://{PORTAL_PUBLIC_HOST}:{svc['port']}"
                       f"{svc.get('path', '/')}"}
    async with httpx.AsyncClient(verify=False, timeout=4.0,
                                 follow_redirects=False) as client:
        services = await asyncio.gather(
            *[_check(s, client) for s in _PORTAL_SERVICES])
    return JSONResponse({"host": _host_stats(), "services": services,
                         "ts": int(time.time())})


@app.get("/portal/service/{port}")
async def portal_service_detail(port: int) -> JSONResponse:
    """On-demand detail for one service (clicked in the dashboard): live
    status + container state/image + recent log lines (best-effort)."""
    svc = next((s for s in _PORTAL_SERVICES if s["port"] == port), None)
    if not svc:
        return JSONResponse({"error": "unknown service"}, status_code=404)
    pmap = await _podman_ps()
    cinfo = (pmap["port"].get(port)
             or pmap["name"].get(svc.get("container_name", ""), {}))
    logs = ""
    cname = cinfo.get("container", "")
    if cname:
        try:
            proc = await asyncio.create_subprocess_exec(
                "podman", "logs", "--tail", "40", cname,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT)
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            logs = _sanitize_tool_text((out or b"").decode(
                "utf-8", "replace"))[-4000:]
        except Exception:
            logs = ""
    ok = False
    async with httpx.AsyncClient(verify=False, timeout=4.0,
                                 follow_redirects=False) as client:
        try:
            r = await client.get(svc["local"])
            ok = r.status_code < 500
        except Exception:
            ok = False
    return JSONResponse({
        "name": svc["name"], "port": port, "ok": ok,
        "internal": svc["local"],
        "url": f"https://{PORTAL_PUBLIC_HOST}:{port}{svc.get('path', '/')}",
        "container": cname, "state": cinfo.get("state", ""),
        "image": cinfo.get("image", ""), "logs": logs})


@app.get("/portal/swarm")
async def portal_swarm() -> JSONResponse:
    """Live SWARM roster (operator 2026-05-22 'emitters for all nodes/
    endpoints to confirm live the nodes/models/endpoints'): every registered
    agent/node with live reachability + the model(s) it actually serves
    (probed, not just configured). health_gate client nodes (mobile/Tailscale)
    show up/down as they join/leave the swarm."""
    async def _probe(name: str, cfg: dict, client) -> dict:
        ep = (cfg.get("endpoint") or "").rstrip("/")
        t0 = time.time()
        reachable, live = False, []
        try:  # OpenAI /v1/models
            r = await client.get(f"{ep}/models")
            if r.status_code < 500:
                reachable = True
                live = [str(m.get("id")) for m in
                        ((r.json() or {}).get("data") or [])
                        if isinstance(m, dict) and m.get("id")]
        except Exception:
            pass
        if not reachable:  # ollama-style /api/tags
            tb = ep[:-3].rstrip("/") if ep.endswith("/v1") else ep
            try:
                r = await client.get(f"{tb}/api/tags")
                if r.status_code < 500:
                    reachable = True
                    live = [str(m.get("name")) for m in
                            ((r.json() or {}).get("models") or [])
                            if isinstance(m, dict) and m.get("name")]
            except Exception:
                pass
        return {"name": name, "role": cfg.get("role", ""),
                "lane": _agent_lane(cfg), "endpoint": ep,
                "model": cfg.get("model", ""), "live_models": live[:8],
                "reachable": reachable, "ms": int((time.time() - t0) * 1000),
                "default": bool(cfg.get("default")),
                "fanout": bool(cfg.get("fanout", True)),
                "health_gate": bool(cfg.get("health_gate")),
                "strengths": cfg.get("strengths") or []}
    async with httpx.AsyncClient(verify=False, timeout=3.0,
                                 follow_redirects=False) as client:
        agents = await asyncio.gather(
            *[_probe(n, c, client) for n, c in _AGENT_REGISTRY.items()])
    agents.sort(key=lambda a: (not a["reachable"], a["name"]))
    up = sum(1 for a in agents if a["reachable"])
    return JSONResponse({"agents": agents, "up": up,
                         "total": len(agents), "ts": int(time.time())})


_PORTAL_HTML = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MiOS</title>
<link rel="manifest" href="/portal/manifest.webmanifest">
<meta name="theme-color" content="#282262">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="MiOS">
<link rel="icon" href="/portal/icon.svg">
<link rel="icon" type="image/png" sizes="192x192" href="/portal/icon-192.png">
<link rel="apple-touch-icon" href="/portal/icon-192.png">
<style>
/* MiOS unified palette (mios.toml [colors]; Hokusai "Great Wave" + operator
   neutrals). Base tones are SSOT-injected at serve time; derived surfaces
   recompute from them via color-mix. */
:root{
--bg:#282262;        /* deep indigo (Hokusai sky) */
--panel:#1A407F;     /* operator blue (surfaces) */
--fg:#E7DFD3;        /* foam cream */
--mut:#B7C9D7;       /* pale blue-grey */
--accent:#F35C15;    /* sunset orange (interactive) */
--ok:#3E7765;        /* wave green */
--bad:#DC271B;       /* coral red */
--silver:#E0E0E0;--earth:#734F39;
--card:color-mix(in srgb,var(--panel) 24%,var(--bg));
--card2:color-mix(in srgb,var(--panel) 42%,var(--bg));
--line:color-mix(in srgb,var(--mut) 24%,transparent);
--rad:12px;
--mono:ui-monospace,"Cascadia Code","Source Code Pro",Consolas,monospace;
--sans:-apple-system,"Segoe UI",system-ui,Roboto,sans-serif}
*{box-sizing:border-box}
body{margin:0;color:var(--fg);font:15px/1.5 var(--sans);
background:radial-gradient(1100px 520px at 12% -12%,
  color-mix(in srgb,var(--accent) 13%,transparent),transparent 60%),
  radial-gradient(900px 500px at 100% 0%,
  color-mix(in srgb,var(--panel) 30%,transparent),transparent 55%),var(--bg);
background-attachment:fixed}
a{color:var(--accent);text-decoration:none}
.bar{display:flex;align-items:center;gap:16px;padding:14px 22px;
border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--bg);z-index:30}
h1{margin:0;font-size:24px;letter-spacing:.5px}h1 b{color:var(--accent)}
.host{display:flex;gap:18px;flex-wrap:wrap;font-size:12.5px;color:var(--mut);margin-left:6px}
.host b{color:var(--fg)}
.spacer{flex:1}
.menu{position:relative}
.btn{background:var(--card2);border:1px solid var(--line);color:var(--fg);
border-radius:9px;padding:7px 12px;font-size:13px;cursor:pointer;transition:.15s}
.btn:hover{border-color:var(--accent);color:var(--accent)}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#1a1230;font-weight:700}
.btn.primary:hover{background:color-mix(in srgb,var(--accent) 84%,#fff);color:#1a1230}
.drop{position:absolute;right:0;top:110%;background:var(--card);border:1px solid var(--line);
border-radius:10px;padding:8px;min-width:200px;display:none;box-shadow:0 10px 30px rgba(0,0,0,.5)}
.drop.open{display:block}
.drop label{display:flex;justify-content:space-between;align-items:center;
padding:7px 8px;font-size:13px;color:var(--mut);gap:10px}
.drop select,.drop input{background:var(--bg);color:var(--fg);border:1px solid var(--line);
border-radius:7px;padding:4px 7px;font-size:13px}
section{padding:18px 22px}
.h{display:flex;align-items:center;gap:10px;margin:4px 0 14px}
.h h2{font-size:15px;letter-spacing:.4px;text-transform:uppercase;color:var(--silver);
margin:0;border-left:4px solid var(--accent);padding-left:9px}
.h .n{color:var(--ok);font-size:12px;font-weight:600}
/* Top column: SearXNG search + MiOS AI chat, centered, same width as the
   header (operator 2026-05-22). */
.top{width:min(760px,100%);margin:20px auto 8px;padding:0 18px}
.websearch{display:flex;gap:8px;margin:0 0 12px}
.websearch input{flex:1;background:var(--card);border:1px solid var(--line);color:var(--fg);
border-radius:11px;padding:12px 16px;font-size:15px}
.websearch input:focus{outline:none;border-color:var(--accent)}
.hoststrip{width:min(760px,100%);margin:0 auto 2px;padding:8px 18px 0;display:flex;
gap:18px;flex-wrap:wrap;justify-content:center;font-size:12.5px;color:var(--mut)}
.hoststrip b{color:var(--fg)}
/* chat window: portrait-ish 4:5 (taller than landscape, not phone-tall),
   inline + drag-resizable (operator 2026-05-22) */
#chatwrap{border:1px solid var(--line);border-radius:var(--rad);overflow:hidden;
margin:0 auto;width:100%;aspect-ratio:2/3;resize:both;
min-width:280px;min-height:720px;max-width:100%}
#chatwrap.min{display:none}
#chat{width:100%;height:100%;border:0;background:#0d1117;display:block}
.grid{display:grid;gap:13px;grid-template-columns:repeat(auto-fill,minmax(215px,1fr))}
/* Services grid: exactly 2 columns (operator 2026-05-22); 1 on narrow. */
#grid{grid-template-columns:repeat(2,minmax(0,1fr))}
@media(max-width:600px){#grid{grid-template-columns:1fr}}
.addr{font-family:var(--mono);font-size:11.5px;color:var(--mut);margin-top:8px;
white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.addr a{color:var(--mut)}.addr a:hover{color:var(--accent)}
.card{position:relative;background:var(--card);border:1px solid var(--line);
border-left:3px solid var(--mut);
border-radius:var(--rad);padding:15px 15px 13px;transition:.15s border-color,.15s transform}
.card.up{border-left-color:var(--ok)}
.card.down{border-left-color:var(--bad)}
.card:hover{border-color:var(--accent);transform:translateY(-2px)}
.card .lnk{position:absolute;inset:0;border-radius:var(--rad)}
.row{display:flex;align-items:center;justify-content:space-between}
.name{font-size:15.5px;font-weight:600}
.dot{width:10px;height:10px;border-radius:50%;background:var(--mut)}
.dot.ok{background:var(--ok)}.dot.bad{background:var(--bad)}
/* swarm node tiles */
.lane{font-size:10px;text-transform:uppercase;letter-spacing:.4px;padding:1px 7px;
border-radius:20px;border:1px solid var(--line);color:var(--mut)}
.lane.gpu{color:var(--accent);border-color:color-mix(in srgb,var(--accent) 45%,transparent)}
.lane.cpu{color:var(--ok);border-color:color-mix(in srgb,var(--ok) 45%,transparent)}
.lane.mobile{color:var(--silver);border-color:color-mix(in srgb,var(--silver) 45%,transparent)}
.node .m{font-size:11.5px;color:var(--mut);margin-top:7px;font-family:var(--mono);
white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.node .ep{font-size:10.5px;color:color-mix(in srgb,var(--mut) 70%,transparent);
font-family:var(--mono);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:3px}
.node .tags{font-size:10px;color:var(--earth);margin-top:6px}
.meta{color:var(--mut);font-size:12px;margin-top:9px;display:flex;justify-content:space-between}
.port{font-family:ui-monospace,Menlo,monospace}
.kebab{position:absolute;top:9px;right:9px;z-index:5;background:transparent;border:0;
color:var(--mut);font-size:18px;cursor:pointer;line-height:1;padding:2px 6px;border-radius:6px}
.kebab:hover{background:var(--card2);color:var(--fg)}
.cdrop{position:absolute;top:30px;right:9px;z-index:6;background:var(--card2);
border:1px solid var(--line);border-radius:9px;padding:5px;display:none;min-width:140px}
.cdrop.open{display:block}
.cdrop button{display:block;width:100%;text-align:left;background:transparent;border:0;
color:var(--fg);font-size:13px;padding:7px 9px;border-radius:6px;cursor:pointer}
.cdrop button:hover{background:var(--card)}
.state{font-size:11px;padding:1px 7px;border-radius:20px;border:1px solid var(--line);color:var(--mut)}
.state.running{color:var(--ok);border-color:#1c3b22}
.search{display:flex;gap:8px;margin-bottom:14px}
.search input{flex:1;background:var(--card);border:1px solid var(--line);color:var(--fg);
border-radius:9px;padding:9px 12px;font-size:14px}
.app{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 13px}
.app .c{color:var(--accent);font-size:11px;text-transform:uppercase;letter-spacing:.4px}
.app .d{color:var(--mut);font-size:12.5px;margin-top:4px}
.modal{position:fixed;inset:0;background:rgba(0,0,0,.6);display:none;z-index:50;
align-items:center;justify-content:center;padding:20px}
.modal.open{display:flex}
.sheet{background:var(--card);border:1px solid var(--line);border-radius:14px;
width:min(720px,100%);max-height:86vh;overflow:auto;padding:20px 22px}
.sheet h3{margin:0 0 4px;font-size:20px}
.kv{display:flex;gap:10px;font-size:13px;margin:6px 0;color:var(--mut)}
.kv b{color:var(--fg);font-weight:600;min-width:90px}
.kv code{font-family:ui-monospace,Menlo,monospace;color:var(--fg);word-break:break-all}
pre{background:#06090d;border:1px solid var(--line);border-radius:9px;padding:12px;
font-size:12px;max-height:340px;overflow:auto;color:#aeb9c4;white-space:pre-wrap}
.x{float:right;background:transparent;border:0;color:var(--mut);font-size:22px;cursor:pointer}
footer{color:var(--mut);font-size:12px;text-align:center;padding:16px}
.toast{position:fixed;bottom:18px;left:50%;transform:translateX(-50%);background:var(--card2);
border:1px solid var(--line);border-radius:9px;padding:9px 16px;font-size:13px;display:none;z-index:60}
</style></head><body>
<div class="bar">
  <h1>Mi<b>OS</b></h1>
  <div class="spacer"></div>
  <button class="btn primary" id="installBtn">&#11015; Install</button>
  <button class="btn" id="chatToggle">&#128172; Chat</button>
  <div class="menu">
    <button class="btn" id="menuBtn">&#9776; Menu</button>
    <div class="drop" id="menu">
      <label>Refresh <select id="refresh">
        <option value="5000">5s</option><option value="15000">15s</option>
        <option value="30000">30s</option><option value="0">off</option></select></label>
      <label>Sort <select id="sort">
        <option value="name">name</option><option value="status">status</option>
        <option value="port">port</option></select></label>
      <label>Only down <input type="checkbox" id="onlydown"></label>
      <label><a href="/portal/stats" target="_blank">raw stats JSON</a></label>
    </div>
  </div>
</div>

<div class="top">
  <form class="websearch" id="wsform">
    <input id="wsq" placeholder="Search the web with SearXNG&hellip;" autocomplete="off">
    <button class="btn" type="submit">&#128269; Search</button>
  </form>
  <div id="chatwrap"><iframe id="chat" title="MiOS AI"></iframe></div>
</div>

<div class="hoststrip" id="host"></div>

<section>
  <div class="h"><h2>Swarm Nodes</h2><span class="n" id="swarmn"></span></div>
  <div class="grid" id="swarm"></div>
</section>

<section>
  <div class="h"><h2>Services</h2><span class="n" id="svcn"></span></div>
  <div class="grid" id="grid"></div>
</section>

<section>
  <div class="h"><h2>MiOS Apps</h2><span class="n">windows &middot; terminal &middot; TUIs</span></div>
  <div class="search">
    <input id="appq" placeholder="Search installed apps (e.g. browser, htop, steam)&hellip;">
    <button class="btn" id="appgo">Search</button>
  </div>
  <div class="grid" id="apps"></div>
</section>

<div class="modal" id="modal"><div class="sheet" id="sheet"></div></div>
<div class="toast" id="toast"></div>
<footer id="foot">loading&hellip;</footer>

<script>
var S=[],OPTS={refresh:5000,sort:"name",onlydown:false},timer=null,chatSet=false,SEARX="";
function $(id){return document.getElementById(id);}
function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,function(c){
  return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function toast(t){var e=$("toast");e.textContent=t;e.style.display="block";
  setTimeout(function(){e.style.display="none";},1600);}
function fmtUp(s){if(!s)return"?";var d=Math.floor(s/86400),h=Math.floor(s%86400/3600),
  m=Math.floor(s%3600/60);return(d?d+"d ":"")+(h?h+"h ":"")+m+"m";}
function copy(t){navigator.clipboard&&navigator.clipboard.writeText(t);toast("copied "+t);}
function sorted(){var a=S.slice();
  if(OPTS.onlydown)a=a.filter(function(s){return !s.ok;});
  a.sort(function(x,y){return OPTS.sort=="status"?(x.ok-y.ok):
    OPTS.sort=="port"?(x.port-y.port):x.name.localeCompare(y.name);});return a;}
function cards(){
  $("grid").innerHTML=sorted().map(function(s){
    var st=s.state?' &middot; <span class="state '+esc(s.state)+'">'+esc(s.state)+'</span>':'';
    var addr=(s.url||"").replace(/^https?:\/\//,"").replace(/\/$/,"");
    var loc=(s.internal||"").replace(/^https?:\/\//,"").replace(/\/$/,"");
    return '<div class="card '+(s.ok?"up":"down")+'" data-p="'+s.port+'">'+
      '<a class="lnk" href="'+esc(s.url)+'" target="_blank" rel="noopener"></a>'+
      '<button class="kebab" data-k="'+s.port+'">&#8942;</button>'+
      '<div class="cdrop" id="cd'+s.port+'">'+
        '<button data-act="open" data-u="'+esc(s.url)+'">Open</button>'+
        '<button data-act="copy" data-u="'+esc(s.url)+'">Copy URL</button>'+
        '<button data-act="detail" data-p="'+s.port+'">Details</button></div>'+
      '<div class="row"><span class="name">'+esc(s.name)+'</span>'+
        '<span class="dot '+(s.ok?"ok":"bad")+'"></span></div>'+
      '<div class="addr">&#128279; '+esc(addr)+'</div>'+
      (loc?'<div class="addr" style="opacity:.7">&#8627; '+esc(loc)+'</div>':'')+
      '<div class="meta"><span class="port">:'+s.port+'</span>'+
        '<span>'+(s.ok?(s.ms+" ms"):"down")+st+'</span></div></div>';
  }).join("");
  $("svcn").textContent=S.filter(function(s){return s.ok;}).length+" / "+S.length+" up";
}
function render(j){
  var h=j.host||{},hs=[];
  if(h.host)hs.push("<b>"+esc(h.host)+"</b>");
  if(h.load)hs.push("load <b>"+esc(h.load.join(" "))+"</b>");
  if(h.cpu)hs.push("<b>"+h.cpu+"</b> cpu");
  if(h.mem_used_pct!=null)hs.push("mem <b>"+h.mem_used_pct+"%</b>/"+(h.mem_total_gb||"?")+"G");
  if(h.uptime_s)hs.push("up <b>"+fmtUp(h.uptime_s)+"</b>");
  $("host").innerHTML=hs.join("");
  S=j.services||[];cards();
  if(!chatSet){var ow=S.filter(function(s){return s.port==3030;})[0];
    if(ow){$("chat").src=ow.url;chatSet=true;}}
  var sx=S.filter(function(s){return s.port==8888;})[0];if(sx)SEARX=sx.url;
  $("foot").textContent="refreshed "+new Date((j.ts||0)*1000).toLocaleTimeString();
}
function renderSwarm(j){
  var a=j.agents||[];
  $("swarmn").textContent=(j.up||0)+" / "+(j.total||a.length)+" nodes live";
  $("swarm").innerHTML=a.map(function(n){
    var ep=(n.endpoint||"").replace(/^https?:\/\//,"");
    var lm=(n.live_models&&n.live_models.length)?n.live_models.join(", "):(n.model||"?");
    var tag=n.health_gate?' &middot; <span class="tags">client</span>':
      (n.default?' &middot; <span class="tags">primary</span>':"");
    return '<div class="card node '+(n.reachable?"up":"down")+'">'+
      '<div class="row"><span class="name">'+esc(n.name)+'</span>'+
        '<span class="dot '+(n.reachable?"ok":"bad")+'"></span></div>'+
      '<div class="m">'+esc(lm)+'</div>'+
      '<div class="ep">'+esc(ep||"-")+'</div>'+
      '<div class="meta"><span class="lane '+esc(n.lane||"")+'">'+
        esc(n.lane||n.role||"node")+'</span>'+
        '<span>'+(n.reachable?(n.ms+" ms"):"down")+tag+'</span></div></div>';
  }).join("");
}
function tickSwarm(){fetch("/portal/swarm",{cache:"no-store"})
  .then(function(r){return r.json();}).then(renderSwarm).catch(function(){});}
function tick(){fetch("/portal/stats",{cache:"no-store"}).then(function(r){return r.json();})
  .then(render).catch(function(){$("foot").textContent="stats unavailable";});
  tickSwarm();}
function arm(){if(timer)clearInterval(timer);if(OPTS.refresh)timer=setInterval(tick,OPTS.refresh);}
function detail(p){
  fetch("/portal/service/"+p,{cache:"no-store"}).then(function(r){return r.json();}).then(function(d){
    $("sheet").innerHTML='<button class="x" onclick="closeM()">&times;</button>'+
      '<h3>'+esc(d.name)+' <span class="dot '+(d.ok?"ok":"bad")+'"></span></h3>'+
      '<div class="kv"><b>URL</b><code>'+esc(d.url)+'</code></div>'+
      '<div class="kv"><b>Internal</b><code>'+esc(d.internal)+'</code></div>'+
      (d.container?'<div class="kv"><b>Container</b><code>'+esc(d.container)+'</code></div>':'')+
      (d.state?'<div class="kv"><b>State</b><code>'+esc(d.state)+'</code></div>':'')+
      (d.image?'<div class="kv"><b>Image</b><code>'+esc(d.image)+'</code></div>':'')+
      '<div class="kv"><b>Open</b><code><a href="'+esc(d.url)+'" target="_blank">'+esc(d.url)+'</a></code></div>'+
      (d.logs?'<div class="kv"><b>Logs</b></div><pre>'+esc(d.logs)+'</pre>':'<div class="kv">no container logs</div>');
    $("modal").classList.add("open");
  });
}
function closeM(){$("modal").classList.remove("open");}
function searchApps(){var q=$("appq").value.trim();if(!q)return;
  $("apps").innerHTML='<div class="app">searching&hellip;</div>';
  fetch("/v1/app-search?limit=12&query="+encodeURIComponent(q)).then(function(r){return r.json();})
    .then(function(j){var hits=j.hits||[];
      $("apps").innerHTML=hits.length?hits.map(function(a){
        return '<div class="app"><div class="c">'+esc(a.category||"app")+'</div>'+
          '<div class="name">'+esc(a.name)+'</div>'+
          (a.description?'<div class="d">'+esc(a.description)+'</div>':'')+
          (a.launch?'<div class="d"><code>'+esc(a.launch)+'</code></div>':'')+'</div>';
      }).join(""):'<div class="app">no matches</div>';
    }).catch(function(){$("apps").innerHTML='<div class="app">app search unavailable</div>';});}
// events
document.addEventListener("click",function(e){
  var k=e.target.closest("[data-k]");
  document.querySelectorAll(".cdrop.open").forEach(function(d){
    if(!k||d.id!="cd"+k.getAttribute("data-k"))d.classList.remove("open");});
  if(k){var cd=$("cd"+k.getAttribute("data-k"));if(cd)cd.classList.toggle("open");return;}
  var b=e.target.closest("[data-act]");
  if(b){var act=b.getAttribute("data-act");
    if(act=="open")window.open(b.getAttribute("data-u"),"_blank");
    else if(act=="copy")copy(b.getAttribute("data-u"));
    else if(act=="detail")detail(b.getAttribute("data-p"));
    document.querySelectorAll(".cdrop.open").forEach(function(d){d.classList.remove("open");});return;}
  if(e.target.id=="modal")closeM();
  if(!e.target.closest("#menu")&&e.target.id!="menuBtn")$("menu").classList.remove("open");
});
$("menuBtn").onclick=function(){$("menu").classList.toggle("open");};
$("chatToggle").onclick=function(){$("chatwrap").classList.toggle("min");};
$("refresh").onchange=function(){OPTS.refresh=+this.value;arm();};
$("sort").onchange=function(){OPTS.sort=this.value;cards();};
$("onlydown").onchange=function(){OPTS.onlydown=this.checked;cards();};
$("appgo").onclick=searchApps;
$("appq").addEventListener("keydown",function(e){if(e.key=="Enter")searchApps();});
$("wsform").addEventListener("submit",function(e){e.preventDefault();
  var q=$("wsq").value.trim();if(!q)return;
  var base=(SEARX||("https://"+location.hostname+":8888/")).replace(/\/+$/,"");
  window.open(base+"/search?q="+encodeURIComponent(q),"_blank");});
if("serviceWorker" in navigator){
  navigator.serviceWorker.register("/sw.js").catch(function(){});}
// PWA install option (operator 2026-05-22): capture the install prompt and
// expose it as an in-portal button; fall back to browser-menu instructions.
var deferredPrompt=null;
window.addEventListener("beforeinstallprompt",function(e){
  e.preventDefault();deferredPrompt=e;});
window.addEventListener("appinstalled",function(){
  deferredPrompt=null;$("installBtn").style.display="none";toast("MiOS installed");});
if(window.matchMedia&&window.matchMedia("(display-mode: standalone)").matches)
  $("installBtn").style.display="none";  // already running as the installed app
$("installBtn").onclick=function(){
  if(deferredPrompt){deferredPrompt.prompt();
    deferredPrompt.userChoice.then(function(){deferredPrompt=null;});}
  else{toast("Browser menu → Install app / Add to Home Screen");}};
tick();arm();
</script></body></html>"""


def _portal_theme_css() -> str:
    """Build a :root override from mios.toml [colors] (SSOT) so the portal
    tracks the operator's palette. Maps the MiOS color ROLES to the portal's
    CSS vars; derived surfaces (--card/--line) recompute via color-mix in the
    page CSS. Returns '' on any failure -> the static MiOS-default :root
    stands. Per the no-hardcode rule: the toml is the source, the static
    block is just the documented fallback."""
    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore
        path = os.environ.get("MIOS_TOML", "/usr/share/mios/mios.toml")
        with open(path, "rb") as f:
            c = tomllib.load(f).get("colors") or {}
    except Exception:
        return ""
    roles = {"--bg": c.get("bg"), "--fg": c.get("fg"),
             "--panel": c.get("accent"), "--accent": c.get("cursor"),
             "--ok": c.get("success"), "--bad": c.get("error"),
             "--mut": c.get("subtle") or c.get("muted"),
             "--silver": c.get("silver"), "--earth": c.get("earth")}
    decl = ";".join(f"{k}:{v}" for k, v in roles.items()
                    if isinstance(v, str) and v.startswith("#"))
    return f"<style>:root{{{decl}}}</style>" if decl else ""


# ── PWA assets (operator 2026-05-22: minimal Android web-app wrapper).
# A manifest + icon + service worker make the portal "Add to Home Screen"
# installable as a standalone, chrome-less app -- no third-party wrapper
# needed (and works inside Native Alpha / a TWA too). MiOS-palette themed.
_PORTAL_ICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">'
                '<rect width="512" height="512" rx="104" fill="#282262"/>'
                '<path d="M48 372 q68 -86 136 0 t136 0 t144 0" stroke="#F35C15"'
                ' stroke-width="26" fill="none" stroke-linecap="round"/>'
                '<text x="256" y="250" font-family="system-ui,Segoe UI,sans-serif"'
                ' font-size="208" font-weight="700" fill="#E7DFD3"'
                ' text-anchor="middle">Mi</text></svg>')


def _read_portal_asset(name: str) -> bytes:
    """Read a baked portal asset (PNG icons) from /usr/share/mios/portal."""
    try:
        with open(os.path.join("/usr/share/mios/portal", name), "rb") as f:
            return f.read()
    except OSError:
        return b""


# PNG icons (generated by the build / tools). Chrome on Android requires
# PNG icons at 192px + 512px for PWA installability -- an SVG-only icon is
# why "Add to Home Screen" was unavailable. Maskable 512 covers adaptive.
_PORTAL_ICON_192 = _read_portal_asset("icon-192.png")
_PORTAL_ICON_512 = _read_portal_asset("icon-512.png")
_PORTAL_MANIFEST = json.dumps({
    "name": "MiOS Portal", "short_name": "MiOS",
    "start_url": "/", "scope": "/", "display": "standalone",
    "orientation": "any", "background_color": "#282262",
    "theme_color": "#282262", "description": "MiOS service portal",
    "icons": [
        {"src": "/portal/icon-192.png", "sizes": "192x192",
         "type": "image/png", "purpose": "any"},
        {"src": "/portal/icon-512.png", "sizes": "512x512",
         "type": "image/png", "purpose": "any"},
        {"src": "/portal/icon-512.png", "sizes": "512x512",
         "type": "image/png", "purpose": "maskable"},
        {"src": "/portal/icon.svg", "sizes": "any", "type": "image/svg+xml"},
    ],
})
_PORTAL_SW = (
    "self.addEventListener('install',function(e){self.skipWaiting();});\n"
    "self.addEventListener('activate',function(e){"
    "e.waitUntil(self.clients.claim());});\n"
    "// network passthrough -- no caching; presence makes the app installable\n"
    "self.addEventListener('fetch',function(e){});\n")


@app.get("/portal/icon.svg")
async def portal_icon() -> Response:
    return Response(_PORTAL_ICON, media_type="image/svg+xml")


@app.get("/portal/icon-192.png")
async def portal_icon_192() -> Response:
    if not _PORTAL_ICON_192:
        return Response(_PORTAL_ICON, media_type="image/svg+xml")
    return Response(_PORTAL_ICON_192, media_type="image/png")


@app.get("/portal/icon-512.png")
async def portal_icon_512() -> Response:
    if not _PORTAL_ICON_512:
        return Response(_PORTAL_ICON, media_type="image/svg+xml")
    return Response(_PORTAL_ICON_512, media_type="image/png")


@app.get("/portal/manifest.webmanifest")
async def portal_manifest() -> Response:
    return Response(_PORTAL_MANIFEST, media_type="application/manifest+json")


@app.get("/sw.js")
async def portal_sw() -> Response:
    return Response(_PORTAL_SW, media_type="application/javascript")


@app.get("/", response_class=HTMLResponse)
async def portal_page() -> HTMLResponse:
    # Inject the SSOT palette AFTER the static defaults so it wins.
    return HTMLResponse(
        _PORTAL_HTML.replace("</head>", _portal_theme_css() + "</head>"))


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
        "planner": {
            "enabled": PLANNER_ENABLED,
            "model": PLANNER_MODEL,
            "endpoint": PLANNER_ENDPOINT,
            "max_nodes": PLANNER_MAX_NODES,
            "reflexion_cap": PLANNER_REFLEXION_CAP,
        },
        "dci": {
            "enabled": DCI_ENABLED,
            "model": DCI_MODEL,
            "endpoint": DCI_ENDPOINT,
            "act_count": len(DCI_ACTS),
            "flow": {
                "enabled": DCI_FLOW_ENABLED,
                "r_max": DCI_FLOW_R_MAX,
                "personas": [name for name, _ in _DCI_PERSONAS],
                "auto_trigger_conf": DCI_FLOW_TRIGGER_CONF,
            },
        },
        "security": {
            "allowlist_hosts": sorted(_ALLOWLIST_HOSTS),
            "high_privilege_verbs": sorted(_HIGH_PRIVILEGE_VERBS),
        },
        "skills": {
            "enabled": SKILLS_ENABLED,
            "min_length": SKILLS_MIN_LENGTH,
            "max_length": SKILLS_MAX_LENGTH,
            "min_support": SKILLS_MIN_SUPPORT,
            "window_hours": SKILLS_WINDOW_HOURS,
            "auto_promote_threshold": SKILLS_AUTO_PROMOTE_THRESHOLD,
        },
        "passport": {
            "enabled": PASSPORT_ENABLE,
            "algo": PASSPORT_ALGO,
            "agent_name": PASSPORT_AGENT_NAME,
            "key_dir": PASSPORT_KEY_DIR,
            "private_key_present": (
                _passport_load_priv() is not None
            ),
            "kid": _passport_kid() if PASSPORT_ENABLE else None,
            "verify_on_read": PASSPORT_VERIFY_ON_READ,
        },
        "refine": {
            "enabled": REFINE_ENABLED,
            "model": REFINE_MODEL,
            "endpoint": REFINE_ENDPOINT,
            "bypass_chars": REFINE_BYPASS_CHARS,
        },
        "polish": {
            "enabled": POLISH_ENABLED,
            "model": POLISH_MODEL,
            "endpoint": POLISH_ENDPOINT,
        },
        "agents": {
            name: {
                "endpoint": cfg.get("endpoint"),
                "model":    cfg.get("model"),
                "role":     cfg.get("role"),
                "default":  cfg.get("default"),
                "strengths": cfg.get("strengths"),
            }
            for name, cfg in _AGENT_REGISTRY.items()
        },
        "broker_sock": LAUNCHER_SOCK,
        "broker_present": os.path.exists(LAUNCHER_SOCK),
        "db_url": DB_URL,
        "port": PORT,
    }


# ── /kg/lookup (Phase C.1 Personal Knowledge Graph) ────────────────
# Resolve a phrase via the operator's preference graph. Returns
# the matched app_install record (alias-resolved or direct).
# Operator-callable curl-test endpoint; the planner can also hit
# it pre-decomposition to ground noun phrases.
@app.get("/kg/lookup")
async def kg_lookup_endpoint(phrase: str = "") -> JSONResponse:
    if not phrase:
        return JSONResponse(
            content={"error": "phrase query param required"},
            status_code=400,
        )
    result = await kg_lookup(phrase)
    if result is None:
        return JSONResponse(
            content={"match": None, "phrase": phrase},
            status_code=404,
        )
    return JSONResponse(content={"match": result, "phrase": phrase})


# ── /skills/* (Phase C.2 cross-agent skill catalog) ────────────────
# Shared surface for every agent in the MiOS stack. MiOS-Hermes
# pulls /skills/openai-tools at startup so its OpenAI-compat tool
# schema auto-includes every promoted skill -- no Hermes-side
# hardcoding. MiOS-OpenCode does the same (or reads SurrealDB
# directly for offline-only runs). Skill execution always goes
# through /skills/run so the firewall + taint chain + audit rows
# are identical regardless of which agent initiated the call.

@app.get("/skills/list")
async def skills_list(status: str = "promoted",
                      source: str = "",
                      limit: int = 200) -> JSONResponse:
    rows = await _skill_list(
        status=status or "all",
        source=source or None,
        limit=max(1, min(int(limit or 200), 1000)),
    )
    return JSONResponse(content={"skills": rows, "count": len(rows)})


@app.get("/skills/show")
async def skills_show(name: str = "") -> JSONResponse:
    if not name:
        return JSONResponse(
            content={"error": "name query param required"},
            status_code=400)
    row = await _skill_fetch(name)
    if not row:
        return JSONResponse(content={"skill": None, "name": name},
                            status_code=404)
    return JSONResponse(content={"skill": row})


@app.post("/skills/run")
async def skills_run(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except (json.JSONDecodeError, ValueError):
        return JSONResponse(
            content={"error": "invalid JSON body"}, status_code=400)
    name = str(body.get("name", "")).strip()
    if not name:
        return JSONResponse(
            content={"error": "name required"}, status_code=400)
    params = body.get("params") or {}
    if not isinstance(params, dict):
        return JSONResponse(
            content={"error": "params must be an object"},
            status_code=400)
    session_id = body.get("session_id")
    result = await execute_skill(
        name, params, session_id=session_id)
    status_code = 200 if result.get("success") else 422
    return JSONResponse(content=result, status_code=status_code)


@app.get("/skills/openai-tools")
async def skills_openai_tools() -> JSONResponse:
    """Dump the OpenAI tool-schema array for every promoted skill.
    Hermes + OpenCode fetch this and append it to their static tool
    surface so promoted skills become first-class callable tools
    on every external gateway -- no client-side edits per skill."""
    rows = await _skill_list(status="promoted")
    tools = [_skill_to_openai_tool(r) for r in rows]
    return JSONResponse(content={"tools": tools, "count": len(tools)})


# ── /passport/* (Phase C.3 -- Ed25519 attribution chain) ───────────
# Cross-agent verification surface. Any agent in the stack can POST
# {envelope, payload?} to /passport/verify and get a structured
# (ok, reason) response without holding the signer's private key.
# Public keys are filesystem-cached (world-readable) and SurrealDB-
# backed as a fallback.

@app.post("/passport/verify")
async def passport_verify(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except (json.JSONDecodeError, ValueError):
        return JSONResponse(
            content={"error": "invalid JSON body"}, status_code=400)
    envelope = body.get("envelope")
    if not isinstance(envelope, dict):
        return JSONResponse(
            content={"error": "envelope object required"},
            status_code=400)
    payload_for_hash = None
    table = body.get("table")
    fields = body.get("fields")
    if table and isinstance(fields, dict):
        payload_for_hash = (str(table), fields)
    ok, reason = _passport_verify(envelope, payload_for_hash)
    return JSONResponse(content={
        "ok": ok,
        "reason": reason,
        "agent": envelope.get("agent"),
        "kid": envelope.get("kid"),
        "alg": envelope.get("alg"),
    })


@app.get("/passport/public-key")
async def passport_public_key(agent: str = "") -> JSONResponse:
    """Return the requested agent's public PEM. Defaults to this
    service's own agent identity. Lets external integrators
    bootstrap verification without filesystem access."""
    target = (agent or PASSPORT_AGENT_NAME).strip()
    pub = _passport_load_public(target)
    if pub is None:
        return JSONResponse(
            content={"error": f"no public key for {target}"},
            status_code=404)
    from cryptography.hazmat.primitives import serialization
    pem = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return JSONResponse(content={
        "agent": target,
        "alg": PASSPORT_ALGO,
        "public_key_pem": pem,
    })


# ── /dci/deliberate (Phase B.2 on-demand convergent flow) ──────────
# Operator-callable endpoint that runs the full 4-persona DCI-CF
# flow against a supplied (user_text, envelope) pair. Latency:
# 4 personas * up to R_max rounds * ~3-10s per call = up to ~2min
# on cold-load. Use for high-stakes / ambiguous deliberation; the
# always-on B.1 Challenger covers cheap audit-trail cases.
@app.post("/dci/deliberate")
async def dci_deliberate(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except (json.JSONDecodeError, ValueError):
        return JSONResponse(
            content={"error": "invalid JSON body"},
            status_code=400,
        )
    user_text = str(body.get("user_text", "")).strip()
    envelope = body.get("envelope") or {}
    if not user_text:
        return JSONResponse(
            content={"error": "user_text required"}, status_code=400,
        )
    if not isinstance(envelope, dict):
        return JSONResponse(
            content={"error": "envelope must be an object"},
            status_code=400,
        )
    r_max = body.get("r_max")
    if r_max is not None:
        try:
            r_max = max(1, min(int(r_max), 5))
        except (TypeError, ValueError):
            r_max = None
    result = await run_dci_flow(
        user_text, envelope,
        session_id=body.get("session_id"),
        r_max=r_max,
    )
    return JSONResponse(content=result)


# ── /dci/schema (Phase B.1 introspection) ──────────────────────────
# Exposes the 14-act vocabulary + JSON schema so external gateways
# (Discord, Slack, future MCP clients) can introspect what a DCI
# act looks like without hardcoding. The operator can also hit
# this endpoint to verify a deployment has the expected act set.
@app.get("/dci/schema")
async def dci_schema() -> JSONResponse:
    return JSONResponse(content={
        "acts": DCI_ACTS,
        "act_names": DCI_ACT_NAMES,
        "response_schema": DCI_ACT_SCHEMA,
        "enabled": DCI_ENABLED,
    })


# ── /v1/models (passthrough) ───────────────────────────────────────
@app.get("/v1/models")
async def list_models(request: Request) -> JSONResponse:
    # Always advertise the MiOS-Agent chain model so ANY OpenAI-compatible
    # client (Firefox Smart Window "bring your own model", etc.) can list +
    # select it WITHOUT a backend key -- /v1/chat/completions runs the chain
    # locally and needs no auth. If the caller DID pass an Authorization
    # header, augment with the backend's own model list (best-effort).
    created = int(time.time())
    models: list = [{
        "id": "MiOS-Agent", "object": "model",
        "created": created, "owned_by": "mios",
    }]
    auth = request.headers.get("authorization")
    if auth:
        try:
            client = await _get_client()
            r = await client.get(f"{BACKEND}/models", headers={"authorization": auth})
            if r.status_code == 200:
                have = {m.get("id") for m in models}
                for m in ((r.json() or {}).get("data") or []):
                    if isinstance(m, dict) and m.get("id") not in have:
                        models.append(m)
        except httpx.HTTPError as e:
            log.warning("models proxy (augment) failed: %s", e)
    return JSONResponse(content={"object": "list", "data": models})


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
# ── Vision branch (operator 2026-05-22: "we need a vision model local to
# MiOS"). The text executor can't see images, so a turn carrying an image
# is routed DIRECTLY to the local VLM (qwen3-vl on the dGPU lane), bypassing
# refine/planning/Hermes. SSOT model via MIOS_AGENT_PIPE_VISION_MODEL
# (rendered from mios.toml [ai].chat_vision_model); no hardcoded literal
# beyond the env default, matching the REFINE_MODEL/POLISH_MODEL pattern.
VISION_ENABLE = os.environ.get(
    "MIOS_AGENT_PIPE_VISION", "true").lower() not in ("0", "false", "no", "")
# Default = llama3.2-vision:11b: verified working through ollama's /v1 image
# path (2026-05-22). qwen3-vl:4b was the lighter first choice but its ollama
# runner crashes on image input in this build ("model runner unexpectedly
# stopped" / "png: invalid format") -- switch back via this env once fixed.
VISION_MODEL = os.environ.get("MIOS_AGENT_PIPE_VISION_MODEL", "llama3.2-vision:11b")
VISION_ENDPOINT = os.environ.get(
    "MIOS_AGENT_PIPE_VISION_ENDPOINT", "http://localhost:11434").rstrip("/")


def _messages_have_image(messages: list) -> bool:
    """True if any message carries OpenAI vision content (a content list with
    an image_url / input_image part) -- the signal to route this turn to the
    local VLM instead of the text executor (which cannot see images)."""
    for m in messages or []:
        if not isinstance(m, dict):
            continue
        c = m.get("content")
        if isinstance(c, list):
            for part in c:
                if isinstance(part, dict) and part.get("type") in (
                        "image_url", "input_image", "image"):
                    return True
    return False


async def _vision_complete(body: dict, streaming: bool, chat_id: str,
                           model: str) -> Any:
    """Proxy an image-bearing turn to the local VLM (OpenAI-compatible, on the
    dGPU ollama lane). Streams the VLM SSE verbatim; non-stream returns its
    JSON. Best-effort: a backend error surfaces honestly, never fabricated."""
    vbody = dict(body)
    vbody["model"] = VISION_MODEL
    headers = {"content-type": "application/json"}
    if _BACKEND_KEY:
        headers["authorization"] = f"Bearer {_BACKEND_KEY}"
    url = f"{VISION_ENDPOINT}/v1/chat/completions"
    client = await _get_client()
    if not streaming:
        vbody["stream"] = False
        try:
            r = await client.post(
                url, content=json.dumps(vbody).encode("utf-8"), headers=headers)
            return JSONResponse(content=r.json(), status_code=r.status_code)
        except Exception as e:
            log.warning("vision backend failed: %s", e)
            return JSONResponse(
                content={"error": {"message": f"vision backend error: {e}",
                                   "type": "server_error"}}, status_code=502)

    async def _gen() -> AsyncGenerator[bytes, None]:
        vbody["stream"] = True
        try:
            async with client.stream(
                    "POST", url,
                    content=json.dumps(vbody).encode("utf-8"),
                    headers=headers) as resp:
                async for chunk in resp.aiter_bytes():
                    yield chunk
        except Exception as e:
            log.warning("vision stream failed: %s", e)
            yield ("data: " + json.dumps(
                {"choices": [{"delta": {"content": f"[vision error: {e}]"}}]})
                + "\n\n").encode("utf-8")
            yield b"data: [DONE]\n\n"

    return StreamingResponse(_gen(), media_type="text/event-stream")


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
    # Per-chat scratchpad key from the forwarded OpenAI metadata.chat_id
    # (stable across this conversation's turns); falls back to a per-request
    # id for non-OWUI callers. Read by _scratchpad_note/_render downstream.
    _conv_key_var.set(_scratchpad_key(body, chat_id))
    # SWARM toggles (operator 2026-05-22): per-request force flags set by the
    # OWUI chat-bar toggle-filters, injected into body.mios_flags and
    # forwarded here verbatim by the pipe. They OVERRIDE the mios.toml SSOT
    # defaults for THIS turn only (the tool_choice-style 'forced vs natural'
    # control). Stripped from proxy_body before Hermes sees it.
    #   force_council  -> engage the FULL swarm (every eligible agent)
    #   force_delegate -> force per-agent DAG decomposition (swarm planner)
    #   force_tool     -> tool_choice=required on the executor (anti-narrate)
    _mflags = body.get("mios_flags")
    _mflags = _mflags if isinstance(_mflags, dict) else {}
    _force_council = bool(_mflags.get("force_council"))
    _force_delegate = bool(_mflags.get("force_delegate"))
    _force_tool = bool(_mflags.get("force_tool"))
    if _mflags:
        log.info("swarm flags: council=%s delegate=%s tool=%s",
                 _force_council, _force_delegate, _force_tool)
    # Operator-facing persona + environment/language/locale guidance the
    # OWUI pipe injected as system message(s). Captured once so the final
    # polish can apply the operator's voice + the correct language
    # (operator 2026-05-22: "polish the final response with persona
    # applied"). Joined; polish frames it as STYLE-only.
    _persona_system = "\n\n".join(
        str(m.get("content") or "").strip()
        for m in messages
        if isinstance(m, dict) and m.get("role") == "system"
        and str(m.get("content") or "").strip()
    )[:2000]

    # VISION: an image-bearing turn can't be served by the text executor --
    # route it DIRECTLY to the local VLM (operator 2026-05-22), bypassing
    # refine / planning / Hermes. No session or refine overhead.
    if VISION_ENABLE and _messages_have_image(messages):
        log.info("vision: image turn -> %s", VISION_MODEL)
        return await _vision_complete(body, streaming, chat_id, model)

    # SurrealDB session row -- the record id is captured for
    # downstream tool_call linking + the inline confirmation engine.
    # passport_sign=False: the `session` table is SCHEMAFULL and has
    # NO `passport` field, so attaching the default Ed25519 envelope
    # made SurrealDB reject the CREATE with a per-statement ERR
    # ("Found field 'passport', but no such field exists for table
    # 'session'"). That ERR comes back inside an HTTP 200, so _db_post
    # returned a list whose statement result was an error STRING (not a
    # row list) -> session_id stayed None on EVERY agent turn. That
    # silently disabled session-scoped machinery: tool_call session
    # links, taint propagation, AND the inline satisfaction /
    # confirmation check (which bails on a None session_id). The
    # session row is lightweight bookkeeping; the audit-relevant
    # tool_call / event / firewall_block rows keep their passports
    # (those tables carry the field). Operator 2026-05-22.
    session_id: Optional[str] = None
    try:
        resp = await _db_post(_db_create(
            "session",
            {"platform": "mios-agent-pipe",
             "model": model},
            now_fields=("started_at",),
            extra="RETURN id",
            passport_sign=False,
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

    # Phase D.5 -- refine FIRST when input isn't trivial. The
    # quick-refine pass on the iGPU lane produces a structured
    # plan {intent, refined_text, intended_outcome, target_agent,
    # hint_tools, hint_skills}. Operator directive 2026-05-18:
    # "should always be refined/processed/enhanced", but ALSO
    # "FAST AND EFFICIENT FOR PURE LOCAL COMPUTE" -- so trivial
    # input (short greeting / single-token status check) skips
    # refine and goes straight to the layer-1 router which has
    # its own chat-reply fast path. Refine returns None on the
    # bypass case; refine_intent + classify_intent are
    # complementary, not redundant.
    refined = await refine_intent(last_user_text, messages)

    # SHORT-CIRCUIT: when refine emitted intent=chat with a reply,
    # we already have the final answer. No router + no sub-agent
    # delegation needed. Operator-flagged 2026-05-18 trace: short
    # greetings like "hey! How's it going?" were ending up at
    # Hermes (which then ran tool cascades) because the router
    # was independently re-classifying them as `agent`. Refine
    # already nailed the chat-classification at 25s; using its
    # verdict directly saves the 30-90s Hermes roundtrip on every
    # conversational message.
    _chat_reply = ""
    if (refined and refined.get("intent") == "chat"
            and not _force_council and not _force_delegate):
        _chat_reply = str(refined.get("reply") or "").strip()
        if not _chat_reply:
            # The JSON classifier reliably tags chat but often omits the
            # `reply` field -- generate it now so a greeting never falls
            # through to Hermes (which tried a bogus 'chat' verb, operator
            # 2026-05-20). Generated, not canned. Empty -> fall through.
            _chat_reply = await _quick_chat_reply(last_user_text, messages)
    if _chat_reply:
        reply = _chat_reply
        log.info("refine short-circuit: chat reply (no router/backend)")
        if streaming:
            async def _stream_refine_chat() -> AsyncGenerator[bytes, None]:
                yield _sse_status_phase(chat_id=chat_id, model=model,
                                        phase="prompt")
                yield _sse_status_phase(chat_id=chat_id, model=model,
                                        phase="refine")
                yield _sse_chunk("", chat_id=chat_id, model=model,
                                 role="assistant")
                yield _sse_chunk(reply, chat_id=chat_id, model=model)
                yield _sse_status_phase(chat_id=chat_id, model=model,
                                        phase="chat_done", done=True)
                yield _sse_chunk("", chat_id=chat_id, model=model,
                                 finish_reason="stop")
                yield _sse_done()
            return StreamingResponse(_stream_refine_chat(),
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

    # MULTI-TASK SHORT-CIRCUIT: refine detected several independent
    # goals (>=2 tasks in the array). Write them to kanban_shadow,
    # promote task #1 as the active dispatch, and stash the queue on
    # the refined envelope so polish can prepend a "queued N tasks"
    # preamble to the final reply.
    if (refined and refined.get("intent") == "multi_task"
            and isinstance(refined.get("tasks"), list)
            and len(refined["tasks"]) >= 2):
        queued = _shadow_queue_tasks(refined["tasks"], session_id)
        if queued:
            log.info(
                "multi_task: queued=%d active=%r others=%r",
                len(queued),
                queued[0].get("title", ""),
                [t.get("title", "") for t in queued[1:]],
            )
            # Operator 2026-05-22 ("separate prompts per refinement step ->
            # sub-agents ... concurrent Compute"): run the independent tasks
            # as a CONCURRENT per-agent DAG THIS turn -- each task routed to
            # its target_agent, all in parallel -- and synthesise one answer,
            # instead of promoting task #0 and deferring the rest to follow-up
            # turns. The kanban_shadow queue above stays (audit/visibility).
            # Falls through to the legacy promote-and-queue path when fewer
            # than 2 tasks resolve to agents.
            if PLANNER_ENABLED:
                _adag = _agent_dag_from_tasks(queued)
                if len(_adag.get("nodes") or []) >= 2:
                    log.info("multi_task -> concurrent agent DAG (%d): %s",
                             len(_adag["nodes"]),
                             [n["agent"] for n in _adag["nodes"]])
                    return await _respond_agent_dag(
                        _adag, refined, streaming=streaming, chat_id=chat_id,
                        model=model, session_id=session_id,
                        last_user_text=last_user_text,
                        persona_system=_persona_system)
            # Promote task #0 to the active turn. Replace
            # last_user_text + the refined envelope's top-level
            # fields with task #0's, so all downstream branches
            # (router, agent dispatch, polish) operate on the
            # active task. Keep the original `tasks` array +
            # active index on the envelope so polish can render
            # the preamble.
            active = queued[0]
            last_user_text = str(active.get("refined_text")
                                 or active.get("title", "")
                                 or last_user_text)
            for k in ("refined_text", "intended_outcome",
                      "target_agent", "hint_tools", "hint_skills"):
                if active.get(k) is not None:
                    refined[k] = active[k]
            refined["intent"] = "agent"
            refined["_multi_task_queue"] = queued
            refined["_multi_task_active_idx"] = 0

    # MULTI-STEP -> per-agent DAG bridge (operator 2026-05-22 "separate
    # prompts per refinement step -> sub-agents ... concurrent Compute").
    # refine flagged this turn multi-step but didn't itemise a tasks array
    # (so the multi_task block above didn't fire). Give the planner ONE
    # chance to decompose it; if it returns a genuine MULTI-AGENT plan
    # (>=1 agent node), run that DAG concurrently this turn + synthesise.
    # Otherwise fall through to the unified Hermes + council path unchanged.
    # This is the unify-on entry point to the per-agent planner DAG.
    # The 🧩 Delegate SWARM toggle (force_delegate) forces this decomposition
    # regardless of refine's classification -- the manual override for when
    # the classifier under-fires (operator 2026-05-22).
    # Decompose-by-default: a substantive agent-intent ask attempts the swarm
    # decomposer even without an explicit delegate toggle / _multi_step flag.
    # _plan_swarm self-gates (returns [] when not worth splitting), so simple
    # asks fall through to council unharmed.
    _decompose_default = bool(
        SWARM_DECOMPOSE_DEFAULT and refined
        and refined.get("intent") == "agent"
        and len((last_user_text or "").split()) >= SWARM_DECOMPOSE_MIN_WORDS)
    if PLANNER_ENABLED and (_force_delegate
                            or (refined and refined.get("_multi_step"))
                            or _decompose_default):
        # Layer B (operator 'AI SWARM'): the DEDICATED swarm decomposer
        # first (reliable {agent, sub-task} assignments), then fall back to
        # the general verb-DAG planner if it produced an agent plan. Either
        # yields a concurrent per-agent DAG; otherwise fall through to the
        # unified Hermes + council path.
        _swarm_tasks = await _plan_swarm(last_user_text)
        log.info("swarm hook: force_delegate=%s plan_swarm=%d tasks",
                 _force_delegate, len(_swarm_tasks))
        _mdag = (_agent_dag_from_tasks(_swarm_tasks)
                 if len(_swarm_tasks) >= 2 else None)
        if not (_mdag and len(_mdag.get("nodes") or []) >= 2):
            _gen = await decompose_intent(last_user_text)
            _gn = (_gen.get("nodes") or []) if _gen else []
            _n_agents = sum(1 for n in _gn if n.get("agent"))
            _has_action = any(
                str((_VERB_CATALOG.get(str(n.get("tool"))) or {})
                    .get("permission", "")).lower() == "write"
                for n in _gn)
            # Take the planner DAG ONLY when it's a REAL multi-agent split
            # (>=2 agents) OR an EXECUTABLE action (a WRITE verb like
            # winget_install). A thin [web_search, hermes] plan is a single task
            # with a tool, NOT a swarm -- let it fall through to the ALL-NODES
            # council so the FIRST PASS is the full swarm (operator 2026-05-23:
            # "just using only Hermes ... not swarm from first operations").
            # Actions still execute via the broker; research multi-splits run.
            _mdag = _gen if (_n_agents >= 2 or _has_action) else None
        if _mdag and (_mdag.get("nodes") or []):
            _nd = _mdag["nodes"]
            log.info("swarm -> DAG (%d nodes; %s)", len(_nd),
                     [n.get("tool") or ("agent:" + str(n.get("agent")))
                      for n in _nd])
            return await _respond_agent_dag(
                _mdag, refined, streaming=streaming, chat_id=chat_id,
                model=model, session_id=session_id,
                last_user_text=last_user_text, persona_system=_persona_system)

    # 🧩 Delegate GUARANTEES a swarm: when structured decomposition declined
    # above (the local planner is inconsistent at splitting), escalate to the
    # FULL council swarm downstream (every agent, same prompt) rather than the
    # relevance-gated fan-out -- the toggle must never collapse to one agent.
    if _force_delegate:
        _force_council = True

    # Unify-on default (operator 2026-05-20: "Unify should be on by
    # default"). Non-chat routes through the agent path (refine -> Hermes
    # streamed -> critic -> polish) for a clean answer + streaming; the
    # dispatch/DAG fast-paths stay hardened (verb-name normalisation,
    # capped CPU polish) for when MIOS_AGENT_PIPE_UNIFY_AGENT=0.
    _unify_agent = os.environ.get(
        "MIOS_AGENT_PIPE_UNIFY_AGENT", "1") not in {"0", "false", "no"}
    # TWO CLASSIFIERS -> ONE (operator 2026-05-20 refactor): under
    # unify-on, refine already classified and chat + multi_task have
    # short-circuited above, so all that remains is intent=agent -> the
    # agent path. The layer-1 router only added dispatch-shape (tool+args)
    # extraction, which unify-on bypasses -- so skip the redundant second
    # classifier LLM call. (Unify-off still runs it for dispatch/DAG.)
    if _unify_agent and refined and refined.get("intent"):
        verdict = None
    else:
        # Layer-1 router: {"action": "dispatch"|"chat"|"agent", ...}.
        verdict = await classify_intent(last_user_text)
    # Carry refined hints into the verdict for downstream branches.
    if verdict and refined:
        verdict["_refined"] = refined
    # No router verdict but refine classified agent/dag -> promote
    # refine's verdict so we proxy to the right sub-agent.
    if not verdict and refined and refined.get("intent") in ("agent", "dag"):
        verdict = {"action": "agent", "reason": "refine-classified",
                   "_refined": refined}

    if verdict:
        action = verdict.get("action")

        # ── DISPATCH fast-path (skipped when unified onto agent) ──
        if action == "dispatch" and not _unify_agent:
            tool = str(verdict.get("tool", "")).strip()
            args = verdict.get("args") or {}
            if tool:
                result = await dispatch_mios_verb(
                    tool, args if isinstance(args, dict) else {},
                    session_id=session_id,
                )
                ok = bool(result.get("success"))
                # SurrealDB tool_call row -- write fire-and-forget.
                # Phase A.3: include taint state for the firewall.
                _row = {
                    "tool": tool,
                    "args": args if isinstance(args, dict) else {},
                    "result_preview": (result.get("output") or "")[:500],
                    "success": ok,
                    "latency_ms": int(result.get("latency_ms", 0)),
                    "tainted": bool(result.get("tainted")),
                    "taint_reason": (result.get("taint_reason") or "") or None,
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
                # Phase B.1 + B.3 chained critic: Challenger runs
                # post-dispatch (audit trail); on a high-confidence
                # challenge / ask, the chain auto-escalates to the
                # B.2 4-persona flow; if THAT flow surfaces dissent,
                # the session gets tainted so the firewall refuses
                # the next high-privilege dispatch. Fire-and-forget
                # so the operator's reply isn't delayed.
                if DCI_ENABLED:
                    _db_fire(critic_then_maybe_flow(
                        last_user_text, envelope,
                        session_id=session_id,
                    ))
                symbol = "✅" if ok else "⚠️"
                envelope_block = (
                    f"<details type=\"tool_calls\" done=\"true\">\n"
                    f"<summary>{symbol} `{tool}`</summary>\n\n"
                    f"```json\n{json.dumps(envelope, indent=2, default=str)}\n```\n"
                    f"</details>"
                )
                # Polish the tool output into a human-facing summary
                # so the operator sees "Here are your 32 installed
                # apps: ..." above the collapsible envelope, NOT just
                # the raw JSON. Synthesise a minimal refined dict for
                # the polish call when refine didn't run (dispatch
                # path can fire without a full refine envelope when
                # the trivial-bypass kicked in).
                _refined_for_polish = refined or {
                    "intent": "dispatch",
                    "intended_outcome": f"answer the question by running {tool}",
                    "refined_text": last_user_text,
                }
                # Cap tight for the CPU polish lane: 6000 chars of (e.g.)
                # system_status JSON made the 1.7b CPU polish blow its
                # timeout -> raw JSON fallback (operator 2026-05-20). 1800
                # chars summarises fast on pure CPU while keeping the
                # salient fields. mios-os-control stays CPU-capable.
                tool_output = (result.get("output") or "")[:1800]
                # Inline satisfaction check writes the user_query_
                # (un)satisfied event before polish queries verdicts.
                await _inline_satisfaction_check(
                    session_id, _refined_for_polish)
                polished = ""
                if tool_output.strip():
                    polished_raw = await polish_response(
                        f"Tool `{tool}` ran successfully and returned:\n"
                        f"{tool_output}\n\n"
                        f"Write a friendly natural-language answer to the "
                        f"operator's question using this tool output.",
                        _refined_for_polish, session_id=session_id,
                        original_user_text=last_user_text,
                        persona_system=_persona_system,
                    )
                    polished = (_strip_think_tags(polished_raw)
                                if polished_raw else "")
                # Compose: polished answer ABOVE the collapsible
                # envelope (envelope is the audit trail, polished is
                # the operator-visible reply).
                if polished.strip():
                    rendered = f"{polished}\n\n{envelope_block}"
                else:
                    rendered = envelope_block
                if streaming:
                    async def _stream_dispatch() -> AsyncGenerator[bytes, None]:
                        # Phase markers: listening -> picking -> doing -> done.
                        # Technical detail (tool args, exit codes, latencies)
                        # lives in the SurrealDB event_log; the strip stays
                        # readable for non-technical operators.
                        yield _sse_status_phase(chat_id=chat_id, model=model,
                                                phase="prompt")
                        yield _sse_status_phase(chat_id=chat_id, model=model,
                                                phase="route")
                        yield _sse_status_phase(chat_id=chat_id, model=model,
                                                phase="tool")
                        yield _sse_chunk("", chat_id=chat_id, model=model,
                                         role="assistant")
                        yield _sse_chunk(rendered, chat_id=chat_id, model=model)
                        yield _sse_status_phase(
                            chat_id=chat_id, model=model,
                            phase="tool_done" if ok else "tool_done_warn",
                            done=True)
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
                        yield _sse_status_phase(chat_id=chat_id, model=model,
                                                phase="prompt")
                        yield _sse_status_phase(chat_id=chat_id, model=model,
                                                phase="route")
                        yield _sse_chunk("", chat_id=chat_id, model=model,
                                         role="assistant")
                        yield _sse_chunk(reply, chat_id=chat_id, model=model)
                        yield _sse_status_phase(chat_id=chat_id, model=model,
                                                phase="chat_done", done=True)
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

        # action == "agent" -> planner gets a chance to decompose
        # into a DAG of dispatch verbs (Phase A.1). If the planner
        # returns >=2 actionable nodes, run the DAG locally; if it
        # returns empty or fails, fall through to the backend proxy
        # which has Hermes's full tool-calling agent loop available.
        if action == "agent" and PLANNER_ENABLED and not _unify_agent:
            dag = await decompose_intent(last_user_text)
            if dag and (dag.get("nodes") or []):
                if streaming:
                    async def _stream_dag() -> AsyncGenerator[bytes, None]:
                        yield _sse_status_phase(chat_id=chat_id, model=model,
                                                phase="prompt")
                        yield _sse_status_phase(chat_id=chat_id, model=model,
                                                phase="route")
                        yield _sse_status_phase(chat_id=chat_id, model=model,
                                                phase="plan")
                        yield _sse_chunk("", chat_id=chat_id, model=model,
                                         role="assistant")
                        # Run the DAG via the unified CONCURRENT executor
                        # (topological levels; agent + verb nodes run in
                        # parallel per level), then render the audit
                        # envelope. Per-node "tool" pills are dropped --
                        # independent nodes now run concurrently so a
                        # per-node stream order is no longer meaningful;
                        # the collapsible envelope is the audit trail.
                        yield _sse_status_phase(chat_id=chat_id, model=model,
                                                phase="tool")
                        dag_result = {}
                        async for _k, _p in _execute_dag_emitting(
                                dag, session_id=session_id,
                                chat_id=chat_id, model=model):
                            if _k == "event":
                                yield _p
                            else:
                                dag_result = _p
                        all_ok = dag_result.get("success", False)
                        env = {
                            "dag": {
                                "summary": dag.get("summary", ""),
                                "nodes_total": dag_result.get("nodes_total", 0),
                                "nodes_executed": dag_result.get("nodes_executed", 0),
                                "success": all_ok,
                            },
                            "nodes": dag_result.get("node_results", []),
                        }
                        symbol = "✅" if all_ok else "⚠️"
                        rendered = (
                            f"<details type=\"tool_calls\" done=\"true\">\n"
                            f"<summary>{symbol} dag · {env['dag']['nodes_total']} steps</summary>\n\n"
                            f"```json\n{json.dumps(env, indent=2, default=str)}\n```\n"
                            f"</details>"
                        )
                        yield _sse_chunk(rendered, chat_id=chat_id, model=model)
                        yield _sse_status_phase(
                            chat_id=chat_id, model=model,
                            phase="dag_done" if all_ok else "dag_done_warn",
                            done=True)
                        yield _sse_chunk("", chat_id=chat_id, model=model,
                                         finish_reason="stop")
                        yield _sse_done()
                    return StreamingResponse(_stream_dag(),
                                             media_type="text/event-stream")
                # Non-streaming DAG execution.
                dag_result = await execute_dag(dag, session_id=session_id)
                env = {
                    "dag": {
                        "summary": dag.get("summary", ""),
                        "nodes_total": dag_result.get("nodes_total", 0),
                        "nodes_executed": dag_result.get("nodes_executed", 0),
                        "success": dag_result.get("success", False),
                    },
                    "nodes": dag_result.get("node_results", []),
                }
                symbol = "✅" if dag_result.get("success") else "⚠️"
                rendered = (
                    f"<details type=\"tool_calls\" done=\"true\">\n"
                    f"<summary>{symbol} dag · {env['dag']['nodes_total']} steps</summary>\n\n"
                    f"```json\n{json.dumps(env, indent=2, default=str)}\n```\n"
                    f"</details>"
                )
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
            # Planner returned empty / unparseable -> fall through.

        # action == "agent" (planner declined) or unrecognized -> backend.

    # ── No router verdict (router timed out / unparseable) ─────
    # Phase A.1 graceful-degrade: even with no router verdict, give
    # the planner a chance to decompose multi-step intents. If the
    # planner returns a usable DAG, run it; otherwise proceed to the
    # backend proxy. This avoids losing tool dispatch entirely when
    # the router (qwen3:1.7b on the CPU-fallback iGPU lane) takes
    # longer than its timeout budget under cold-load.
    if not verdict and PLANNER_ENABLED and not _unify_agent:
        dag = await decompose_intent(last_user_text)
        if dag and (dag.get("nodes") or []):
            # Same handling as the action=agent path: the unified
            # execute_dag runs it (concurrent levels, agent + verb nodes).
            if streaming:
                async def _stream_dag2() -> AsyncGenerator[bytes, None]:
                    yield _sse_status_phase(chat_id=chat_id, model=model,
                                            phase="prompt")
                    yield _sse_status_phase(chat_id=chat_id, model=model,
                                            phase="plan")
                    yield _sse_chunk("", chat_id=chat_id, model=model,
                                     role="assistant")
                    # Unified CONCURRENT executor (agent + verb nodes,
                    # topological levels in parallel), same as the
                    # action=agent streaming path -- no per-node loop here.
                    yield _sse_status_phase(chat_id=chat_id, model=model,
                                            phase="tool")
                    dag_result = {}
                    async for _k, _p in _execute_dag_emitting(
                            dag, session_id=session_id,
                            chat_id=chat_id, model=model):
                        if _k == "event":
                            yield _p
                        else:
                            dag_result = _p
                    all_ok = dag_result.get("success", False)
                    env = {
                        "dag": {
                            "summary": dag.get("summary", ""),
                            "nodes_total": dag_result.get("nodes_total", 0),
                            "nodes_executed": dag_result.get("nodes_executed", 0),
                            "success": all_ok,
                        },
                        "nodes": dag_result.get("node_results", []),
                    }
                    symbol = "✅" if all_ok else "⚠️"
                    rendered = (
                        f"<details type=\"tool_calls\" done=\"true\">\n"
                        f"<summary>{symbol} dag · {env['dag']['nodes_total']} steps</summary>\n\n"
                        f"```json\n{json.dumps(env, indent=2, default=str)}\n```\n"
                        f"</details>"
                    )
                    yield _sse_chunk(rendered, chat_id=chat_id, model=model)
                    yield _sse_status_phase(
                        chat_id=chat_id, model=model,
                        phase="dag_done" if all_ok else "dag_done_warn",
                        done=True)
                    yield _sse_chunk("", chat_id=chat_id, model=model,
                                     finish_reason="stop")
                    yield _sse_done()
                return StreamingResponse(_stream_dag2(),
                                         media_type="text/event-stream")
            dag_result = await execute_dag(dag, session_id=session_id)
            env = {
                "dag": {
                    "summary": dag.get("summary", ""),
                    "nodes_total": dag_result.get("nodes_total", 0),
                    "nodes_executed": dag_result.get("nodes_executed", 0),
                    "success": dag_result.get("success", False),
                },
                "nodes": dag_result.get("node_results", []),
            }
            symbol = "✅" if dag_result.get("success") else "⚠️"
            rendered = (
                f"<details type=\"tool_calls\" done=\"true\">\n"
                f"<summary>{symbol} dag · {env['dag']['nodes_total']} steps</summary>\n\n"
                f"```json\n{json.dumps(env, indent=2, default=str)}\n```\n"
                f"</details>"
            )
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

    # ── AGENT path / fallback -> proxy to a sub-agent ──────────
    # Phase D.5b: multi-agent routing + hint injection + polish.
    #   1. Pick target_agent from refined hints, fall back to
    #      registry default (Hermes).
    #   2. Build a hint-injected system message ("MiOS-Agent
    #      refined plan: ...") so the sub-agent gets the
    #      operator's intent + suggested tools/skills as context.
    #   3. Forward to the sub-agent's endpoint.
    #   4. Non-streaming: polish the response before returning.
    #      Streaming: emit raw stream + a final polished delta if
    #      polish succeeded (heavy on token re-emission; gated on
    #      response shape so we don't re-stream small chat replies).
    target_role = ""
    if refined:
        target_role = str(refined.get("target_agent") or "").lower()
    target_name, target_cfg = _pick_agent(target_role)
    target_endpoint = target_cfg.get("endpoint") or BACKEND
    # Casual MiOS-convention label for SSE strip; the literal name
    # stays in the event payload + journal for debuggability.
    target_label = f"→ {_casual_agent_label(target_name)}"
    # Multi-agent concurrent fan-out (operator 2026-05-21): pick a COUPLE
    # of relevant secondary agents to run alongside the primary. Empty
    # unless [dispatch].fanout_max>1 AND a registered agent's role/strengths
    # match the refined intent -> safe single-agent no-op by default.
    _fanout = _pick_fanout_agents(target_name, refined,
                                  force_council=_force_council)
    if _fanout:
        log.info("fanout%s: primary=%s + %d secondary %s",
                 " (FORCED swarm)" if _force_council else "",
                 target_name, len(_fanout), [n for n, _ in _fanout])

    # Build the proxy body: original messages + hint-injected
    # system prefix (only when refine emitted hints; trivial inputs
    # skip refine + skip the prefix).
    proxy_body = dict(body)
    # Strip the SWARM control flags before the executor sees them (they are
    # MiOS orchestration metadata, not part of the OpenAI chat request).
    proxy_body.pop("mios_flags", None)
    # 🧠 Force-tool toggle: tool_choice=required tells the executor it MUST
    # emit a real tool_call instead of narrating the action (the standard
    # anti-"I posted to Discord"-lie guard). Best-effort -- honoured by
    # tool-calling executors; a model that ignores it just behaves as auto.
    if _force_tool:
        proxy_body["tool_choice"] = "required"
    # Enrich stage: prepend RAG context (SurrealDB vector store, in-loop
    # for every agent/sub-agent turn) + the refined plan hints as system
    # messages before the sub-agent runs (operator 2026-05-20: "RAG in
    # the loop for all agents/sub-agents every turn").
    _sys_prefix: list = [{"role": "system", "content": _temporal_grounding()}]
    _sp_block = _scratchpad_render()
    if _sp_block:
        _sys_prefix.append({"role": "system", "content": _sp_block})
    _rag_ctx = await _rag_enrich(last_user_text)
    if _rag_ctx:
        _sys_prefix.append({"role": "system", "content": _rag_ctx})
    # Knowledge recall: surface relevant PRIOR answers (the read half of the
    # store/recall loop) so the stack builds on what it already worked out.
    _recall_ctx = await _recall_knowledge(last_user_text)
    if _recall_ctx:
        _sys_prefix.append({"role": "system", "content": _recall_ctx})
    if refined and (refined.get("hint_tools") or refined.get("hint_skills")
                    or refined.get("intended_outcome")):
        _sys_prefix.append({"role": "system",
                            "content": _build_agent_hint(refined, target_name)})
    if _sys_prefix:
        proxy_body["messages"] = _sys_prefix + list(messages)
    proxy_bytes = json.dumps(proxy_body).encode("utf-8")
    # Normalise header keys to lowercase so the Content-Type set
    # below replaces (not duplicates) whatever the incoming request
    # supplied. Operator-flagged 2026-05-18 trace: Hermes :8642
    # returned 400 "Duplicate 'Content-Type' header found" because
    # request.headers preserved case ("Content-Type") + setdefault
    # added a second copy ("content-type").
    headers = {k.lower(): v for k, v in request.headers.items()
               if k.lower() in ("authorization", "accept")}
    headers["content-type"] = "application/json"
    # Drop an empty / placeholder client Authorization (a keyless OpenAI
    # client like Firefox Smart Window may send a blank "Bearer" or omit the
    # key) so the backend-key fallback below applies instead of forwarding an
    # unusable header that Hermes 401s on.
    _ca = headers.get("authorization", "").strip()
    if _ca.lower() in ("", "bearer", "bearer null", "bearer none", "bearer undefined"):
        headers.pop("authorization", None)
    # Self-inject bearer when caller didn't supply a usable one + we have a
    # key from /etc/mios/hermes/api.env (or env override). Lets direct
    # callers (curl, MCP clients, Smart Window) reach Hermes without each
    # gateway re-implementing the auth flow.
    if "authorization" not in headers and _BACKEND_KEY:
        headers["authorization"] = f"Bearer {_BACKEND_KEY}"

    # Detail strings: refine elapsed/intent/model, target endpoint,
    # tool_cards count, multi_task queue length. Operator should be
    # able to read the strip and tell exactly which sub-agent got
    # what plan.
    if streaming:
        # OPERATOR-BINDING: ALL sub-agent output goes inside the
        # <details type="reasoning"> dropdown; polished answer is
        # main content; <think> tags are stripped.
        #
        # Strategy: force upstream stream=false so we get the
        # COMPLETE final message (Hermes's tool-loop fully resolved,
        # tool_calls invoked + their results folded in, final
        # message.content assembled). Then run polish/wrap/strip on
        # that and emit ONE assistant content delta. We lose
        # mid-tool-call streaming visibility but gain a COMPLETE
        # final content -- the previous SSE-line parser dropped
        # tool_call envelope deltas, leaving the content cut off
        # mid-sentence ("using the standard Windows screenshot
        # command:" with nothing after). Real-time status strip
        # still streams (agent-pipe's own _sse_status_phase events
        # below).
        async def _stream_backend() -> AsyncGenerator[bytes, None]:
            yield _sse_status_phase(chat_id=chat_id, model=model,
                                    phase="prompt")
            if refined:
                yield _sse_status_phase(chat_id=chat_id, model=model,
                                        phase="refine")
            yield _sse_status_phase(chat_id=chat_id, model=model,
                                    phase="route")
            yield _sse_status_phase(chat_id=chat_id, model=model,
                                    phase="agent_target")
            # Endpoint emitter: announce the PRIMARY node + its endpoint.
            yield _node_status(
                chat_id=chat_id, model=model, name=target_name,
                cfg={**(_AGENT_REGISTRY.get(target_name) or {}),
                     "endpoint": target_endpoint}, state="engage")
            client = await _get_client()
            stream_body = dict(proxy_body)
            stream_body["stream"] = True
            raw = ""
            # Stream Hermes's INLINE output (reasoning + tool steps + answer
            # are one interleaved stream -- "Hermes prints everything
            # inline", operator 2026-05-20) and forward it into the dropdown
            # as CHECKPOINTED, self-contained <details done="true"> reasoning
            # blocks. Each block renders the instant it closes (a single
            # growing <details> only renders once closed -> "everything
            # dumps at the end"). The full content is accumulated for the
            # polish pass. CRITICAL: accumulate EVERY content delta and
            # REPRESENT tool_calls inline -- the previous parser dropped
            # tool_call deltas and cut content off mid-sentence, which is
            # why this path used to buffer.
            _block_buf = ""
            _last_flush = time.time()
            _ckpt_s = float(os.environ.get("MIOS_AGENT_CKPT_S", "2.0"))
            _reasoning_open = False
            # CONFIRMATION ENGINE: names of verbs the sub-agent invokes
            # inside its own tool-loop, captured from the stream. Feeds
            # the Definition-of-Done check below -- agent-pipe records no
            # tool_call row for a hermes-internal verb, so this is the
            # only signal that the turn DID act.
            _tools_called: list = []
            _summary = _HUMAN_LABELS.get("agent_target", ("🤖", ""))[0]

            def _flush_reasoning(buf: str) -> bytes:
                # KEYSTONE (operator 2026-05-20): stream the agent's live
                # thinking on the STANDARD delta.reasoning_content channel --
                # NOT as a <details> block inside content. OWUI renders
                # reasoning_content as its native Thinking dropdown; strict
                # OpenAI clients (Firefox Smart Window) ignore it and show
                # only the clean `content` answer. This is what stops the
                # <think> leaks, the reasoning masquerading as the answer, and
                # the empty-answer / no-emit behaviour.
                return _sse_reasoning(_sanitize_tool_text(buf),
                                      chat_id=chat_id, model=model)

            # The reasoning dropdown opens on the FIRST real reasoning delta
            # (tool steps / council merges via _flush_reasoning below). The old
            # "👂 ✨ 🧭 🤖" preamble was REMOVED 2026-05-22 -- it dumped bare
            # emojis into the dropdown ("Hermes just prints emojis"); the phase
            # pills already carry that progress signal as status events.
            # Kick the secondary fan-out agents CONCURRENTLY with the primary
            # stream (operator 2026-05-21 'a couple at a time'). They run
            # non-streaming + best-effort; their answers fold into polish +
            # the reasoning dropdown once the primary finishes. Dead endpoints
            # drop out harmlessly (return_exceptions on the gather below).
            # Endpoint emitters: announce EACH secondary node as it's engaged,
            # and remember its cfg so the collection loop can mark it
            # responded/silent (operator 2026-05-22).
            _fanout_cfg = {_n: _c for _n, _c in _fanout}
            # Live MERGED-event-queue streaming (operator 2026-05-23): the
            # PRIMARY is pumped in the BACKGROUND into the SAME queue the
            # secondaries stream into, so the generator drains ONE queue and
            # secondary fragments interleave LIVE even while the primary sits
            # SILENT in a tool-loop (the prior version only drained on a
            # primary delta). Per-agent buffered + checkpoint-flushed
            # (🤝 <agent>: ...) so N concurrent agents stay readable.
            _ev_q: "asyncio.Queue" = asyncio.Queue()
            _sec_bufs: dict = {}
            _sec_last: dict = {}

            def _flush_sec(force: bool = False) -> list:
                out: list = []
                _now = time.time()
                for _nm in list(_sec_bufs.keys()):
                    _buf = _sec_bufs.get(_nm, "")
                    if not _buf.strip():
                        continue
                    if force or (_now - _sec_last.get(_nm, 0.0) >= _ckpt_s):
                        out.append(_flush_reasoning(f"\n🤝 {_nm}: {_buf}"))
                        _sec_bufs[_nm] = ""
                        _sec_last[_nm] = _now
                return out

            def _pump_sec(force: bool = False) -> list:
                # Non-blocking pull of queued secondary fragments into the
                # per-agent buffers, for the post-primary phases where the
                # main merged loop is no longer draining the queue.
                while True:
                    try:
                        ev = _ev_q.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                    if ev and ev[0] == "SF":
                        _sec_bufs[ev[1]] = _sec_bufs.get(ev[1], "") + ev[2]
                return _flush_sec(force)

            async def _primary_pump():
                # Stream the primary (Hermes) in the BACKGROUND, pushing typed
                # events onto _ev_q; a PD sentinel marks end-of-stream so the
                # merged drain loop knows the primary is finished.
                try:
                    async with client.stream(
                            "POST",
                            f"{target_endpoint}/chat/completions",
                            content=json.dumps(stream_body).encode("utf-8"),
                            headers=headers) as resp:
                        if resp.status_code != 200:
                            await resp.aread()
                            log.warning("streamed backend %s",
                                        resp.status_code)
                        else:
                            async for line in resp.aiter_lines():
                                if not line or not line.startswith("data:"):
                                    continue
                                data = line[5:].strip()
                                if data == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(data)
                                except (json.JSONDecodeError, ValueError):
                                    continue
                                ch = chunk.get("choices") or []
                                if not ch:
                                    continue
                                delta = ch[0].get("delta") or {}
                                piece = delta.get("content") or ""
                                if piece:
                                    _ev_q.put_nowait(("PR", piece))
                                for _tc in (delta.get("tool_calls") or []):
                                    _fn = (_tc.get("function") or {}).get("name")
                                    if _fn:
                                        _ev_q.put_nowait(("PT", _fn))
                except Exception as e:
                    log.warning("streamed backend call failed: %s", e)
                finally:
                    _ev_q.put_nowait(("PD", None))

            _sec_tasks = []
            for _n, _c in _fanout:
                # context = the secondary's ROLE/specialty (why it's engaged on
                # this turn); council members all answer the same prompt, so the
                # role is the relevant per-node step context.
                yield _node_status(chat_id=chat_id, model=model, name=_n,
                                   cfg=_c, state="engage",
                                   context=str(_c.get("role", "")))
                _sec_tasks.append(asyncio.create_task(
                    _call_agent_stream(_n, _c, proxy_body, headers, client,
                                       _ev_q)))
            _prim_task = asyncio.create_task(_primary_pump())
            # Per-secondary ✅/💤 emitted LIVE as each fan-out task FINISHES
            # (operator 2026-05-23: "emitters per-step compute, not all at
            # once"). Was a burst after the post-primary gather. Records each
            # result so the post-loop merge reuses it (no second emit).
            _sec_meta = list(_fanout)
            _sec_done_emitted: set = set()
            _sec_results: dict = {}

            def _finished_sec_status() -> list:
                _o: list = []
                for _ti, _t in enumerate(_sec_tasks):
                    if _t in _sec_done_emitted or not _t.done():
                        continue
                    _sec_done_emitted.add(_t)
                    _mn, _mc = _sec_meta[_ti]
                    try:
                        _rn, _rt = _t.result()
                    except Exception:
                        _rn, _rt = _mn, ""
                    _sec_results[_mn] = (_rn, _rt)
                    _o.append(_node_status(
                        chat_id=chat_id, model=model, name=_mn, cfg=_mc,
                        state="ok" if (_rt and _rt.strip()) else "down"))
                return _o

            # Drain the MERGED queue until the primary signals done. Primary
            # reasoning + tool steps and secondary fragments interleave LIVE,
            # whichever source is producing. The pending get() is KEPT across
            # idle timeouts (never cancelled) so no event -- including a piece
            # of the primary `raw` -- is ever dropped by a wait_for race.
            _primary_done = False
            _get_task = None
            while not _primary_done:
                if _get_task is None:
                    _get_task = asyncio.ensure_future(_ev_q.get())
                _done, _ = await asyncio.wait({_get_task}, timeout=2.0)
                # Stream ✅/💤 for any secondary that JUST finished -- per-step
                # live, interleaved with the primary, not a burst at the end.
                for _b in _finished_sec_status():
                    yield _b
                if not _done:
                    for _b in _flush_sec():
                        yield _b
                    yield b": keepalive\n\n"
                    continue
                ev = _get_task.result()
                _get_task = None
                _k = ev[0]
                if _k == "PR":
                    raw += ev[1]
                    _block_buf += ev[1]
                    if (_block_buf.strip()
                            and time.time() - _last_flush >= _ckpt_s):
                        yield _flush_reasoning(_block_buf)
                        _block_buf = ""
                        _last_flush = time.time()
                    for _b in _flush_sec():
                        yield _b
                elif _k == "PT":
                    _fn = ev[1]
                    _block_buf += f"\n🛠️ {_fn}\n"
                    if _fn not in _tools_called:
                        _tools_called.append(_fn)
                    yield _sse_status(chat_id=chat_id, model=model,
                                      emoji="🛠️", label="", detail=_fn)
                    for _b in _flush_sec():
                        yield _b
                elif _k == "SF":
                    _sec_bufs[ev[1]] = _sec_bufs.get(ev[1], "") + ev[2]
                    for _b in _flush_sec():
                        yield _b
                elif _k == "PD":
                    _primary_done = True
            # Flush the tail of the reasoning buffer. No </details> to close --
            # reasoning_content is a separate delta channel, not inline markup.
            if _block_buf.strip():
                yield _flush_reasoning(_block_buf)
            # CONFIRMATION ENGINE (operator 2026-05-22): run the
            # Definition-of-Done check NOW -- on the agent's just-finished
            # answer + the verbs it invoked -- BEFORE the heavy critic
            # re-pass. The check writes the authoritative
            # user_query_(un)satisfied verdict polish reads downstream.
            # When the turn is CONFIRMED satisfied (the agent acted and
            # delivered an answer, no recorded tool failed), the chain
            # HALTS here: the critic is SKIPPED. The critic re-litigates a
            # done answer and can flip a confirmed success into a false
            # failure -- the mios-os-control "succeeds early then reports
            # failed after a long chain" bug. Only re-critique an
            # UNCONFIRMED / unsatisfied turn, where a corrective pass is
            # actually warranted.
            _verdict = await _inline_satisfaction_check(
                session_id, refined,
                agent_tools_called=_tools_called,
                agent_answered=bool(raw.strip()))
            _confirmed = bool(
                _verdict
                and _verdict.get("kind") == "user_query_satisfied")
            if _confirmed:
                # Halt: surface the confirmation in the live dropdown so
                # the operator sees the chain stopped on success, not on a
                # timeout. Glyph-only, locale-neutral.
                yield _flush_reasoning("\n✅\n")
            else:
                # Critic->refiner (heavy agent path; fires only when the
                # turn is NOT confirmed satisfied): if the DCI critic
                # challenges this answer, revise it ONCE before polish.
                # No-op for short answers + when the critic is happy.
                # Heartbeat-wrap it: the DCI critic runs on a possibly-
                # contended lane and may re-invoke Hermes (5-40s); a bare
                # await went silent (operator 2026-05-20). Robust: returns
                # the original `raw` on any error.
                critic_task = asyncio.create_task(_critic_refine_agent(
                    raw, last_user_text, refined, session_id,
                    client=client, target_endpoint=target_endpoint,
                    headers=headers, base_body=proxy_body))
                while not critic_task.done():
                    try:
                        await asyncio.wait_for(
                            asyncio.shield(critic_task), timeout=2.0)
                    except asyncio.TimeoutError:
                        for _b in _pump_sec():
                            yield _b
                        yield b": keepalive\n\n"
                    except Exception:
                        break
                try:
                    raw = critic_task.result()
                except Exception:
                    pass  # keep the pre-critic raw on any failure
            # Collect the concurrent fan-out agents (operator 2026-05-21):
            # they ran alongside the primary, so this await adds little. Each
            # secondary's work surfaces in the reasoning dropdown and merges
            # into the polish input so the final answer SYNTHESISES all agents.
            raw_for_polish = raw
            # Roster of contributing agents (primary + ok secondaries) -- used
            # by the generative synthesis emit + the dropdown summary. Always
            # defined (even with no secondaries) so polish-time refs are safe.
            _roster = [(target_name, "ok")]
            if _sec_tasks:
                while not all(t.done() for t in _sec_tasks):
                    try:
                        await asyncio.wait_for(
                            asyncio.shield(asyncio.gather(
                                *_sec_tasks, return_exceptions=True)),
                            timeout=2.0)
                    except asyncio.TimeoutError:
                        for _b in _pump_sec():
                            yield _b
                        yield b": keepalive\n\n"
                    except Exception:
                        break
                # Flush tail fragments + emit ✅/💤 for any FINAL straggler
                # secondary (finished after the primary; most already streamed
                # their status live during the drain loop above).
                for _b in _pump_sec(force=True):
                    yield _b
                for _b in _finished_sec_status():
                    yield _b
                # Build the polish merge from the per-secondary results that the
                # live-status helper recorded (status already emitted -> no
                # duplicate _node_status here; their text already streamed into
                # the dropdown via the merged queue, so we fold text only).
                _merge = []
                for _mn, _mc in _sec_meta:
                    _sn, _stext = _sec_results.get(_mn, (_mn, ""))
                    if _stext and _stext.strip():
                        _merge.append(f"[{_sn} agent]:\n{_stext.strip()}")
                        _scratchpad_note(_sn, _stext, phase="council")
                        _roster.append((_mn, "ok"))
                    else:
                        _roster.append((_mn, "down"))
                # Final dropdown summary line (the per-node ✅/💤 already streamed
                # live, per-step; this is just the at-a-glance recap).
                yield _flush_reasoning(
                    "\n🛰️ swarm: " + " · ".join(
                        f"{_nm} {'✅' if _st == 'ok' else '💤'}"
                        for _nm, _st in _roster) + "\n")
                if _merge:
                    raw_for_polish = (raw + "\n\n" + "\n\n".join(_merge)).strip()
            # (Satisfaction verdict already written by the confirmation
            # engine above, BEFORE the critic gate, so polish's recent-
            # verdicts block sees THIS turn's authoritative verdict.)
            if raw.strip():
                # Skip the (slow CPU) polish when the sub-agent's answer
                # is ALREADY clean -- no <think>-tag leakage and not
                # absurdly long. Hermes usually formats its answer well,
                # so re-writing it just burns the CPU polish lane, which
                # was timing out 45s on an already-clean answer (operator
                # 2026-05-20 "slight refactor"). Polish only messy raw.
                # Polish PREPARES the final user-facing answer from the
                # sub-agent's think blocks -- "Hermes doesn't create the
                # final answer EVER" (operator 2026-05-20). So it ALWAYS
                # runs; it's fast now on the 4b dGPU lane. Heartbeat-
                # wrapped so the SSE stream stays alive during it.
                # Live status across the otherwise-silent ~8s synthesis pass:
                # name the agents actually being synthesised (generative, not a
                # static label) -- operator 2026-05-22 "emits are generative
                # live to the tasks being done".
                yield _sse_status(
                    chat_id=chat_id, model=model, emoji="🧬",
                    label=" + ".join(_nm for _nm, _st in _roster if _st == "ok"))
                polish_task = asyncio.create_task(polish_response(
                    raw_for_polish, refined, session_id=session_id,
                    original_user_text=last_user_text,
                    persona_system=_persona_system,
                    agent_tools=_tools_called))
                while not polish_task.done():
                    try:
                        await asyncio.wait_for(
                            asyncio.shield(polish_task), timeout=8.0)
                    except asyncio.TimeoutError:
                        yield b": keepalive\n\n"
                    except Exception:
                        break
                try:
                    polished = polish_task.result()
                except Exception:
                    polished = None
                # The sub-agent's FULL raw work -- its responses, prints,
                # AND reasoning -- goes into the collapsed
                # <details type="reasoning"> dropdown (operator binding:
                # 'sub-agent responses and prints and thinking is all
                # printed to thinking'). The POLISHED clean answer is the
                # main reply. <think>-family tag MARKERS are unwrapped
                # (content kept, readable) so reasoning shows in the
                # dropdown instead of bleeding inline or being discarded.
                dropdown_content = _THINK_ORPHAN_RE.sub("", raw).strip()
                answer_only = _strip_think_tags(raw)
                polished_clean = (
                    _strip_think_tags(polished) if polished else ""
                )
                main = polished_clean.strip() or answer_only.strip()
                preamble = ""
                if (isinstance(refined, dict)
                        and refined.get("_multi_task_queue")):
                    preamble = _multi_task_preamble(
                        refined["_multi_task_queue"],
                        int(refined.get(
                            "_multi_task_active_idx", 0)),
                    )
                # Show the dropdown whenever the sub-agent's work is more
                # than the bare answer (reasoning/prints present, or polish
                # reshaped it). When the raw IS already the clean answer,
                # skip the dropdown (no double-render).
                # agent-pipe emits ONLY the clean polished answer. The
                # live thinking dropdown is owned by the OWUI pipe, which
                # streams the AI's actual work from the hermes-tail
                # (generative, live) -- operator 2026-05-20: "pure streamed
                # + generative, nothing hardcoded". No post-hoc wrap here
                # (that wrap caused the "answered twice" duplication).
                wrapped = f"{preamble}{main}"
            else:
                # Upstream returned nothing usable (HTTP error,
                # truncated, etc.). Emit a brief warning marker so
                # the operator gets visible feedback instead of an
                # empty turn. Localised by glyph alone.
                wrapped = "⚠️"
            yield _sse_chunk("", chat_id=chat_id, model=model,
                             role="assistant")
            async for _ab in _stream_answer(wrapped, chat_id=chat_id,
                                            model=model):
                yield _ab
            yield _sse_status_phase(chat_id=chat_id, model=model,
                                    phase="subagent_done", done=True)
            yield _sse_chunk("", chat_id=chat_id, model=model,
                             finish_reason="stop")
            yield _sse_done()
        return StreamingResponse(_stream_backend(),
                                 media_type="text/event-stream")
    client = await _get_client()
    # Council fan-out on the NON-streaming path too (operator 2026-05-22
    # "every prompt/query/request"): kick the secondaries CONCURRENTLY with
    # the primary call so a stream:false request (external OpenAI clients)
    # gets the SAME multi-agent council as the streamed OWUI path instead of
    # Hermes-only. Their answers merge into the polish input below. Best-
    # effort; CPU twins offload to :11435, dead endpoints drop to ''.
    _sec_tasks = [
        asyncio.create_task(
            _call_agent_complete(_n, _c, proxy_body, headers, client))
        for _n, _c in _fanout
    ]
    try:
        r = await client.post(
            f"{target_endpoint}/chat/completions",
            content=proxy_bytes, headers=headers,
        )
        try:
            backend_json = r.json()
        except (json.JSONDecodeError, ValueError):
            for _t in _sec_tasks:
                _t.cancel()
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
        # Drain + collect the concurrent council secondaries; merged into
        # the polish input below so the final answer SYNTHESISES all agents
        # (the non-streaming twin of the streamed 🤝 merge).
        _merge: list = []
        if _sec_tasks:
            for _res in await asyncio.gather(*_sec_tasks,
                                             return_exceptions=True):
                if (isinstance(_res, tuple) and _res[1]
                        and str(_res[1]).strip()):
                    _merge.append(f"[{_res[0]} agent]:\n{str(_res[1]).strip()}")
                    _scratchpad_note(_res[0], str(_res[1]), phase="council")
        # Polish the assistant content when refine produced an
        # intended_outcome. Skip on streaming, on empty responses,
        # and on backend errors. The raw sub-agent output is
        # preserved as a collapsed <details type="reasoning">
        # block ABOVE the polished answer -- operator directive
        # 2026-05-18: "all sub-agents tasked by MiOS-Agent have
        # their printing and patterns/responses they end up
        # printing to the user -- is all written to the OWUI
        # thinking blocks/OWUI dropdown for thoughts".
        log.info(
            "polish-gate: enabled=%s refined=%s status=%s json=%s",
            POLISH_ENABLED, bool(refined), r.status_code,
            isinstance(backend_json, dict),
        )
        if (POLISH_ENABLED and refined and r.status_code == 200
                and isinstance(backend_json, dict)):
            choices = backend_json.get("choices") or []
            if choices:
                msg = choices[0].get("message") or {}
                raw = str(msg.get("content") or "")
                log.info("polish-gate: raw_len=%d refined_outcome=%s",
                         len(raw),
                         (refined.get("intended_outcome") or "")[:60])
                # CONFIRMATION ENGINE (operator 2026-05-22) -- same gate
                # as the streaming branch above. Capture the verbs the
                # sub-agent invoked (final-message tool_calls), run the
                # Definition-of-Done check FIRST, and SKIP the critic
                # re-pass on a confirmed-satisfied turn so a succeeded
                # verb isn't re-litigated into a false failure.
                _tools_called = [
                    (tc.get("function") or {}).get("name")
                    for tc in (msg.get("tool_calls") or [])
                    if (tc.get("function") or {}).get("name")
                ]
                _verdict = await _inline_satisfaction_check(
                    session_id, refined,
                    agent_tools_called=_tools_called,
                    agent_answered=bool(raw.strip()))
                _confirmed = bool(
                    _verdict
                    and _verdict.get("kind") == "user_query_satisfied")
                if not _confirmed:
                    raw = await _critic_refine_agent(
                        raw, last_user_text, refined, session_id,
                        client=client, target_endpoint=target_endpoint,
                        headers=headers, base_body=proxy_body)
                raw_for_polish = (
                    (raw + "\n\n" + "\n\n".join(_merge)).strip()
                    if _merge else raw)
                if raw_for_polish.strip():
                    polished = await polish_response(
                        raw_for_polish, refined, session_id=session_id,
                        original_user_text=last_user_text,
                        persona_system=_persona_system,
                        agent_tools=_tools_called)
                    # qwen3 reasoning models occasionally leak
                    # <think>...</think> blocks past /no_think; strip
                    # them from BOTH the dropdown content and the
                    # polished main content so neither carries the
                    # internal CoT through to the operator.
                    # Sub-agent FULL raw work (responses + prints +
                    # reasoning) -> collapsed dropdown; polished clean
                    # answer -> main. Mirrors the streaming branch +
                    # operator binding: all sub-agent output goes to the
                    # thinking dropdown. Tag MARKERS unwrapped so the
                    # reasoning is readable, not bleeding inline.
                    dropdown_content = _THINK_ORPHAN_RE.sub("", raw).strip()
                    answer_only = _strip_think_tags(raw)
                    polished_clean = (
                        _strip_think_tags(polished) if polished else ""
                    )
                    main = polished_clean.strip() or answer_only.strip()
                    # Multi-task: prepend the queue preamble so the
                    # operator sees "started X; queued Y, Z" before
                    # the polished answer for task #1.
                    preamble = ""
                    if (isinstance(refined, dict)
                            and refined.get("_multi_task_queue")):
                        preamble = _multi_task_preamble(
                            refined["_multi_task_queue"],
                            int(refined.get(
                                "_multi_task_active_idx", 0)),
                        )
                    # Show the dropdown whenever the sub-agent's work is
                    # more than the bare answer; else just the clean main.
                    # agent-pipe emits ONLY the clean polished answer; the
                    # OWUI pipe owns the live thinking dropdown (streamed
                    # from the hermes-tail). No post-hoc wrap (it caused
                    # the "answered twice" duplication). Operator 2026-05-20.
                    wrapped = f"{preamble}{main}"
                    polish_ok = bool(polished_clean.strip())
                    msg["content"] = wrapped
                    choices[0]["message"] = msg
                    backend_json["choices"] = choices
                    _db_fire(_db_post(_db_create("event", {
                        "source": "mios-agent-pipe",
                        "kind": "polish",
                        "severity": "info" if polish_ok else "warn",
                        "summary": f"{target_name} "
                                   f"{'polished' if polish_ok else 'wrapped (polish no-op)'}",
                        "payload": {
                            "target_agent": target_name,
                            "raw_len": len(raw),
                            "polished_len": len(polished_clean),
                            "polish_ok": polish_ok,
                        },
                    }, now_fields=("ts",))))
        return JSONResponse(content=backend_json, status_code=r.status_code)
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
