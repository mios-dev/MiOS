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

# ── All-nodes-enabled-by-default + idle reclaim + lane priority (operator
# "all nodes enabled by default... concurrently dispatched... clear
# RAM/VRAM for idle agents to be loaded so nothing in the pipeline is idle until
# the final synthesis"). AIOS-correct layering (research): ELIGIBILITY
# is universal (no node disabled), AVAILABILITY is the health gate, and SAFETY is
# ADMISSION -- so a wide roster is made safe by (a) admission ON (above), (b) lane
# PRIORITY so slow/remote lanes self-shed under host pressure, and (c) reclaiming
# an IDLE model's VRAM to load the one a turn needs instead of only waiting.
#
# nodes_research_only: the [nodes.*] pool's default research_only. FALSE here =
# every node is eligible on EVERY turn (the operator's "enabled by default"),
# kept safe by admission + COUNCIL_MAX + per-endpoint/lane semaphores + priority.
# (A node may still override per-entry; set true to restore research-turn-only.)
NODES_RESEARCH_ONLY = str(os.environ.get("MIOS_NODES_RESEARCH_ONLY")
                          or _DISPATCH_TOML.get("nodes_research_only", "false")
                          ).strip().lower() in {"1", "true", "yes"}
# Proactively evict an IDLE resident model to make VRAM headroom for a cold model
# a turn needs (vs only waiting it out). The hard semaphores remain the OOM
# backstop; this just stops idle models from starving an active dispatch.
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


# lane -> dispatch priority (1..9; higher = admitted first / shorter _admit
# backoff). SSOT [dispatch].lane_priority; fast LOCAL lanes high, slow/remote
# lanes low so the wide 'all nodes enabled' roster degrades gracefully.
_LANE_PRIORITY = _parse_lane_priority(
    os.environ.get("MIOS_LANE_PRIORITY")
    or _DISPATCH_TOML.get("lane_priority",
                          "gpu:8,cpu:7,accelerator:6,igpu:3,mobile:2,_default:5"))
# In-flight model refcount keyed by (endpoint, model). A model with count>0 is
# ACTIVELY serving a dispatch and must NEVER be evicted out from under it; idle
# reclaim only frees count==0 residents.
_ACTIVE_MODELS: "collections.Counter" = collections.Counter()
_ACTIVE_LOCK = asyncio.Lock()
# SWARM Phase-1: per-endpoint VRAM RESERVATION (MB). The
# _admit measured-VRAM read LAGS a sibling that just passed admit but hasn't
# loaded its weights yet -- so two workers co-admitting onto ONE endpoint in the
# same turn could both pass then both load -> oversubscribe the 4090. Each
# in-flight dispatch reserves its declared vram_mb here on _model_active(+1) and
# releases on -1 (bulletproof: the dispatch finally always runs); _admit adds
# this to measured-used so co-admitting siblings see each other's pending cost.
# Estimate-based + degrade-open (errs conservative); the hard lane/endpoint
# semaphores remain the OOM backstop. Inert until [nodes.*] declare vram_mb.
_ENDPOINT_RESERVED: dict = {}


def _lane_sem(key: str) -> asyncio.Semaphore:
    """The concurrency gate for ONE hardware lane / engine / node (lazily
    created -- safe: no await between the check and the set in the single-
    threaded event loop)."""
    key = str(key or "gpu").lower().strip() or "gpu"
    if key not in _LANE_SEMS:
        # SSOT ("HARDCODES!!!" + cap the shared 4090): per-lane
        # concurrency from mios.toml [dispatch] -- lane_concurrency_<lane> (env
        # override MIOS_AGENT_LANE_CONCURRENCY_<LANE>) else lane_concurrency (env
        # MIOS_AGENT_LANE_CONCURRENCY) else AGENT_CONCURRENCY. The LOCAL gpu/cpu
        # lanes are capped LOW in [dispatch] so a wide research fan-out doesn't
        # oversubscribe the single shared 4090 (live test it thrashed).
        # Custom/remote lanes (potato-gpu, igpu, ...) fall to the general default.
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
    # WS-SCHED-SLO fail-closed shed (independent of ADMIT_ENABLE): shed a
    # best_effort dispatch FAST (before the capacity wait) when over the ceiling
    # OR when the host probe failed (empty stats -> healthy=False -> shed). An
    # interactive turn (high priority) is never shed. Default-off.
    if SLO_SHED_ENABLE:
        # The SLO class is the FOREGROUND/autonomous axis -- NOT the capacity-gate
        # scheduling `priority` (3.4-6.8 for normal turns), which never reaches the
        # interactive floor and so misclassified EVERY turn as best_effort/shed-
        # eligible. A fan-out / background dispatch passes foreground=False (->
        # best_effort, shed-eligible under contention); a genuine foreground turn is
        # protected (-> interactive, never shed). `healthy` degrades OPEN (omitted ->
        # should_shed's default True) so a missing/cold host-stats probe never sheds --
        # consistent with _over_global_ceiling() which ALSO degrades open; over_ceiling
        # is the sole contention trigger.
        _slo = mios_slo.classify(foreground=foreground)
        if mios_slo.should_shed(_slo, over_ceiling=_over_global_ceiling()):
            raise _SloShed(_slo)
    if not ADMIT_ENABLE:
        return
    try:
        deadline = time.monotonic() + ADMIT_MAX_WAIT
        # (1) global ceiling: if over, wait (low priority waits longer) up to the
        # deadline, re-checking; then admit regardless (degrade-open). V5: when
        # multiblade is on, the ceiling is the endpoint's BLADE ceiling (a remote
        # blade is NOT gated by the local /proc/loadavg); OFF -> _over_global_ceiling()
        # EXACTLY as today (byte-identical -- the new helper is never consulted).
        while (_over_blade_ceiling(ep) if MULTIBLADE_ENABLE
               else _over_global_ceiling()) and time.monotonic() < deadline:
            # higher priority -> shorter back-off; bounded so we always progress
            _backoff = max(0.15, (10.0 - float(priority)) * 0.1)
            await asyncio.sleep(min(_backoff, max(0.0, deadline - time.monotonic())))
        # (2) VRAM-aware co-load admission: a COLD model is
        # admitted onto the endpoint only when measured free VRAM fits it + a
        # reserve -- so the dGPU packs several small/medium models concurrently by
        # REAL headroom (the "multiple models on the dGPU within a turn" goal),
        # NOT a flat count. If it doesn't fit yet, wait (a sibling dispatch may
        # finish + free VRAM, or the turn-start _vram_checkpoint may have evicted)
        # up to the deadline, then admit anyway (degrade-open) -- the bounded
        # lane/endpoint semaphores remain the hard OOM backstop.
        warm = await _is_warm(ep, model)
        if not warm:
            _reclaimed = False
            # V5: admit a cold model against the endpoint's BLADE VRAM budget (a remote
            # node's residents belong to ITS machine, not the local 4090). DEFAULT-OFF
            # (or any unknown blade) -> the LOCAL VRAM_BUDGET_MB scalar EXACTLY as today.
            _budget = _blade_vram_budget(ep) if MULTIBLADE_ENABLE else VRAM_BUDGET_MB
            while time.monotonic() < deadline:
                res = await _resident_cached(ep)
                # measured resident + Phase-1 pending sibling reservations, so two
                # workers co-loading onto this endpoint in the same turn account
                # for each other before either has finished loading.
                used_mb = (sum(int(m.get("size_vram") or 0)
                               for m in res) // (1024 * 1024)
                           + int(_ENDPOINT_RESERVED.get(ep, 0)))
                # this cold model's cost: its own size if /api/ps already knows it
                # (re-load), else the worker's DECLARED vram_mb (est_mb), else the
                # conservative flat estimate.
                est = next((int(m.get("size_vram") or 0) // (1024 * 1024)
                            for m in res
                            if _norm_model_tag(m.get("name")) == _norm_model_tag(model)),
                           0) or est_mb or VRAM_COLOAD_EST_MB
                # fits if used + this model + reserve stays under budget (the blade's
                # budget when multiblade is on; the local scalar otherwise -- _budget).
                if (not VRAM_COLOAD_ENABLE) or \
                        (used_mb + est + VRAM_COLOAD_RESERVE_MB) <= _budget:
                    break
                # Doesn't fit: first RECLAIM an idle model's VRAM (clear idle
                # agents so this one loads now -> 'nothing in the pipeline idle'),
                # then re-check immediately; only sleep-wait if reclaim freed
                # nothing (a sibling dispatch may finish + free VRAM). Reclaim once
                # per admit so we don't thrash a steady-state-full endpoint.
                if VRAM_RECLAIM_IDLE and not _reclaimed:
                    _reclaimed = True
                    if await _reclaim_idle_vram(
                            ep, model, est + VRAM_COLOAD_RESERVE_MB):
                        continue
                await asyncio.sleep(min(0.5, max(0.0, deadline - time.monotonic())))
    except Exception:  # noqa: BLE001 -- admission must never block a turn
        log.warning("Admit check encountered unexpected error", exc_info=True)
        return
