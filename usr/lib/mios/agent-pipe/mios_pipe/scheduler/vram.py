# AI-hint: VRAM and model-residency manager extracted from server.py (AGY-346).
# AI-related: usr/lib/mios/agent-pipe/server.py, usr/lib/mios/agent-pipe/mios_pipe/scheduler/vram.py
"""VRAM and model-residency management module."""

from __future__ import annotations

import asyncio
import collections
import logging
import os
import time
from typing import Optional

import mios_blades

log = logging.getLogger("mios-agent-pipe")

_ACTIVE_MODELS: collections.Counter = collections.Counter()
_ACTIVE_LOCK = asyncio.Lock()
_HOST_STATS_CACHE: dict = {"t": 0.0, "v": None}
_RESIDENT_CACHE: dict = {}
_ENDPOINT_RESERVED: dict = {}

VRAM_CHECKPOINT_ENABLE = os.environ.get("MIOS_VRAM_CHECKPOINT", "true").lower() not in {"false", "0", "no"}
VRAM_BUDGET_MB = int(os.environ.get("MIOS_VRAM_BUDGET_MB", "23000"))
VRAM_TURN_HEADROOM_MB = 2000
REFINE_ENDPOINT = "http://localhost:8450/v1"
REFINE_MODEL = ""
POLISH_MODEL = ""
ADMIT_LOAD_CEIL = 12.0
ADMIT_MEM_PCT = 90.0
MULTIBLADE_ENABLE = False
VRAM_RECLAIM_IDLE = True

_host_stats = None
_endpoint_key = None
_agent_lane = None
_BLADE_POOL: dict = {}
_ENDPOINT_BLADE: dict = {}
_LOCAL_BLADE: str = ""
_LANE_PRIORITY: dict = {"_default": 5.0}


def configure(*, vram_checkpoint_enable=None, vram_budget_mb=None,
              vram_turn_headroom_mb=None, refine_endpoint=None,
              refine_model=None, polish_model=None, admit_load_ceil=None,
              admit_mem_pct=None, multiblade_enable=None, vram_reclaim_idle=None,
              host_stats=None, endpoint_key=None, agent_lane=None,
              blade_pool=None, endpoint_blade=None, local_blade=None,
              lane_priority=None) -> None:
    """Inject configuration and helper callbacks."""
    global VRAM_CHECKPOINT_ENABLE, VRAM_BUDGET_MB, VRAM_TURN_HEADROOM_MB
    global REFINE_ENDPOINT, REFINE_MODEL, POLISH_MODEL, ADMIT_LOAD_CEIL
    global ADMIT_MEM_PCT, MULTIBLADE_ENABLE, VRAM_RECLAIM_IDLE
    global _host_stats, _endpoint_key, _agent_lane
    global _BLADE_POOL, _ENDPOINT_BLADE, _LOCAL_BLADE, _LANE_PRIORITY

    if vram_checkpoint_enable is not None:
        VRAM_CHECKPOINT_ENABLE = vram_checkpoint_enable
    if vram_budget_mb is not None:
        VRAM_BUDGET_MB = vram_budget_mb
    if vram_turn_headroom_mb is not None:
        VRAM_TURN_HEADROOM_MB = vram_turn_headroom_mb
    if refine_endpoint is not None:
        REFINE_ENDPOINT = refine_endpoint
    if refine_model is not None:
        REFINE_MODEL = refine_model
    if polish_model is not None:
        POLISH_MODEL = polish_model
    if admit_load_ceil is not None:
        ADMIT_LOAD_CEIL = admit_load_ceil
    if admit_mem_pct is not None:
        ADMIT_MEM_PCT = admit_mem_pct
    if multiblade_enable is not None:
        MULTIBLADE_ENABLE = multiblade_enable
    if vram_reclaim_idle is not None:
        VRAM_RECLAIM_IDLE = vram_reclaim_idle
    if host_stats is not None:
        _host_stats = host_stats
    if endpoint_key is not None:
        _endpoint_key = endpoint_key
    if agent_lane is not None:
        _agent_lane = agent_lane
    if blade_pool is not None:
        _BLADE_POOL = blade_pool
    if endpoint_blade is not None:
        _ENDPOINT_BLADE = endpoint_blade
    if local_blade is not None:
        _LOCAL_BLADE = local_blade
    if lane_priority is not None:
        _LANE_PRIORITY = lane_priority


def _checkpoint_keep_models() -> set:
    """Models that must stay resident across turns."""
    keep = set()
    for m in (REFINE_MODEL, POLISH_MODEL, os.environ.get("MIOS_AGENT_PIPE_BACKEND_MODEL", "")):
        if m:
            keep.add(m)
    return keep


async def _engine_resident(endpoint: str) -> list:
    """Resident-model list for an endpoint (degrades open to [] on /v1 plane)."""
    return []


def _norm_model_tag(name: str) -> str:
    """Normalise model names so untagged and :latest match."""
    n = str(name or "").strip()
    return n if ":" in n else f"{n}:latest"


def _host_stats_cached(ttl: float = 1.0) -> dict:
    """_host_stats() with a short TTL cache."""
    try:
        now = time.monotonic()
        if _HOST_STATS_CACHE["v"] is None or now - _HOST_STATS_CACHE["t"] > ttl:
            _HOST_STATS_CACHE["v"] = _host_stats() if _host_stats else {}
            _HOST_STATS_CACHE["t"] = now
        return _HOST_STATS_CACHE["v"] or {}
    except Exception:
        return {}


async def _resident_cached(ep: str, ttl: float = 1.5) -> list:
    """_engine_resident(ep) with a short per-endpoint TTL cache."""
    try:
        now = time.monotonic()
        c = _RESIDENT_CACHE.get(ep)
        if c is None or now - c["t"] > ttl:
            v = await _engine_resident(ep)
            _RESIDENT_CACHE[ep] = {"t": now, "v": v or []}
            return v or []
        return c["v"]
    except Exception:
        return []


def _over_global_ceiling(load_ceil: Optional[float] = None) -> bool:
    """True when host load or mem is over the admission ceiling."""
    try:
        s = _host_stats_cached()
        if not s:
            return False
        load = s.get("load") or []
        l1 = float(load[0]) if load else 0.0
        memp = float(s.get("mem_used_pct") or 0.0)
        _ceil = ADMIT_LOAD_CEIL if load_ceil is None else float(load_ceil)
        return l1 > _ceil or memp > ADMIT_MEM_PCT
    except Exception:
        return False


def _blade_vram_budget(ep: str) -> int:
    """The VRAM budget (MB) to admit a cold model on ep."""
    if not MULTIBLADE_ENABLE:
        return VRAM_BUDGET_MB
    try:
        ep_key_fn = _endpoint_key or (lambda u: str(u or ""))
        blade = mios_blades.blade_for_endpoint(_ENDPOINT_BLADE, ep_key_fn, ep, _LOCAL_BLADE)
        return mios_blades.blade_vram_budget(_BLADE_POOL, blade, VRAM_BUDGET_MB)
    except Exception:
        return VRAM_BUDGET_MB


def _over_blade_ceiling(ep: str) -> bool:
    """The host-load ceiling check for ep's blade."""
    if not MULTIBLADE_ENABLE:
        return _over_global_ceiling()
    try:
        ep_key_fn = _endpoint_key or (lambda u: str(u or ""))
        blade = mios_blades.blade_for_endpoint(_ENDPOINT_BLADE, ep_key_fn, ep, _LOCAL_BLADE)
        if blade == _LOCAL_BLADE:
            _ceil = (_BLADE_POOL.get(blade) or {}).get("load_ceil")
            return _over_global_ceiling(_ceil)
        return False
    except Exception:
        return _over_global_ceiling()


async def _is_warm(ep: str, model: str) -> bool:
    """Is model already resident on ep?"""
    try:
        if not model:
            return True
        res = await _resident_cached(ep)
        return any(_norm_model_tag(m.get("name")) == _norm_model_tag(model) for m in res) if res else False
    except Exception:
        return True


async def _engine_unload(name: str, endpoint: str) -> None:
    """No-op on the /v1 plane."""
    return None


async def _vram_checkpoint(keep: Optional[set] = None) -> None:
    """Free VRAM as needed at a turn checkpoint by unloading non-kept models."""
    if not VRAM_CHECKPOINT_ENABLE:
        return
    ep = REFINE_ENDPOINT
    keep = keep or _checkpoint_keep_models()
    resident = await _engine_resident(ep)
    if not resident:
        return
    used_mb = sum(int(m.get("size_vram", 0)) for m in resident) // (1024 * 1024)
    free_mb = max(0, VRAM_BUDGET_MB - used_mb)
    if free_mb >= VRAM_TURN_HEADROOM_MB:
        return
    keepn = {_norm_model_tag(k) for k in keep}
    evictable = sorted(
        (m for m in resident if m.get("name") and _norm_model_tag(m.get("name")) not in keepn),
        key=lambda m: -int(m.get("size_vram", 0)))
    for m in evictable:
        await _engine_unload(m["name"], ep)
        free_mb += int(m.get("size_vram", 0)) // (1024 * 1024)
        if free_mb >= VRAM_TURN_HEADROOM_MB:
            break


async def _model_active(ep: str, model: str, delta: int, est_mb: int = 0) -> None:
    """Adjust the in-flight refcount for (ep, model)."""
    if not (ep and model):
        return
    model = _norm_model_tag(model)
    async with _ACTIVE_LOCK:
        _ACTIVE_MODELS[(ep, model)] += delta
        if _ACTIVE_MODELS[(ep, model)] <= 0:
            _ACTIVE_MODELS.pop((ep, model), None)
        if est_mb and ep:
            _ENDPOINT_RESERVED[ep] = max(
                0, int(_ENDPOINT_RESERVED.get(ep, 0)) + (int(est_mb) if delta > 0 else -int(est_mb)))
            if _ENDPOINT_RESERVED.get(ep, 0) <= 0:
                _ENDPOINT_RESERVED.pop(ep, None)


def _model_is_active(ep: str, model: str) -> bool:
    return _ACTIVE_MODELS.get((ep, _norm_model_tag(model)), 0) > 0


def _dispatch_priority(cfg: dict) -> float:
    """Lane-based admission priority for an agent dispatch."""
    try:
        lane = str((_agent_lane(cfg) if _agent_lane else None) or "gpu").lower()
    except Exception:
        lane = "gpu"
    base = float(_LANE_PRIORITY.get(lane, _LANE_PRIORITY.get("_default", 5.0)))
    if cfg.get("research_only"):
        base = max(1.0, base - 2.0)
    return base


async def _reclaim_idle_vram(ep: str, want_model: str, need_mb: int) -> bool:
    """Evict IDLE resident models on ep to free need_mb."""
    try:
        res = await _resident_cached(ep)
        if not res:
            return False
        keep = _checkpoint_keep_models()
        keepn = {_norm_model_tag(k) for k in keep}
        _wantn = _norm_model_tag(want_model)
        ep_key_str = _endpoint_key(ep) if _endpoint_key else ep
        evictable = sorted(
            (m for m in res
             if m.get("name") and _norm_model_tag(m.get("name")) != _wantn
             and _norm_model_tag(m.get("name")) not in keepn
             and not _model_is_active(ep, str(m.get("name")))),
            key=lambda m: -int(m.get("size_vram") or 0))
        freed = 0
        for m in evictable:
            await _engine_unload(str(m["name"]), ep)
            freed += int(m.get("size_vram") or 0) // (1024 * 1024)
            if freed >= max(0, need_mb):
                break
        if freed:
            _RESIDENT_CACHE.pop(ep, None)
        return freed > 0
    except Exception:
        return False
