# AI-hint: Pure endpoint protocol + capability detection extracted verbatim from server.py (strangler-fig refactor R-wave). Answers "what dialect/features does THIS lane speak?" from CONFIG-first signals: _binding_api reads the per-engine/per-agent `api` field; _endpoint_is_ollama (native /api/chat think=False vs OpenAI /v1), _endpoint_is_llamacpp (llama.cpp llama-server that exposes /slots KV paging), _endpoint_supports_tool_choice (llama.cpp 400s on tool_choice='required'), _endpoint_supports_parallel_tools (only the capable heavy lane emits well-formed parallel calls) all fall back to env-SSOT host:port hint tuples so NO bare port literal lives in the routing decision. The hint tuples + api-name sets (_OLLAMA_API_HINTS/_NO_TOOL_CHOICE_*/_PARALLEL_TOOLS_HINTS/_LLAMACPP_API/_KV_PAGING_HINTS) moved with the fns since only this cluster consumed them. Self-contained + side-effect-free (stdlib + mios_config._DISPATCH_TOML); NO DI, never imports server. server.py re-imports every name under its original _-prefixed alias (surface-parity zero-diff).
# AI-related: ./server.py, ./mios_config.py, ./test_mios_endpoints.py
# AI-functions: _binding_api, _endpoint_is_ollama, _endpoint_supports_tool_choice, _endpoint_supports_parallel_tools, _endpoint_is_llamacpp
"""Endpoint protocol + capability detection (pure leaf extracted from server.py).

Probes what dialect/feature-set a given inference endpoint speaks -- native
ollama ``/api/chat`` vs OpenAI ``/v1``, a llama.cpp ``llama-server`` that can do
``/slots`` KV paging, whether it accepts ``tool_choice='required'``, and whether
its model reliably emits well-formed PARALLEL tool calls. Every probe is
CONFIG-FIRST (a per-binding/agent ``api`` field wins) and falls back to an
env-SSOT host:port hint tuple, so no bare port literal lives in the routing
code. All functions are pure (endpoint string + cfg dict + optional engine);
the only dependency is ``mios_config._DISPATCH_TOML`` for the hint defaults.
``server.py`` re-imports every name under its original ``_``-prefixed alias so
the module's importable surface is byte-identical (surface-parity gate).
"""

from __future__ import annotations

import os
from typing import Optional

from mios_config import _DISPATCH_TOML


# SSOT for the native-ollama API lanes -- endpoints that speak /api/chat
# (think=False) instead of OpenAI /v1. Env-configurable so NO port literal
# lives in the routing code ("no hardcodes; all agents and
# models can run on any node/endpoint"); a per-binding/agent `api` field
# overrides it entirely, so an ollama (or OpenAI) endpoint on ANY port/host just
# declares its protocol in mios.toml [agents.*]/[agents.*.engines.*].
_OLLAMA_API_HINTS = tuple(
    h.strip() for h in os.environ.get(
        "MIOS_OLLAMA_API_HINTS", "11434,11435").split(",") if h.strip())


def _binding_api(cfg: dict, engine: Optional[str]) -> str:
    """The protocol an endpoint speaks, from CONFIG: the engine binding's `api`
    field, else the agent's top-level `api`, else '' (auto-detect). Lets ANY
    agent/model on ANY node declare 'ollama' or 'openai' explicitly."""
    if engine:
        b = (cfg.get("engines") or {}).get(str(engine).lower().strip())
        if isinstance(b, dict) and b.get("api"):
            return str(b["api"]).strip().lower()
    return str(cfg.get("api") or "").strip().lower()


def _endpoint_is_ollama(ep: str, cfg: dict, engine: Optional[str] = None) -> bool:
    """True when `ep` speaks the native ollama /api/chat protocol (think=False)
    rather than OpenAI /v1. CONFIG-FIRST: a per-binding/agent `api` field wins
    ('ollama'/'native' -> True; 'openai'/'v1'/'oai' -> False); otherwise fall
    back to the env-SSOT _OLLAMA_API_HINTS (default ports, no literal in code).
    So an ollama on a non-default port works by just setting api='ollama'."""
    api = _binding_api(cfg, engine)
    if api in ("ollama", "native"):
        return True
    if api in ("openai", "v1", "oai", "chat"):
        return False
    return any(h and h in (ep or "") for h in _OLLAMA_API_HINTS)


# Endpoints whose OpenAI surface does NOT accept tool_choice="required"
# (the Windows iGPU llama.cpp server b9305 at :11436 400s on
# tool_choice=required -> the iGPU node always 💤'd on a force-tool turn). SSOT:
# an agent/engine declares api="llamacpp" (or tool_choice=false) to opt out, else
# the env hint list (default the iGPU :11436 lane) -- no bare port literal in the
# routing decision. llama.cpp still honours `tools`; only the FORCED choice fails.
_NO_TOOL_CHOICE_API = {"llamacpp", "llama.cpp", "llama-server", "vulkan"}
_NO_TOOL_CHOICE_HINTS = tuple(
    h.strip() for h in str(os.environ.get("MIOS_NO_TOOL_CHOICE_HINTS")
                           or _DISPATCH_TOML.get("no_tool_choice_hints", "11436")).split(",")
    if h.strip())


def _endpoint_supports_tool_choice(ep: str, cfg: dict,
                                   engine: Optional[str] = None) -> bool:
    """False when the endpoint rejects tool_choice='required' (llama.cpp). The
    agent/engine can opt out via api=llamacpp or an explicit tool_choice=false;
    else fall back to the env-SSOT host:port hint list."""
    api = _binding_api(cfg, engine)
    if api in _NO_TOOL_CHOICE_API:
        return False
    if cfg.get("tool_choice") is False or \
            (engine and isinstance((cfg.get("engines") or {}).get(engine), dict)
             and (cfg["engines"][engine].get("tool_choice") is False)):
        return False
    return not any(h and h in (ep or "") for h in _NO_TOOL_CHOICE_HINTS)


# Endpoints whose model RELIABLY emits well-formed PARALLEL tool calls (operator
# "proper patterns + loops to OpenAI standards"). OpenAI DEFAULTS
# parallel_tool_calls=True; MiOS forces it False in the tool-loop because a SMALL
# local model malforms parallel calls (the "@ open notepad and type" failure: the
# fn wrapper dropped, leaving raw arguments in content). A CAPABLE lane (the heavy
# SGLang/Qwen) handles parallel correctly AND it is faster -- the model batches
# INDEPENDENT calls into ONE turn (fewer round-trips) while still SEQUENCING
# dependent steps itself. So OPT IN per-endpoint via this SSOT host:port hint list
# (default the heavy lane :11441); everything else stays sequential (robust). Note
# dependent OS actions ("open then type") take the deterministic fast-path, not this
# loop, so enabling parallelism here never reorders a launch+type chain.
_PARALLEL_TOOLS_HINTS = tuple(
    h.strip() for h in str(os.environ.get("MIOS_PARALLEL_TOOLS_HINTS")
                           or _DISPATCH_TOML.get("parallel_tools_hints", "11441")).split(",")
    if h.strip())


def _endpoint_supports_parallel_tools(ep: str) -> bool:
    """True when the endpoint's model reliably emits well-formed PARALLEL tool calls
    (the capable heavy lane) -> OpenAI-default parallel_tool_calls. Default False
    (sequential, robust for small local models); opt IN via the SSOT hint list."""
    return any(h and h in (ep or "") for h in _PARALLEL_TOOLS_HINTS)


_LLAMACPP_API = {"llamacpp", "llama.cpp", "llama-server", "vulkan"}
# Which endpoints support /slots paging, by host:port substring (SSOT; default
# the iGPU llama.cpp lane). An agent/engine api='llamacpp' opts in regardless.
_KV_PAGING_HINTS = tuple(
    h.strip() for h in str(os.environ.get("MIOS_KV_PAGING_HINTS")
                           or _DISPATCH_TOML.get("kv_paging_hints", "11436")).split(",")
    if h.strip())


def _endpoint_is_llamacpp(ep: str, cfg: dict, engine: Optional[str] = None) -> bool:
    """True when `ep` is a llama.cpp llama-server that can do /slots KV paging.
    CONFIG-FIRST (api='llamacpp'/'vulkan' on the agent/engine), else the
    env/SSOT host:port hint list -- no bare port literal in the routing code."""
    if _binding_api(cfg, engine) in _LLAMACPP_API:
        return True
    return any(h and h in (ep or "") for h in _KV_PAGING_HINTS)
