# AI-hint: CLUSTER/SCHEDULER/HEALTH route-handler LOGIC extracted VERBATIM from server.py (refactor ROUTE-SURFACE wave).
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_lib_mios_agent_pipe_mios_pipe_kernel_clusterhealth_py.md
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
from mios_pipe.kernel.config import PROBE_VERIFY_TLS as _PROBE_VERIFY_TLS

log = logging.getLogger("mios-agent-pipe")


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




async def _probe_one_endpoint(client, ep: str, timeout_s: float = 3.0) -> tuple:
    """Single (reachable, live_models, latency_ms) tuple for one endpoint.
    Probes the OpenAI /v1/models surface (MiOS is /v1-only)."""
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
        async with httpx.AsyncClient(verify=_PROBE_VERIFY_TLS, timeout=3.0,
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
                agents_out.append({
                    "name": name,
                    "role": cfg.get("role", ""),
                    "lane": _agent_lane(cfg),
                    "default": bool(cfg.get("default")),
                    "enabled": bool(cfg.get("enabled", True)),
                    "health_gate": bool(cfg.get("health_gate")),
                    "primary_up": primary_ok,
                    "any_failover_up": fallback_ok,
                    "failover_only": (fallback_ok and not primary_ok),
                    "effective_up": primary_ok or fallback_ok,
                    "single_point_of_failure": (
                        (not fallback_ok) and len(links) == 1),
                    "chain": links,
                })
        up = sum(1 for a in agents_out if a["effective_up"])
        spofs = [a["name"] for a in agents_out
                 if a["single_point_of_failure"]]
        _peers_up = sum(1 for a in agents_out
                        if a["effective_up"] and not a["default"] and a["enabled"])
        _distinct_up = sum(1 for a in agents_out
                           if a["primary_up"] and not a["default"] and a["enabled"])
        _mode = ("council" if _peers_up > 0
                 else "single-agent (no council peers up)")
        _lr = sys.modules["mios_lanes_resolver"]._lane_resolver_current()
        try:
            import mios_db_config
            divergences = mios_db_config.get_divergences()
        except Exception:
            divergences = 0

        return JSONResponse({
            "object": "mios.cluster.health",
            "mode": _mode,
            "council_peers_up": _peers_up,
            "council_distinct_up": _distinct_up,
            "diversity_gate_active": bool(COUNCIL_DIVERSITY_GATE),
            "aggregator_bypass_active": bool(COUNCIL_AGGREGATOR_BYPASS),
            "aggregator_calls_bypassed_pct": mios_council_diversity.bypassed_pct(),
            "agents": agents_out,
            "agents_up": up,
            "agents_total": len(agents_out),
            "spofs": spofs,
            "lane_resolver": (_lr.snapshot()
                              if _lr is not None else None),
            "config_divergences": divergences,
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
            "recall": ("pgvector knowledge table (embed + HNSW cosine recall)"
                       if _PG_PRIMARY else
                       "legacy knowledge table (embed + cosine recall)"),
            "archival": "episodic SKILL.md + viking:// VFS",
        },
        # MIOS_ADMIT_ENABLE on. Default OFF -> deploy is a no-op until observed.
        "admission": {
            "enabled": ADMIT_ENABLE,
            "over_ceiling": _over_global_ceiling(),
            "load_ceil": ADMIT_LOAD_CEIL,
            "mem_pct_ceil": ADMIT_MEM_PCT,
            "host": _host_stats_cached(),
            "turn_priority_range": "1.6-9.4",
        },
        "priority_gate": {
            "enabled": PRIORITY_QUEUE_ENABLE,
            "starvation_s": PRIORITY_STARVATION_S,
            **_GLOBAL_PRIORITY_GATE.stats(),
        },
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
        "tool_conflict": _TOOL_CONFLICT.stats(),
        "trace": {**_TRACER.stats(), "recent": _TRACER.recent(10)},
        "preempt": {"enabled": RR_ENABLE, "quantum_s": RR_QUANTUM_S,
                    "slice_tokens": RR_SLICE_TOKENS, **_PREEMPT.stats()},
        "batch": {"enabled": BATCH_ENABLE, "interval_s": BATCH_INTERVAL_S,
                  "max_size": BATCH_MAX_SIZE, "native_bypass_hints": BATCH_NATIVE_HINTS},
        "smartroute": {"enabled": SMARTROUTE_ENABLE, "budget": SMARTROUTE_BUDGET},
        "slo": {"shed_enable": SLO_SHED_ENABLE,
                "classes": [mios_slo.BEST_EFFORT, mios_slo.INTERACTIVE],
                "model": "EDF least-deadline-first + fail-closed best_effort shed"},
        "cost": {"enabled": COST_ACCOUNTING_ENABLE, "budget_usd": COST_BUDGET_USD,
                 "over_budget": _COST_LEDGER.over_budget(COST_BUDGET_USD),
                 **_COST_LEDGER.snapshot()},
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
