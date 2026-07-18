# AI-hint: Pure config-constant + SSOT-reader layer extracted from server.py (refactor WS R1). Module-level env/literal-derived constants (PORT, MCP_SERVER_PORT, _LIGHT_BASE, BACKEND/_BACKEND_IS_LIGHT/BACKEND_MODEL/_BACKEND_HOSTPORT, _HERMES_ENDPOINT/_HERMES_WORKER_ENDPOINT, _AUTH_HOSTPORTS, _AGENT_AUTH_BY_HOSTPORT, CLIENT_TOOLS_PASSTHROUGH, _TOOL_BACKEND*, _HEAVY_PROBE_TTL, _INGRESS_KEY, _STACK_MODEL/_MICRO_*) plus the layered mios.toml readers (_toml_section, _cfg_num, _dispatch_toml/_DISPATCH_TOML/_dispatch_num). Pure: stdlib (os, logging, tomllib/tomli) only -- NO import of server (one-way boundary, 38-drift-checks.sh check 6). server.py re-imports every name verbatim (surface-parity zero-diff); runtime-coupled fns (_apply_outbound_auth/_heavy_lane_up/_lane_resolver/_pick_tool_backend) STAY in server.py and call these re-imported readers/constants.
# AI-related: ./server.py, ./test_mios_config.py, ./mios_surface.py, /usr/share/mios/mios.toml
# AI-functions: _toml_section, _cfg_num, _dispatch_toml, _dispatch_num
"""Pure config constants + SSOT mios.toml readers (extracted from server.py).

Moved verbatim from ``server.py`` (refactor R1); the module is pure (stdlib only
-- ``os`` / ``logging`` / lazily-imported ``tomllib``) and ``server.py`` re-imports
every name so its importable surface is unchanged. ``mios_config`` MUST NOT import
``server`` (the one-way boundary enforced by ``38-drift-checks.sh`` check 6).
"""

from __future__ import annotations

import logging
import os

# Same logger name server.py uses, so log output is byte-identical post-extraction.
log = logging.getLogger("mios-agent-pipe")


def _toml_section(section: str) -> dict:
    """Layered <section> table from mios.toml (vendor <- /etc <- ~/.config)
    or from PostgreSQL config tables (behind the db_authoritative sentinel)."""
    try:
        import sys
        lib_path = "/usr/lib/mios"
        if not os.path.exists(lib_path):
            lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        if lib_path not in sys.path:
            sys.path.insert(0, lib_path)
        import mios_db_config
        out = mios_db_config.section(None, section) or {}
    except Exception as e:
        log.warning("Failed to load overlay config section %s: %s", section, e)
        out = {}
        
    def _xpand(v):
        if isinstance(v, str):
            return os.path.expandvars(v) if "$" in v else v
        if isinstance(v, dict):
            return {k: _xpand(x) for k, x in v.items()}
        if isinstance(v, list):
            return [_xpand(x) for x in v]
        return v
    return _xpand(out)


def _cfg_num(table: dict, env: str, key: str, default, cast=int):
    """Resolve a numeric tunable: env override -> table[key] -> literal default.
    Preserves a legit 0 (unlike a bare `or` chain)."""
    v = os.environ.get(env)
    if v not in (None, ""):
        try:
            return cast(v)
        except (ValueError, TypeError):
            pass
    v = table.get(key)
    if v is not None:
        try:
            return cast(v)
        except (ValueError, TypeError):
            pass
    return default


def _dispatch_toml() -> dict:
    """Layered [dispatch] table from mios.toml (vendor <- /etc <- ~/.config)
    or from PostgreSQL config tables (behind the db_authoritative sentinel)."""
    try:
        import sys
        lib_path = "/usr/lib/mios"
        if not os.path.exists(lib_path):
            lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        if lib_path not in sys.path:
            sys.path.insert(0, lib_path)
        import mios_db_config
        return mios_db_config.section(None, "dispatch") or {}
    except Exception as e:
        log.warning("Failed to load overlay config for dispatch: %s", e)
        return {}


_DISPATCH_TOML = _dispatch_toml()


def _dispatch_num(env: str, key: str, default, cast=int):
    """Resolve a numeric tunable: env override -> mios.toml [dispatch].<key> ->
    literal default. Unlike a bare `a or b or default` chain this PRESERVES a
    legitimate 0 (e.g. dag_node_retry = 0 = no retry)."""
    v = os.environ.get(env)
    if v not in (None, ""):
        try:
            return cast(v)
        except (ValueError, TypeError):
            pass
    v = _DISPATCH_TOML.get(key)
    if v is not None:
        try:
            return cast(v)
        except (ValueError, TypeError):
            pass
    return default


PORT = int(os.environ.get("MIOS_PORT_AGENT_PIPE", "8640"))
# MCP server port (SSOT, no-hardcode): the AGNTCY manifest
# advertised a hardcoded :8765. Reuse the canonical precedence from
# mios-mcp-server (MIOS_PORT_MCP -> MIOS_MCP_PORT -> 8765 default).
MCP_SERVER_PORT = int(os.environ.get("MIOS_PORT_MCP")
                      or os.environ.get("MIOS_MCP_PORT") or "8460")
# WS-0B: ONE owned light-lane base. The mios-llm-light port was hardcoded as the
# literal `http://localhost:11450` in ~10 endpoint defaults below (drift). Derive
# it ONCE from the [ports].llm_light SSOT key (MIOS_PORT_LLM_LIGHT via install.env;
# default 8450) so a port change is a single edit; each endpoint still honors its
# explicit MIOS_*_ENDPOINT override first.
_LIGHT_BASE = "http://localhost:" + (os.environ.get("MIOS_PORT_LLM_LIGHT") or "8450")
# WS-0B: the agent-pipe's reasoning backend. An explicit MIOS_AGENT_PIPE_BACKEND URL
# wins; else when the deployment opts into reasoning DIRECTLY on the light lane
# (MIOS_AGENT_PIPE_BACKEND_LIGHT -- the operator "EVERYTHING IS LLAMA.CPP, bypass
# Hermes" directive) compose it from the ONE owned light-lane base (no port literal
# in the unit); else front Hermes on :8642 (the original design default).
BACKEND = (os.environ.get("MIOS_AGENT_PIPE_BACKEND")
           or (_LIGHT_BASE + "/v1"
               if (os.environ.get("MIOS_AGENT_PIPE_BACKEND_LIGHT") or "").strip().lower()
                  in {"1", "true", "yes", "on"}
               else f"http://localhost:{os.environ.get('MIOS_PORT_HERMES', '8642')}/v1")).rstrip("/")
# True when the reasoning backend is the light llama.cpp lane DIRECTLY (the
# BACKEND_LIGHT "bypass Hermes" deployment), so callers know the primary endpoint
# is llama.cpp -- which 200-accepts but SILENTLY IGNORES tool_choice='required'.
# Hermes (:8642) is an OpenAI gateway that DOES honor it, so this stays False then.
_BACKEND_IS_LIGHT = (
    (os.environ.get("MIOS_AGENT_PIPE_BACKEND_LIGHT") or "").strip().lower()
    in {"1", "true", "yes", "on"}
    and not (os.environ.get("MIOS_AGENT_PIPE_BACKEND") or "").strip())
BACKEND_MODEL = (os.environ.get("MIOS_AGENT_PIPE_BACKEND_MODEL")
                 or os.environ.get("MIOS_AI_MODEL")   # WS-0B: ONE owned key = [ai].model
                 or "hermes-agent")
# host:port of the Hermes backend -- used to scope the bearer key so the
# fanout/DAG agent path authenticates to Hermes (which enforces it) without
# leaking the key to other local agents (swarm non-answer:
# hermes facets 401'd in the swarm because the key was never attached).
_BACKEND_HOSTPORT = BACKEND.split("://")[-1].split("/")[0]
# Endpoints that ENFORCE the bearer key. Always includes the configured
# BACKEND; ALSO the Hermes gateway, whose host:port differs from BACKEND when
# MIOS_AGENT_PIPE_BACKEND is repointed at a keyless local lane (mios-llm-light on
# :8450) while Hermes still runs on its own port (:8642). Scoping the key to
# this SET (not just BACKEND) keeps non-streaming hermes dispatch (swarm /
# council / DAG facets) authenticated instead of silently 401'ing -- the
# regression of the "hermes facets 401'd in the swarm" fix once
# BACKEND moved off :8642.. SSOT: same :8642 default as
# BACKEND above and mios.toml [agents.hermes].endpoint; env-overridable.
_HERMES_ENDPOINT = (os.environ.get("MIOS_HERMES_ENDPOINT")
                    or _toml_section("hermes").get("endpoint")
                    or f"http://localhost:{os.environ.get('MIOS_PORT_HERMES', '8642')}/v1").rstrip("/")
# P1 : the hermes WORKER on :8643 (hermes-worker.service) is the
# [agents.hermes].endpoint dispatch target now, and it REQUIRES API_SERVER_KEY auth
# (it rejected the pipe's probes with "invalid API key" until added here). Scope the
# backend key to it too so swarm/council/DAG hermes dispatch authenticates. SSOT env-
# overridable; same :8643 default as the worker unit's API_SERVER_PORT.
_HERMES_WORKER_ENDPOINT = (os.environ.get("MIOS_HERMES_WORKER_ENDPOINT")
                           or _toml_section("agents").get("hermes", {}).get("endpoint")
                           or f"http://localhost:{os.environ.get('MIOS_PORT_HERMES_WORKER', '8643')}/v1").rstrip("/")
_AUTH_HOSTPORTS = {
    _BACKEND_HOSTPORT,
    _HERMES_ENDPOINT.split("://")[-1].split("/")[0],
    _HERMES_WORKER_ENDPOINT.split("://")[-1].split("/")[0],
}

# WS-FED / gap G2 (open agent-agnostic federation): per-agent OUTBOUND credential,
# indexed by endpoint host:port. _load_agent_registry resolves each [agents.*].auth
# header_template (env-expanded) into this map; dispatch attaches it to ANY endpoint
# NOT in _AUTH_HOSTPORTS (the shared-backend-key set) -- so a remote OpenAI /v1
# endpoint (a second MiOS node, a Claude/Gemini/vLLM box) finally gets its OWN
# Authorization header and joins the council by network + credential. Empty until
# an agent declares auth.header_template => byte-identical legacy behaviour.
_AGENT_AUTH_BY_HOSTPORT: dict = {}

# ── Client-side tool-calling passthrough (Zen smart-window) ──
# An external OpenAI client (Zen browser "smart window", an IDE assistant, etc.)
# that supplies its OWN tools[] expects the standard OpenAI contract: the model
# RETURNS tool_calls which the CLIENT executes (Zen's get_page_content /
# get_open_tabs / run_search run IN THE BROWSER) and feeds back as role:tool
# messages. MiOS's orchestration (refine/council/swarm + server-side _VERB_CATALOG
# execution) is the WRONG shape for this -- it drops the client tools as
# "hallucinated", tries to run them server-side (impossible; they live in the
# browser), and never relays tool_calls back. So when a request carries client
# tools, bypass orchestration ENTIRELY and proxy it verbatim to a tool-capable
# backend, relaying tool_calls (SSE deltas + non-stream) unmodified -- the
# structural twin of _vision_complete. Researched + code-grounded
# (workflow zen-clienttools-a2a-research): A2A/passports are the wrong tool here;
# this transparent passthrough is the fix. SSOT: mios.toml [ai].client_tools_*.
# DEDICATED backend knobs (NOT BACKEND/BACKEND_MODEL) so the relay never inherits
# the stale gemma4:12b drift; default granite4.1:8b on the keyless :11450 lane
# (verified tool-capable); repoint to mios-heavy (:11441) for harder routing.
CLIENT_TOOLS_PASSTHROUGH = os.environ.get(
    "MIOS_AGENT_PIPE_CLIENT_TOOLS_PASSTHROUGH", "true"
).strip().lower() in {"1", "true", "yes", "on"}
# WS-0B: _LIGHT_BASE (the ONE owned light-lane base) is defined above, before BACKEND.
_TOOL_BACKEND = os.environ.get(
    "MIOS_AGENT_PIPE_TOOL_BACKEND", _LIGHT_BASE + "/v1").rstrip("/")
_TOOL_BACKEND_MODEL = os.environ.get(
    "MIOS_AGENT_PIPE_TOOL_BACKEND_MODEL", "granite4.1:8b")
# Heavy-lane PREFERENCE for the client-tools tool loop (the agentic surface that
# fronts the Hermes desktop app + Zen). The SGLang heavy lane runs a REASONING model
# (Qwen3) -> real thinking + reliable tool-use; the light lane (granite) is weak but
# always-up/low-VRAM. Prefer heavy WHEN it is serving, fall back to light when it is
# down (e.g. gaming/VRAM) -- so "SGLang for all agents" holds when the GPU is free and
# the agentic surface NEVER hard-fails when it isn't. Health probe cached for the TTL.
_TOOL_BACKEND_HEAVY = (os.environ.get("MIOS_AGENT_PIPE_TOOL_BACKEND_HEAVY")
                       or _toml_section("nodes").get("local-sglang", {}).get("endpoint")
                       or f"http://localhost:{os.environ.get('MIOS_PORT_SGLANG', '8442')}/v1").rstrip("/")
_TOOL_BACKEND_HEAVY_MODEL = os.environ.get(
    "MIOS_AGENT_PIPE_TOOL_BACKEND_HEAVY_MODEL", "mios-heavy")
_HEAVY_PROBE_TTL = float(os.environ.get("MIOS_AGENT_PIPE_HEAVY_PROBE_TTL", "30"))

# Optional inbound bearer gate for the passthrough route (a browser CAN send a
# static Authorization header; passports can't gate Zen -- it's keyless). OFF by
# default (unset) so the smart-window works immediately for testing; set the env
# to require a matching client bearer before any tool_calls are returned.
_INGRESS_KEY = os.environ.get("MIOS_AGENT_PIPE_INGRESS_KEY", "").strip()

# Micro-LLM (SSOT: mios.toml [ai].micro_model / micro_endpoint, surfaced
# as MIOS_MICRO_MODEL / MIOS_MICRO_ENDPOINT by userenv.sh). This is the
# always-warm (keep_alive=-1) sub-second classifier. Default repointed
# from qwen3:0.6b-cpu (a dropped 5th base) to qwen3:1.7b -- the
# operator's chosen micro/CPU model in the 4-model set (also the daemon's
# background MODEL + the mios-agent-cpu base). Operator directive
# "we have access to micro-llms for fast refinements too" -- the layer-1
# classifier passes (router + refine) default to this micro-LLM; the bigger
# PLANNER + POLISH passes keep their own (larger) models.
# Unified pipeline reasoning model ("use the large gemma4
# 12b model for the entire stack"). ONE resident model on the dGPU -> no qwen3
# <-> gemma4 swap-thrash, AND far better tool-routing than a 1.7b (the research's
# small-model mis-routing fix -- a 12b picks the right verb among 82). SSOT knob
# MIOS_STACK_MODEL; embeddings + vision keep their own. Every reasoning stage
# below defaults to this single model.
_STACK_MODEL = (os.environ.get("MIOS_STACK_MODEL")        # explicit per-deploy override
                or os.environ.get("MIOS_AI_MODEL")        # WS-0B: ONE owned key = [ai].model (install.env)
                or "granite4.1:8b")  # served brain on :11450 (gemma4:12b retired -> 404;)
_MICRO_MODEL = (os.environ.get("MIOS_MICRO_MODEL")
                or _toml_section("ai").get("micro_model")
                or _STACK_MODEL)
_MICRO_ENDPOINT = (os.environ.get("MIOS_MICRO_ENDPOINT")
                   or _toml_section("ai").get("micro_endpoint")
                   or _LIGHT_BASE + "/v1").rstrip("/")
# Callers below append "/v1/chat/completions"; strip a trailing /v1 so we
# don't double it.
_MICRO_BASE = (_MICRO_ENDPOINT[:-3].rstrip("/")
               if _MICRO_ENDPOINT.endswith("/v1") else _MICRO_ENDPOINT)

# Router (layer-1 micro-LLM classifier) config -- relocated from server.py (R14
# config SSOT). The micro classifier runs on the CPU light-lane, ISOLATED from
# the dGPU queue so router latency stays sub-second even under big-model load.
_LIGHT_LANE = os.environ.get("MIOS_LLM_CPU_ENDPOINT",
                             _LIGHT_BASE).rstrip("/")  # mios-llm-light (WS-0B: one owned port key)
ROUTER_ENABLED = os.environ.get("MIOS_AGENT_PIPE_ROUTER_ENABLED",
                                "true").lower() not in {"false", "0", "no"}
ROUTER_MODEL = os.environ.get("MIOS_AGENT_PIPE_ROUTER_MODEL", _MICRO_MODEL)
ROUTER_ENDPOINT = os.environ.get(
    "MIOS_AGENT_PIPE_ROUTER_ENDPOINT", _LIGHT_LANE
).rstrip("/")
ROUTER_TIMEOUT_S = int(os.environ.get("MIOS_AGENT_PIPE_ROUTER_TIMEOUT_S", "30"))
ROUTER_MAX_TOKENS = int(os.environ.get("MIOS_AGENT_PIPE_ROUTER_MAX_TOKENS", "200"))

# Planner (stage-2 LLM DAG decomposer) config -- relocated from server.py (R14).
PLANNER_ENABLED = os.environ.get(
    "MIOS_AGENT_PIPE_PLANNER_ENABLED", "true",
).lower() not in {"false", "0", "no"}
PLANNER_MODEL = os.environ.get(
    "MIOS_AGENT_PIPE_PLANNER_MODEL", _STACK_MODEL,   # gemma4:12b entire-stack
)
PLANNER_ENDPOINT = os.environ.get(
    # mios-llm-light /v1 (the old :11434 legacy lane default is dead -- G5/G17). Env (SSOT
    # agent-pipe.env) overrides; this is only the fresh-install fallback.
    "MIOS_AGENT_PIPE_PLANNER_ENDPOINT", _LIGHT_BASE,
).rstrip("/")
PLANNER_TIMEOUT_S = int(os.environ.get(
    "MIOS_AGENT_PIPE_PLANNER_TIMEOUT_S", "30"))
PLANNER_MAX_TOKENS = int(os.environ.get(
    # 1536 (was 800): gemma4:12b spends tokens on reasoning_content before the JSON,
    # so a tight budget truncates the decompose to empty -> council dups.
    "MIOS_AGENT_PIPE_PLANNER_MAX_TOKENS", "1536"))
PLANNER_MAX_NODES = int(os.environ.get(
    "MIOS_AGENT_PIPE_PLANNER_MAX_NODES", "8"))
PLANNER_REFLEXION_CAP = int(os.environ.get(
    "MIOS_AGENT_PIPE_PLANNER_REFLEXION_CAP", "2"))

# Router (layer-1) system prompt -- static literal, relocated from server.py (R14).
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

# Refine / Polish (stage iGPU quick passes) config -- relocated from server.py (R14).
REFINE_ENABLED = os.environ.get(
    "MIOS_REFINE_ENABLE", "true",
).lower() not in {"false", "0", "no"}
# Refine CLASSIFIES intent (chat vs agent) -- the decisive routing call; a capable
# general model is worth the latency for correct routing (think=False keeps it fast).
REFINE_MODEL = os.environ.get("MIOS_REFINE_MODEL", _STACK_MODEL)
REFINE_ENDPOINT = os.environ.get(
    "MIOS_REFINE_ENDPOINT", _LIGHT_BASE,  # mios-llm-light (WS-0B: one owned port key)
).rstrip("/")
# 30s (was 12): a COLD dGPU refine measured ~10-12s; warm is 4-6s. 30s only bites a
# genuine cold-reload, where a correct-but-slow classification beats a fast wrong route.
REFINE_TIMEOUT_S = int(os.environ.get("MIOS_REFINE_TIMEOUT_S", "30"))
# 1 retry: a cold-load first call can exceed the deadline; the retry runs warm so an
# OS-action never silently drops to the council on a transient refine timeout.
REFINE_ATTEMPTS = int(os.environ.get("MIOS_REFINE_ATTEMPTS", "2"))
REFINE_MAX_TOKENS = int(os.environ.get("MIOS_REFINE_MAX_TOKENS", "700"))
REFINE_BYPASS_CHARS = int(os.environ.get("MIOS_REFINE_BYPASS_CHARS", "24"))
# Keep the refine model resident between turns (cold ~10s, warm ~0.4s). "30m" frees
# it after idle (VRAM-friendly); -1 pins, a shorter value eases VRAM pressure.
REFINE_KEEP_ALIVE = os.environ.get("MIOS_REFINE_KEEP_ALIVE", "30m")

# Reflect DoD judge examples (R-DH)
_REFLECT_TOML = _toml_section("reflect") or {}
JUDGE_EXAMPLES = os.environ.get(
    "MIOS_REFLECT_JUDGE_EXAMPLES",
    _REFLECT_TOML.get("judge_examples", "a punt, refusal, 'I cannot', or 'where to look'")
)

POLISH_ENABLED = os.environ.get(
    "MIOS_POLISH_ENABLE", "true",
).lower() not in {"false", "0", "no"}
# Polish PREPARES the final answer (the key output step, not cosmetic) -- needs a
# capable + fast model, not the slow CPU lane that timed out.
POLISH_MODEL = os.environ.get("MIOS_POLISH_MODEL", _STACK_MODEL)
POLISH_ENDPOINT = os.environ.get(
    "MIOS_POLISH_ENDPOINT", _LIGHT_BASE,  # mios-llm-light (WS-0B: one owned port key)
).rstrip("/")
POLISH_TIMEOUT_S = int(os.environ.get("MIOS_POLISH_TIMEOUT_S", "15"))
POLISH_MAX_TOKENS = int(os.environ.get("MIOS_POLISH_MAX_TOKENS", "800"))

# ── COUNCIL input-diversity gate (T-047 RouteMoA GAP-1) + confidence-aware
# aggregation bypass (T-048 MOSAIC GAP-2). Both ride the ALREADY-computed 768-d
# nomic council-response embeddings (no extra model calls). Read from [council]
# in mios.toml (env override MIOS_COUNCIL_*); thresholds are cosine cut points.
# DEFAULT-OFF (degrade-open): both off => the council synthesis path is
# byte-identical, so the defaults below are the SAFE values applied when the
# [council] keys are ABSENT.
_COUNCIL_TOML = _toml_section("council") or {}


def _cfg_bool(table: dict, env: str, key: str, default: bool) -> bool:
    """Resolve a boolean tunable: env override -> table[key] -> literal default.
    Truthy set matches the rest of the config layer (1/true/yes/on)."""
    v = os.environ.get(env)
    if v not in (None, ""):
        return v.strip().lower() in {"1", "true", "yes", "on"}
    v = table.get(key)
    if v is not None:
        return str(v).strip().lower() in {"1", "true", "yes", "on"}
    return default


COUNCIL_DIVERSITY_GATE = _cfg_bool(
    _COUNCIL_TOML, "MIOS_COUNCIL_DIVERSITY_GATE", "diversity_gate", False)
COUNCIL_DIVERSITY_THRESHOLD = _cfg_num(
    _COUNCIL_TOML, "MIOS_COUNCIL_DIVERSITY_THRESHOLD", "diversity_threshold",
    0.92, cast=float)
COUNCIL_AGGREGATOR_BYPASS = _cfg_bool(
    _COUNCIL_TOML, "MIOS_COUNCIL_AGGREGATOR_BYPASS", "aggregator_bypass", False)
COUNCIL_AGGREGATOR_BYPASS_THRESHOLD = _cfg_num(
    _COUNCIL_TOML, "MIOS_COUNCIL_AGGREGATOR_BYPASS_THRESHOLD",
    "aggregator_bypass_threshold", 0.95, cast=float)

# Memory / KV Paging Slot Persistence (T-021)
_MEMORY_TOML = _toml_section("memory") or {}
KV_SLOT_PERSIST = (
    os.environ.get("MIOS_KV_SLOT_PERSIST", "").strip().lower() in {"1", "true", "yes"}
    or str(_MEMORY_TOML.get("kv_slot_persist", "true")).strip().lower() in {"1", "true", "yes", "on"}
)


def quote_key(k: str) -> str:
    import re
    if re.match(r"^[A-Za-z0-9_-]+$", k):
        return k
    escaped = k.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def to_toml(d: dict, prefix: list = None) -> str:
    import datetime
    if prefix is None:
        prefix = []
        
    lines = []
    
    # 1. Output non-dict and non-list-of-dict keys first (simple values and lists of scalars)
    for k, v in sorted(d.items()):
        if isinstance(v, dict):
            continue
        if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
            continue
            
        k_str = quote_key(k)
        # Format simple value
        if isinstance(v, bool):
            lines.append(f"{k_str} = {str(v).lower()}")
        elif isinstance(v, (int, float)):
            lines.append(f"{k_str} = {v}")
        elif isinstance(v, str):
            escaped = v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            lines.append(f'{k_str} = "{escaped}"')
        elif isinstance(v, (datetime.datetime, datetime.date, datetime.time)):
            lines.append(f"{k_str} = {v.isoformat()}")
        elif isinstance(v, list):
            list_str = []
            for item in v:
                if isinstance(item, str):
                    escaped_item = item.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
                    list_str.append(f'"{escaped_item}"')
                elif isinstance(item, bool):
                    list_str.append(str(item).lower())
                elif isinstance(item, (int, float)):
                    list_str.append(str(item))
                elif isinstance(item, (datetime.datetime, datetime.date, datetime.time)):
                    list_str.append(item.isoformat())
                else:
                    raise TypeError(f"Unsupported list item type: {type(item)}")
            lines.append(f"{k_str} = [{', '.join(list_str)}]")
        elif v is None:
            continue
        else:
            raise TypeError(f"Unsupported TOML type: {type(v)}")
            
    # 2. Output dictionaries (sub-tables) next
    for k, v in sorted(d.items()):
        if isinstance(v, dict):
            new_prefix = prefix + [k]
            sect_name = ".".join(quote_key(p) for p in new_prefix)
            lines.append(f"\n[{sect_name}]")
            lines.append(to_toml(v, new_prefix))
            
    # 3. Output lists of dictionaries (array of tables) last
    for k, v in sorted(d.items()):
        if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
            new_prefix = prefix + [k]
            sect_name = ".".join(quote_key(p) for p in new_prefix)
            for item in v:
                lines.append(f"\n[[{sect_name}]]")
                lines.append(to_toml(item, new_prefix))
                
    return "\n".join(lines)


# ── WS-CONFIG server-side SAFETY validation ──────────────────────────────
# Run by POST /portal/config AFTER the parse-check and BEFORE the atomic write.
# This is deliberately a small SAFETY NET (a handful of critical invariants),
# NOT a full schema -- mios.toml is intentionally flexible, so anything not on
# this allowlist is left alone. It exists to stop a save that would BRICK the
# deploy: dropping a critical section the live config has, an absurd payload
# size, a blanked identity, or a nonsense port. Returns (ok, errors) where
# `ok` is True with an empty list only when the config is safe to write.
_VALIDATE_MAX_BYTES = 2 * 1024 * 1024  # 2 MB payload cap
# Sections whose LOSS bricks the deploy. If the live config carries one of
# these, the replacement must carry it too.
_VALIDATE_CRITICAL_SECTIONS = ("identity", "ports")


def validate_config(toml_text: str, live_config: dict = None):
    """SAFETY-validate a posted mios.toml replacement.

    Args:
        toml_text: the raw replacement TOML text (already parse-checked by the
            caller, but re-parsed here so this helper is standalone/testable).
        live_config: the current live merged config dict (used ONLY to detect a
            DROPPED critical section). Omit / pass None to skip the drop check
            (degrade-open: if the live config can't be read we don't block).

    Returns:
        (ok: bool, errors: list[str]). ``ok`` is True with an empty ``errors``
        list when the config is safe to write.
    """
    errors: list = []

    # (b) size cap -- reject an absurd payload before doing any more work.
    try:
        size = len(toml_text.encode("utf-8"))
    except Exception:
        size = len(toml_text or "")
    if size > _VALIDATE_MAX_BYTES:
        return (False, [f"Config too large: {size} bytes exceeds the "
                        f"{_VALIDATE_MAX_BYTES}-byte (2 MB) safety cap."])

    # Parse standalone so the helper is testable in isolation.
    try:
        import tomllib as _toml
    except ImportError:
        import tomli as _toml  # type: ignore
    try:
        parsed = _toml.loads(toml_text)
    except Exception as e:
        return (False, [f"Invalid TOML: {e}"])

    # (a) do not DROP a critical section the live config currently has.
    live = live_config if isinstance(live_config, dict) else {}
    for sec in _VALIDATE_CRITICAL_SECTIONS:
        live_sec = live.get(sec)
        if isinstance(live_sec, dict) and live_sec:
            new_sec = parsed.get(sec)
            if not isinstance(new_sec, dict) or not new_sec:
                errors.append(
                    f"Refusing to drop critical [{sec}] section -- it is "
                    f"present in the live config and losing it bricks the deploy.")

    # (c1) identity.mios_user must not be blanked when present.
    identity = parsed.get("identity")
    if isinstance(identity, dict) and "mios_user" in identity:
        mu = identity.get("mios_user")
        if not isinstance(mu, str) or not mu.strip():
            errors.append("[identity].mios_user must be a non-empty string.")

    # (c2) every [ports].* scalar must be an integer in 1..65535.
    ports = parsed.get("ports")
    if isinstance(ports, dict):
        for k, v in ports.items():
            if k == "stack_id":
                continue
            if isinstance(v, (dict, list)):
                continue  # nested table -- not a port scalar; leave it alone
            # bool is an int subclass in Python -- exclude it explicitly.
            if isinstance(v, bool) or not isinstance(v, int):
                errors.append(
                    f"[ports].{k} must be an integer 1-65535 (got {v!r}).")
            elif not (1 <= v <= 65535):
                errors.append(
                    f"[ports].{k} = {v} is out of the valid 1-65535 range.")

    return (len(errors) == 0, errors)


def write_user_config(cfg: dict, dest_path: str = None) -> None:
    """Atomically write the dictionary to the user-layer config file."""
    base_cfg = {}
    try:
        import sys
        if "/usr/lib/mios" not in sys.path:
            sys.path.insert(0, "/usr/lib/mios")
        import mios_toml
        vendor, vendor_d, host, host_d, user, user_d = mios_toml._tier_dirs()
        paths = ([vendor] + mios_toml._frags(vendor_d)
                 + [host] + mios_toml._frags(host_d))
        for p in paths:
            mios_toml.deep_merge(base_cfg, mios_toml._load_one(p))
    except Exception:
        pass

    def _dict_diff(new_dict: dict, base_dict: dict) -> dict:
        diff = {}
        for k, v in new_dict.items():
            if k not in base_dict:
                diff[k] = v
            elif isinstance(v, dict) and isinstance(base_dict[k], dict):
                sub_diff = _dict_diff(v, base_dict[k])
                if sub_diff:
                    diff[k] = sub_diff
            elif v != base_dict[k]:
                diff[k] = v
        return diff

    delta_cfg = _dict_diff(cfg, base_cfg)

    if dest_path is None:
        try:
            import mios_toml
            dest_path = mios_toml.USER
        except Exception:
            dest_path = os.path.expanduser("~/.config/mios/mios.toml")
            
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    temp_path = dest_path + ".tmp"
    toml_str = to_toml(delta_cfg)
    with open(temp_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(toml_str)
    os.replace(temp_path, dest_path)

    # Invalidate configuration caches on write
    try:
        import mios_toml
        mios_toml.clear_cache()
    except Exception:
        pass
    try:
        import mios_db_config
        mios_db_config.clear_cache()
    except Exception:
        pass


