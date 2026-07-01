# AI-hint: Shared sub-agent COMPLETION-call primitive extracted verbatim from server.py (refactor R3 dispatch-substrate wave). Holds the HOT _call_agent_complete (the bounded entry point every council secondary AND DAG node dispatches through: it derives the lane binding, runs the capacity-aware _admit gate, drives the RR-preemptible path or the priority/endpoint/lane semaphore stack, marks the model in-flight, records cost, and strips agent chrome) plus its helper _call_agent_complete_inner (the best-effort non-streaming /v1-or-native-ollama call: pipe-side secondary tool-loop, KV fork/paging bracket, outbound auth + turn/trace header propagation, sub-source harvest, think-tag strip, and the P3.2b failover-chain recursion). Keeps its own httpx import. Also OWNS the engine-side actors the inner call routes through -- the KV demand-paging/fork bracket (_kv_base/_kv_filename/_kv_lock/_kv_slot_action/_kv_paging/_kv_fork) and the RR-preemptible chunked decode (_rr_eligible/_rr_slice/_rr_run) -- which moved here from server.py (their only caller is this module) over directly-imported leaf siblings (_endpoint_is_llamacpp from mios_endpoints, the validate_fork/plan_fork/fork_outcome/kv_filename plan from mios_kvfork, the mios_preempt policy) and _AUTH_HOSTPORTS from mios_config; _kv_filename stays SSOT with the server-side KV-GC sweep. Also OWNS _record_cost (the WS-RES-GOV per-dispatch cost recorder), which moved here because _call_agent_complete is its sole caller -- its token estimate routes through the mios_tokenize seam, and its cost-domain deps (the COST_ACCOUNTING_ENABLE flag + the server-owned CostLedger/CostModel instances + the _is_remote_endpoint lane probe) are injected via configure(). Every other server-side symbol it touches (lane semaphores _endpoint_sem/_lane_sem/_priority_gate, _admit/_SloShed, the binding helpers _agent_binding/_agent_offload_engine/_dispatch_priority/_lane_sem_key, _model_active, _apply_outbound_auth, the secondary tool-loops _ollama_secondary_tool_loop/_v1_secondary_tool_loop, the ContextVars _conv_key_var/_dispatch_agent_var/_kv_fork_parent_var, the header/trace helpers _src_turn_key/_hop_via_headers/_current_trace_id, _harvest_sub_sources/_strip_think_tags/_strip_agent_chrome/_trip_breaker/_should_health_probe/_num_predict_cap_for/_opt_int_mb, _AGENT_REGISTRY, the shared KV/priority/preempt state _KV_LOCKS/_KV_RESIDENT/_GLOBAL_PRIORITY_GATE/_PREEMPT/_BACKEND_KEY, and the config scalars HEALTHGATE_*/SECONDARY_TOOL_LOOP/KV_FORK_ENABLE/KV_PAGING_*/RR_*/PRIORITY_QUEUE_ENABLE/_SRC_TURN_HEADER) is dependency-INJECTED via configure() (one-way boundary -- this module NEVER imports server). _endpoint_is_ollama is imported directly from its sibling mios_endpoints. server.py re-imports every moved name verbatim under its original alias (surface-parity zero-diff) and re-injects _AGENT_REGISTRY on live membership reload.
# AI-related: ./server.py, ./mios_config.py, ./mios_endpoints.py, ./mios_kvfork.py, ./mios_preempt.py, ./mios_tokenize.py, ./mios_cost.py, ./mios_fanout.py, ./test_mios_agent_call.py
# AI-functions: _call_agent_complete, _call_agent_complete_inner, _call_agent_stream_inner, configure, _record_cost, _kv_base, _kv_filename, _kv_lock, _kv_slot_action, _kv_paging, _kv_fork, _rr_eligible, _rr_slice, _rr_run
"""Shared sub-agent completion-call primitive (council secondaries + DAG nodes).

Extracted verbatim from ``server.py``. ``_call_agent_complete`` is the bounded
dispatch entry point (admission + per-lane semaphores + RR preemption + cost +
chrome strip); ``_call_agent_complete_inner`` is its best-effort non-streaming
/v1-or-native call with the pipe-side secondary tool-loop, KV fork/paging
bracket, outbound auth, source harvest and the P3.2b failover-chain recursion.

The moved bodies are unchanged. ``_endpoint_is_ollama`` is imported directly
from its sibling module ``mios_endpoints``; every other server-side symbol the
two functions touch (the lane semaphores, the binding/priority helpers, the
secondary tool-loops, the KV helpers, the ContextVars, the header/trace helpers,
the agent registry and the config scalars) is injected via :func:`configure`
(one-way module boundary -- this module never imports ``server``). ``server.py``
re-imports both names under their original aliases so the public surface stays
byte-identical, and re-injects the agent registry on a live membership reload.
"""

from __future__ import annotations

import asyncio
import contextlib
import httpx
import json
import logging
import time
from typing import Optional

from mios_config import _AUTH_HOSTPORTS, _DISPATCH_TOML
import os
KV_SLOTS_DIR = (os.environ.get("MIOS_KV_SLOTS_DIR", "")
                or str(_DISPATCH_TOML.get("kv_slots_dir", "") or "")).strip()
from mios_endpoints import _endpoint_is_ollama, _endpoint_is_llamacpp
from mios_jsonsalvage import loads_lenient as _loads_lenient
from mios_kvfork import (validate_fork as _kvfork_validate,
                         plan_fork as _kvfork_plan,
                         fork_outcome as _kvfork_outcome,
                         kv_filename as _kvfork_kv_filename)
import mios_preempt
import mios_tokenize

log = logging.getLogger("mios-agent-pipe")


# -- Dependency-injection seam --------------------------------------
# The two dispatch functions read server.py's config scalars and call back into
# the lane/admission gates, the binding helpers, the secondary tool-loops, the
# KV helpers and the header/trace helpers. server.py calls configure() with those
# AFTER every one is defined (one-way boundary: this module never imports
# server). The placeholders below carry the documented defaults so a standalone
# ``import mios_agent_call`` still succeeds; every consumer is async/runtime so
# nothing fires before configure() runs.

# config scalars (server SSOT/env-derived; injected at import-completion)
HEALTHGATE_CONNECT_TIMEOUT = 6.0
HEALTHGATE_READ_TIMEOUT = 120.0
SECONDARY_TOOL_LOOP = True
KV_FORK_ENABLE = False
_SRC_TURN_HEADER = "X-MiOS-Turn"
# KV-paging + RR-preemption config scalars (server SSOT/env-derived; injected).
# Booleans default OFF so the moved engine actors stay inert until configure().
KV_PAGING_ENABLE = False
KV_PAGING_SLOT = 0
KV_PAGING_TIMEOUT = 12.0
KV_SLOT_PERSIST = True
RR_ENABLE = False
PRIORITY_QUEUE_ENABLE = False
RR_SLICE_TOKENS = 512
RR_SLICE_TIMEOUT = 120.0
RR_QUANTUM_S = 8.0
# Per-dispatch num_predict ceilings (server SSOT [dispatch].ollama_num_predict_cap*
# / env-derived; injected). _num_predict_cap_for (moved below) picks the CPU cap on
# a slow lane, the full cap otherwise. Documented defaults so a standalone import
# still resolves a ceiling; configure() overrides them from the live SSOT.
OLLAMA_NUM_PREDICT_CAP = 2048
OLLAMA_NUM_PREDICT_CAP_CPU = 512

# mutable registry (injected BY REFERENCE; re-injected on live membership reload)
_AGENT_REGISTRY: dict = {}

# shared KV/priority/preempt state owned by server (injected BY REFERENCE so the
# moved _kv_* mutations and the server-side KV-GC sweep observe the SAME dicts).
_KV_LOCKS: dict = {}
_KV_RESIDENT: dict = {}
_BACKEND_KEY = ""
_GLOBAL_PRIORITY_GATE = None
_PREEMPT = None
# dead-node liveness map (server-owned; injected BY REFERENCE so _trip_breaker's
# breaker-open write is observed by mios_turn's prune + the server liveness probe,
# which share the SAME dict). name -> (probed_ts, reachable).
_NODE_LIVE: dict = {}

# server-side helpers / ContextVars / exception class (injected)
_SloShed = None
_admit = None
_agent_binding = None
_agent_offload_engine = None
_apply_outbound_auth = None
_conv_key_var = None
_current_trace_id = None
_dispatch_agent_var = None
_dispatch_priority = None
_endpoint_sem = None
_harvest_sub_sources = None
_hop_via_headers = None
_kv_fork_parent_var = None
_lane_sem = None
_lane_sem_key = None
_model_active = None
# _num_predict_cap_for + _trip_breaker are now NATIVE to this module (moved from
# server.py -- the dispatch path below is their sole caller). _is_slow_lane_ep (the
# CPU/iGPU lane probe _num_predict_cap_for branches on) stays server-owned and is
# injected, since mios_swarm consumes it too.
_is_slow_lane_ep = None
_ollama_secondary_tool_loop = None
_opt_int_mb = None
_priority_gate = None
_should_health_probe = None
_src_turn_key = None
_strip_agent_chrome = None
_strip_think_tags = None
_v1_secondary_tool_loop = None

# WS-RES-GOV cost accounting (injected). _record_cost is now NATIVE to this module
# (this module is its sole caller), so it reads these directly instead of being
# injected as a function. The CostLedger/CostModel instances stay SERVER-owned
# (shared by reference with /v1/cost + the native loop); the enable flag + the
# _is_remote_endpoint lane probe are injected too. Default-off so cost recording
# is a no-op until configured (degrade-open: accounting must never break a turn).
COST_ACCOUNTING_ENABLE = False
_COST_LEDGER = None
_COST_MODEL = None
_is_remote_endpoint = None

_otel_tracer = None


def configure(*, healthgate_connect_timeout=None, healthgate_read_timeout=None,
              secondary_tool_loop=None, kv_fork_enable=None, src_turn_header=None,
              agent_registry=None, sloshed=None, admit=None, agent_binding=None,
              agent_offload_engine=None, apply_outbound_auth=None,
              conv_key_var=None, current_trace_id=None, dispatch_agent_var=None,
              dispatch_priority=None, endpoint_sem=None, harvest_sub_sources=None,
              hop_via_headers=None, kv_fork_parent_var=None,
              lane_sem=None, lane_sem_key=None, model_active=None,
              ollama_secondary_tool_loop=None,
              opt_int_mb=None, priority_gate=None,
              cost_accounting_enable=None, cost_ledger=None, cost_model=None,
              is_remote_endpoint=None, is_slow_lane_ep=None, node_live=None,
              ollama_num_predict_cap=None, ollama_num_predict_cap_cpu=None,
              should_health_probe=None,
              src_turn_key=None, strip_agent_chrome=None, strip_think_tags=None,
              v1_secondary_tool_loop=None,
              kv_paging_enable=None, kv_paging_slot=None, kv_paging_timeout=None,
              kv_slot_persist=None,
              rr_enable=None, priority_queue_enable=None, rr_slice_tokens=None,
              rr_slice_timeout=None, rr_quantum_s=None, kv_locks=None,
              kv_resident=None, backend_key=None, global_priority_gate=None,
              preempt=None, otel_tracer=None) -> None:
    """Inject server.py's config scalars, the agent registry, the lane/admission
    gates, the binding/priority helpers, the secondary tool-loops, the KV helpers
    and the header/trace helpers the two dispatch functions call back into."""
    global HEALTHGATE_CONNECT_TIMEOUT, HEALTHGATE_READ_TIMEOUT
    global SECONDARY_TOOL_LOOP, KV_FORK_ENABLE, _SRC_TURN_HEADER, _AGENT_REGISTRY
    global _SloShed, _admit, _agent_binding, _agent_offload_engine
    global _apply_outbound_auth, _conv_key_var, _current_trace_id
    global _dispatch_agent_var, _dispatch_priority, _endpoint_sem
    global _harvest_sub_sources, _hop_via_headers, _kv_fork_parent_var
    global _lane_sem, _lane_sem_key, _model_active
    global _ollama_secondary_tool_loop, _opt_int_mb
    global _priority_gate, _is_slow_lane_ep, _NODE_LIVE
    global OLLAMA_NUM_PREDICT_CAP, OLLAMA_NUM_PREDICT_CAP_CPU
    global COST_ACCOUNTING_ENABLE, _COST_LEDGER, _COST_MODEL, _is_remote_endpoint
    global _should_health_probe, _src_turn_key, _strip_agent_chrome
    global _strip_think_tags, _v1_secondary_tool_loop
    global KV_PAGING_ENABLE, KV_PAGING_SLOT, KV_PAGING_TIMEOUT, RR_ENABLE
    global PRIORITY_QUEUE_ENABLE, RR_SLICE_TOKENS, RR_SLICE_TIMEOUT, RR_QUANTUM_S
    global _KV_LOCKS, _KV_RESIDENT, _BACKEND_KEY, _GLOBAL_PRIORITY_GATE, _PREEMPT
    global KV_SLOT_PERSIST
    global _otel_tracer
    if otel_tracer is not None:
        _otel_tracer = otel_tracer
    if healthgate_connect_timeout is not None:
        HEALTHGATE_CONNECT_TIMEOUT = healthgate_connect_timeout
    if healthgate_read_timeout is not None:
        HEALTHGATE_READ_TIMEOUT = healthgate_read_timeout
    if secondary_tool_loop is not None:
        SECONDARY_TOOL_LOOP = secondary_tool_loop
    if kv_fork_enable is not None:
        KV_FORK_ENABLE = kv_fork_enable
    if src_turn_header is not None:
        _SRC_TURN_HEADER = src_turn_header
    if agent_registry is not None:
        _AGENT_REGISTRY = agent_registry
    if sloshed is not None:
        _SloShed = sloshed
    if admit is not None:
        _admit = admit
    if agent_binding is not None:
        _agent_binding = agent_binding
    if agent_offload_engine is not None:
        _agent_offload_engine = agent_offload_engine
    if apply_outbound_auth is not None:
        _apply_outbound_auth = apply_outbound_auth
    if conv_key_var is not None:
        _conv_key_var = conv_key_var
    if current_trace_id is not None:
        _current_trace_id = current_trace_id
    if dispatch_agent_var is not None:
        _dispatch_agent_var = dispatch_agent_var
    if dispatch_priority is not None:
        _dispatch_priority = dispatch_priority
    if endpoint_sem is not None:
        _endpoint_sem = endpoint_sem
    if harvest_sub_sources is not None:
        _harvest_sub_sources = harvest_sub_sources
    if hop_via_headers is not None:
        _hop_via_headers = hop_via_headers
    if kv_fork_parent_var is not None:
        _kv_fork_parent_var = kv_fork_parent_var
    if lane_sem is not None:
        _lane_sem = lane_sem
    if lane_sem_key is not None:
        _lane_sem_key = lane_sem_key
    if model_active is not None:
        _model_active = model_active
    if ollama_secondary_tool_loop is not None:
        _ollama_secondary_tool_loop = ollama_secondary_tool_loop
    if opt_int_mb is not None:
        _opt_int_mb = opt_int_mb
    if priority_gate is not None:
        _priority_gate = priority_gate
    if cost_accounting_enable is not None:
        COST_ACCOUNTING_ENABLE = cost_accounting_enable
    if cost_ledger is not None:
        _COST_LEDGER = cost_ledger
    if cost_model is not None:
        _COST_MODEL = cost_model
    if is_remote_endpoint is not None:
        _is_remote_endpoint = is_remote_endpoint
    if is_slow_lane_ep is not None:
        _is_slow_lane_ep = is_slow_lane_ep
    if node_live is not None:
        _NODE_LIVE = node_live
    if ollama_num_predict_cap is not None:
        OLLAMA_NUM_PREDICT_CAP = ollama_num_predict_cap
    if ollama_num_predict_cap_cpu is not None:
        OLLAMA_NUM_PREDICT_CAP_CPU = ollama_num_predict_cap_cpu
    if should_health_probe is not None:
        _should_health_probe = should_health_probe
    if src_turn_key is not None:
        _src_turn_key = src_turn_key
    if strip_agent_chrome is not None:
        _strip_agent_chrome = strip_agent_chrome
    if strip_think_tags is not None:
        _strip_think_tags = strip_think_tags
    if v1_secondary_tool_loop is not None:
        _v1_secondary_tool_loop = v1_secondary_tool_loop
    # KV-paging + RR-preemption config scalars + the shared KV/priority/preempt
    # state owned by server (mutable dicts/objects injected BY REFERENCE).
    if kv_paging_enable is not None:
        KV_PAGING_ENABLE = kv_paging_enable
    if kv_paging_slot is not None:
        KV_PAGING_SLOT = kv_paging_slot
    if kv_paging_timeout is not None:
        KV_PAGING_TIMEOUT = kv_paging_timeout
    if kv_slot_persist is not None:
        KV_SLOT_PERSIST = kv_slot_persist
    KV_PAGING_ENABLE = KV_PAGING_ENABLE and KV_SLOT_PERSIST
    if rr_enable is not None:
        RR_ENABLE = rr_enable
    if priority_queue_enable is not None:
        PRIORITY_QUEUE_ENABLE = priority_queue_enable
    if rr_slice_tokens is not None:
        RR_SLICE_TOKENS = rr_slice_tokens
    if rr_slice_timeout is not None:
        RR_SLICE_TIMEOUT = rr_slice_timeout
    if rr_quantum_s is not None:
        RR_QUANTUM_S = rr_quantum_s
    if kv_locks is not None:
        _KV_LOCKS = kv_locks
    if kv_resident is not None:
        _KV_RESIDENT = kv_resident
    if backend_key is not None:
        _BACKEND_KEY = backend_key
    if global_priority_gate is not None:
        _GLOBAL_PRIORITY_GATE = global_priority_gate
    if preempt is not None:
        _PREEMPT = preempt


# ── Moved from server.py (strangler-fig): the per-dispatch lane-governance pair the
# dispatch path is the SOLE caller of, so they live with their caller (the injections
# were reversed). _trip_breaker opens the dead-node circuit breaker; _num_predict_cap_for
# picks the per-lane token ceiling. Their server-owned deps -- the _should_health_probe /
# _is_slow_lane_ep lane probes, the shared _NODE_LIVE map, and the SSOT num_predict caps --
# are dependency-injected via configure() (one-way boundary: never imports server).
def _trip_breaker(name: str, cfg: dict) -> None:
    """Open the circuit for a REMOTE agent that just failed a dispatch: mark it
    DOWN in _NODE_LIVE so the next turn prunes it (no repeated inline retries on a
    dead node -- reachability becomes a precondition, retries go off the hot path).
    No-op for local lanes (a transient local error must not strand a core agent for
    the whole TTL). Rejoins automatically when the TTL re-probe finds it back up."""
    try:
        if name and _should_health_probe(cfg):
            _NODE_LIVE[str(name)] = (time.time(), False)
    except Exception:  # noqa: BLE001
        pass


def _num_predict_cap_for(ep: str) -> int:
    """Token ceiling for THIS dispatch -- the short slow-lane cap on a CPU/iGPU
    endpoint, the full cap otherwise (runaway fix: a slow lane can't be allowed to
    grind a full-length generation for hundreds of seconds of pegged cores)."""
    return OLLAMA_NUM_PREDICT_CAP_CPU if _is_slow_lane_ep(ep) else OLLAMA_NUM_PREDICT_CAP


# ── Moved from server.py (strangler-fig): cost recording is driven ONLY by
# _call_agent_complete below, so it lives with its sole caller (the injection was
# reversed). De-hardcoded on the move: the prompt/completion token estimate now
# routes through the mios_tokenize seam (the shared ~chars/token measure) instead
# of an inline `// 4` literal -- byte-identical under the default heuristic backend.
def _record_cost(cfg: dict, ep: str, t0: float, body: dict, text: str) -> None:
    """WS-RES-GOV observe-only: record one dispatch's energy/$ cost into the
    ledger. No-op unless COST_ACCOUNTING_ENABLE; degrade-open (accounting must
    never break a turn). Token counts come from the tokenizer seam (energy is
    dominated by elapsed x watts; tokens matter only for a remote $/Mtok lane)."""
    if not COST_ACCOUNTING_ENABLE:
        return
    try:
        _msgs = (body or {}).get("messages") or []
        _ptok = mios_tokenize.count_messages(_msgs)
        _ctok = mios_tokenize.count_text(text)
        _COST_LEDGER.record(_COST_MODEL.estimate(
            lane=_lane_sem_key(cfg), elapsed_s=max(0.0, time.time() - t0),
            prompt_tokens=_ptok, completion_tokens=_ctok,
            is_remote=_is_remote_endpoint(ep)))
    except Exception:  # noqa: BLE001
        pass


# ── Moved verbatim from server.py (refactor R3 dispatch-substrate) ─────────────
async def _call_agent_complete(name, cfg, body, headers, client,
                               *, prefer_cpu: bool = True,
                               priority: Optional[float] = None) -> tuple:
    """Bounded entry point (/24): concurrent agent dispatches
    -- council secondaries AND DAG-level nodes -- acquire the PER-LANE semaphore
    for the engine/node they actually run on, so distinct hardware (dGPU, CPU,
    iGPU, accelerator, each remote node) all fire CONCURRENTLY and only same-lane
    agents queue. No nested agent calls, so no deadlock. `priority` feeds the
    capacity-aware _admit gate; default None -> lane-derived (_dispatch_priority)
 so slow/remote lanes self-shed under load ('all nodes
    enabled by default')."""
    _engine = _agent_offload_engine(cfg) if prefer_cpu else None
    _ep, _adm_model = _agent_binding(cfg, _engine)
    _prio = priority if priority is not None else _dispatch_priority(cfg)
    # Capacity-aware admission BEFORE the semaphores (no-op unless ADMIT_ENABLE;
    # degrade-open -- never blocks a turn). Endpoint cap OUTER (serialize cold-
    # loads on ONE ollama daemon), lane cap INNER (hardware category) -- operator
    # thundering-herd fix.
    _est = _opt_int_mb(cfg.get("vram_mb"))   # Phase-1 per-worker VRAM (0 = unknown)
    try:
        # foreground=False: this is the fan-out / secondary dispatch -- background
        # work that IS shed-eligible (best_effort) under contention (the merge
        # degrades gracefully when a node drops). A genuine foreground turn keeps
        # the protective default (interactive, never shed).
        await _admit(_ep, _adm_model, _engine or _lane_sem_key(cfg), _prio, _est,
                     foreground=False)
    except _SloShed:  # WS-SCHED-SLO: best_effort shed -> drop this node from the merge
        log.info("SLO shed: best_effort fan-out %s dropped under contention", name)
        return name, ""
    # WS-A12: RR-preemptible path. This fn IS the fan-out/secondary dispatch (the
    # work that SHOULD yield a lane to a higher-priority waiter), so when RR is on
    # and this is a plain completion on a /slots lane, drive it through _rr_run --
    # which OWNS the priority gate itself (release/re-acquire across preemptions),
    # so it runs UNDER the endpoint+lane caps but NOT _priority_gate (single gate
    # owner = no double-accounting). Default-off => the else-branch below is the
    # unchanged, proven path.
    if _rr_eligible(body, _ep, cfg, _engine):
        async with _endpoint_sem(_ep):
            async with _lane_sem(_engine or _lane_sem_key(cfg)):
                await _model_active(_ep, _adm_model, 1, _est)
                try:
                    _conv = _conv_key_var.get() or name
                    _t = await _rr_run(client, _ep, _adm_model,
                                       body.get("messages") or [], conv=_conv,
                                       priority=_prio, max_tokens=body.get("max_tokens"),
                                       headers=headers)
                finally:
                    await _model_active(_ep, _adm_model, -1, _est)
                return name, _strip_agent_chrome(_t)
    # Global host cap OUTERMOST (bounds TOTAL running dispatches across all lanes
    # so a wide all-nodes fan-out can't sum past host capacity), then endpoint,
    # then lane.
    async with _priority_gate(_prio):
        async with _endpoint_sem(_ep):
            async with _lane_sem(_engine or _lane_sem_key(cfg)):
                # Mark the model in-flight so idle-VRAM reclaim won't evict it.
                await _model_active(_ep, _adm_model, 1, _est)
                _cost_t0 = time.time()
                try:
                    _n, _t = await _call_agent_complete_inner(
                        name, cfg, body, headers, client, prefer_cpu=prefer_cpu)
                finally:
                    await _model_active(_ep, _adm_model, -1, _est)
                _record_cost(cfg, _ep, _cost_t0, body, _t)   # WS-RES-GOV observe-only
                return _n, _strip_agent_chrome(_t)


async def _call_agent_complete_inner(name: str, cfg: dict, body: dict,
                               headers: dict, client,
                               *, prefer_cpu: bool = True,
                               _failover_depth: int = 0) -> tuple:
    if _otel_tracer:
        from opentelemetry.trace import SpanKind
        req_model = body.get("model") or cfg.get("model") or ""
        with _otel_tracer.start_as_current_span(
            "invoke_agent",
            kind=SpanKind.CLIENT,
            attributes={
                "gen_ai.system": "mios",
                "gen_ai.request.model": req_model,
                "session_id": (_conv_key_var.get() if _conv_key_var else "") or "",
            }
        ) as span:
            res_name, res_text = await _call_agent_complete_inner_orig(
                name, cfg, body, headers, client,
                prefer_cpu=prefer_cpu, _failover_depth=_failover_depth
            )
            _eng = _agent_offload_engine(cfg) if prefer_cpu else None
            _, _mdl = _agent_binding(cfg, _eng)
            actual_model = _mdl or cfg.get("model") or ""
            if actual_model:
                span.set_attribute("gen_ai.response.model", actual_model)
            return res_name, res_text
    else:
        return await _call_agent_complete_inner_orig(
            name, cfg, body, headers, client,
            prefer_cpu=prefer_cpu, _failover_depth=_failover_depth
        )


async def _call_agent_complete_inner_orig(name: str, cfg: dict, body: dict,
                               headers: dict, client,
                               *, prefer_cpu: bool = True,
                               _failover_depth: int = 0) -> tuple:
    """Best-effort non-streaming /v1 call to a secondary fan-out agent.
    Returns (name, text); text='' -> dropped from the merge. A dead or
    absent endpoint (e.g. opencode :8633 when not served as /v1) just
    yields '' and is skipped, so fan-out degrades to the live agents.

 CPU-lane offload : a secondary always runs
    CONCURRENTLY with the GPU primary, so if the agent declares a CPU
    twin (cpu_endpoint/cpu_model -> mios-*-cpu Modelfile on :11435) we
    dispatch THAT -- the secondary works on the light iGPU/CPU lane while
    the dGPU stays dedicated to the primary. No twin -> its own endpoint.

    An ollama-lane endpoint (the :11434/:11435 instances, incl. every CPU
    twin) is called via the NATIVE /api/chat with think=False -- the same
    fix refine/polish use: a qwen3 model on the /v1 compat path dumps its
 answer into message.reasoning with EMPTY content,
    so a /v1 secondary folds in nothing. Custom gateways (opencode :8633,
    hermes :8642) are not ollama -> stay on /v1/chat/completions.

 P3.2b AUTO-FAILOVER ('remove SPOFs'): when a
    transport-level failure (unreachable endpoint, non-200, timeout)
    leaves THIS hop empty AND the agent declares a failover_agents chain
    (mios.toml SSOT), retry the SAME body against the next live agent in
    the chain. _failover_depth bounds the recursion + skips already-visited
    names. A semantically-empty answer (model returned content="") DOES NOT
    trigger failover -- the agent succeeded; the council merge handles
    quality. Only TRANSPORT failure flips us into failover."""
    _dispatch_agent_var.set(name)  # WS-A9: scope the dispatching agent for the PDP gate
    # prefer_cpu (fan-out secondaries): offload to the agent's CPU twin so
    # it runs concurrent with the GPU primary. prefer_cpu=False (planner
    # agent-task nodes): use the agent's PRIMARY endpoint/model -- a coding
    # sub-task must hit opencode proper, not a small CPU twin.
    # Resolve (endpoint, model) for THIS dispatch via the agent's engine/node
    # binding map. prefer_cpu (fan-out secondaries) offloads to a LIGHT engine
    # the agent declares (cpu/igpu/accelerator) so it runs concurrent with the
    # GPU primary; prefer_cpu=False (planner agent-task nodes) uses the default
    # binding. Any agent can now run on any engine OR node it binds.
    _eng = _agent_offload_engine(cfg) if prefer_cpu else None
    ep, _mdl = _agent_binding(cfg, _eng)
    # P3.2b: failover helper -- iterate the declared chain in order, recurse
    # into this same function so each hop inherits the same body + headers and
    # the bounded depth keeps a misconfigured cycle from spinning.
    async def _try_failover(reason: str) -> tuple:
        if _failover_depth >= 3:
            return name, ""
        for fname in (cfg.get("failover_agents") or []):
            fcfg = _AGENT_REGISTRY.get(fname)
            if not isinstance(fcfg, dict):
                continue
            rn, rt = await _call_agent_complete_inner(
                fname, fcfg, body, headers, client,
                prefer_cpu=False,
                _failover_depth=_failover_depth + 1)
            if rt and rt.strip():
                log.info("failover: %s -> %s (%s) ok", name, fname, reason)
                return rn, rt
        return name, ""
    if not ep:
        rn, rt = await _try_failover("no endpoint")
        if rt and rt.strip():
            return rn, rt
        return name, ""
    # ollama lanes speak the native API + honour think=False; the bespoke
    # sub-agent servers do not. Detect by the SSOT lane ports.
    _is_ollama = _endpoint_is_ollama(ep, cfg, _eng)
    # health-gated client node (mobile / Tailscale-hosted): SHORT timeout so a
    # sleeping/absent node drops from the merge fast instead of stalling.
    # health-gated nodes: a SHORT CONNECT timeout drops an ABSENT node (e.g. the
    # phone asleep) from the merge fast, but a GENEROUS READ timeout lets a
    # PRESENT-but-slow node still generate. A flat 2.5s total read-timed-out the
    # Windows iGPU (mios-reasoner-cpu, ~13 tok/s: prefill+TTFB > 2.5s) so it was
    # dispatched but contributed nothing ("fanout secondary ... failed:").
    _to = (httpx.Timeout(connect=HEALTHGATE_CONNECT_TIMEOUT,
                         read=HEALTHGATE_READ_TIMEOUT, write=10.0, pool=10.0)
           if _should_health_probe(cfg) else None)
    try:
        if _is_ollama:
            base = ep[:-3].rstrip("/") if ep.endswith("/v1") else ep
            _msgs = body.get("messages") or []
            # Pipe-side tool-loop for a raw ollama worker (
            # "all tools to all agents"): resolve its tool_calls (web_search etc.;
            # write/launch via the broker when allow_write) before the final
            # answer so it GROUNDS in live output, not fabrication. Mirrors the
            # streaming path; no-op when disabled or no tools.
            if SECONDARY_TOOL_LOOP and body.get("tools"):
                _msgs = await _ollama_secondary_tool_loop(
                    client, base, _mdl or cfg.get("model"), _msgs,
                    body["tools"], _to, lambda _s: None,
                    num_ctx=body.get("num_ctx"),
                    allow_write=bool(body.get("_allow_write")))
            payload = {
                "model": _mdl or cfg.get("model"),
                "messages": _msgs,
                "stream": False,
            }
            _opts2: dict = {}
            _np_cap = _num_predict_cap_for(ep)
            _opts2["num_predict"] = (min(int(body["max_tokens"]), _np_cap)
                                     if body.get("max_tokens") else _np_cap)
            if body.get("num_ctx"):
                _opts2["num_ctx"] = int(body["num_ctx"])
            if _opts2:
                payload["options"] = _opts2
            # Note: 'think' is an Ollama native extension; for /v1 we omit it or
            # rely on the model/backend default.
            _oll_hdrs = {"Content-Type": "application/json"}
            _tk = _src_turn_key()
            if _tk:   # propagate the turn-id so a re-entrant sub-request's sources
                _oll_hdrs[_SRC_TURN_HEADER] = _tk   # land in the parent turn bucket
            _oll_hdrs.update(_hop_via_headers())   # P0 cross-hop recursion bound
            # FED-G2 follow-up: attach the OUTBOUND credential for `base` (shared key for
            # a local lane, the per-agent header for a remote/federated endpoint). Was
            # omitted on this shim path -> a keyed remote peer reached here got no auth.
            # Idempotent + degrade-open: a keyless endpoint gets no header (no-op today).
            _apply_outbound_auth(_oll_hdrs, base)
            r = await client.post(
                f"{base}/v1/chat/completions",
                content=json.dumps(payload).encode("utf-8"),
                headers=_oll_hdrs, timeout=_to)
            if r.status_code != 200:
                rn, rt = await _try_failover(f"ollama /v1 {r.status_code}")
                if rt and rt.strip():
                    return rn, rt
                return name, ""
            _rj = r.json()
            choices = (_rj.get("choices") or [])
            msg = (choices[0].get("message") if choices else {})
            _content = str(msg.get("content") or "")
            try:   # harvest the sub-agent's real sources into THIS (parent) turn
                _harvest_sub_sources(_rj, _content)
            except Exception:  # noqa: BLE001
                pass
            return name, _strip_think_tags(_content)
        nb = dict(body)
        nb["stream"] = False
        # Private worker-loop signalling keys are ollama-side only -- never send
        # them to a strict /v1 gateway (it may reject unknown fields).
        nb.pop("_allow_write", None)
        nb.pop("num_ctx", None)
        # /v1 ignores ollama options.num_predict/think -> set max_tokens + disable
        # the thinking channel so the DAG node renders content (not an empty answer
        # the synth merge then drops -> merged_chars=0;).
        if not nb.get("max_tokens"):
            _np = (nb.get("options") or {}).get("num_predict")
            nb["max_tokens"] = int(_np) if _np else _num_predict_cap_for(ep)
        nb.pop("options", None)
        nb.pop("think", None)
        nb.setdefault("chat_template_kwargs", {"enable_thinking": False})
        if _mdl:
            nb["model"] = _mdl
        # The Hermes gateway (:8642) enforces Authorization: Bearer <key>; the
        # fanout/DAG dispatch path never attached it, so hermes facets 401'd and
        # silently dropped from the merge -- leaving only the weaker CPU/code
        # agents (swarm non-answer). Attach the backend key
        # when THIS dispatch targets the Hermes backend and no auth was already
        # supplied; scoped to the backend netloc so the key never reaches a
        # non-backend node (opencode/daemon/ollama don't enforce it anyway).
        _hdrs = dict(headers or {})
        # WS-FED/G2: shared backend key for a local lane, or this agent's OWN
        # header for a remote/federated endpoint (see _apply_outbound_auth).
        _apply_outbound_auth(_hdrs, ep)
        # Propagate the turn-id so a sub-request that re-enters :8640 records its
        # web_search sources into the PARENT turn's registry bucket (cross-agent
        # source unification). Harmless on a leaf endpoint (ignored).
        _tk = _src_turn_key()
        if _tk:
            _hdrs[_SRC_TURN_HEADER] = _tk
        _hdrs.update(_hop_via_headers())   # P0 cross-hop recursion bound
        # WS-A8: propagate the request trace id to the Hermes hop so a downstream
        # re-entry continues THIS request's trace (it adopts X-MiOS-Trace at the top).
        _tid = _current_trace_id()
        if _tid:
            _hdrs["X-MiOS-Trace"] = _tid
        # WS-A4: KV-cache FORK for a fan-out child. When KV_FORK_ENABLE and this
        # dispatch is a swarm/DAG child (a parent conv is set), branch the parent's
        # saved KV into a child file (mios-kv-<parent>#fork:<node>) so the node
        # warm-starts from the SHARED PREFIX, then page the forked child below.
        # Fully inert by default: _kv_fork self-guards (disabled / non-llama.cpp ->
        # no-op) and degrades open; the parent var is "" on the primary path.
        _kv_parent = _kv_fork_parent_var.get() or ""
        if KV_FORK_ENABLE and _kv_parent and _kv_parent != (_conv_key_var.get() or ""):
            _child_conv = f"{_kv_parent}#fork:{name}"
            try:
                if (await _kv_fork(client, ep, cfg, _eng, _kv_parent, _child_conv)).get("forked"):
                    _conv_key_var.set(_child_conv)   # page the forked child slot file
            except Exception:  # noqa: BLE001 -- degrade-open: a fork miss -> cold start
                pass
        # KV-paging bracket : on a llama.cpp endpoint, page
        # THIS conversation's KV into the slot (saving whoever held it) before the
        # tool-loop + final completion, holding the slot across the bracket so a
        # concurrent conversation can't evict it mid-flight. No-op everywhere else.
        async with _kv_paging(client, ep, cfg, _eng):
            # Pipe-side OpenAI tool-loop ("full loop until
            # satisfied"): resolve the /v1 agent's read-only tool_calls --
            # rescuing a narrated call -- before the final non-streaming answer.
            # No-op when the agent self-loops or offers no tools.
            if SECONDARY_TOOL_LOOP and body.get("tools"):
                sess_id = (_conv_key_var.get() if _conv_key_var else None) or None
                nb["messages"] = await _v1_secondary_tool_loop(
                    client, ep, nb.get("model") or cfg.get("model"),
                    headers, nb.get("messages") or [], body["tools"], _to,
                    lambda _s: None, session_id=sess_id)
            r = await client.post(
                f"{ep}/chat/completions",
                content=json.dumps(nb).encode("utf-8"), headers=_hdrs,
                timeout=_to)
        if r.status_code != 200:
            rn, rt = await _try_failover(f"http {r.status_code}")
            if rt and rt.strip():
                return rn, rt
            return name, ""
        _rj = r.json()
        ch = (_rj.get("choices") or [])
        msg = (ch[0].get("message") if ch else {}) or {}
        _content = str(msg.get("content") or "")
        try:   # harvest the sub-agent's real sources into THIS (parent) turn
            _harvest_sub_sources(_rj, _content)
        except Exception:  # noqa: BLE001
            pass
        return name, _strip_think_tags(_content)
    except Exception as e:
        log.info("fanout secondary %s failed: %s", name, e)
        # Circuit-breaker: a REMOTE node that just failed (e.g. the phone offline ->
        # 'All connection attempts failed') is marked DOWN so the next turn prunes
        # it instead of re-dispatching + retrying it.
        _trip_breaker(name, cfg)
        rn, rt = await _try_failover(f"exception {type(e).__name__}")
        if rt and rt.strip():
            return rn, rt
        return name, ""


# ── Streaming sibling moved verbatim from server.py (refactor dispatch-substrate) ──
async def _call_agent_stream_inner(name: str, cfg: dict, body: dict,
                                   headers: dict, client, q,
                                   *, prefer_cpu: bool = True) -> tuple:
    if _otel_tracer:
        from opentelemetry.trace import SpanKind
        req_model = body.get("model") or cfg.get("model") or ""
        with _otel_tracer.start_as_current_span(
            "invoke_agent",
            kind=SpanKind.CLIENT,
            attributes={
                "gen_ai.system": "mios",
                "gen_ai.request.model": req_model,
                "session_id": (_conv_key_var.get() if _conv_key_var else "") or "",
            }
        ) as span:
            res_name, res_text = await _call_agent_stream_inner_orig(
                name, cfg, body, headers, client, q,
                prefer_cpu=prefer_cpu
            )
            _eng = _agent_offload_engine(cfg) if prefer_cpu else None
            _, _mdl = _agent_binding(cfg, _eng)
            actual_model = _mdl or cfg.get("model") or ""
            if actual_model:
                span.set_attribute("gen_ai.response.model", actual_model)
            return res_name, res_text
    else:
        return await _call_agent_stream_inner_orig(
            name, cfg, body, headers, client, q,
            prefer_cpu=prefer_cpu
        )


async def _call_agent_stream_inner_orig(name: str, cfg: dict, body: dict,
                                   headers: dict, client, q,
                                   *, prefer_cpu: bool = True) -> tuple:
    _dispatch_agent_var.set(name)  # WS-A9: scope the dispatching agent for the PDP gate
    # Resolve (endpoint, model) for THIS dispatch via the agent's engine/node
    # binding map. prefer_cpu (fan-out secondaries) offloads to a LIGHT engine
    # the agent declares (cpu/igpu/accelerator) so it runs concurrent with the
    # GPU primary; prefer_cpu=False (planner agent-task nodes) uses the default
    # binding. Any agent can now run on any engine OR node it binds.
    _eng = _agent_offload_engine(cfg) if prefer_cpu else None
    ep, _mdl = _agent_binding(cfg, _eng)
    if not ep:
        return name, ""
    _is_ollama = _endpoint_is_ollama(ep, cfg, _eng)
    # health-gated nodes: a SHORT CONNECT timeout drops an ABSENT node (e.g. the
    # phone asleep) from the merge fast, but a GENEROUS READ timeout lets a
    # PRESENT-but-slow node still generate. A flat 2.5s total read-timed-out the
    # Windows iGPU (mios-reasoner-cpu, ~13 tok/s: prefill+TTFB > 2.5s) so it was
    # dispatched but contributed nothing ("fanout secondary ... failed:").
    _to = (httpx.Timeout(connect=HEALTHGATE_CONNECT_TIMEOUT,
                         read=HEALTHGATE_READ_TIMEOUT, write=10.0, pool=10.0)
           if _should_health_probe(cfg) else None)
    parts: list = []

    def _push(frag: str) -> None:
        if frag and q is not None:
            try:
                # Tagged event for the orchestrator's MERGED event queue:
                # ("SF", agent_name, fragment). Distinguishes secondary
                # fragments from the primary's ("PR"/"PT"/"PD") events.
                q.put_nowait(("SF", name, frag))
            except Exception:
                pass

    try:
        if _is_ollama:
            base = ep[:-3].rstrip("/") if ep.endswith("/v1") else ep
            _omdl = _mdl or cfg.get("model")
            _omsgs = body.get("messages") or []
            # LIVE tool-loop for this raw ollama secondary:
            # resolve its READ-only tool_calls pipe-side first (web tools + state),
            # then stream the grounded answer. Skipped when disabled or the request
            # carries no tools. Best-effort -- a model that emits no tool_calls
            # just falls straight through to the stream below.
            if SECONDARY_TOOL_LOOP and body.get("tools"):
                _omsgs = await _ollama_secondary_tool_loop(
                    client, base, _omdl, _omsgs, body["tools"], _to, _push,
                    num_ctx=body.get("num_ctx"),
                    allow_write=bool(body.get("_allow_write")))
            payload = {
                "model": _omdl,
                "messages": _omsgs,
                "stream": True,
            }
            if body.get("max_tokens"):
                payload["max_tokens"] = min(int(body["max_tokens"]), _num_predict_cap_for(ep))
            else:
                payload["max_tokens"] = _num_predict_cap_for(ep)
            if body.get("response_format"):
                payload["response_format"] = body["response_format"]
            async with client.stream(
                    "POST", f"{base}/v1/chat/completions",
                    content=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    timeout=_to) as r:
                if r.status_code != 200:
                    return name, ""
                async for line in r.aiter_lines():
                    if not line:
                        continue
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = _loads_lenient(data)
                    except (json.JSONDecodeError, ValueError):
                        continue
                    ch = chunk.get("choices") or []
                    if not ch:
                        continue
                    delta = ch[0].get("delta") or {}
                    _content = delta.get("content") or ""
                    frag = _content or (delta.get("reasoning_content") or "")
                    if _content:
                        parts.append(_content)
                    if frag:
                        _push(frag)
            return name, _strip_think_tags("".join(parts))
        # Bespoke /v1 gateway (opencode :8633, hermes :8642): SSE stream.
        nb = dict(body)
        nb["stream"] = True
        # Private worker-loop signalling keys are ollama-side only -- never send
        # them to a strict /v1 gateway (it may reject unknown fields).
        nb.pop("_allow_write", None)
        nb.pop("num_ctx", None)
        # /v1 (llama.cpp) IGNORES ollama options.num_predict + think -> without an
        # explicit max_tokens the server's tiny default lets gemma4's separate
        # thinking channel eat the whole budget and return EMPTY content (operator
        # grounded/browse nodes). Translate the cap to max_tokens and
        # turn off the thinking channel so the node renders a clean answer.
        if not nb.get("max_tokens"):
            _np = (nb.get("options") or {}).get("num_predict")
            nb["max_tokens"] = int(_np) if _np else _num_predict_cap_for(ep)
        nb.pop("options", None)
        nb.pop("think", None)
        nb.setdefault("chat_template_kwargs", {"enable_thinking": False})
        if _mdl:
            nb["model"] = _mdl
        # Pipe-side OpenAI tool-loop FIRST ("fix opencode +
        # others, full loop until satisfied"): resolve the /v1 agent's read-only
        # tool_calls -- RESCUING a narrated call (the opencode ```json webfetch```
        # lie) -- before streaming the final answer, symmetric to the ollama
        # branch above. No-op when the agent self-loops (returns no tool_calls)
        # or offers no tools, so a correctly-looping Hermes is unaffected.
        if SECONDARY_TOOL_LOOP and body.get("tools"):
            sess_id = (_conv_key_var.get() if _conv_key_var else None) or None
            nb["messages"] = await _v1_secondary_tool_loop(
                client, ep, nb.get("model") or cfg.get("model"),
                headers, nb.get("messages") or [], body["tools"], _to, _push,
                session_id=sess_id)
        # Attach the backend key when streaming from the Hermes backend (it
        # enforces Bearer auth; see _call_agent_complete_inner). Scoped to the
        # backend netloc so a non-backend node never receives the key.
        _hdrs = dict(headers or {})
        # WS-FED/G2: shared backend key for a local lane, or this agent's OWN
        # header for a remote/federated endpoint (see _apply_outbound_auth).
        _apply_outbound_auth(_hdrs, ep)
        # Propagate the turn-id (cross-agent source unification; see the
        # non-streaming sibling). Harmless on a leaf endpoint.
        _tk = _src_turn_key()
        if _tk:
            _hdrs[_SRC_TURN_HEADER] = _tk
        _hdrs.update(_hop_via_headers())   # P0 cross-hop recursion bound
        # WS-A8: propagate the request trace id to the Hermes hop so a downstream
        # re-entry continues THIS request's trace (it adopts X-MiOS-Trace at the top).
        _tid = _current_trace_id()
        if _tid:
            _hdrs["X-MiOS-Trace"] = _tid
        async with client.stream(
                "POST", f"{ep}/chat/completions",
                content=json.dumps(nb).encode("utf-8"), headers=_hdrs,
                timeout=_to) as r:
            if r.status_code != 200:
                return name, ""
            _nonsse: list = []
            async for line in r.aiter_lines():
                if not line:
                    continue
                if not line.startswith("data:"):
                    _nonsse.append(line)        # a non-streaming endpoint's body
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = _loads_lenient(data)
                except (json.JSONDecodeError, ValueError):
                    continue
                ch = chunk.get("choices") or []
                if not ch:
                    continue
                delta = ch[0].get("delta") or {}
                _content = delta.get("content") or ""
                # Display BOTH the answer + any native reasoning the gateway
                # streams; only the answer content folds into the merge text.
                frag = _content or (delta.get("reasoning_content") or "")
                if _content:
                    parts.append(_content)
                if frag:
                    _push(frag)
            # NON-STREAMING /v1 fallback ("bring mios daemon
            # back up"): mios-daemon-agent (:8644) IGNORES stream=true and returns
            # ONE chat.completion JSON (no `data:` lines), so the SSE parser saw
            # nothing and the node 💤'd despite being HEALTHY. If nothing streamed,
            # parse the whole body as a non-streaming completion + push it.
            if not parts and _nonsse:
                try:
                    _obj = _loads_lenient("".join(_nonsse))
                    _m = ((_obj.get("choices") or [{}])[0].get("message") or {})
                    _c = (_m.get("content") or "").strip()
                    if _c:
                        parts.append(_c)
                        _push(_c)
                except Exception:  # noqa: BLE001
                    pass
        return name, _strip_think_tags("".join(parts))
    except Exception as e:
        log.info("fanout secondary %s (stream) failed: %s", name, e)
        return name, ""


# ── KV-cache demand-paging + fork + RR-preemptible decode (moved verbatim) ─────
# The engine-side actors the two dispatch functions above route through:
# _kv_paging brackets a completion with per-conversation /slots save+restore,
# _kv_fork branches a parent's saved KV into a swarm child, and the _rr_* cluster
# drives the RR-preemptible chunked decode. These lived in server.py and were
# dependency-injected back into this module; they now live HERE (their natural
# home -- only _call_agent_complete[_inner] uses them) over directly-imported
# leaf siblings (mios_endpoints/_endpoint_is_llamacpp, mios_kvfork, mios_preempt)
# plus the config scalars + the shared KV/priority/preempt state injected via
# configure(). server.py re-imports every name verbatim so its surface is
# unchanged, and the _kv_filename derivation stays SSOT with the KV-GC sweep.
def _kv_base(ep: str) -> str:
    """The llama-server root (strip a trailing /v1) where /slots lives."""
    return ep[:-3].rstrip("/") if (ep or "").endswith("/v1") else (ep or "").rstrip("/")


def _kv_filename(conv: str) -> str:
    """A filesystem-safe slot-save filename for one conversation's KV. The file
    lands under the server's --slot-save-path on the llama.cpp host. WS-A4:
    delegates to mios_kvfork.kv_filename so the naming has ONE source (the fork
    child-filename derivation and this paging filename can never diverge)."""
    return _kvfork_kv_filename(conv)


def _kv_lock(key: str) -> "asyncio.Lock":
    lk = _KV_LOCKS.get(key)
    if lk is None:
        lk = asyncio.Lock()
        _KV_LOCKS[key] = lk
    return lk


_SAVED_CONVS: set = set()
_LLM_LIGHT_YAML_CACHE: dict = {}
_ENDPOINT_SLOTS_CACHE: dict = {}

def _stable_hash(s: str) -> int:
    import hashlib
    return int(hashlib.md5(s.encode("utf-8")).hexdigest(), 16)

def _get_llm_light_config() -> dict:
    global _LLM_LIGHT_YAML_CACHE
    if _LLM_LIGHT_YAML_CACHE:
        return _LLM_LIGHT_YAML_CACHE
    yaml_path = os.environ.get("MIOS_LLM_LIGHT_YAML", "/usr/share/mios/llamacpp/mios-llm-light.yaml")
    if not os.path.exists(yaml_path):
        return {}
    try:
        import yaml
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if isinstance(data, dict):
                _LLM_LIGHT_YAML_CACHE = data
                return data
    except Exception as e:
        log.warning("Failed to parse mios-llm-light.yaml: %s", e)
    return {}

def _is_gemma_or_qwen(model: str) -> bool:
    if not model:
        return False
    model_lower = model.lower()
    if "gemma" in model_lower or "qwen" in model_lower:
        return True
    try:
        cfg = _get_llm_light_config()
        models = cfg.get("models", {})
        for key, entry in models.items():
            aliases = [a.lower() for a in entry.get("aliases", [])]
            if key.lower() == model_lower or model_lower in aliases:
                if "gemma" in key.lower() or "qwen" in key.lower():
                    return True
                cmd = str(entry.get("cmd", "")).lower()
                if "gemma" in cmd or "qwen" in cmd:
                    return True
    except Exception as e:
        log.debug("Error in _is_gemma_or_qwen: %s", e)
    return False

async def _get_slot_count(client, ep: str, model: Optional[str] = None) -> int:
    base = _kv_base(ep)
    cache_key = f"{base}#{model or ''}"
    if cache_key in _ENDPOINT_SLOTS_CACHE:
        return _ENDPOINT_SLOTS_CACHE[cache_key]
    urls = []
    if model:
        urls.append(f"{base}/upstream/{model}/slots")
    urls.append(f"{base}/slots")
    for url in urls:
        try:
            r = await client.get(url, timeout=KV_PAGING_TIMEOUT)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    n = len(data)
                    if n > 0:
                        _ENDPOINT_SLOTS_CACHE[cache_key] = n
                        return n
        except Exception as e:
            log.debug("Failed to get slots count from %s: %s", url, e)
    return 1

async def _kv_slot_action(client, ep: str, action: str, conv: str,
                          model: "Optional[str]" = None,
                          slot_id: Optional[int] = None) -> bool:
    """POST one llama.cpp slot save|restore for conversation `conv`. Best-effort:
    returns False (never raises) on any failure.

    Passes swa_full=true / --swa-full=true for Gemma/Qwen family models on restore."""
    sid = slot_id if slot_id is not None else KV_PAGING_SLOT
    base = _kv_base(ep)
    urls = []
    if model:
        urls.append(f"{base}/upstream/{model}/slots/{sid}")
    urls.append(f"{base}/slots/{sid}")
    
    is_swa = (action == "restore" and _is_gemma_or_qwen(model))
    
    params = {"action": action}
    if is_swa:
        params["swa_full"] = "true"
        params["--swa-full"] = "true"
        
    body = {"filename": _kv_filename(conv)}
    if is_swa:
        body["swa_full"] = True
        body["--swa-full"] = True
        
    for url in urls:
        try:
            r = await client.post(
                url,
                params=params,
                content=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                timeout=KV_PAGING_TIMEOUT)
            if r.status_code == 200:
                return True
            log.debug("kv %s %s conv=%s -> %s", action, url, conv, r.status_code)
        except Exception as e:  # noqa: BLE001 -- paging is best-effort
            log.debug("kv %s %s failed: %s", action, url, e)
    return False


@contextlib.asynccontextmanager
async def _kv_paging(client, ep: str, cfg: dict, engine):
    """Demand-page this conversation's llama.cpp KV around a completion: on a
    conversation SWITCH, page the resident one OUT (save=unload) and this one IN
    (restore=load); a same-conversation turn is a no-op (warm in-slot KV). Holds
    a per-(endpoint,slot) lock across the bracket so a concurrent conversation
    can't swap the slot mid-flight. No-op + zero overhead unless paging is on
    AND `ep` is a llama.cpp endpoint with /slots."""
    if not (KV_PAGING_ENABLE and ep and _endpoint_is_llamacpp(ep, cfg, engine)):
        yield
        return
    conv = _conv_key_var.get()
    if not conv:
        yield
        return
    model = (cfg or {}).get("model")
    
    n_slots = await _get_slot_count(client, ep, model)
    slot_id = _stable_hash(conv) % n_slots
    key = f"{_kv_base(ep)}#{slot_id}"
    
    async with _kv_lock(key):
        resident = _KV_RESIDENT.get(key)
        if resident != conv:
            if resident is not None:                       # page OUT (unload)
                await _kv_slot_action(client, ep, "save", resident, model, slot_id)
                _SAVED_CONVS.add(resident)
                _KV_RESIDENT[key] = None
            
            has_snapshot = (conv in _SAVED_CONVS)
            if not has_snapshot and KV_SLOTS_DIR:
                import os
                has_snapshot = os.path.exists(os.path.join(KV_SLOTS_DIR, _kv_filename(conv)))
                
            if has_snapshot:
                await _kv_slot_action(client, ep, "restore", conv, model, slot_id)  # page IN
            _KV_RESIDENT[key] = conv
        try:
            yield
        finally:
            await _kv_slot_action(client, ep, "save", conv, model, slot_id)
            _SAVED_CONVS.add(conv)


async def _kv_fork(client, ep: str, cfg: dict, engine, src_conv: str,
                  dst_conv: str) -> dict:
    """WS-8: fork `src_conv`'s saved llama.cpp KV into a NEW file for `dst_conv`
    so a swarm branch can page in the shared prefix independently. Drives the
    PURE plan from mios_kvfork over the existing _kv_slot_action primitive, under
    the per-(endpoint,slot) lock so a concurrent conversation can't swap the slot
    between the restore and the save. DEFAULT-OFF + degrade-open: returns
    {forked: bool, reason: str} and NEVER raises -- a disabled flag, a non-
    llama.cpp endpoint, a bad request, or a failed slot op all just mean the
    child starts cold (as today). After a successful fork the slot resident is
    the CHILD (it was just saved from the slot), so _KV_RESIDENT is updated to
    keep the demand-pager's bookkeeping honest."""
    if not (KV_FORK_ENABLE and KV_PAGING_ENABLE and ep
            and _endpoint_is_llamacpp(ep, cfg, engine)):
        return {"forked": False, "reason": "kv_fork disabled or endpoint not llama.cpp"}
    ok, reason = _kvfork_validate(src_conv, dst_conv)
    if not ok:
        return {"forked": False, "reason": reason}
    
    model = (cfg or {}).get("model")
    n_slots = await _get_slot_count(client, ep, model)
    slot_id = _stable_hash(dst_conv) % n_slots
    key = f"{_kv_base(ep)}#{slot_id}"
    
    async with _kv_lock(key):
        resident = _KV_RESIDENT.get(key)
        if resident is not None and resident != dst_conv:
            await _kv_slot_action(client, ep, "save", resident, model, slot_id)
            _SAVED_CONVS.add(resident)
            _KV_RESIDENT[key] = None
            
        restore_ok = False
        save_ok = False
        for action, conv, _fname in _kvfork_plan(src_conv, dst_conv):
            res = await _kv_slot_action(client, ep, action, conv, model, slot_id)
            if action == "restore":
                restore_ok = res
            else:
                save_ok = res
        forked, reason = _kvfork_outcome(restore_ok, save_ok)
        if forked:
            _KV_RESIDENT[key] = dst_conv  # the slot now holds the child's KV
            _SAVED_CONVS.add(dst_conv)
    return {"forked": forked, "reason": reason}


# ── RR preemptible decode driver (WS-A12) ────────────────────────────────────
# The engine-side actor for the mios_preempt policy. See the RR_ENABLE comment
# block above for the design; in short: chunk a fan-out completion into
# RR_SLICE_TOKENS slices and, when a higher-priority dispatch is queued and the
# quantum is spent, snapshot the KV (/slots save) + yield the priority gate, then
# re-acquire + restore so the preempted gen resumes WITHOUT reprocessing.
def _rr_eligible(body: dict, ep: str, cfg: dict, engine) -> bool:
    """A fan-out dispatch is RR-preemptible only when preemption can both HELP and
    be done safely: RR is on, the priority gate is active (it is what re-orders
    waiters), the lane is a llama.cpp /slots lane (save/restore actually work),
    and this is a PLAIN completion -- no tools[] -> no multi-step tool loop to
    bisect mid-flight (that needs the WS-A11 Context seam)."""
    return bool(RR_ENABLE and PRIORITY_QUEUE_ENABLE
                and not (body or {}).get("tools")
                and (body or {}).get("messages")
                and ep and _endpoint_is_llamacpp(ep, cfg, engine))


async def _rr_slice(client, ep: str, model, messages, max_tokens, headers, slot_id: Optional[int] = None):
    """One bounded completion slice on a llama.cpp /v1 lane. cache_prompt + a
    pinned id_slot reuse the warm (or just-restored) KV so only the new suffix is
    decoded. Returns (text, finished); `finished` is True on a real stop/EOS
    (finish_reason not in {length, ''}) -- else the slice hit the token budget and
    more remains."""
    sid = slot_id if slot_id is not None else KV_PAGING_SLOT
    payload = {"model": model, "messages": messages,
               "max_tokens": int(max_tokens), "stream": False,
               "cache_prompt": True, "id_slot": sid,
               "chat_template_kwargs": {"enable_thinking": False}}
    hdrs = {"Content-Type": "application/json", **(headers or {})}
    if _BACKEND_KEY and ep.split("://")[-1].split("/")[0] in _AUTH_HOSTPORTS:
        for _k in [k for k in hdrs if k.lower() == "authorization"]:
            hdrs.pop(_k)
        hdrs["Authorization"] = f"Bearer {_BACKEND_KEY}"
    r = await client.post(ep.rstrip("/") + "/chat/completions",
                           content=json.dumps(payload).encode("utf-8"),
                           headers=hdrs, timeout=RR_SLICE_TIMEOUT)
    r.raise_for_status()
    j = r.json()
    ch = (j.get("choices") or [{}])[0]
    text = str((ch.get("message") or {}).get("content") or "")
    finished = (ch.get("finish_reason") or "") not in ("length", "")
    return text, finished


async def _rr_run(client, ep: str, model, messages, *, conv: str,
                  priority: float, max_tokens, headers=None) -> str:
    """Interruptible chunked decode (WS-A12). SINGLE-OWNER of the global priority
    gate: acquires once, releases once in `finally`, and across a preemption does
    a balanced release->re-acquire (held tracked precisely) so permit accounting
    can never drift. Returns the full assistant text. Degrade-open: ANY failure
    falls back to one completion of the whole budget; the partial is never lost."""
    held = False
    partial, produced = "", 0
    total = int(max_tokens or RR_SLICE_TOKENS)
    try:
        n_slots = await _get_slot_count(client, ep, model)
        slot_id = _stable_hash(conv) % n_slots
        await _GLOBAL_PRIORITY_GATE.acquire(priority)
        held = True
        q = mios_preempt.Quantum(time.monotonic(), RR_QUANTUM_S)
        while produced < total:
            msgs = list(messages)
            if partial:                       # continue the assistant turn
                msgs.append({"role": "assistant", "content": partial})
            want = min(RR_SLICE_TOKENS, total - produced)
            text, finished = await _rr_slice(client, ep, model, msgs, want, headers, slot_id)
            partial += text
            produced += want
            if finished or not text:
                break
            try:
                head = _GLOBAL_PRIORITY_GATE.head_priority()
            except Exception:  # noqa: BLE001
                head = None
            action = mios_preempt.decide(
                finished=False,
                quantum_expired=q.expired(time.monotonic()),
                higher_priority_waiting=(head is not None and head > priority),
                can_suspend=_PREEMPT.can_admit())
            if action != mios_preempt.PREEMPT:
                continue
            slot = _PREEMPT.acquire_slot()
            if slot is None:                  # lost the slot race -> keep running
                continue
            # Snapshot KV, record the suspension, hand the lane to the waiter.
            await _kv_slot_action(client, ep, "save", conv, model, slot_id)
            _PREEMPT.suspend(mios_preempt.Snapshot(conv, priority, produced, partial, slot))
            _GLOBAL_PRIORITY_GATE.release()
            held = False
            try:
                await _GLOBAL_PRIORITY_GATE.acquire(priority)  # blocks till we're next
                held = True
            finally:
                _PREEMPT.discharge(conv)      # free our snapshot slot
            await _kv_slot_action(client, ep, "restore", conv, model, slot_id)
            q = mios_preempt.Quantum(time.monotonic(), RR_QUANTUM_S)  # fresh quantum
        return partial
    except asyncio.CancelledError:
        raise
    except Exception:  # noqa: BLE001 -- degrade-open: one shot for the whole budget
        log.warning("RR preemptible decode failed; single-completion fallback",
                    exc_info=True)
        if _PREEMPT.is_suspended(conv):
            _PREEMPT.discharge(conv)
        if not held:
            try:
                await _GLOBAL_PRIORITY_GATE.acquire(priority)
                held = True
            except Exception:  # noqa: BLE001
                pass
        try:
            n_slots = await _get_slot_count(client, ep, model)
            slot_id = _stable_hash(conv) % n_slots
            text, _ = await _rr_slice(client, ep, model, list(messages), total, headers, slot_id)
            return (partial + text) if partial else text
        except Exception:  # noqa: BLE001
            return partial
    finally:
        if held:
            try:
                _GLOBAL_PRIORITY_GATE.release()
            except Exception:  # noqa: BLE001
                pass
