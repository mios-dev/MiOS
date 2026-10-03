# AI-hint: Global priority-gate seam extracted from server.py; lane/endpoint semaphores and _admit live in mios_pipe/vram_scheduler.py.
# AI-related: usr/lib/mios/agent-pipe/server.py, usr/lib/mios/agent-pipe/mios_pipe/vram_scheduler.py
"""Global dispatch priority gate and per-lane tool-cap parsing."""

from __future__ import annotations

import asyncio
import contextlib
import logging

log = logging.getLogger("mios-agent-pipe")

PRIORITY_QUEUE_ENABLE = True
TENANT_QUOTA_ENABLE = False
_GLOBAL_PRIORITY_GATE = None
_turn_tenant = None

def configure(*, priority_queue_enable=None, tenant_quota_enable=None,
              global_priority_gate=None, turn_tenant=None) -> None:
    """Inject the [dispatch]/[admission] gate switches, the live gate and the tenant hook."""
    global PRIORITY_QUEUE_ENABLE, TENANT_QUOTA_ENABLE, _GLOBAL_PRIORITY_GATE, _turn_tenant
    if priority_queue_enable is not None:
        PRIORITY_QUEUE_ENABLE = priority_queue_enable
    if tenant_quota_enable is not None:
        TENANT_QUOTA_ENABLE = tenant_quota_enable
    if global_priority_gate is not None:
        _GLOBAL_PRIORITY_GATE = global_priority_gate
    if turn_tenant is not None:
        _turn_tenant = turn_tenant

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
