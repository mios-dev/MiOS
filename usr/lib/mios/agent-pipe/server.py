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
# Router runs the micro-LLM classifier (qwen3:1.7b) on the iGPU lane
# (mios-ollama-igpu at :11435) -- isolates micro-LLM workload from the
# dGPU/CUDA queue so router latency stays sub-second even when big-model
# inference is saturating :11434. Falls back to the CUDA-ollama lane
# if the iGPU instance is down (operator override via the env).
ROUTER_ENDPOINT = os.environ.get(
    "MIOS_AGENT_PIPE_ROUTER_ENDPOINT", "http://localhost:11435"
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
REFINE_MODEL = os.environ.get("MIOS_REFINE_MODEL", "qwen3:1.7b")
REFINE_ENDPOINT = os.environ.get(
    "MIOS_REFINE_ENDPOINT", ROUTER_ENDPOINT,
).rstrip("/")
REFINE_TIMEOUT_S = int(os.environ.get("MIOS_REFINE_TIMEOUT_S", "12"))
REFINE_MAX_TOKENS = int(os.environ.get("MIOS_REFINE_MAX_TOKENS", "400"))
REFINE_BYPASS_CHARS = int(os.environ.get("MIOS_REFINE_BYPASS_CHARS", "24"))

POLISH_ENABLED = os.environ.get(
    "MIOS_POLISH_ENABLE", "true",
).lower() not in {"false", "0", "no"}
POLISH_MODEL = os.environ.get("MIOS_POLISH_MODEL", "qwen3:1.7b")
POLISH_ENDPOINT = os.environ.get(
    "MIOS_POLISH_ENDPOINT", ROUTER_ENDPOINT,
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
    toml_path = os.environ.get("MIOS_TOML", "/usr/share/mios/mios.toml")
    try:
        try:
            import tomllib  # py311+
        except ImportError:
            import tomli as tomllib  # fallback (Fedora <= py310)
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
        agents = data.get("agents") or {}
        for name, cfg in agents.items():
            if not isinstance(cfg, dict):
                continue
            registry[name] = {
                "endpoint": str(cfg.get("endpoint", "")).rstrip("/"),
                "model":    str(cfg.get("model", name)),
                "role":     str(cfg.get("role", "general")),
                "default":  bool(cfg.get("default", False)),
                "strengths": list(cfg.get("strengths") or []),
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
    '        "priority":         1   // lower runs first; 1..N\n'
    '      }, ...\n'
    '    ]\n'
    '  }\n'
    "\n"
    "Intent classification:\n"
    "  chat        -- greeting, thanks, single-turn conversation; no system\n"
    "                 effect needed; emit `reply` and no agent is called.\n"
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
)


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
    if _is_trivial_bypass(user_text):
        return None
    # Pull the registered agents into the prompt so the model picks
    # one that actually exists.
    agents_summary = "\n".join(
        f"  - {n}: role={c.get('role','?')} "
        f"strengths={','.join(c.get('strengths') or [])[:80]}"
        for n, c in _AGENT_REGISTRY.items()
    )
    # qwen3 family applies the `/no_think` token to suppress chain-
    # of-thought emission when it appears in EITHER the system or
    # the latest user turn. The model still reasons internally but
    # emits the answer directly without a <think> block. ~3x faster
    # on CPU + reliably fits the JSON answer in the token budget.
    system = (_REFINE_SYSTEM
              + "\nRegistered sub-agents:\n" + agents_summary
              + "\n\n/no_think")
    msgs = [{"role": "system", "content": system}]
    # Last 4 turns of history for context (small to stay fast).
    if history:
        for h in history[-4:]:
            if isinstance(h, dict) and h.get("role") in ("user", "assistant"):
                msgs.append({"role": h["role"],
                             "content": str(h.get("content", ""))[:600]})
    # qwen3 family is a reasoning model -- by default it produces a
    # long <think>...</think> chain-of-thought BEFORE the JSON
    # answer. For refine we want the JSON only; the `/no_think` user-
    # message suffix disables reasoning per-request. Drops latency
    # ~3x on CPU + reliably fits answer in REFINE_MAX_TOKENS.
    msgs.append({"role": "user", "content": user_text[:2000] + " /no_think"})
    payload = {
        "model": REFINE_MODEL,
        "messages": msgs,
        "response_format": {"type": "json_object"},
        "temperature": 0.0,
        "max_tokens": REFINE_MAX_TOKENS,
        "stream": False,
    }
    url = f"{REFINE_ENDPOINT}/v1/chat/completions"
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
    choices = body.get("choices") or []
    if not choices:
        log.warning("refine: %.1fs no_choices", elapsed)
        return None
    content = ((choices[0].get("message") or {}).get("content") or "").strip()
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
            parsed.pop("tasks", None)
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
    "You are MiOS-Agent's polish pass. The raw answer below came\n"
    "from a sub-agent. Your job: produce the FINAL user-facing\n"
    "response by re-shaping the raw answer to match the intended\n"
    "outcome -- nothing more. Be tight; do not add new content;\n"
    "do not editorialise; do not say `the agent says`. Strip\n"
    "internal reasoning leaks (lines like `Thought:`, `Reasoning:`,\n"
    "`Plan:`, tool-call envelopes, JSON thinking blocks). Locale-\n"
    "neutralise any stray English when the original user prompt\n"
    "was in another language.\n"
    "\n"
    "CRITICAL ground-truth rule: the TOOL HISTORY below records\n"
    "what actually happened in the agent's execution environment.\n"
    "When a tool call has success=false, the user-facing answer\n"
    "MUST acknowledge the failure -- do NOT paraphrase as success.\n"
    "When the sub-agent's draft contradicts the tool history\n"
    "(claims a launch succeeded when the tool returned failure,\n"
    "invents an unrelated error not present in any tool stderr,\n"
    "fabricates a `move command failed` explanation when the\n"
    "intent was `open app`), REWRITE the answer to surface the\n"
    "ACTUAL failure mode from the tool stderr.\n"
    "\n"
    "Output the polished answer ONLY -- no prose around it,\n"
    "no JSON envelope.\n"
)


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


async def polish_response(raw_text: str,
                          refined: Optional[dict],
                          session_id: Optional[str] = None) -> Optional[str]:
    """Polish a sub-agent's raw response into the final user-facing
    answer. Returns the polished string or None on error (caller
    keeps the raw answer).

    When session_id is supplied, the polish prompt receives the
    recent tool_call history as ground truth. The CRITICAL rule in
    _POLISH_SYSTEM tells the model to REWRITE the response when it
    contradicts the tool history (Operator-flagged 2026-05-18:
    'open nautilus' -> assistant claimed 'The move command failed
    because the destination directory wasn't writable' -- a
    completely fabricated unrelated error)."""
    if not POLISH_ENABLED or not raw_text or not raw_text.strip():
        return None
    intended = (refined or {}).get("intended_outcome", "") or ""
    user_q = (refined or {}).get("refined_text", "") or ""
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
    system = _POLISH_SYSTEM + (
        f"\nIntended outcome: {intended}\n" if intended else ""
    )
    hist_block = _format_tool_history(tool_history)
    # Phase E.1d: also fold in mios-daemon's satisfaction verdicts so
    # polish has the daemon's AND-folded ground truth available
    # alongside the raw tool_call rows. The daemon verdict is the
    # MOST AUTHORITATIVE signal (it cross-checks multiple sources);
    # raw tool_calls are still useful for the per-step detail.
    sat_verdicts = await _recent_satisfaction_verdicts(limit=3)
    sat_block = _format_satisfaction_block(sat_verdicts)
    # `/no_think` to disable qwen3 reasoning (same rationale as refine).
    user_msg_parts = [f"User's question:\n{user_q}"]
    if sat_block:
        user_msg_parts.append(sat_block)
    if hist_block:
        user_msg_parts.append(hist_block)
    user_msg_parts.append(f"Raw answer from sub-agent:\n{raw_text[:8000]}")
    user_msg_parts.append("/no_think")
    user_msg = "\n\n".join(user_msg_parts)
    payload = {
        "model": POLISH_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user_msg},
        ],
        "temperature": 0.0,
        "max_tokens": POLISH_MAX_TOKENS,
        "stream": False,
    }
    url = f"{POLISH_ENDPOINT}/v1/chat/completions"
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
    choices = body.get("choices") or []
    if not choices:
        return None
    polished = ((choices[0].get("message") or {}).get("content") or "").strip()
    if not polished:
        return None
    return polished


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

async def pkg_lookup(phrase: str) -> Optional[dict]:
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
    results: list[dict] = []
    failures: list[str] = []
    for idx, step in enumerate(steps):
        verb = (step or {}).get("verb") or ""
        raw_args = (step or {}).get("args") or {}
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
                f"SELECT id FROM tool_call "
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
    "Mirror the user's language. Output JSON ONLY -- no preamble,\n"
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
        "Mirror the operator's language. Output JSON ONLY shaped:\n"
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
    "Output shape (EXACT):\n"
    '{"action":"decompose",\n'
    ' "summary": "<one-line plan in user\'s language>",\n'
    ' "nodes": [\n'
    '   {"id":"n1","tool":"<verb>","args":{...},"deps":[]},\n'
    '   {"id":"n2","tool":"<verb>","args":{...},"deps":["n1"]},\n'
    '   ...\n'
    ' ]}\n'
    "\n"
    "If you cannot decompose into AT LEAST 2 dispatchable verbs, emit\n"
    '{"action":"decompose","summary":"","nodes":[]} so the chain falls\n'
    "through to the backend sub-agent (Hermes / OpenCode / etc.) which\n"
    "has tool-calling + web access itself.\n"
    "\n"
    "Available verbs (use EXACT name + args shape -- the dispatcher\n"
    "rejects unknown verbs):\n"
    "\n"
    "  ── Window / app launch ──\n"
    '  open_app(name, position="default"?)        -- LAUNCH an app\n'
    '  launch_app(name)                          -- simpler launch\n'
    '  focus_window(title, position="default"?)  -- raise + reposition\n'
    '  move_window(title, position)              -- semantic move (left/right/center/...)\n'
    '  position_window(title, x, y)              -- literal pixel coords\n'
    '  resize_window(title, width, height)       -- pixel WxH\n'
    '  minimize_window(title) / maximize_window(title) / restore_window(title)\n'
    '  close_window(title, mode="graceful"?)     -- close\n'
    '  open_url(url, browser?)                   -- open in browser\n'
    '  list_windows()                            -- enumerate windows\n'
    '  screen_layout()                           -- monitor geometry\n'
    "\n"
    "  ── Discovery / resolution ──\n"
    '  mios_find(name)                           -- resolve, no launch\n'
    '  mios_apps(filter?)                        -- INVENTORY all installed apps\n'
    '  everything_search(query, limit=10?, ext?) -- Windows FS search\n'
    '  fs_search(query, limit=20?, ext?, path?, type?)  -- Linux FS\n'
    '  pkg_lookup(phrase)                        -- Personal KG alias -> app\n'
    "\n"
    "  ── PC input ──\n"
    '  pc_type(text) / pc_key(key) / pc_click(x, y, button="left"?)\n'
    "\n"
    "  ── Text editor (native; replaces pc_type+pc_key save chain) ──\n"
    '  text_view(path, start?, end?)             -- read file / list dir\n'
    '  text_create(path, content)                -- new file\n'
    '  text_str_replace(path, old, new)          -- exact replace\n'
    '  text_insert(path, line, content)          -- insert after line\n'
    "\n"
    "  ── Package management ──\n"
    '  winget_search(query, limit?) / winget_list() / winget_show(id)\n'
    '  winget_install(id) / winget_upgrade(id?) / winget_uninstall(id)\n'
    '  flatpak_search(query, limit?) / flatpak_list() / flatpak_show(id)\n'
    '  flatpak_install(id, scope?) / flatpak_upgrade(id?) / flatpak_uninstall(id)\n'
    '  flatpak_preflight(id)                     -- probe sandbox BEFORE launch\n'
    "\n"
    "  ── System ──\n"
    '  system_status() / service_status(name) / service_restart(name)\n'
    '  process_list(filter?, sort="rss"?, limit=20?)\n'
    '  container_status(name?) / container_restart(name)\n'
    "\n"
    "  ── Windows-side shell ──\n"
    '  powershell_run(script, timeout=30?, work_dir?)  -- arbitrary PS\n'
    "\n"
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
    error / unparseable response."""
    if not PLANNER_ENABLED or not user_text or not user_text.strip():
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
    # Validate each node has the required fields + a known verb.
    for n in nodes:
        if not isinstance(n, dict):
            return None
        if "id" not in n or "tool" not in n:
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


async def execute_dag(dag: dict, *, session_id: Optional[str]) -> dict:
    """Topologically execute the DAG nodes via the broker. Reflexion
    cap (default 2) retries failed nodes before marking dag-fail.
    Returns aggregate {success, node_results[], summary}. Each node
    result is the standard tool_call shape from dispatch_mios_verb."""
    nodes = _topological_order(dag.get("nodes") or [])
    results: list[dict] = []
    all_ok = True
    for node in nodes:
        nid = str(node.get("id", "?"))
        tool = str(node.get("tool", "")).strip()
        args = node.get("args") or {}
        attempt = 0
        last_result: dict = {}
        while attempt <= PLANNER_REFLEXION_CAP:
            # Phase A.3: forward session_id so the firewall pre-check
            # can see upstream taint.
            last_result = await dispatch_mios_verb(
                tool, args, session_id=session_id,
            )
            if last_result.get("success"):
                break
            attempt += 1
            if attempt <= PLANNER_REFLEXION_CAP:
                # Brief backoff before retry; gives transient WSL/
                # broker/Win32 racing windows time to settle.
                await asyncio.sleep(0.5)
        node_result = dict(last_result)
        node_result["node_id"] = nid
        node_result["attempts"] = attempt + (1 if last_result.get("success") and attempt == 0 else 0)
        results.append(node_result)
        # SurrealDB tool_call row per node, linked to session.
        # Phase A.3: include taint state so the firewall + downstream
        # critics see the propagation chain.
        _row = {
            "tool": tool,
            "args": args if isinstance(args, dict) else {},
            "result_preview": (last_result.get("output") or "")[:500],
            "success": bool(last_result.get("success")),
            "latency_ms": int(last_result.get("latency_ms", 0)),
            "tainted": bool(last_result.get("tainted")),
            "taint_reason": (last_result.get("taint_reason") or "") or None,
        }
        if session_id:
            _db_fire(_db_post(
                _db_create("tool_call", _row, now_fields=("ts",)).rstrip(";")
                + f", session = {session_id};"
            ))
        else:
            _db_fire(_db_post(_db_create("tool_call", _row,
                                         now_fields=("ts",))))
        if not last_result.get("success"):
            all_ok = False
            # Stop on first hard failure (deps not satisfied, etc.).
            # Future enhancement: prune ONLY the failed branch and
            # continue independent siblings; for now fail-fast.
            break
    return {
        "success": all_ok,
        "summary": dag.get("summary", ""),
        "nodes_total": len(nodes),
        "nodes_executed": len(results),
        "node_results": results,
    }


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
        return "mios-pc-control window-list --json"
    # ── Window-state verbs (Phase D.3 -- PC-control template) ──
    # All five wrap `mios-window <subcmd>` which resolves the title
    # pattern to an hwnd internally; the agent only needs to supply
    # a substring match. Title patterns are quoted via shlex so
    # spaces / special chars in window titles ("Task Manager",
    # "VS Code - foo.py") survive the broker round-trip.
    if tool == "minimize_window":
        title = shlex.quote(str(args.get("title", "")))
        return f"mios-window minimize {title}"
    if tool == "maximize_window":
        title = shlex.quote(str(args.get("title", "")))
        return f"mios-window maximize {title}"
    if tool == "restore_window":
        title = shlex.quote(str(args.get("title", "")))
        return f"mios-window restore {title}"
    if tool == "resize_window":
        title = shlex.quote(str(args.get("title", "")))
        w = int(args.get("width", 0))
        h = int(args.get("height", 0))
        if w <= 0 or h <= 0:
            return None
        return f"mios-window resize {title} {w} {h}"
    if tool == "position_window":
        # Distinct from move_window: this takes LITERAL pixel coords
        # (x, y) instead of a semantic position name ("center" /
        # "top-right" / ...). Use when the agent has already done
        # screen_layout reasoning and knows where the window should
        # land precisely.
        title = shlex.quote(str(args.get("title", "")))
        x = int(args.get("x", 0))
        y = int(args.get("y", 0))
        return f"mios-window move {title} {x} {y}"
    # ── Package management (Phase D.4 -- winget + flatpak surfaces) ──
    # Both shims emit JSON envelopes by default; agent-pipe surfaces
    # the JSON straight back to the gateway. WRITE verbs (install /
    # upgrade / uninstall) are firewall-gated.
    if tool == "winget_search":
        q = shlex.quote(str(args.get("query", "")))
        n = int(args.get("limit", 10))
        return f"mios-winget search {q} -n {n}"
    if tool == "winget_list":
        return "mios-winget list"
    if tool == "winget_show":
        pid = shlex.quote(str(args.get("id", "")))
        return f"mios-winget show {pid}"
    if tool == "winget_install":
        pid = shlex.quote(str(args.get("id", "")))
        return f"mios-winget install {pid}"
    if tool == "winget_upgrade":
        pid = str(args.get("id", "")).strip()
        if not pid or pid.lower() == "all" or pid == "--all":
            return "mios-winget upgrade --all"
        return f"mios-winget upgrade {shlex.quote(pid)}"
    if tool == "winget_uninstall":
        pid = shlex.quote(str(args.get("id", "")))
        return f"mios-winget uninstall {pid}"
    if tool == "flatpak_search":
        q = shlex.quote(str(args.get("query", "")))
        n = int(args.get("limit", 10))
        return f"mios-flatpak search {q} -n {n}"
    if tool == "flatpak_list":
        return "mios-flatpak list"
    if tool == "flatpak_show":
        pid = shlex.quote(str(args.get("id", "")))
        return f"mios-flatpak show {pid}"
    if tool == "flatpak_install":
        pid = shlex.quote(str(args.get("id", "")))
        scope = str(args.get("scope", "")).lower()
        scope_arg = ""
        if scope in ("system", "--system"):
            scope_arg = " --system"
        elif scope in ("user", "--user"):
            scope_arg = " --user"
        return f"mios-flatpak install {pid}{scope_arg}"
    if tool == "flatpak_upgrade":
        pid = str(args.get("id", "")).strip()
        if not pid or pid.lower() == "all" or pid == "--all":
            return "mios-flatpak upgrade --all"
        return f"mios-flatpak upgrade {shlex.quote(pid)}"
    if tool == "flatpak_uninstall":
        pid = shlex.quote(str(args.get("id", "")))
        return f"mios-flatpak uninstall {pid}"
    if tool == "flatpak_preflight":
        # Cheap sandbox probe -- exits 0 if the flatpak's bubblewrap
        # sandbox bootstraps cleanly, exit 1 + structured error_kind
        # otherwise. Agents call BEFORE open_app/open_url for a
        # flatpak target so they fail-fast on broken environments
        # (WSL portal-helper credential issues, /dev/dxg sandbox
        # rejection, etc.) instead of looping on doomed launches.
        pid = shlex.quote(str(args.get("id", "")))
        return f"mios-flatpak-preflight {pid}"
    if tool == "screen_layout":
        return "mios-pc-control screen-layout"
    if tool == "open_url":
        url = shlex.quote(str(args.get("url", "")))
        browser = args.get("browser") or ""
        return f"mios-open-url {url}" + (
            f" {shlex.quote(str(browser))}" if browser else "")
    if tool == "mios_find":
        # --json -> {ok, query, resolved:{launch, source}, error?,
        # stderr_preview?}. Polish-grounding consumes typed fields
        # instead of grepping the prose `launch` line.
        return f"mios-find --json {shlex.quote(str(args.get('name', '')))}"
    if tool == "mios_apps":
        # --json -> NDJSON inventory (one app per line: short_name /
        # app_id / source / label / launch_hint). Same shape mios-pkg
        # bootstrap consumes; the polish pass + the games-research
        # path read app_id directly instead of grepping prose.
        f = args.get("filter") or ""
        return "mios-apps --json" + (f" --filter {shlex.quote(str(f))}" if f else "")
    if tool == "everything_search":
        q = shlex.quote(str(args.get("query", "")))
        n = int(args.get("limit", 10))
        ext = args.get("ext") or ""
        cmd = f"mios-everything --json -n {n} {q}"
        if ext:
            cmd += f" -ext {shlex.quote(str(ext))}"
        return cmd
    if tool == "fs_search":
        q = shlex.quote(str(args.get("query", "")))
        n = int(args.get("limit", 20))
        ext = args.get("ext") or ""
        path = args.get("path") or ""
        type_filter = args.get("type") or ""
        # --json -> structured {ok, count, results:[{path,name,ext}]}
        cmd = f"mios-locate --json -n {n} {q}"
        if ext:
            cmd += f" -ext {shlex.quote(str(ext))}"
        if path:
            cmd += f" -path {shlex.quote(str(path))}"
        if type_filter in ("f", "d"):
            cmd += f" -type {type_filter}"
        return cmd
    if tool == "system_status":
        # Already emits a JSON blob by default (see mios-system-status
        # docstring -- single structured object the agent reads verbatim).
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
    # ── PC-input verbs (Phase A.1 -- needed for DAG chains like
    # open_app -> focus_window -> pc_type -> pc_key Ctrl+S) ──
    if tool == "pc_type":
        text = shlex.quote(str(args.get("text", "")))
        return f"mios-pc-control type {text}"
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
    if tool == "text_view":
        path = shlex.quote(str(args.get("path", "")))
        cmd = f"mios-text-edit view {path}"
        start = args.get("start")
        end = args.get("end")
        if start is not None:
            cmd += f" --start {int(start)}"
        if end is not None:
            cmd += f" --end {int(end)}"
        return cmd
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


async def dispatch_mios_verb(
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


# ── /pkg/lookup (Phase C.1 Personal Knowledge Graph) ───────────────
# Resolve a phrase via the operator's preference graph. Returns
# the matched app_install record (alias-resolved or direct).
# Operator-callable curl-test endpoint; the planner can also hit
# it pre-decomposition to ground noun phrases.
@app.get("/pkg/lookup")
async def pkg_lookup_endpoint(phrase: str = "") -> JSONResponse:
    if not phrase:
        return JSONResponse(
            content={"error": "phrase query param required"},
            status_code=400,
        )
    result = await pkg_lookup(phrase)
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
    if (refined and refined.get("intent") == "chat"
            and str(refined.get("reply") or "").strip()):
        reply = str(refined["reply"]).strip()
        log.info("refine short-circuit: chat reply (no router/backend)")
        if streaming:
            async def _stream_refine_chat() -> AsyncGenerator[bytes, None]:
                yield _sse_status(chat_id=chat_id, model=model,
                                  emoji="📡", label="prompt")
                yield _sse_status(chat_id=chat_id, model=model,
                                  emoji="✨", label="refine")
                yield _sse_chunk("", chat_id=chat_id, model=model,
                                 role="assistant")
                yield _sse_chunk(reply, chat_id=chat_id, model=model)
                yield _sse_status(chat_id=chat_id, model=model,
                                  emoji="💬", label="chat", done=True)
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

    # Run the layer-1 router. Verdict possibilities:
    #   {"action":"dispatch","tool":"<name>","args":{...}}
    #   {"action":"chat","reply":"<text>"}
    #   {"action":"agent","reason":"..."}
    # The router still runs even when refine produced a verdict --
    # the dispatch-shape extraction (tool + args) needs the layer-1
    # JSON shape which refine's `intent=dispatch` doesn't populate
    # directly. Refine + router are complementary, not redundant.
    verdict = await classify_intent(last_user_text)
    # Carry refined hints into verdict so downstream branches
    # (dispatch / agent / DAG) can read them.
    if verdict and refined:
        verdict["_refined"] = refined
    # When refine classified as `agent` but the router missed,
    # promote refine's verdict so we proxy to the right sub-agent
    # instead of falling through to default-Hermes blindly.
    if not verdict and refined and refined.get("intent") in ("agent", "dag"):
        verdict = {"action": "agent", "reason": "refine-classified",
                   "_refined": refined}

    if verdict:
        action = verdict.get("action")

        # ── DISPATCH fast-path ──────────────────────────────────
        if action == "dispatch":
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

        # action == "agent" -> planner gets a chance to decompose
        # into a DAG of dispatch verbs (Phase A.1). If the planner
        # returns >=2 actionable nodes, run the DAG locally; if it
        # returns empty or fails, fall through to the backend proxy
        # which has Hermes's full tool-calling agent loop available.
        if action == "agent" and PLANNER_ENABLED:
            dag = await decompose_intent(last_user_text)
            if dag and (dag.get("nodes") or []):
                if streaming:
                    async def _stream_dag() -> AsyncGenerator[bytes, None]:
                        yield _sse_status(chat_id=chat_id, model=model,
                                          emoji="📡", label="prompt")
                        yield _sse_status(chat_id=chat_id, model=model,
                                          emoji="🧭", label="route")
                        yield _sse_status(chat_id=chat_id, model=model,
                                          emoji="📋", label="plan")
                        yield _sse_chunk("", chat_id=chat_id, model=model,
                                         role="assistant")
                        # Emit per-node markers + execute.
                        nodes = _topological_order(dag.get("nodes") or [])
                        results: list[dict] = []
                        all_ok = True
                        for node in nodes:
                            nid = str(node.get("id", "?"))
                            tool = str(node.get("tool", "")).strip()
                            args = node.get("args") or {}
                            yield _sse_status(
                                chat_id=chat_id, model=model,
                                emoji="🛠️", label=f"{nid}:{tool}",
                            )
                            attempt = 0
                            last_result: dict = {}
                            while attempt <= PLANNER_REFLEXION_CAP:
                                last_result = await dispatch_mios_verb(
                                    tool, args, session_id=session_id,
                                )
                                if last_result.get("success"):
                                    break
                                attempt += 1
                                if attempt <= PLANNER_REFLEXION_CAP:
                                    await asyncio.sleep(0.5)
                            nres = dict(last_result)
                            nres["node_id"] = nid
                            results.append(nres)
                            _row = {
                                "tool": tool,
                                "args": args if isinstance(args, dict) else {},
                                "result_preview": (last_result.get("output") or "")[:500],
                                "success": bool(last_result.get("success")),
                                "latency_ms": int(last_result.get("latency_ms", 0)),
                                "tainted": bool(last_result.get("tainted")),
                                "taint_reason": (last_result.get("taint_reason") or "") or None,
                            }
                            if session_id:
                                _db_fire(_db_post(
                                    _db_create("tool_call", _row, now_fields=("ts",)).rstrip(";")
                                    + f", session = {session_id};"
                                ))
                            else:
                                _db_fire(_db_post(_db_create(
                                    "tool_call", _row, now_fields=("ts",))))
                            if not last_result.get("success"):
                                all_ok = False
                                break
                        # Render the DAG envelope as collapsible.
                        env = {
                            "dag": {
                                "summary": dag.get("summary", ""),
                                "nodes_total": len(nodes),
                                "nodes_executed": len(results),
                                "success": all_ok,
                            },
                            "nodes": results,
                        }
                        symbol = "✅" if all_ok else "⚠️"
                        rendered = (
                            f"<details type=\"tool_calls\" done=\"true\">\n"
                            f"<summary>{symbol} dag · {len(nodes)} steps</summary>\n\n"
                            f"```json\n{json.dumps(env, indent=2, default=str)}\n```\n"
                            f"</details>"
                        )
                        yield _sse_chunk(rendered, chat_id=chat_id, model=model)
                        yield _sse_status(chat_id=chat_id, model=model,
                                          emoji=symbol, label="dag", done=True)
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
    if not verdict and PLANNER_ENABLED:
        dag = await decompose_intent(last_user_text)
        if dag and (dag.get("nodes") or []):
            # Re-enter the streaming DAG path by simulating
            # action=agent. Build inline so we don't duplicate logic.
            nodes = _topological_order(dag.get("nodes") or [])
            if streaming:
                async def _stream_dag2() -> AsyncGenerator[bytes, None]:
                    yield _sse_status(chat_id=chat_id, model=model,
                                      emoji="📡", label="prompt")
                    yield _sse_status(chat_id=chat_id, model=model,
                                      emoji="📋", label="plan")
                    yield _sse_chunk("", chat_id=chat_id, model=model,
                                     role="assistant")
                    results: list[dict] = []
                    all_ok = True
                    for node in nodes:
                        nid = str(node.get("id", "?"))
                        tool = str(node.get("tool", "")).strip()
                        args = node.get("args") or {}
                        yield _sse_status(
                            chat_id=chat_id, model=model,
                            emoji="🛠️", label=f"{nid}:{tool}",
                        )
                        attempt = 0
                        last_result: dict = {}
                        while attempt <= PLANNER_REFLEXION_CAP:
                            last_result = await dispatch_mios_verb(
                                tool, args, session_id=session_id,
                            )
                            if last_result.get("success"):
                                break
                            attempt += 1
                            if attempt <= PLANNER_REFLEXION_CAP:
                                await asyncio.sleep(0.5)
                        nres = dict(last_result)
                        nres["node_id"] = nid
                        results.append(nres)
                        # Phase A.3: also write the tool_call row in
                        # this no-verdict streaming path so the firewall
                        # can see taint chains on planner-only runs.
                        _row = {
                            "tool": tool,
                            "args": args if isinstance(args, dict) else {},
                            "result_preview": (last_result.get("output") or "")[:500],
                            "success": bool(last_result.get("success")),
                            "latency_ms": int(last_result.get("latency_ms", 0)),
                            "tainted": bool(last_result.get("tainted")),
                            "taint_reason": (last_result.get("taint_reason") or "") or None,
                        }
                        if session_id:
                            _db_fire(_db_post(
                                _db_create("tool_call", _row, now_fields=("ts",)).rstrip(";")
                                + f", session = {session_id};"
                            ))
                        else:
                            _db_fire(_db_post(_db_create(
                                "tool_call", _row, now_fields=("ts",))))
                        if not last_result.get("success"):
                            all_ok = False
                            break
                    env = {
                        "dag": {
                            "summary": dag.get("summary", ""),
                            "nodes_total": len(nodes),
                            "nodes_executed": len(results),
                            "success": all_ok,
                        },
                        "nodes": results,
                    }
                    symbol = "✅" if all_ok else "⚠️"
                    rendered = (
                        f"<details type=\"tool_calls\" done=\"true\">\n"
                        f"<summary>{symbol} dag · {len(nodes)} steps</summary>\n\n"
                        f"```json\n{json.dumps(env, indent=2, default=str)}\n```\n"
                        f"</details>"
                    )
                    yield _sse_chunk(rendered, chat_id=chat_id, model=model)
                    yield _sse_status(chat_id=chat_id, model=model,
                                      emoji=symbol, label="dag", done=True)
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
    target_label = f"→ {target_name}"

    # Build the proxy body: original messages + hint-injected
    # system prefix (only when refine emitted hints; trivial inputs
    # skip refine + skip the prefix).
    proxy_body = dict(body)
    if refined and (refined.get("hint_tools") or refined.get("hint_skills")
                    or refined.get("intended_outcome")):
        hint_msg = _build_agent_hint(refined, target_name)
        proxy_body["messages"] = [{"role": "system", "content": hint_msg}] + list(messages)
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
    # Self-inject bearer when caller didn't supply one + we have a
    # key from /etc/mios/hermes/api.env (or env override). Lets
    # direct callers (curl, MCP clients, future Discord) reach
    # Hermes without each gateway re-implementing the auth flow.
    if "authorization" not in headers and _BACKEND_KEY:
        headers["authorization"] = f"Bearer {_BACKEND_KEY}"

    if streaming:
        async def _stream_backend() -> AsyncGenerator[bytes, None]:
            yield _sse_status(chat_id=chat_id, model=model,
                              emoji="📡", label="prompt")
            if refined:
                yield _sse_status(chat_id=chat_id, model=model,
                                  emoji="✨", label="refine")
            yield _sse_status(chat_id=chat_id, model=model,
                              emoji="🧭", label="route")
            yield _sse_status(chat_id=chat_id, model=model,
                              emoji="🤖", label=target_label)
            client = await _get_client()
            async with client.stream(
                "POST", f"{target_endpoint}/chat/completions",
                content=proxy_bytes, headers=headers,
            ) as r:
                async for chunk in r.aiter_bytes():
                    if chunk:
                        yield chunk
        return StreamingResponse(_stream_backend(),
                                 media_type="text/event-stream")
    client = await _get_client()
    try:
        r = await client.post(
            f"{target_endpoint}/chat/completions",
            content=proxy_bytes, headers=headers,
        )
        try:
            backend_json = r.json()
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
                if raw.strip():
                    polished = await polish_response(
                        raw, refined, session_id=session_id)
                    if polished and polished.strip() != raw.strip():
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
                        # Render: collapsible "thoughts" with the raw
                        # sub-agent output, then the polished answer
                        # as the main visible content.
                        wrapped = (
                            f"<details type=\"reasoning\">"
                            f"<summary>🤖 {target_name}</summary>\n\n"
                            f"{raw}\n"
                            f"</details>\n\n"
                            f"{preamble}{polished}"
                        )
                        msg["content"] = wrapped
                        choices[0]["message"] = msg
                        backend_json["choices"] = choices
                        _db_fire(_db_post(_db_create("event", {
                            "source": "mios-agent-pipe",
                            "kind": "polish",
                            "severity": "info",
                            "summary": f"{target_name} polished",
                            "payload": {
                                "target_agent": target_name,
                                "raw_len": len(raw),
                                "polished_len": len(polished),
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
