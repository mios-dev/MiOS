# AI-hint: INFERENCE LANE-RESOLVER cluster extracted VERBATIM from server.py
#   (strangler-fig refactor). Owns the WS-1 unified lane selector: _lane_resolver
#   builds the mios_lanes.LaneResolver lazily from SSOT ([ai].heavy_engine-preferred
#   heavy lane -> the other heavy lane -> the always-on light lane, plus remote
#   [nodes.*] escalation lanes), _pick_tool_backend delegates the client-tools
#   (url, model) pick to it with a legacy heavy/light-probe fallback, and
#   _heavy_lane_up is the cached SGLang-heavy reachability probe. The _LANE_RESOLVER
#   lazy singleton is OWNED here and REBOUND at runtime by _lane_resolver; server.py
#   reads the live value through the _lane_resolver_current getter (it is unsafe to
#   inject a runtime-reassigned global by value -- the cluster-health route uses the
#   getter). mios_lanes is imported directly; the config scalars come from mios_config;
#   the two server-resident helpers (_get_client, _is_remote_endpoint) are
#   dependency-INJECTED via configure(). This module NEVER imports server. server.py
#   re-imports the moved names under their EXACT original aliases so the importable
#   surface stays byte-identical.
# AI-related: ./server.py, ./mios_config.py, ./mios_lanes.py, ./test_mios_lanes_resolver.py
# AI-functions: _heavy_lane_up, _lane_resolver, _pick_tool_backend, _lane_resolver_current, configure
"""INFERENCE lane-resolver cluster (strangler-fig refactor).

Extracted VERBATIM from ``server.py``. ``_lane_resolver`` lazily builds the WS-1
unified :class:`mios_lanes.LaneResolver` from SSOT and caches it in the
module-owned ``_LANE_RESOLVER`` singleton (rebound at runtime); ``_pick_tool_backend``
returns the ``(url, model)`` for the client-tools loop via that resolver with a
legacy heavy/light-probe fallback; ``_heavy_lane_up`` is the cached SGLang-heavy
reachability probe. The config scalars are imported from :mod:`mios_config`;
``mios_lanes`` is imported directly; every server-resident symbol (``_get_client``,
``_is_remote_endpoint``) is injected via :func:`configure` (one-way boundary -- this
module never imports ``server``). server.py re-imports the moved names under their
original aliases, and reads the live ``_LANE_RESOLVER`` through
:func:`_lane_resolver_current` so the importable surface stays byte-identical.
"""

from __future__ import annotations

import os
import logging

import mios_lanes   # WS-1 unified inference-lane resolver

from mios_config import (
    _TOOL_BACKEND,
    _TOOL_BACKEND_MODEL,
    _TOOL_BACKEND_HEAVY,
    _TOOL_BACKEND_HEAVY_MODEL,
    _HEAVY_PROBE_TTL,
    _toml_section,
)

log = logging.getLogger("mios-agent-pipe")


# -- Dependency-injection seam ----------------------------------------
# The resolver calls back into two server-resident helpers: the shared httpx
# client factory (_get_client) and the remote-endpoint classifier
# (_is_remote_endpoint). server.py calls configure() with those AFTER both are
# defined (one-way boundary: this module never imports server). The placeholders
# below let a standalone import succeed; every consumer is async/runtime so
# nothing fires before configure() runs.

_get_client = None
_is_remote_endpoint = None


_INJECTED = frozenset((
    "_get_client", "_is_remote_endpoint",
))


def configure(**deps) -> None:
    """Inject server-side deps under their EXACT original names (one-way boundary).

    Called once from ``server.py`` after every injected symbol is defined. Each
    keyword equals the module global it sets.
    """
    g = globals()
    for _k, _v in deps.items():
        if _k in _INJECTED:
            g[_k] = _v


_heavy_probe = {"ok": False, "ts": -1e9}


async def _heavy_lane_up() -> bool:
    """Is the SGLang heavy lane serving right now? Cached for _HEAVY_PROBE_TTL s so we
    probe at most once per window, never per request."""
    import time as _t
    now = _t.monotonic()
    if (now - _heavy_probe["ts"]) < _HEAVY_PROBE_TTL:
        return _heavy_probe["ok"]
    ok = False
    try:
        client = await _get_client()
        r = await client.get(f"{_TOOL_BACKEND_HEAVY}/models", timeout=2.0)
        ok = (r.status_code == 200)
    except Exception:  # noqa: BLE001 -- any failure => heavy is down, use light
        ok = False
    _heavy_probe["ok"] = ok
    _heavy_probe["ts"] = now
    return ok


_LANE_RESOLVER = None


def _lane_resolver():
    """WS-1 unified lane resolver (mios_lanes), built LAZILY from SSOT so _toml_section
    / _get_client are defined, then cached. ONE place a model lane is chosen: the
    [ai].heavy_engine-preferred heavy lane, then the other heavy lane, then the always-on
    light lane, with a per-lane cooldown so a dead lane fails over (never 404s). Collapses
    the two 'mios-heavy' lanes (SGLang :11441 + vLLM :11440) behind one selector."""
    global _LANE_RESOLVER
    if _LANE_RESOLVER is not None:
        return _LANE_RESOLVER
    try:
        _ai = _toml_section("ai")
    except Exception:  # noqa: BLE001 -- degrade to env/defaults
        _ai = {}
    heavy_engine = (os.environ.get("MIOS_AGENT_PIPE_HEAVY_ENGINE")
                    or str(_ai.get("heavy_engine", "sglang"))).strip()
    _vllm_url = (os.environ.get("MIOS_AGENT_PIPE_TOOL_BACKEND_VLLM")
                 or _toml_section("nodes").get("local-vllm", {}).get("endpoint")
                 or f"http://localhost:{os.environ.get('MIOS_PORT_VLLM', '8441')}/v1").rstrip("/")
    _vllm_model = os.environ.get("MIOS_AGENT_PIPE_TOOL_BACKEND_VLLM_MODEL",
                                 _TOOL_BACKEND_HEAVY_MODEL)
    lanes = {
        "light":  mios_lanes.Lane("light",  _TOOL_BACKEND,       _TOOL_BACKEND_MODEL),
        "sglang": mios_lanes.Lane("sglang", _TOOL_BACKEND_HEAVY, _TOOL_BACKEND_HEAVY_MODEL),
        "vllm":   mios_lanes.Lane("vllm",   _vllm_url,           _vllm_model),
    }
    chain = mios_lanes.build_chain(heavy_engine, lanes.keys())
    # WS-A16: make remote [nodes.*] cores FIRST-CLASS escalation lanes appended
    # AFTER the local lanes (LiteLLM order-based fallback: local-first, escalate to
    # a remote core only when every local lane is on cooldown / unreachable). The
    # quality/cost trigger (mios_smartroute.should_escalate) is the richer layer;
    # this is the reliability-escalation baseline. INERT BY DEFAULT: when
    # [ai].remote_escalation is off (default) OR no remote node is configured, the
    # lanes/chain are byte-identical to the local-only resolver. Degrade-open.
    try:
        if str(_ai.get("remote_escalation", "off")).strip().lower() in {
                "on", "true", "1", "yes", "enforce"}:
            for _nname, _ncfg in (_toml_section("nodes") or {}).items():
                if not isinstance(_ncfg, dict):
                    continue
                _nep = str(_ncfg.get("endpoint") or "").strip().rstrip("/")
                if _nep and _is_remote_endpoint(_nep) and f"remote:{_nname}" not in lanes:
                    _lid = f"remote:{_nname}"
                    lanes[_lid] = mios_lanes.Lane(
                        _lid, _nep, str(_ncfg.get("model") or _TOOL_BACKEND_MODEL))
                    chain = chain + [_lid]   # trailing = lowest preference = escalation
    except Exception:  # noqa: BLE001 -- escalation is best-effort; never break lanes
        pass

    async def _probe(url: str) -> bool:
        client = await _get_client()
        r = await client.get(f"{url}/models", timeout=2.0)
        return r.status_code == 200

    _LANE_RESOLVER = mios_lanes.LaneResolver(
        lanes, {"heavy": chain, "tool": chain}, _probe,
        ttl=_HEAVY_PROBE_TTL,
        cooldown=float(os.environ.get("MIOS_AGENT_PIPE_LANE_COOLDOWN", "60")))
    try:
        log.info("lane resolver: heavy_engine=%s chain=%s", heavy_engine, chain)
    except Exception:  # noqa: BLE001
        pass
    return _LANE_RESOLVER


async def _pick_tool_backend() -> tuple:
    """(url, model) for the client-tools loop -- delegated to the WS-1 unified lane
    resolver: the preferred heavy reasoner when reachable, else the other heavy lane,
    else the always-on light lane (with per-lane cooldown so a dead lane fails over,
    never 404s). Degrade-open: any resolver error falls back to the legacy heavy/light
    probe so the agentic surface never hard-fails."""
    try:
        lane = await _lane_resolver().pick("tool")
        if lane is not None:
            return lane.url, lane.model
    except Exception as _e:  # noqa: BLE001 -- degrade to the legacy probe
        log.debug("lane resolver failed (-> legacy pick): %s", _e)
    if await _heavy_lane_up():
        return _TOOL_BACKEND_HEAVY, _TOOL_BACKEND_HEAVY_MODEL
    return _TOOL_BACKEND, _TOOL_BACKEND_MODEL


def _lane_resolver_current():
    """The live ``_LANE_RESOLVER`` singleton (None until first resolved). server.py's
    cluster-health route reads it through this getter because the global is REBOUND at
    runtime by ``_lane_resolver`` and so is unsafe to inject/re-import by value."""
    return _LANE_RESOLVER
