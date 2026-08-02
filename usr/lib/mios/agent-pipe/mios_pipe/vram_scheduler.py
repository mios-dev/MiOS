# AI-hint: Extracted module for vram_scheduler.py.
"""VRAM and Lane Scheduler."""

from __future__ import annotations
import asyncio
import collections
import time
import os
import mios_slo

log = None
_toml_section = None
_DISPATCH_TOML = {}
AGENT_CONCURRENCY = 4
ENDPOINT_CONCURRENCY = 2
SLO_SHED_ENABLE = False
ADMIT_ENABLE = False
ADMIT_MAX_WAIT = 15.0
MULTIBLADE_ENABLE = False
_over_blade_ceiling = None
_over_global_ceiling = None
_is_warm = None
_blade_vram_budget = None
VRAM_BUDGET_MB = 24000
_resident_cached = None
_norm_model_tag = None
VRAM_COLOAD_EST_MB = 4000
VRAM_COLOAD_ENABLE = True
VRAM_COLOAD_RESERVE_MB = 1000
_reclaim_idle_vram = None
_dispatch_num = None

_LANE_SEMS = {}
_ENDPOINT_SEMS = {}

def configure(**kwargs):
    globals().update(kwargs)

class _SloShed(Exception):
    """Raised by _admit to SHED a best_effort dispatch under contention (WS-SCHED-
    SLO). Caught at the fan-out call sites -> the node drops from the merge (the
    swarm already tolerates a dead/empty node); never raised for interactive."""


_HOST_STATS_CACHE = {"t": 0.0, "v": None}
_RESIDENT_CACHE: dict = {}   # ep -> {"t":ts,"v":[models]}
_ADMIT_SEQ = 0  # monotonic tie-breaker for priority waits

NODES_RESEARCH_ONLY = str(os.environ.get("MIOS_NODES_RESEARCH_ONLY")
                          or _DISPATCH_TOML.get("nodes_research_only", "false")
                          ).strip().lower() in {"1", "true", "yes"}
VRAM_RECLAIM_IDLE = str(os.environ.get("MIOS_VRAM_RECLAIM_IDLE")
                        or _DISPATCH_TOML.get("vram_reclaim_idle", "true")
                        ).strip().lower() not in {"0", "false", "no", "off"}


def _parse_lane_priority(s: str) -> dict:
    """'gpu:8,cpu:7,...' -> {lane: prio}. Always carries a _default."""
    out = {"_default": 5.0}
    for part in str(s or "").split(","):
        k, sep, v = part.partition(":")
        if sep:
            try:
                out[k.strip().lower()] = float(v.strip())
            except ValueError:
                pass
    return out


_LANE_PRIORITY = _parse_lane_priority(
    os.environ.get("MIOS_LANE_PRIORITY")
    or _DISPATCH_TOML.get("lane_priority",
                          "gpu:8,cpu:7,accelerator:6,igpu:3,mobile:2,_default:5"))
_ACTIVE_MODELS: "collections.Counter" = collections.Counter()
_ACTIVE_LOCK = asyncio.Lock()
_ENDPOINT_RESERVED: dict = {}


def _lane_sem(key: str) -> asyncio.Semaphore:
    """The concurrency gate for ONE hardware lane / engine / node (lazily
    created -- safe: no await between the check and the set in the single-
    threaded event loop)."""
    key = str(key or "gpu").lower().strip() or "gpu"
    if key not in _LANE_SEMS:
        # MIOS_AGENT_LANE_CONCURRENCY) else AGENT_CONCURRENCY. The LOCAL gpu/cpu
        _k = key.replace("-", "_")
        _general = _dispatch_num("MIOS_AGENT_LANE_CONCURRENCY", "lane_concurrency",
                             AGENT_CONCURRENCY)
        n = _dispatch_num("MIOS_AGENT_LANE_CONCURRENCY_" + _k.upper(),
                      "lane_concurrency_" + _k, _general)
        _LANE_SEMS[key] = asyncio.Semaphore(max(1, n))
    return _LANE_SEMS[key]


def _endpoint_key(ep: str) -> str:
    """host:port of an endpoint URL -- the identity of the physical inference
 daemon. Strips scheme + path so http://localhost:11434
    /v1 and http://localhost:11434/api/chat collapse to one key."""
    s = str(ep or "")
    s = s.split("://", 1)[-1]          # drop scheme
    return s.split("/", 1)[0] or s     # keep host:port


def _endpoint_sem(ep: str) -> asyncio.Semaphore:
    """Concurrency gate for ONE inference endpoint (the physical inference backend),
    so a wide fan-out cannot cold-load N models on the SAME backend at once
 (thundering-herd runaway). Lazily created; SSOT
    [dispatch].endpoint_concurrency. Lane semaphore still applies on top --
    this bounds the shared DAEMON, the lane bounds the hardware CATEGORY."""
    key = _endpoint_key(ep) or "default"
    if key not in _ENDPOINT_SEMS:
        _ENDPOINT_SEMS[key] = asyncio.Semaphore(max(1, ENDPOINT_CONCURRENCY))
    return _ENDPOINT_SEMS[key]


async def _admit(ep: str, model: str, lane: str, priority: float = 5.0,
                 est_mb: int = 0, *, foreground: bool = True) -> None:
    """Capacity-aware admission gate, run BEFORE the endpoint/lane semaphores.
    No-op unless ADMIT_ENABLE. DEGRADE-OPEN: any error -> return (admit). Bounds
    every wait by ADMIT_MAX_WAIT then admits anyway -> never deadlocks a turn.
    Gates: (1) global host-load/mem ceiling; (2) a COLD model on an at-VRAM-
    ceiling endpoint waits briefly so cold loads serialize. Warm/under-ceiling
    dispatch returns immediately. (_host_stats_cached/_resident_cached/
    _over_global_ceiling/_is_warm are defined below near _engine_resident.)"""
    if SLO_SHED_ENABLE:
        _slo = mios_slo.classify(foreground=foreground)
        if mios_slo.should_shed(_slo, over_ceiling=_over_global_ceiling()):
            raise _SloShed(_slo)
    if not ADMIT_ENABLE:
        return
    try:
        deadline = time.monotonic() + ADMIT_MAX_WAIT
        while (_over_blade_ceiling(ep) if MULTIBLADE_ENABLE
               else _over_global_ceiling()) and time.monotonic() < deadline:
            _backoff = max(0.15, (10.0 - float(priority)) * 0.1)
            await asyncio.sleep(min(_backoff, max(0.0, deadline - time.monotonic())))
        warm = await _is_warm(ep, model)
        if not warm:
            _reclaimed = False
            _budget = _blade_vram_budget(ep) if MULTIBLADE_ENABLE else VRAM_BUDGET_MB
            while time.monotonic() < deadline:
                res = await _resident_cached(ep)
                used_mb = (sum(int(m.get("size_vram") or 0)
                               for m in res) // (1024 * 1024)
                           + int(_ENDPOINT_RESERVED.get(ep, 0)))
                est = next((int(m.get("size_vram") or 0) // (1024 * 1024)
                            for m in res
                            if _norm_model_tag(m.get("name")) == _norm_model_tag(model)),
                           0) or est_mb or VRAM_COLOAD_EST_MB
                if (not VRAM_COLOAD_ENABLE) or \
                        (used_mb + est + VRAM_COLOAD_RESERVE_MB) <= _budget:
                    break
                if VRAM_RECLAIM_IDLE and not _reclaimed:
                    _reclaimed = True
                    if await _reclaim_idle_vram(
                            ep, model, est + VRAM_COLOAD_RESERVE_MB):
                        continue
                await asyncio.sleep(min(0.5, max(0.0, deadline - time.monotonic())))
    except Exception:  # noqa: BLE001 -- admission must never block a turn
        log.warning("Admit check encountered unexpected error", exc_info=True)
        return
