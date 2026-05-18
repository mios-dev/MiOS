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
        _db_fire(_db_post(_db_create("event", {
            "source": "mios-agent-pipe",
            "kind": "dissent",
            "severity": "warn",
            "summary": f"unresolved {d['act']} ({d['confidence']:.2f})",
            "payload": {
                "persona": d.get("persona"),
                "content": (d.get("content") or "")[:500],
                "session": session_id,
            },
        }, now_fields=("ts",))))
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
}

# Domains that are part of the operator's own infrastructure -- a
# verb opening these is NOT a taint source. Anything else
# constitutes a "we exposed the agent to untrusted external state"
# event and the tool_call gets tainted=true (the URL itself didn't
# return content, but the operator's screen now shows external
# content the agent might subsequently react to).
_ALLOWLIST_HOSTS = {
    "localhost", "127.0.0.1", "::1",
    "host.containers.internal",
    "mios-ollama", "mios-open-webui", "mios-hermes", "mios-surrealdb",
    "mios-forge", "mios-searxng", "mios-code-server",
}


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
    Returns (tainted, reason). Currently scoped to open_url; future
    web/RAG verbs add their own cases."""
    if tool == "open_url":
        url = str((args or {}).get("url", ""))
        if _is_external_url(url):
            return True, f"external_open_url:{url[:80]}"
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
    "through to the backend agent (which has tool-calling itself).\n"
    "\n"
    "Available verbs (use EXACT name + args shape -- the dispatcher\n"
    "rejects unknown verbs):\n"
    '  open_app(name, position="default"?)        -- LAUNCH an app\n'
    '  launch_app(name)                          -- simpler launch\n'
    '  focus_window(title, position="default"?)  -- raise + reposition\n'
    '  move_window(title, position)              -- move existing\n'
    '  close_window(title, mode="graceful"?)     -- close\n'
    '  open_url(url, browser?)                   -- open in browser\n'
    '  list_windows()                            -- enumerate windows\n'
    '  screen_layout()                           -- monitor geometry\n'
    '  mios_find(name)                           -- resolve, no launch\n'
    '  mios_apps(filter?)                        -- inventory\n'
    '  everything_search(query, limit=10?, ext?) -- Windows FS search\n'
    '  fs_search(query, limit=20?, ext?, path?, type?)  -- Linux FS\n'
    '  system_status()                           -- host snapshot\n'
    '  service_status(name)                      -- systemctl status\n'
    '  service_restart(name)                     -- systemctl restart\n'
    '  process_list(filter?, sort="rss"?, limit=20?)\n'
    '  container_status(name?)                   -- podman ps\n'
    '  container_restart(name)                   -- podman restart\n'
    '  pc_type(text)                             -- type into focused window\n'
    '  pc_key(key)                               -- press key OR "Ctrl+S" combo\n'
    '  pc_click(x, y, button="left"?)            -- mouse click at coords\n'
    "\n"
    "Rules:\n"
    "- Linearize when possible: each node depends only on its predecessor.\n"
    "- For 'open X and do Y' chains: open_app -> focus_window -> action.\n"
    "- The focus_window step is OFTEN needed before pc_type / pc_key so\n"
    "  the input reaches the right window.\n"
    "- Use pc_key with 'Ctrl+S', 'Alt+F4', 'Enter', 'Tab' as appropriate.\n"
    "- Cap your DAG at " + str(PLANNER_MAX_NODES) + " nodes.\n"
    "- If the user asked for something AMBIGUOUS or requiring web/agent\n"
    "  reasoning, return empty nodes -- the backend agent handles it.\n"
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
            },
        },
        "broker_sock": LAUNCHER_SOCK,
        "broker_present": os.path.exists(LAUNCHER_SOCK),
        "db_url": DB_URL,
        "port": PORT,
    }


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
                # Phase B.1: fire the DCI Challenger critic post-
                # dispatch. Fire-and-forget so the chat reply isn't
                # delayed; the act is written to SurrealDB event
                # (kind=dci_act) for the audit log. Phase B.2 will
                # consume these to drive the 4-persona convergent
                # flow + bring high-confidence challenges back into
                # the operator-facing response.
                if DCI_ENABLED:
                    _db_fire(dci_critic_pass(
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
