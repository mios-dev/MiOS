# AI-hint: Extracted module for streaming.py.
"""Agent Streaming."""

from __future__ import annotations
import logging

log = logging.getLogger("mios.streaming")

_agent_offload_engine = None
_agent_binding = None
_dispatch_priority = None
_opt_int_mb = None
_admit = None
_SloShed = None
_priority_gate = None
_endpoint_sem = None
_lane_sem = None
_lane_sem_key = None
_model_active = None
_call_agent_stream_inner = None
_strip_agent_chrome = None

def configure(**kwargs):
    globals().update(kwargs)

async def call_agent_stream(name, cfg, body, headers, client, q, *, prefer_cpu=True, priority=None) -> tuple:
    """Bounded STREAMING sibling of _call_agent_complete"""
    _engine = _agent_offload_engine(cfg) if prefer_cpu else None
    _ep, _adm_model = _agent_binding(cfg, _engine)
    _prio = priority if priority is not None else _dispatch_priority(cfg)
    _est = _opt_int_mb(cfg.get("vram_mb"))
    try:
        await _admit(_ep, _adm_model, _engine or _lane_sem_key(cfg), _prio, _est, foreground=False)
    except _SloShed:
        log.info("SLO shed: best_effort fan-out %s dropped under contention", name)
        return name, ""
    async with _priority_gate(_prio):
        async with _endpoint_sem(_ep):
            async with _lane_sem(_engine or _lane_sem_key(cfg)):
                await _model_active(_ep, _adm_model, 1, _est)
                try:
                    _n, _t = await _call_agent_stream_inner(
                        name, cfg, body, headers, client, q, prefer_cpu=prefer_cpu)
                finally:
                    await _model_active(_ep, _adm_model, -1, _est)
                return _n, _strip_agent_chrome(_t)
