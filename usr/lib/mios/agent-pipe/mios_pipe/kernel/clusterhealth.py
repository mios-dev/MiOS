# AI-hint: CLUSTER/SCHEDULER/HEALTH route-handler LOGIC extracted VERBATIM from server.py (refactor ROUTE-SURFACE wave). Owns the *_logic bodies behind the three deferred liveness/observability endpoints: the per-agent + per-endpoint health probe (/v1/cluster/health -> cluster_health_logic), the AIOS-style per-lane scheduler snapshot (/v1/scheduler -> scheduler_state_logic), and the capability/health rollup (/health -> health_logic). These were deferred from the R-CAPS wave because they read the runtime-REASSIGNED lane-resolver singleton; that landmine is solved -- mios_lanes_resolver owns it behind _lane_resolver_current(), which the moved cluster-health body already reaches through sys.modules, so nothing is injected by value. Bodies moved byte-identically; the @app routes stay THIN in server.py calling these via sys.modules so the HTTP + importable surface is unchanged. Static config is imported from mios_config, the DCI posture from mios_dci, the SLO classes from mios_slo, and the privilege-set provenance from mios_secset; every server-resident runtime global/helper is dependency-INJECTED via configure(). This module NEVER imports server.
# AI-related: ./server.py, ./mios_config.py, ./mios_dci.py, ./mios_slo.py, ./mios_secset.py, ./test_mios_clusterhealth.py
# AI-functions: cluster_health_logic, scheduler_state_logic, health_logic, clusterhealth_router, cluster_health, scheduler_state, health, configure
"""Cluster / scheduler / health route-handler logic (refactor ROUTE-SURFACE wave).

Extracted VERBATIM from ``server.py``: the bodies behind the three deferred
liveness/observability endpoints -- ``/v1/cluster/health`` (per-agent + per-
endpoint probe), ``/v1/scheduler`` (AIOS-style per-lane concurrency + priority
posture), and ``/health`` (capability/health rollup). Each body is moved byte-
identically into a ``*_logic`` function; the ``@app`` routes stay in ``server.py``
as thin wrappers calling these through ``sys.modules`` so the HTTP + importable
surface is unchanged.

The live lane resolver is read through ``mios_lanes_resolver._lane_resolver_current()``
(via ``sys.modules``) inside ``cluster_health_logic`` -- the runtime-reassigned
singleton is never captured by value. Static config / DCI / SLO / secset symbols are
imported directly; every server-resident runtime dependency is injected via
:func:`configure` (one-way boundary -- this module never imports ``server``).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from typing import Any

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

import mios_secset
import mios_slo
import mios_council_diversity
from mios_config import (
    BACKEND, BACKEND_MODEL, ROUTER_ENABLED, ROUTER_MODEL, ROUTER_ENDPOINT,
    PLANNER_ENABLED, PLANNER_MODEL, PLANNER_ENDPOINT, PLANNER_MAX_NODES,
    PLANNER_REFLEXION_CAP, REFINE_ENABLED, REFINE_MODEL, REFINE_ENDPOINT,
    REFINE_BYPASS_CHARS, POLISH_ENABLED, POLISH_MODEL, POLISH_ENDPOINT, PORT,
    COUNCIL_DIVERSITY_GATE, COUNCIL_AGGREGATOR_BYPASS,
)
from mios_dci import (
    DCI_ENABLED, DCI_MODEL, DCI_ENDPOINT, DCI_FLOW_ENABLED, DCI_FLOW_R_MAX,
    DCI_FLOW_TRIGGER_CONF, _DCI_ACTS, _DCI_PERSONAS,
)

log = logging.getLogger("mios-agent-pipe")


# -- Dependency-injection seam --------------------------------------
# Every server-resident dependency the moved logic references stays in server.py
# and is injected here AFTER each is defined (one-way boundary: this module never
# imports server). Objects/registries (the agent registry, priority gate, KV
# resident map, conflict/preempt gates, tracer, cost ledger, kernel, the
# privilege/allowlist sets, and the FastAPI ``app``) are injected BY REFERENCE so
# server-side mutation stays visible; the flag/scalar posture constants are stable
# config values. Placeholders keep a standalone ``import mios_clusterhealth``
# working for the unit tests; the routes are runtime-only so nothing fires before
# configure() runs.
app = None
_AGENT_REGISTRY = None
_GLOBAL_PRIORITY_GATE = None
_KV_RESIDENT = None
_TOOL_CONFLICT = None
_TRACER = None
_PREEMPT = None
_COST_LEDGER = None
_KERNEL = None
_ALLOWLIST_HOSTS = None
_HIGH_PRIVILEGE_VERBS = None
_HIGH_PRIVILEGE_CURATED = None
_TAINT_VERBS = None
_agent_lane = None
_over_global_ceiling = None
_host_stats_cached = None
_toml_section = None
# Deps for the cluster/scheduler helper fns that now live HERE natively
# (_resolve_failover_chain / _probe_one_endpoint / _lane_sched_stats /
# _kernel_managers_detail were only ever injected back into this module, so they
# moved home). Injected BY REFERENCE -- the
# semaphore map / verb catalog / memory provider are mutated in place or set once
# server-side (never rebound after configure), so this module sees the live values;
# _probe_auth_headers is the server's per-endpoint auth-header builder.
_probe_auth_headers = None
_LANE_SEMS = None
_MEMORY = None
_VERB_CATALOG = None
_PERMISSION_TIERS = None
_passport_load_priv = None
_passport_kid = None
AGENT_CONCURRENCY = None
_PG_PRIMARY = None
ADMIT_ENABLE = None
ADMIT_LOAD_CEIL = None
ADMIT_MEM_PCT = None
PRIORITY_QUEUE_ENABLE = None
PRIORITY_STARVATION_S = None
KV_FORK_ENABLE = None
KV_PAGING_ENABLE = None
KV_PAGING_SLOT = None
KV_FORK_MAX_BRANCHES = None
KNOWLEDGE_EVICT_ENABLE = None
KNOWLEDGE_EVICT_DRYRUN = None
KNOWLEDGE_EVICT_INTERVAL_S = None
KNOWLEDGE_EVICT_TTL_DAYS = None
KNOWLEDGE_EVICT_MAX_ROWS = None
KNOWLEDGE_EVICT_BATCH = None
RR_ENABLE = None
RR_QUANTUM_S = None
RR_SLICE_TOKENS = None
BATCH_ENABLE = None
BATCH_INTERVAL_S = None
BATCH_MAX_SIZE = None
BATCH_NATIVE_HINTS = None
SMARTROUTE_ENABLE = None
SMARTROUTE_BUDGET = None
SLO_SHED_ENABLE = None
COST_ACCOUNTING_ENABLE = None
COST_BUDGET_USD = None
KERNEL_ROUTE = None
SKILLS_ENABLED = None
SKILLS_MIN_LENGTH = None
SKILLS_MAX_LENGTH = None
SKILLS_MIN_SUPPORT = None
SKILLS_WINDOW_HOURS = None
SKILLS_AUTO_PROMOTE_THRESHOLD = None
PASSPORT_ENABLE = None
PASSPORT_ALGO = None
PASSPORT_AGENT_NAME = None
PASSPORT_KEY_DIR = None
PASSPORT_VERIFY_ON_READ = None
LAUNCHER_SOCK = None
DB_URL = None

_INJECTED = frozenset({
    'app',
    '_AGENT_REGISTRY',
    '_GLOBAL_PRIORITY_GATE',
    '_KV_RESIDENT',
    '_TOOL_CONFLICT',
    '_TRACER',
    '_PREEMPT',
    '_COST_LEDGER',
    '_KERNEL',
    '_ALLOWLIST_HOSTS',
    '_HIGH_PRIVILEGE_VERBS',
    '_HIGH_PRIVILEGE_CURATED',
    '_TAINT_VERBS',
    '_agent_lane',
    # _resolve_failover_chain / _probe_one_endpoint / _lane_sched_stats /
    # _kernel_managers_detail are NATIVE to this module now; they stay allow-listed so
    # a test (or an alternate probe transport / failover policy) can OVERRIDE the
    # default impl via configure(). Production server.py no longer injects them -- the
    # in-module defaults stand.
    '_probe_one_endpoint',
    '_resolve_failover_chain',
    '_lane_sched_stats',
    '_over_global_ceiling',
    '_host_stats_cached',
    '_kernel_managers_detail',
    '_toml_section',
    '_probe_auth_headers',
    '_LANE_SEMS',
    '_MEMORY',
    '_VERB_CATALOG',
    '_PERMISSION_TIERS',
    '_passport_load_priv',
    '_passport_kid',
    'AGENT_CONCURRENCY',
    '_PG_PRIMARY',
    'ADMIT_ENABLE',
    'ADMIT_LOAD_CEIL',
    'ADMIT_MEM_PCT',
    'PRIORITY_QUEUE_ENABLE',
    'PRIORITY_STARVATION_S',
    'KV_FORK_ENABLE',
    'KV_PAGING_ENABLE',
    'KV_PAGING_SLOT',
    'KV_FORK_MAX_BRANCHES',
    'KNOWLEDGE_EVICT_ENABLE',
    'KNOWLEDGE_EVICT_DRYRUN',
    'KNOWLEDGE_EVICT_INTERVAL_S',
    'KNOWLEDGE_EVICT_TTL_DAYS',
    'KNOWLEDGE_EVICT_MAX_ROWS',
    'KNOWLEDGE_EVICT_BATCH',
    'RR_ENABLE',
    'RR_QUANTUM_S',
    'RR_SLICE_TOKENS',
    'BATCH_ENABLE',
    'BATCH_INTERVAL_S',
    'BATCH_MAX_SIZE',
    'BATCH_NATIVE_HINTS',
    'SMARTROUTE_ENABLE',
    'SMARTROUTE_BUDGET',
    'SLO_SHED_ENABLE',
    'COST_ACCOUNTING_ENABLE',
    'COST_BUDGET_USD',
    'KERNEL_ROUTE',
    'SKILLS_ENABLED',
    'SKILLS_MIN_LENGTH',
    'SKILLS_MAX_LENGTH',
    'SKILLS_MIN_SUPPORT',
    'SKILLS_WINDOW_HOURS',
    'SKILLS_AUTO_PROMOTE_THRESHOLD',
    'PASSPORT_ENABLE',
    'PASSPORT_ALGO',
    'PASSPORT_AGENT_NAME',
    'PASSPORT_KEY_DIR',
    'PASSPORT_VERIFY_ON_READ',
    'LAUNCHER_SOCK',
    'DB_URL',
})


def configure(**deps) -> None:
    """Inject server.py's runtime deps under their EXACT original names. Objects
    are passed BY REFERENCE so server-side mutation stays visible; the moved logic
    is byte-identical. Allowlist-gated (``_INJECTED``) so an unknown key is ignored;
    server may call with a partial set.
    """
    g = globals()
    for _k, _v in deps.items():
        if _k in _INJECTED:
            g[_k] = _v


# -- Cluster/scheduler helper fns (moved home from server.py) ----------
# These were defined in server.py purely to be injected BACK into this module's
# logic; they have no other server-side caller, so they live here natively now.
# Each reads only injected-by-reference deps (the agent registry, the agent auth-
# header builder, the live lane semaphores, the kernel-seam objects) -- never a
# server-rebound global -- so the move is byte-for-byte behaviour-identical. They
# remain configure()-overridable (a unit test stubs the network probe / lane map /
# failover chain).


async def _probe_one_endpoint(client, ep: str, timeout_s: float = 3.0) -> tuple:
    """Single (reachable, live_models, latency_ms) tuple for one endpoint.
    Tries OpenAI /v1/models first then ollama /api/tags fallback."""
    ep = (ep or "").rstrip("/")
    if not ep:
        return (False, [], 0)
    t0 = time.time()
    try:
        r = await client.get(f"{ep}/models", timeout=timeout_s,
                             headers=_probe_auth_headers(ep))
        if r.status_code < 500:
            try:
                lm = [str(m.get("id"))
                      for m in ((r.json() or {}).get("data") or [])
                      if isinstance(m, dict) and m.get("id")]
            except (json.JSONDecodeError, ValueError):
                lm = []
            return (True, lm, int((time.time() - t0) * 1000))
    except Exception:  # noqa: BLE001
        pass
    tb = ep[:-3].rstrip("/") if ep.endswith("/v1") else ep
    try:
        r = await client.get(f"{tb}/api/tags", timeout=timeout_s)
        if r.status_code < 500:
            try:
                lm = [str(m.get("name"))
                      for m in ((r.json() or {}).get("models") or [])
                      if isinstance(m, dict) and m.get("name")]
            except (json.JSONDecodeError, ValueError):
                lm = []
            return (True, lm, int((time.time() - t0) * 1000))
    except Exception:  # noqa: BLE001
        return (False, [], int((time.time() - t0) * 1000))
    return (False, [], int((time.time() - t0) * 1000))


def _lane_sched_stats() -> list:
    """Per-lane scheduler state from the live semaphores: cap, in-flight,
    available, queue depth. asyncio.Semaphore._value = available permits;
    in-flight = cap - available; waiters = len of its _waiters deque."""
    out = []
    for lane, sem in sorted(_LANE_SEMS.items()):
        try:
            cap = int(os.environ.get(
                "MIOS_AGENT_LANE_CONCURRENCY_" + lane.upper(),
                os.environ.get("MIOS_AGENT_LANE_CONCURRENCY",
                               str(AGENT_CONCURRENCY))))
            avail = sem._value  # noqa: SLF001 -- read-only introspection
            waiters = len(getattr(sem, "_waiters", None) or [])
            out.append({
                "lane": lane,
                "cap": cap,
                "in_flight": max(0, cap - avail),
                "available": avail,
                "queued": waiters,
            })
        except Exception:  # noqa: BLE001
            out.append({"lane": lane, "error": "introspection failed"})
    return out


def _kernel_managers_detail() -> dict:
    """Per-seam liveness + a live stat, for /v1/scheduler observability."""
    return {
        "scheduler": _GLOBAL_PRIORITY_GATE.stats(),
        "preempt": _PREEMPT.stats(),
        "memory": {"provider": type(_MEMORY).__name__ if _MEMORY is not None else None,
                   "pg_primary": _PG_PRIMARY},
        "context": {"kv_paging": KV_PAGING_ENABLE},
        "tools": {"verbs": len(_VERB_CATALOG)},
        "access": {"pdp": True, "tiers": list(_PERMISSION_TIERS)},
    }


def _resolve_failover_chain(name: str) -> list:
    """Expand an agent name into the FULL failover chain (
    'remove SPOFs'): self -> declared failover_agents (mios.toml) -> self's
    cpu_endpoint as a last-resort virtual agent. Each entry is {name, endpoint,
    model, kind in {primary,failover,cpu-twin}}. Names already visited in the
    chain are skipped so a config loop can't recurse. Reads the injected-by-
    reference _AGENT_REGISTRY (the only server-side dep), so the move is
    behaviour-identical; the sole caller is cluster_health_logic below."""
    out: list = []
    seen: set = set()
    cfg = _AGENT_REGISTRY.get(name)
    if cfg:
        ep = cfg.get("endpoint") or ""
        out.append({"name": name, "endpoint": ep,
                    "model": cfg.get("model"), "kind": "primary"})
        seen.add(name)
        for fname in (cfg.get("failover_agents") or []):
            if fname in seen:
                continue
            fcfg = _AGENT_REGISTRY.get(fname)
            if not fcfg:
                continue
            out.append({"name": fname,
                        "endpoint": fcfg.get("endpoint") or "",
                        "model": fcfg.get("model"),
                        "kind": "failover"})
            seen.add(fname)
        cpu_ep = (cfg.get("cpu_endpoint") or "").rstrip("/")
        if cpu_ep and cpu_ep != (cfg.get("endpoint") or "").rstrip("/"):
            out.append({"name": f"{name}.cpu",
                        "endpoint": cpu_ep,
                        "model": cfg.get("cpu_model") or cfg.get("model"),
                        "kind": "cpu-twin"})
    return out


async def cluster_health_logic() -> JSONResponse:
    """Per-agent + per-endpoint health snapshot. Probes EVERY agent's primary
    AND cpu_endpoint AND declared failover targets in parallel; surfaces
    {reachable, live_models, latency_ms} per endpoint + the resolved
    failover_chain per agent. Public (no auth) so a sidecar / dashboard can
    pull it the same way A2A clients pull the agent card."""
    try:
        async with httpx.AsyncClient(verify=False, timeout=3.0,
                                     follow_redirects=False) as client:
            agents_out: list = []
            for name, cfg in _AGENT_REGISTRY.items():
                chain = _resolve_failover_chain(name)
                probes = await asyncio.gather(
                    *[_probe_one_endpoint(client, h["endpoint"]) for h in chain],
                    return_exceptions=True)
                links: list = []
                primary_ok = False
                fallback_ok = False
                for hop, pr in zip(chain, probes):
                    if isinstance(pr, tuple):
                        reach, lm, ms = pr
                    else:
                        reach, lm, ms = (False, [], 0)
                    hop_state = {
                        "name": hop["name"],
                        "kind": hop["kind"],
                        "endpoint": hop["endpoint"],
                        "model": hop["model"],
                        "reachable": bool(reach),
                        "latency_ms": int(ms),
                        "live_models": lm[:8],
                    }
                    if hop["kind"] == "primary" and reach:
                        primary_ok = True
                    if hop["kind"] != "primary" and reach:
                        fallback_ok = True
                    links.append(hop_state)
                # "effective" = primary live OR at least one fallback live
                agents_out.append({
                    "name": name,
                    "role": cfg.get("role", ""),
                    "lane": _agent_lane(cfg),
                    "default": bool(cfg.get("default")),
                    "enabled": bool(cfg.get("enabled", True)),
                    "health_gate": bool(cfg.get("health_gate")),
                    "primary_up": primary_ok,
                    "any_failover_up": fallback_ok,
                    # a peer "up" ONLY via failover is borrowing ANOTHER agent's backend
                    # (often a SHARED one) -- not a distinct council voice. Surface it.
                    "failover_only": (fallback_ok and not primary_ok),
                    "effective_up": primary_ok or fallback_ok,
                    "single_point_of_failure": (
                        (not fallback_ok) and len(links) == 1),
                    "chain": links,
                })
        up = sum(1 for a in agents_out if a["effective_up"])
        spofs = [a["name"] for a in agents_out
                 if a["single_point_of_failure"]]
        # A5 council honesty: a COUNCIL needs >=1 SECONDARY
        # (non-default) peer that is ENABLED + effective_up. A DISABLED agent must NOT
        # inflate the count just because its failover chain reaches a shared backend --
        # that made the council look 3-strong when "opencode" (enabled=false; its
        # headless `run` is broken upstream so its OWN :8633 is unreachable) was silently
        # failing over to hermes (already a peer). Count only enabled, non-default,
        # effective_up peers; `council_distinct_up` further excludes failover-only ones.
        _peers_up = sum(1 for a in agents_out
                        if a["effective_up"] and not a["default"] and a["enabled"])
        _distinct_up = sum(1 for a in agents_out
                           if a["primary_up"] and not a["default"] and a["enabled"])
        _mode = ("council" if _peers_up > 0
                 else "single-agent (no council peers up)")
        # Read the LIVE resolver (mios_lanes_resolver REBINDS its _LANE_RESOLVER at
        # runtime) through its getter via sys.modules -- server's re-imported
        # _LANE_RESOLVER alias is a stale None placeholder, not the live singleton.
        _lr = sys.modules["mios_lanes_resolver"]._lane_resolver_current()
        return JSONResponse({
            "object": "mios.cluster.health",
            "mode": _mode,
            "council_peers_up": _peers_up,
            "council_distinct_up": _distinct_up,
            # T-047 RouteMoA input-diversity gate posture + T-048 MOSAIC
            # aggregation-bypass posture/rate. diversity_gate_active reflects the
            # [council].diversity_gate flag; aggregator_calls_bypassed_pct is the
            # running share of aggregation opportunities that skipped the
            # aggregator LLM (0.0 until the bypass gate fires).
            "diversity_gate_active": bool(COUNCIL_DIVERSITY_GATE),
            "aggregator_bypass_active": bool(COUNCIL_AGGREGATOR_BYPASS),
            "aggregator_calls_bypassed_pct": mios_council_diversity.bypassed_pct(),
            "agents": agents_out,
            "agents_up": up,
            "agents_total": len(agents_out),
            "spofs": spofs,
            # WS-1: the unified lane-resolver's live health/cooldown snapshot
            # (collapses the two heavy lanes behind [ai].heavy_engine). None until
            # first resolved -> the resolver is lazily built on first dispatch.
            "lane_resolver": (_lr.snapshot()
                              if _lr is not None else None),
            "ts": int(time.time()),
        })
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": f"{type(e).__name__}: {e}"},
                            status_code=500)


async def scheduler_state_logic() -> JSONResponse:
    """AIOS-style scheduler observability: live per-lane concurrency state
    (cap / in-flight / available / queued) across every hardware lane the
    swarm dispatches to. Proves the resource-aware concurrency is real +
    shows where contention is. Includes the priority-scoring shape used to
    rank turns."""
    return JSONResponse({
        "object": "mios.scheduler",
        "model": "per-lane resource-aware concurrency (AIOS resource-need "
                 "dimension) + advisory priority score",
        "lanes": _lane_sched_stats(),
        "global_cap": AGENT_CONCURRENCY,
        "priority_dimensions": ["complexity", "urgency", "resource_need(lane)"],
        "memory_manager_tiers": {
            "core_working": "per-conversation scratchpad (_SCRATCHPADS)",
            # Reflect the ACTUAL recall backend (was a stale hardcoded "SurrealDB"
            # string even after the pgvector cutover -- the kernel must not
            # misreport its own memory backend). _PG_PRIMARY when db_backend=postgres.
            "recall": ("pgvector knowledge table (embed + HNSW cosine recall)"
                       if _PG_PRIMARY else
                       "SurrealDB knowledge table (embed + cosine recall)"),
            "archival": "episodic SKILL.md + viking:// VFS",
        },
        # Capacity-aware admission controller (P1): live
        # state so we can OBSERVE the gate (load/mem vs ceiling) BEFORE flipping
        # MIOS_ADMIT_ENABLE on. Default OFF -> deploy is a no-op until observed.
        "admission": {
            "enabled": ADMIT_ENABLE,
            "over_ceiling": _over_global_ceiling(),
            "load_ceil": ADMIT_LOAD_CEIL,
            "mem_pct_ceil": ADMIT_MEM_PCT,
            "host": _host_stats_cached(),
            "turn_priority_range": "1.6-9.4",
        },
        # WS-1 priority scheduler queue: live gate state so the
        # reordering is OBSERVABLE before flipping MIOS_PRIORITY_QUEUE on. When
        # disabled the gate is idle (queued 0) and the plain FIFO sem is in use.
        "priority_gate": {
            "enabled": PRIORITY_QUEUE_ENABLE,
            "starvation_s": PRIORITY_STARVATION_S,
            **_GLOBAL_PRIORITY_GATE.stats(),
        },
        # WS-3 knowledge eviction: config posture (live counts are
        # logged by the sweep, not computed here, to avoid a DB hit per probe).
        # WS-8 KV-cache fork: config posture so the fork capability
        # is OBSERVABLE before flipping MIOS_KV_FORK on (default-off, paging-gated).
        "kv_fork": {
            "enabled": KV_FORK_ENABLE,
            "paging_enabled": KV_PAGING_ENABLE,
            "slot": KV_PAGING_SLOT,
            "max_branches": KV_FORK_MAX_BRANCHES,
            "resident_slots": len(_KV_RESIDENT),
        },
        "knowledge_eviction": {
            "enabled": KNOWLEDGE_EVICT_ENABLE,
            "dry_run": KNOWLEDGE_EVICT_DRYRUN,
            "interval_s": KNOWLEDGE_EVICT_INTERVAL_S,
            "ttl_days": KNOWLEDGE_EVICT_TTL_DAYS,
            "max_rows": KNOWLEDGE_EVICT_MAX_ROWS,
            "batch": KNOWLEDGE_EVICT_BATCH,
        },
        # WS-A7 Tool-Manager conflict/parallel-limit gate: which verbs are
        # serialized (by per-verb limit or conflict-group) + live in-flight/queued.
        "tool_conflict": _TOOL_CONFLICT.stats(),
        # WS-A8 per-request trace/span observability: buffer posture + recent traces.
        "trace": {**_TRACER.stats(), "recent": _TRACER.recent(10)},
        # WS-A12 RR preemption: policy posture + live suspended/free-slot counts.
        "preempt": {"enabled": RR_ENABLE, "quantum_s": RR_QUANTUM_S,
                    "slice_tokens": RR_SLICE_TOKENS, **_PREEMPT.stats()},
        # WS-A6 batch coalescing: posture (native lanes self-batch -> bypassed).
        "batch": {"enabled": BATCH_ENABLE, "interval_s": BATCH_INTERVAL_S,
                  "max_size": BATCH_MAX_SIZE, "native_bypass_hints": BATCH_NATIVE_HINTS},
        # WS-A16 SmartRouting: local-first escalation posture + budget.
        "smartroute": {"enabled": SMARTROUTE_ENABLE, "budget": SMARTROUTE_BUDGET},
        # WS-SCHED-SLO: deadline/SLO admission posture. When shed_enable, a
        # best_effort dispatch is shed under contention (fail-CLOSED on probe
        # failure); interactive is never shed. EDF ordering available via mios_slo.
        "slo": {"shed_enable": SLO_SHED_ENABLE,
                "classes": [mios_slo.BEST_EFFORT, mios_slo.INTERACTIVE],
                "model": "EDF least-deadline-first + fail-closed best_effort shed"},
        # WS-RES-GOV: cost/energy accounting (CLASSic Cost axis). Observe-only.
        "cost": {"enabled": COST_ACCOUNTING_ENABLE, "budget_usd": COST_BUDGET_USD,
                 "over_budget": _COST_LEDGER.over_budget(COST_BUDGET_USD),
                 **_COST_LEDGER.snapshot()},
        # WS-A11/WS-3 Kernel facade: which manager seams are wired, the
        # Dispatcher's registered modes, and the shadow-route posture. Proves the
        # decomposition's Router/Dispatcher/Kernel are LIVE (not inert modules);
        # POST /v1/route to introspect a classification.
        "kernel": {
            "managers": _KERNEL.managers(),
            "manager_detail": _kernel_managers_detail(),
            "modes": _KERNEL.dispatcher.modes(),
            "shadow_route": KERNEL_ROUTE,
            "stage": "2b (live kernel; all traffic routed through dispatcher)",
        },
        "ts": int(time.time()),
    })


async def health_logic() -> dict[str, Any]:
    import sys
    if "/usr/lib/mios" not in sys.path:
        sys.path.insert(0, "/usr/lib/mios")
    try:
        import mios_db_config
        divergences = mios_db_config.get_divergences()
    except Exception:
        divergences = 0

    return {
        "status": "ok",
        "version": app.version,
        "backend": BACKEND,
        "backend_model": BACKEND_MODEL,
        "config_divergences": divergences,
        "router": {
            "enabled": ROUTER_ENABLED,
            "model": ROUTER_MODEL,
            "endpoint": ROUTER_ENDPOINT,
        },
        "planner": {
            "enabled": PLANNER_ENABLED,
            "model": PLANNER_MODEL,
            "endpoint": PLANNER_ENDPOINT,
            "max_nodes": PLANNER_MAX_NODES,
            "reflexion_cap": PLANNER_REFLEXION_CAP,
        },
        "dci": {
            "enabled": DCI_ENABLED,
            "model": DCI_MODEL,
            "endpoint": DCI_ENDPOINT,
            "act_count": len(_DCI_ACTS),
            "flow": {
                "enabled": DCI_FLOW_ENABLED,
                "r_max": DCI_FLOW_R_MAX,
                "personas": [name for name, _ in _DCI_PERSONAS],
                "auto_trigger_conf": DCI_FLOW_TRIGGER_CONF,
            },
        },
        "security": {
            "allowlist_hosts": sorted(_ALLOWLIST_HOSTS),
            "high_privilege_verbs": sorted(_HIGH_PRIVILEGE_VERBS),
            # WS-A14: provenance -- curated-floor vs SSOT-added origin of the set.
            "high_privilege_provenance": mios_secset.provenance(
                _HIGH_PRIVILEGE_CURATED,
                (_toml_section("security") or {}).get("firewall_high_privilege_verbs")),
            "taint_verbs": sorted(_TAINT_VERBS),
        },
        "skills": {
            "enabled": SKILLS_ENABLED,
            "min_length": SKILLS_MIN_LENGTH,
            "max_length": SKILLS_MAX_LENGTH,
            "min_support": SKILLS_MIN_SUPPORT,
            "window_hours": SKILLS_WINDOW_HOURS,
            "auto_promote_threshold": SKILLS_AUTO_PROMOTE_THRESHOLD,
        },
        "passport": {
            "enabled": PASSPORT_ENABLE,
            "algo": PASSPORT_ALGO,
            "agent_name": PASSPORT_AGENT_NAME,
            "key_dir": PASSPORT_KEY_DIR,
            "private_key_present": (
                _passport_load_priv() is not None
            ),
            "kid": _passport_kid() if PASSPORT_ENABLE else None,
            "verify_on_read": PASSPORT_VERIFY_ON_READ,
        },
        "refine": {
            "enabled": REFINE_ENABLED,
            "model": REFINE_MODEL,
            "endpoint": REFINE_ENDPOINT,
            "bypass_chars": REFINE_BYPASS_CHARS,
        },
        "polish": {
            "enabled": POLISH_ENABLED,
            "model": POLISH_MODEL,
            "endpoint": POLISH_ENDPOINT,
        },
        "agents": {
            name: {
                "endpoint": cfg.get("endpoint"),
                "model":    cfg.get("model"),
                "role":     cfg.get("role"),
                "default":  cfg.get("default"),
                "strengths": cfg.get("strengths"),
            }
            for name, cfg in _AGENT_REGISTRY.items()
        },
        "broker_sock": LAUNCHER_SOCK,
        "broker_present": os.path.exists(LAUNCHER_SOCK),
        "db_url": DB_URL,
        "port": PORT,
    }


# -- @app -> APIRouter migration (refactor R13 batch 3: cluster/scheduler) --------
# The two public liveness/observability endpoints whose LOGIC this module already
# owns -- the per-agent + per-endpoint health probe (/v1/cluster/health) and the
# AIOS-style per-lane scheduler snapshot (/v1/scheduler) -- moved off server.py's
# @app onto this co-located clusterhealth_router (the same routes->APIRouter pattern
# the /a2a wave established). server.py imports clusterhealth_router + the two
# handler NAMES (re-imported there so its importable `provided` surface is unchanged)
# and mounts the router via app.include_router(clusterhealth_router); the served
# path/method set is identical (the live-app route gate proves it). Each body calls
# the module-resident *_logic DIRECTLY (same module -- no sys.modules hop). A later
# R13 batch moved the capability/health rollup (/health) onto the SAME router; its
# body returns health_logic's bare dict (FastAPI serialises the dict to JSON -- the
# identical shape the former @app wrapper served). One-way boundary: this module
# never imports server. APIRouter()/method decorators are structural.
clusterhealth_router = APIRouter()


@clusterhealth_router.get("/v1/cluster/health")
async def cluster_health() -> JSONResponse:
    """P3.2 public per-agent + per-endpoint health probe. Reuses the /portal/swarm
    probe shape without portal auth so external clients (and an eventual mesh-wide
    aggregator) can read it: SPOFs become visible + the declarative failover chain
    (mios.toml [agents.X].failover_agents) is surfaced. Calls cluster_health_logic
    (same module)."""
    return await cluster_health_logic()


@clusterhealth_router.get("/v1/scheduler")
async def scheduler_state() -> JSONResponse:
    """P4.1 AIOS-style scheduler observability: the live per-lane queue/in-flight
    state + an explicit advisory priority posture (the resource-need dimension the
    per-lane semaphores already realise). Calls scheduler_state_logic (same
    module)."""
    return await scheduler_state_logic()


@clusterhealth_router.get("/health")
async def health() -> dict[str, Any]:
    """Capability/health rollup. Calls health_logic (same module); the returned
    bare dict is JSON-serialised by FastAPI -- identical to the former @app wrapper."""
    return await health_logic()
