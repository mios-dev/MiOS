# AI-hint: Admission control / SLO / lane-semaphore seam extracted from server.py.
# AI-related: usr/lib/mios/agent-pipe/server.py, usr/lib/mios/agent-pipe/mios_pipe/scheduler/admission.py
"""Admission control, SLO shedding, and lane semaphore management module."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import time
from typing import Optional

import mios_slo

log = logging.getLogger("mios-agent-pipe")

_LANE_SEMS: dict[str, asyncio.Semaphore] = {}
_ENDPOINT_SEMS: dict[str, asyncio.Semaphore] = {}

PRIORITY_QUEUE_ENABLE = True
TENANT_QUOTA_ENABLE = False
SLO_SHED_ENABLE = True
ADMIT_ENABLE = True
ADMIT_MAX_WAIT = 15.0
MULTIBLADE_ENABLE = False
VRAM_COLOAD_ENABLE = True
VRAM_COLOAD_EST_MB = 4000
VRAM_COLOAD_RESERVE_MB = 1000
VRAM_RECLAIM_IDLE = True
VRAM_BUDGET_MB = 23000
AGENT_CONCURRENCY = 4
ENDPOINT_CONCURRENCY = 2

_GLOBAL_PRIORITY_GATE = None
_turn_tenant = None
_over_global_ceiling = None
_over_blade_ceiling = None
_blade_vram_budget = None
_is_warm = None
_resident_cached = None
_norm_model_tag = None
_reclaim_idle_vram = None
_ENDPOINT_RESERVED: dict = {}
_dispatch_num = None


class _SloShed(Exception):
    """Raised by _admit to SHED a best_effort dispatch under contention (WS-SCHED-SLO)."""


def configure(*, priority_queue_enable=None, tenant_quota_enable=None,
              slo_shed_enable=None, admit_enable=None, admit_max_wait=None,
              multiblade_enable=None, vram_coload_enable=None,
              vram_coload_est_mb=None, vram_coload_reserve_mb=None,
              vram_reclaim_idle=None, vram_budget_mb=None,
              agent_concurrency=None, endpoint_concurrency=None,
              global_priority_gate=None, turn_tenant=None,
              over_global_ceiling=None, over_blade_ceiling=None,
              blade_vram_budget=None, is_warm=None, resident_cached=None,
              norm_model_tag=None, reclaim_idle_vram=None,
              endpoint_reserved=None, dispatch_num=None) -> None:
    """Inject configuration scalars and helper callbacks."""
    global PRIORITY_QUEUE_ENABLE, TENANT_QUOTA_ENABLE, SLO_SHED_ENABLE
    global ADMIT_ENABLE, ADMIT_MAX_WAIT, MULTIBLADE_ENABLE
    global VRAM_COLOAD_ENABLE, VRAM_COLOAD_EST_MB, VRAM_COLOAD_RESERVE_MB
    global VRAM_RECLAIM_IDLE, VRAM_BUDGET_MB, AGENT_CONCURRENCY
    global ENDPOINT_CONCURRENCY, _GLOBAL_PRIORITY_GATE, _turn_tenant
    global _over_global_ceiling, _over_blade_ceiling, _blade_vram_budget
    global _is_warm, _resident_cached, _norm_model_tag, _reclaim_idle_vram
    global _ENDPOINT_RESERVED, _dispatch_num

    if priority_queue_enable is not None:
        PRIORITY_QUEUE_ENABLE = priority_queue_enable
    if tenant_quota_enable is not None:
        TENANT_QUOTA_ENABLE = tenant_quota_enable
    if slo_shed_enable is not None:
        SLO_SHED_ENABLE = slo_shed_enable
    if admit_enable is not None:
        ADMIT_ENABLE = admit_enable
    if admit_max_wait is not None:
        ADMIT_MAX_WAIT = admit_max_wait
    if multiblade_enable is not None:
        MULTIBLADE_ENABLE = multiblade_enable
    if vram_coload_enable is not None:
        VRAM_COLOAD_ENABLE = vram_coload_enable
    if vram_coload_est_mb is not None:
        VRAM_COLOAD_EST_MB = vram_coload_est_mb
    if vram_coload_reserve_mb is not None:
        VRAM_COLOAD_RESERVE_MB = vram_coload_reserve_mb
    if vram_reclaim_idle is not None:
        VRAM_RECLAIM_IDLE = vram_reclaim_idle
    if vram_budget_mb is not None:
        VRAM_BUDGET_MB = vram_budget_mb
    if agent_concurrency is not None:
        AGENT_CONCURRENCY = agent_concurrency
    if endpoint_concurrency is not None:
        ENDPOINT_CONCURRENCY = endpoint_concurrency
    if global_priority_gate is not None:
        _GLOBAL_PRIORITY_GATE = global_priority_gate
    if turn_tenant is not None:
        _turn_tenant = turn_tenant
    if over_global_ceiling is not None:
        _over_global_ceiling = over_global_ceiling
    if over_blade_ceiling is not None:
        _over_blade_ceiling = over_blade_ceiling
    if blade_vram_budget is not None:
        _blade_vram_budget = blade_vram_budget
    if is_warm is not None:
        _is_warm = is_warm
    if resident_cached is not None:
        _resident_cached = resident_cached
    if norm_model_tag is not None:
        _norm_model_tag = norm_model_tag
    if reclaim_idle_vram is not None:
        _reclaim_idle_vram = reclaim_idle_vram
    if endpoint_reserved is not None:
        _ENDPOINT_RESERVED = endpoint_reserved
    if dispatch_num is not None:
        _dispatch_num = dispatch_num


def _parse_lane_caps(spec: str) -> dict:
    out: dict = {}
    for part in (spec or "").split(","):
        part = part.strip()
        if ":" in part:
            k, _, v = part.partition(":")
            try:
                out[k.strip().lower()] = int(v.strip())
            except ValueError:
                pass
    return out


@contextlib.asynccontextmanager
async def _priority_gate(priority: float):
    """Reordering, degrade-open replacement for _GLOBAL_DISPATCH_SEM."""
    use_gate = PRIORITY_QUEUE_ENABLE and (_GLOBAL_PRIORITY_GATE is not None)
    _tenant = _turn_tenant() if (TENANT_QUOTA_ENABLE and _turn_tenant) else None
    if use_gate:
        try:
            await _GLOBAL_PRIORITY_GATE.acquire(priority, tenant=_tenant)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.warning("Priority gate acquire failed, degrading open to FIFO semaphore", exc_info=True)
            use_gate = False
    if use_gate:
        try:
            yield
        finally:
            try:
                _GLOBAL_PRIORITY_GATE.release(tenant=_tenant)
            except Exception:
                pass
        return
    yield


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


def _lane_sem(key: str) -> asyncio.Semaphore:
    """The concurrency gate for ONE hardware lane / engine / node."""
    key = str(key or "gpu").lower().strip() or "gpu"
    if key not in _LANE_SEMS:
        _k = key.replace("-", "_")
        _general = _dispatch_num("MIOS_AGENT_LANE_CONCURRENCY", "lane_concurrency", AGENT_CONCURRENCY) if _dispatch_num else AGENT_CONCURRENCY
        n = _dispatch_num("MIOS_AGENT_LANE_CONCURRENCY_" + _k.upper(), "lane_concurrency_" + _k, _general) if _dispatch_num else _general
        _LANE_SEMS[key] = asyncio.Semaphore(max(1, n))
    return _LANE_SEMS[key]


def _endpoint_key(ep: str) -> str:
    """host:port of an endpoint URL."""
    s = str(ep or "")
    s = s.split("://", 1)[-1]
    return s.split("/", 1)[0] or s


def _endpoint_sem(ep: str) -> asyncio.Semaphore:
    """Concurrency gate for ONE inference endpoint."""
    key = _endpoint_key(ep) or "default"
    if key not in _ENDPOINT_SEMS:
        _ENDPOINT_SEMS[key] = asyncio.Semaphore(max(1, ENDPOINT_CONCURRENCY))
    return _ENDPOINT_SEMS[key]


async def _admit(ep: str, model: str, lane: str, priority: float = 5.0,
                  est_mb: int = 0, *, foreground: bool = True) -> None:
    """Capacity-aware admission gate, run BEFORE endpoint/lane semaphores."""
    if SLO_SHED_ENABLE:
        _slo = mios_slo.classify(foreground=foreground)
        _over = _over_global_ceiling() if _over_global_ceiling else False
        if mios_slo.should_shed(_slo, over_ceiling=_over):
            raise _SloShed(_slo)
    if not ADMIT_ENABLE:
        return
    try:
        deadline = time.monotonic() + ADMIT_MAX_WAIT
        while time.monotonic() < deadline:
            _over = (_over_blade_ceiling(ep) if (MULTIBLADE_ENABLE and _over_blade_ceiling)
                     else (_over_global_ceiling() if _over_global_ceiling else False))
            if not _over:
                break
            _backoff = max(0.15, (10.0 - float(priority)) * 0.1)
            await asyncio.sleep(min(_backoff, max(0.0, deadline - time.monotonic())))

        warm = await _is_warm(ep, model) if _is_warm else False
        if not warm:
            _reclaimed = False
            _budget = _blade_vram_budget(ep) if (MULTIBLADE_ENABLE and _blade_vram_budget) else VRAM_BUDGET_MB
            while time.monotonic() < deadline:
                res = (await _resident_cached(ep)) if _resident_cached else []
                used_mb = (sum(int(m.get("size_vram") or 0) for m in res) // (1024 * 1024)
                           + int(_ENDPOINT_RESERVED.get(ep, 0)))
                est = 0
                if _norm_model_tag:
                    est = next((int(m.get("size_vram") or 0) // (1024 * 1024) for m in res
                                if _norm_model_tag(m.get("name")) == _norm_model_tag(model)), 0)
                est = est or est_mb or VRAM_COLOAD_EST_MB
                if (not VRAM_COLOAD_ENABLE) or ((used_mb + est + VRAM_COLOAD_RESERVE_MB) <= _budget):
                    break
                if VRAM_RECLAIM_IDLE and not _reclaimed:
                    _reclaimed = True
                    if _reclaim_idle_vram and await _reclaim_idle_vram(ep, model, est + VRAM_COLOAD_RESERVE_MB):
                        continue
                await asyncio.sleep(min(0.5, max(0.0, deadline - time.monotonic())))
    except Exception:
        pass
