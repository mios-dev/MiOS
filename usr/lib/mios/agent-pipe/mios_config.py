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


PORT = int(os.environ.get("MIOS_PORT_AGENT_PIPE", "8640"))
# MCP server port (SSOT, no-hardcode): the AGNTCY manifest
# advertised a hardcoded :8765. Reuse the canonical precedence from
# mios-mcp-server (MIOS_PORT_MCP -> MIOS_MCP_PORT -> 8765 default).
MCP_SERVER_PORT = int(os.environ.get("MIOS_PORT_MCP")
                      or os.environ.get("MIOS_MCP_PORT") or "8765")
# WS-0B: ONE owned light-lane base. The mios-llm-light port was hardcoded as the
# literal `http://localhost:11450` in ~10 endpoint defaults below (drift). Derive
# it ONCE from the [ports].llm_light SSOT key (MIOS_PORT_LLM_LIGHT via install.env;
# default 11450) so a port change is a single edit; each endpoint still honors its
# explicit MIOS_*_ENDPOINT override first.
_LIGHT_BASE = "http://localhost:" + (os.environ.get("MIOS_PORT_LLM_LIGHT") or "11450")
# WS-0B: the agent-pipe's reasoning backend. An explicit MIOS_AGENT_PIPE_BACKEND URL
# wins; else when the deployment opts into reasoning DIRECTLY on the light lane
# (MIOS_AGENT_PIPE_BACKEND_LIGHT -- the operator "EVERYTHING IS LLAMA.CPP, bypass
# Hermes" directive) compose it from the ONE owned light-lane base (no port literal
# in the unit); else front Hermes on :8642 (the original design default).
BACKEND = (os.environ.get("MIOS_AGENT_PIPE_BACKEND")
           or (_LIGHT_BASE + "/v1"
               if (os.environ.get("MIOS_AGENT_PIPE_BACKEND_LIGHT") or "").strip().lower()
                  in {"1", "true", "yes", "on"}
               else "http://localhost:8642/v1")).rstrip("/")
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
# :11450) while Hermes still runs on its own port (:8642). Scoping the key to
# this SET (not just BACKEND) keeps non-streaming hermes dispatch (swarm /
# council / DAG facets) authenticated instead of silently 401'ing -- the
# regression of the "hermes facets 401'd in the swarm" fix once
# BACKEND moved off :8642.. SSOT: same :8642 default as
# BACKEND above and mios.toml [agents.hermes].endpoint; env-overridable.
_HERMES_ENDPOINT = os.environ.get(
    "MIOS_HERMES_ENDPOINT", "http://localhost:8642/v1").rstrip("/")
# P1 : the hermes WORKER on :8643 (hermes-worker.service) is the
# [agents.hermes].endpoint dispatch target now, and it REQUIRES API_SERVER_KEY auth
# (it rejected the pipe's probes with "invalid API key" until added here). Scope the
# backend key to it too so swarm/council/DAG hermes dispatch authenticates. SSOT env-
# overridable; same :8643 default as the worker unit's API_SERVER_PORT.
_HERMES_WORKER_ENDPOINT = os.environ.get(
    "MIOS_HERMES_WORKER_ENDPOINT", "http://localhost:8643/v1").rstrip("/")
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
_TOOL_BACKEND_HEAVY = os.environ.get(
    "MIOS_AGENT_PIPE_TOOL_BACKEND_HEAVY", "http://localhost:11441/v1").rstrip("/")
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
_MICRO_MODEL = os.environ.get("MIOS_MICRO_MODEL", _STACK_MODEL)
_MICRO_ENDPOINT = os.environ.get(
    "MIOS_MICRO_ENDPOINT", _LIGHT_BASE + "/v1",  # mios-llm-light (WS-0B: one owned port key)
).rstrip("/")
# Callers below append "/v1/chat/completions"; strip a trailing /v1 so we
# don't double it.
_MICRO_BASE = (_MICRO_ENDPOINT[:-3].rstrip("/")
               if _MICRO_ENDPOINT.endswith("/v1") else _MICRO_ENDPOINT)

# Router (layer-1 micro-LLM classifier) config -- relocated from server.py (R14
# config SSOT). The micro classifier runs on the CPU light-lane, ISOLATED from
# the dGPU queue so router latency stays sub-second even under big-model load.
_LIGHT_LANE = os.environ.get("MIOS_OLLAMA_CPU_ENDPOINT",
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
    # mios-llm-light /v1 (the old :11434 ollama default is dead -- G5/G17). Env (SSOT
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


def _toml_section(section: str) -> dict:
    """Layered <section> table from mios.toml (vendor <- /etc <- ~/.config),
    merged field-by-field -- the ONE SSOT reader for any [section] tunables
 ("HARDCODES!!!": tunables live in mios.toml, not code)."""
    _layers = [os.environ.get("MIOS_TOML", "/usr/share/mios/mios.toml"),
               "/etc/mios/mios.toml",
               os.path.expanduser("~/.config/mios/mios.toml")]
    out: dict = {}
    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        for _p in _layers:
            try:
                with open(_p, "rb") as _f:
                    _layer = (tomllib.load(_f).get(section) or {})
            except (OSError, tomllib.TOMLDecodeError):
                continue
            if isinstance(_layer, dict):
                out.update(_layer)
    except Exception:  # noqa: BLE001 -- best-effort; callers fall to literals
        log.warning("Failed to load overlay config section %s", section, exc_info=True)
    # Expand ${MIOS_PORT_*}/$VAR placeholders in string values against the
    # process env (install.env supplies MIOS_PORT_*). mios.toml stores endpoint
    # URLs as deferred-expansion templates ("http://localhost:${MIOS_PORT_HERMES_WORKER}/v1");
    # systemd EnvironmentFile and Python do NOT expand ${...}, so without this
    # the agent registry got a LITERAL "${MIOS_PORT_HERMES_WORKER}" port ->
    # httpx InvalidURL -> the :8640 front door 500'd on every request. expandvars
    # only touches $-prefixed tokens (ordinary values untouched; an unknown var
    # is left verbatim). install-robustness.
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
    """Layered [dispatch] table from mios.toml (vendor <- /etc <- ~/.config),
    merged field-by-field. ONE SSOT reader for the swarm fan-out + DAG-node +
    deepen tunables; also used by _load_dispatch_cfg() so the layering logic
    lives in a single place."""
    _layers = [os.environ.get("MIOS_TOML", "/usr/share/mios/mios.toml"),
               "/etc/mios/mios.toml",
               os.path.expanduser("~/.config/mios/mios.toml")]
    dd: dict = {}
    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        for _p in _layers:
            try:
                with open(_p, "rb") as _f:
                    _layer = (tomllib.load(_f).get("dispatch") or {})
            except (OSError, tomllib.TOMLDecodeError):
                continue
            if isinstance(_layer, dict):
                dd.update(_layer)
    except Exception:  # noqa: BLE001 -- best-effort; consts fall to literals
        log.warning("Failed to load overlay config for dispatch", exc_info=True)
    return dd


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
