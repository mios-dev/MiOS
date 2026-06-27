# AI-hint: The MiOS agent-pipe scheduler module. Provides (1) PriorityGate, the WS-1
#   bounded concurrency gate that enforces priority-based reordering + anti-starvation
#   so high-priority agent dispatches jump ahead of lower-priority ones, and (2) the
#   lane/scheduling/priority DECISION helpers extracted VERBATIM from server.py
#   (strangler-fig refactor): _lane_tool_cap (per-lane visible-tool cap),
#   _agent_offload_engine (light offload-engine pick for concurrent fan-out),
#   _resolve_autonomous_priority (background-turn priority scalar from SSOT),
#   _sched_priority (the advisory priority = f(complexity, urgency, resource-need),
#   with tiers/weights SSOT in mios.toml [sched] + a priority_mode model-signal hook,
#   that PriorityGate makes ACTIVE), and _lane_sem_key (the per-lane semaphore key). The
#   helpers close over server-owned SSOT constants + _agent_lane via a configure() DI
#   seam (the constants stay server-owned so the importable surface is unchanged);
#   _DISPATCH_TOML comes straight from mios_config. This module NEVER imports server
#   (one-way boundary); server.py re-imports the helpers under their EXACT names so the
#   surface stays byte-identical.
# AI-related: server.py, mios_config.py, test_mios_sched.py
# AI-functions: __init__, cap, available, in_flight, queued, head_priority, stats, _pick, acquire, _release, release, class PriorityGate, configure, _lane_tool_cap, _agent_offload_engine, _resolve_autonomous_priority, _sched_priority, _sched_priority_core, _lane_sem_key
"""mios_sched -- scheduler primitives for the MiOS agent-pipe (WS-1, the AIOS
Agent Scheduler reordering layer).

Pure stdlib (asyncio / time / collections) so it unit-tests in isolation, in the
sibling-module style of mios_jsonsalvage / mios_owui. server.py owns the wiring
(the SSOT flag, the global instance, the degrade-open context manager); this
module owns only the reusable mechanism.

PriorityGate
============
A bounded concurrency gate -- like asyncio.Semaphore -- EXCEPT that, when
contended, it hands the next freed permit to the HIGHEST-PRIORITY waiter
(FIFO tie-break) instead of the earliest arrival. That is the reordering a plain
Semaphore cannot do: with a Semaphore, once a dispatch is queued behind the
global cap, a later higher-priority dispatch can never jump ahead. The MiOS
agent-pipe already computes a per-turn / per-lane priority (_sched_priority /
_dispatch_priority) but, before WS-1, those were advisory only because the global
cap admitted FIFO. PriorityGate makes them ACTIVE.

Anti-starvation
---------------
Strict priority can starve low-priority work forever under sustained
high-priority load. `starvation_s > 0` enables aging: a waiter that has been
queued longer than `starvation_s` is served AHEAD of priority, so the lowest
lanes still make progress.

Key invariant
-------------
    available > 0  =>  no waiters

Release hands a permit DIRECTLY to the chosen waiter (it never bumps
`available` while any waiter exists). Therefore the acquire fast path -- "a
permit is free, take it" -- can only run when the queue is empty, so it can
never jump ahead of a queued higher-priority dispatch. This keeps the fast path
allocation-free (no future, no heap) while preserving correctness.

Concurrency model: single-threaded asyncio. There is no await between the check
and the mutation in any method, so no lock is needed.
"""

from __future__ import annotations

import asyncio
import collections
import os
import time
from typing import Optional

from mios_config import _DISPATCH_TOML, _toml_section


class PriorityGate:
    """Priority-ordered, bounded, cancellation-safe async concurrency gate."""

    def __init__(self, permits: int, starvation_s: float = 0.0) -> None:
        self._cap = max(1, int(permits))
        self._avail = self._cap
        self._starv = max(0.0, float(starvation_s))
        # seq -> [priority, enqueue_monotonic, future]. Insertion-ordered, and
        # seq is monotonic, so the first entry is always the oldest waiter.
        self._waiters: "collections.OrderedDict[int, list]" = collections.OrderedDict()
        self._seq = 0

    # ── observability (read-only; never mutates state) ────────────────────
    @property
    def cap(self) -> int:
        return self._cap

    @property
    def available(self) -> int:
        return self._avail

    @property
    def in_flight(self) -> int:
        return self._cap - self._avail

    @property
    def queued(self) -> int:
        return len(self._waiters)

    def head_priority(self) -> Optional[float]:
        """Priority of the waiter that would be served next (None if idle)."""
        seq = self._pick()
        return None if seq is None else self._waiters[seq][0]

    def stats(self) -> dict:
        return {
            "cap": self._cap,
            "available": self._avail,
            "in_flight": self.in_flight,
            "queued": self.queued,
            "head_priority": self.head_priority(),
        }

    # ── core ──────────────────────────────────────────────────────────────
    def _pick(self) -> Optional[int]:
        """Return the seq of the next waiter to serve, or None. Pure (no
        mutation). Skips any future already resolved (defensive)."""
        live = [(seq, w) for seq, w in self._waiters.items() if not w[2].done()]
        if not live:
            return None
        # Anti-starvation: if the OLDEST live waiter has aged past the threshold,
        # serve it regardless of priority so low lanes never indefinitely starve.
        if self._starv > 0.0:
            old_seq, old_w = live[0]  # insertion order -> oldest first
            if (time.monotonic() - old_w[1]) >= self._starv:
                return old_seq
        # Otherwise: highest priority wins; older (smaller seq) breaks ties.
        best_seq: Optional[int] = None
        best_key = None
        for seq, w in live:
            key = (w[0], -seq)  # max priority, then min seq
            if best_key is None or key > best_key:
                best_key, best_seq = key, seq
        return best_seq

    async def acquire(self, priority: float = 5.0) -> None:
        """Acquire one permit, blocking in PRIORITY order when contended."""
        # Fast path: a permit is free. By the invariant this implies the queue is
        # empty, so taking it cannot jump a queued higher-priority dispatch.
        if self._avail > 0 and not self._waiters:
            self._avail -= 1
            return
        # Contended: enqueue and await our grant.
        self._seq += 1
        seq = self._seq
        fut = asyncio.get_running_loop().create_future()
        self._waiters[seq] = [float(priority), time.monotonic(), fut]
        try:
            await fut
        except asyncio.CancelledError:
            # Cancelled while suspended at `await fut`:
            #   (a) not yet granted (fut not done) -> just drop our queue entry.
            #   (b) granted then cancelled (fut done) -> a permit was handed to
            #       us; hand it back so it is not leaked.
            self._waiters.pop(seq, None)
            if fut.done() and not fut.cancelled():
                self._release()
            raise
        # Granted: the releaser transferred a permit to us without bumping
        # `available` (direct hand-off), so we already hold it. Proceed.
        return

    def _release(self) -> None:
        """Return one permit: hand it to the best waiter, else to the pool."""
        while self._waiters:
            seq = self._pick()
            if seq is None:
                break
            _prio, _ts, fut = self._waiters.pop(seq)
            if fut.done():
                continue  # cancelled before we got here -> skip, try the next
            fut.set_result(True)  # direct hand-off: the permit stays allocated
            return
        self._avail += 1

    def release(self) -> None:
        self._release()


# ── Lane / scheduling / priority DECISION helpers (strangler-fig refactor) ───────
# Moved VERBATIM from server.py. Each closes over server-owned SSOT constants or the
# server-resident _agent_lane; those stay OWNED by server.py (every name is in the
# importable-surface golden), and server.py calls configure() with them under their
# EXACT original names. The None placeholders below let a standalone import succeed;
# every consumer is a runtime call, except _resolve_autonomous_priority which server.py
# calls at import time -- so server configures its one dep (_AUTO_PRIO_WORDS) first.
# _DISPATCH_TOML is imported directly from mios_config (static SSOT). One-way boundary:
# this module never imports server.

_AUTO_PRIO_WORDS = None
LANE_TOOL_CAP = None
SLOW_LANES = None
SLOW_LANE_TOOL_CAP = None
DEFAULT_TOOL_CAP = None
DISPATCH_OFFLOAD_CPU = None
_OFFLOAD_ENGINES = None
_agent_lane = None


_INJECTED = frozenset((
    "_AUTO_PRIO_WORDS", "LANE_TOOL_CAP", "SLOW_LANES", "SLOW_LANE_TOOL_CAP",
    "DEFAULT_TOOL_CAP", "DISPATCH_OFFLOAD_CPU", "_OFFLOAD_ENGINES", "_agent_lane",
))


def configure(**deps) -> None:
    """Inject server-side deps under their EXACT original names (one-way boundary).

    Called from ``server.py`` (possibly more than once with a partial set) after each
    injected symbol is defined. Each keyword equals the module global it sets.
    """
    g = globals()
    for _k, _v in deps.items():
        if _k in _INJECTED:
            g[_k] = _v


def _lane_tool_cap(lane: str) -> int:
    """Tool cap (0 = full). Explicit entry > slow-lane fallback > DEFAULT_TOOL_CAP."""
    _l = str(lane or "").lower().strip()
    if _l in LANE_TOOL_CAP:
        return LANE_TOOL_CAP[_l]
    if _l in SLOW_LANES and SLOW_LANE_TOOL_CAP > 0:
        return SLOW_LANE_TOOL_CAP
    return DEFAULT_TOOL_CAP


def _resolve_autonomous_priority() -> float:
    raw = os.environ.get("MIOS_AUTONOMOUS_PRIORITY")
    if raw in (None, ""):
        raw = _DISPATCH_TOML.get("autonomous_priority", "low")
    try:
        return float(raw)
    except (TypeError, ValueError):
        return _AUTO_PRIO_WORDS.get(str(raw).strip().lower(), 1.0)


def _agent_offload_engine(cfg: dict) -> Optional[str]:
    """Pick a LIGHT engine the agent can run on for concurrent fan-out, else None
    (caller uses the agent's OWN endpoint). DEFAULT: None for everything
    (DISPATCH_OFFLOAD_CPU off) so each distinct node runs on its OWN hardware
    concurrently instead of all funneling to the single CPU lane (operator
)."""
    if not DISPATCH_OFFLOAD_CPU:
        return None
    engines = cfg.get("engines") or {}
    for eng in _OFFLOAD_ENGINES:
        if eng in engines:
            return eng
    return None


# ── _sched_priority SSOT (NO-HARDCODE Law 7) ─────────────────────────────────────
# The turn-priority scorer's tiers + weights are SSOT in mios.toml [sched], read via
# mios_config._toml_section. _SCHED_FALLBACK holds the degrade-open defaults -- each
# value EQUALS the long-standing literal, so an absent or malformed [sched] reproduces
# the prior scoring byte-for-byte (the sanctioned NO-HARDCODE fallback pattern). The
# urgency term LISTS are operator-localizable SSOT; the matcher is plain Unicode-
# casefold membership (NOT an English/ASCII keyword gate). The priority_mode flag (env
# MIOS_SCHED_PRIORITY_MODE) selects behaviour; the default reproduces today's numbers:
#   "ssot"  -> parameterized lexical urgency from the [sched] term sets.
#   "model" -> PREFER an already-present model-supplied numeric refined.urgency /
#              refined.complexity, else the lexical/derived path (adds no LLM call).
_SCHED_FALLBACK = {
    "priority_mode": "ssot",
    "urgency_default": 5,
    "urgency_high": 9,
    "urgency_low": 2,
    "urgency_dispatch_floor": 8,
    "urgency_high_terms": ("high", "urgent", "now"),
    "urgency_low_terms": ("low", "background", "defer"),
    "complexity_base": 1,
    "complexity_hints_divisor": 2,
    "complexity_cap": 10,
    "score_complexity_weight": 0.4,
    "score_urgency_weight": 0.6,
    "score_round_ndigits": 2,
}
try:
    _SCHED_TOML = _toml_section("sched")
except Exception:  # noqa: BLE001 -- degrade-open: absent/broken config -> fallbacks
    _SCHED_TOML = {}


def _sched_priority_core(refined: Optional[dict], cfg: dict) -> dict:
    """Compute the turn priority from ``refined`` + the resolved [sched] ``cfg`` table.
    Every tier/weight resolves from ``cfg`` with an _SCHED_FALLBACK default (== the
    historical literal), so an empty ``cfg`` is byte-identical to the prior heuristic.
    Split from _sched_priority so the wrapper can degrade-open (cfg={}) on any error."""
    r = refined if isinstance(refined, dict) else {}
    F = _SCHED_FALLBACK

    def _num(key, cast=int):
        v = cfg.get(key)
        if v is None:
            return F[key]
        try:
            return cast(v)
        except (TypeError, ValueError):
            return F[key]

    def _termset(key):
        # Operator-localizable SSOT vocabulary -> Unicode-casefold set (no ASCII gate).
        v = cfg.get(key)
        seq = v if isinstance(v, (list, tuple)) else F[key]
        return frozenset(str(t).casefold() for t in seq)

    def _as_number(v):
        # An already-present model-supplied NUMERIC signal (int/float, or a numeric
        # string); a bool is not a number here. None when the field is non-numeric.
        if isinstance(v, bool) or v is None:
            return None
        if isinstance(v, (int, float)):
            return v
        try:
            f = float(str(v).strip())
        except (TypeError, ValueError):
            return None
        return int(f) if f.is_integer() else f

    model_mode = (str(os.environ.get("MIOS_SCHED_PRIORITY_MODE")
                      or cfg.get("priority_mode") or F["priority_mode"]
                      ).strip().casefold() == "model")
    steps = r.get("tasks") if isinstance(r.get("tasks"), list) else []
    hints = r.get("hint_tools") if isinstance(r.get("hint_tools"), list) else []
    div = _num("complexity_hints_divisor")

    # Complexity: an already-present model number wins in model-mode; else derive it
    # from the task + tool-hint counts. Bounded by the SSOT cap either way.
    complexity = _as_number(r.get("complexity")) if model_mode else None
    if complexity is None:
        complexity = _num("complexity_base") + len(steps) + (
            len(hints) // div if div else 0)
    complexity = min(_num("complexity_cap"), complexity)

    # Urgency: an already-present model number wins in model-mode; else membership in
    # the SSOT term sets (Unicode-casefold -- localizable, not an English/ASCII gate).
    urgency = _as_number(r.get("urgency")) if model_mode else None
    if urgency is None:
        urgency = _num("urgency_default")
        u = str(r.get("urgency", "")).casefold()
        if u in _termset("urgency_high_terms"):
            urgency = _num("urgency_high")
        elif u in _termset("urgency_low_terms"):
            urgency = _num("urgency_low")

    intent = str(r.get("intent", "agent"))
    # OS-control / dispatch single-actions are cheap + interactive -> high floor.
    if intent == "dispatch":
        urgency = max(urgency, _num("urgency_dispatch_floor"))
    score = round((complexity * _num("score_complexity_weight", float))
                  + (urgency * _num("score_urgency_weight", float)),
                  _num("score_round_ndigits"))
    return {"score": score, "complexity": complexity, "urgency": urgency,
            "intent": intent}


def _sched_priority(refined: Optional[dict]) -> dict:
    """Score a turn the AIOS way: priority = f(complexity, urgency, resource-need).
    Derived from the refined plan (no hardcoded topic map): complexity from the
    task/step count + tool count; urgency from the model's refined.urgency signal (a
    numeric model value when [sched].priority_mode='model', else membership in the
    operator-localizable [sched] urgency vocabulary, matched Unicode-casefold);
    resource-need from the target lane. Higher = sooner. Tiers + weights are SSOT in
    mios.toml [sched] with degrade-open fallbacks EQUAL to the historical literals, so
    an absent section is byte-identical. Currently ADVISORY (logged + exposed) -- the
    lane semaphores still admit in arrival order; this is the hook a future policy
    engine would order on. Degrades open on any error to the literal-fallback path."""
    try:
        return _sched_priority_core(
            refined, _SCHED_TOML if isinstance(_SCHED_TOML, dict) else {})
    except Exception:  # noqa: BLE001 -- degrade-open to the literal-fallback heuristic
        try:
            return _sched_priority_core(refined, {})
        except Exception:  # noqa: BLE001 -- last resort: the neutral fallback score
            _f = _SCHED_FALLBACK
            return {"score": round(_f["complexity_base"] * _f["score_complexity_weight"]
                                   + _f["urgency_default"] * _f["score_urgency_weight"],
                                   _f["score_round_ndigits"]),
                    "complexity": _f["complexity_base"],
                    "urgency": _f["urgency_default"], "intent": "agent"}


def _lane_sem_key(cfg: dict) -> str:
    """SEMAPHORE KEY -- the distinct HARDWARE UNIT an agent runs on, which is
    NOT the same as its lane CATEGORY (_agent_lane). With more than one machine
    of a category on the tailnet (e.g. the local 4090 AND a remote GPU box),
    'gpu' is no longer ONE piece of hardware, so a shared 'gpu' semaphore would
    throttle BOTH boxes to a single per-lane budget. A custom per-node lane
    (e.g. 'potato-gpu' -- any lane outside the base category set) therefore gets
    its OWN semaphore so distinct machines fire with INDEPENDENT concurrency
 budgets ("each remote node gets its OWN semaphore").
    Agents without a custom lane fall back to the category (local hardware).
    NOTE: _agent_lane stays the CATEGORY (gpu/cpu/igpu/mobile/accelerator) so
    SLOW_LANES trimming + the cpu-parallelism bonus keep working -- e.g. a
    'potato-cpu' node is category 'cpu' (slow -> trimmed) yet has its OWN sem.

 SWARM Phase-0 : an explicit `sub_lane` is the FINEST
    semaphore key -- it lets N single-model servers on the SAME device (e.g.
    'gpu0' for several concurrent small llama-server instances on the one 4090)
    each hold an INDEPENDENT concurrency budget instead of all collapsing onto a
    single 'gpu' semaphore (the documented OOM-cascade mode). Defaults to the
    prior behaviour when unset -> byte-identical for today's nodes (none set it)."""
    sub = str(cfg.get("sub_lane", "")).lower().strip()
    if sub:
        return sub                  # per-engine sub-lane -> dedicated semaphore
    lane = str(cfg.get("lane", "")).lower().strip()
    if lane and lane not in ("cpu", "gpu", "igpu", "accelerator", "mobile"):
        return lane                 # custom per-node lane -> dedicated semaphore
    return _agent_lane(cfg)         # base category -> shared local-hardware lane
