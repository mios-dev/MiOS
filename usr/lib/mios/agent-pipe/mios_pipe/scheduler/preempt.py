# AI-hint: WS-A12 round-robin preemption state machine + generation-snapshot contract, PLUS the T-019/SCHED-01 TURN-boundary preemption seam AND th...
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_lib_mios_agent_pipe_mios_pipe_scheduler_preempt_py.md

from __future__ import annotations

import asyncio
import collections
import logging
import os
import time
from typing import Dict, List, Optional

from mios_config import _toml_section  # layered mios.toml SSOT reader (one-way; never imports server)
import mios_tokenize  # WS-A5 token-accounting seam (shared ~chars/token measure; never a re-derived //N)

log = logging.getLogger("mios-agent-pipe")

CONTINUE = "continue"   # same task keeps the lane -- run another slice
PREEMPT = "preempt"     # snapshot this gen's KV + yield the lane to a waiter
COMPLETE = "complete"   # the slice hit a stop/EOS -> the generation is done


def decide(*, finished: bool, quantum_expired: bool,
           higher_priority_waiting: bool, can_suspend: bool) -> str:
    """Pure per-slice-boundary decision for an interruptible generation.

    - finished -> COMPLETE (the decode loop saw a stop/EOS within the slice).
    - a higher-priority waiter IS queued AND this run has spent its quantum AND
      we can bound the suspension (a free snapshot slot exists) -> PREEMPT.
    - otherwise CONTINUE (run another slice).

    Bounded-suspension safety: when no snapshot slot is free (`can_suspend` is
    False) we NEVER preempt -- the task runs to completion instead -- so the set
    of suspended generations can never exceed the cap and a preempted task is
    never dropped on the floor. A generation is only ever preempted at a slice
    boundary, so its partial output up to that boundary is always captured."""
    if finished:
        return COMPLETE
    if quantum_expired and higher_priority_waiting and can_suspend:
        return PREEMPT
    return CONTINUE


class Quantum:
    """A dispatch's time-slice: started at t0, expires after `limit_s` seconds."""

    __slots__ = ("t0", "limit_s")

    def __init__(self, t0: float, limit_s: float) -> None:
        self.t0 = float(t0)
        self.limit_s = float(limit_s)

    def expired(self, now: float) -> bool:
        return self.limit_s > 0 and (float(now) - self.t0) >= self.limit_s

    def remaining(self, now: float) -> float:
        if self.limit_s <= 0:
            return float("inf")
        return max(0.0, self.limit_s - (float(now) - self.t0))


class Snapshot:
    """The preempted generation's saved state (the restore contract)."""

    __slots__ = ("task_id", "priority", "position", "partial", "slot")

    def __init__(self, task_id: str, priority: float, position: int,
                 partial: str, slot: int) -> None:
        self.task_id = str(task_id)
        self.priority = float(priority)
        self.position = int(position)
        self.partial = partial
        self.slot = int(slot)

    def to_dict(self) -> dict:
        return {"task_id": self.task_id, "priority": self.priority,
                "position": self.position, "slot": self.slot,
                "partial_len": len(str(self.partial or ""))}


class PreemptScheduler:
    """Bounded RR preemption bookkeeping: a free-list of `max_suspended` snapshot
    slots + a priority-ordered suspended queue. Admission is capped so a runaway
    fan-out can't suspend unboundedly (the snapshot slots ARE the cap)."""

    def __init__(self, max_suspended: int = 4) -> None:
        self._cap = max(1, int(max_suspended))
        self._free: List[int] = list(range(self._cap))      # available slot ids
        self._suspended: "collections.OrderedDict[str, Snapshot]" = collections.OrderedDict()

    def can_admit(self) -> bool:
        """True if a slot is free to suspend into (else the caller must run the
        task to completion rather than preempt -- bounded suspension)."""
        return bool(self._free)

    def acquire_slot(self) -> Optional[int]:
        """Take a free snapshot slot id, or None when the cap is reached."""
        return self._free.pop(0) if self._free else None

    def release_slot(self, slot: int) -> None:
        """Return a slot to the free-list (idempotent; ignores unknown/dup)."""
        s = int(slot)
        if 0 <= s < self._cap and s not in self._free:
            self._free.append(s)
            self._free.sort()

    def suspend(self, snap: Snapshot) -> bool:
        """Record a preempted task's snapshot. The slot must already be acquired
        (snap.slot). Returns False if that task is already suspended."""
        if snap.task_id in self._suspended:
            return False
        self._suspended[snap.task_id] = snap
        return True

    def resume(self) -> Optional[Snapshot]:
        """Pop the HIGHEST-priority suspended task to resume (FIFO tie-break by
        insertion order), freeing its slot. None when nothing is suspended."""
        if not self._suspended:
            return None
        best_id = None
        best_key = None
        for i, (tid, snap) in enumerate(self._suspended.items()):
            key = (snap.priority, -i)   # max priority, then earliest-suspended
            if best_key is None or key > best_key:
                best_key, best_id = key, tid
        snap = self._suspended.pop(best_id)
        self.release_slot(snap.slot)
        return snap

    def discharge(self, task_id: str) -> Optional[Snapshot]:
        """Remove a SPECIFIC suspended task and free its slot, returning its
        Snapshot (None if it was not suspended). This is the self-resume path for
        the gate-driven driver: a preempted generation re-acquires the lane via
        the priority gate (which already orders waiters by priority), so it
        discharges ITS OWN snapshot rather than popping the global highest via
        resume() -- that would let one coroutine steal another's saved state."""
        snap = self._suspended.pop(str(task_id), None)
        if snap is not None:
            self.release_slot(snap.slot)
        return snap

    def is_suspended(self, task_id: str) -> bool:
        return str(task_id) in self._suspended

    def stats(self) -> dict:
        return {
            "max_suspended": self._cap,
            "suspended": len(self._suspended),
            "free_slots": len(self._free),
            "queued_ids": list(self._suspended.keys()),
        }


class TokenSliceQueue:
    """Token-time-sliced priority queue (T-020 / SCHED-02) -- the queueing POLICY on
    top of the T-019 turn-boundary mechanism. It orders ready turns by priority and,
    for a dispatched turn, accounts the tokens it generates against a per-turn SLICE
    BUDGET (a token-time quantum -- N tokens, NOT wall-clock). When a turn crosses its
    slice budget the scheduler re-evaluates (the caller drives that via slice_boundary
    -> turn_boundary): a higher-priority waiter may preempt it, else it continues.

    Pure bookkeeping (deterministic; token counts are passed IN) so it unit-tests in
    isolation, like PreemptScheduler. Single-threaded asyncio: every method is
    allocation-light and lock-free (no await between a check and its mutation). The
    queue is BOUNDED (max_turns) and evicts only STALE ready entries, so its advisory
    bookkeeping can never grow without limit even if a caller misses a remove(); a
    turn's coroutine is never affected by eviction (degrade-open). The live token feed
    + the precise gate-relative enqueue/dispatch placement are operator-live-validated;
    this class owns the MLFQ ordering (LRU eviction + contention-gated priority decay)
    + slice accounting."""

    __slots__ = ("_default_slice", "_cap", "_turns", "_seq")

    _PRIO, _BUDGET, _USED, _SEQ, _RUNNING = range(5)

    def __init__(self, default_slice_tokens: int = 0, max_turns: int = 0) -> None:
        self._default_slice = max(0, int(default_slice_tokens or 0))
        self._cap = max(0, int(max_turns or 0))
        self._turns: "collections.OrderedDict[str, list]" = collections.OrderedDict()
        self._seq = 0

    def _evict_if_full(self) -> None:
        """Bounded-queue backstop: at the cap, drop the LEAST RECENTLY USED ready (not-running)
        row so a missed remove() can never leak. Running rows are never evicted; if
        somehow all rows are running we drop the LRU to honour the bound. This
        removes only ADVISORY bookkeeping -- the turn's coroutine is unaffected."""
        if self._cap <= 0 or len(self._turns) < self._cap:
            return
        for tid, row in self._turns.items():        # LRU order -> least recent first
            if not row[self._RUNNING]:
                self._turns.pop(tid, None)
                return
        self._turns.popitem(last=False)

    def enqueue(self, task_id: str, priority: float = 5.0,
                slice_tokens: "Optional[int]" = None) -> bool:
        """Register a READY turn with its priority + per-slice token budget (defaults
        to the SSOT slice size). A re-enqueue of a KNOWN turn refreshes its priority +
        budget in place and returns False (never a duplicate); a NEW turn returns
        True. Bounded: a new turn may evict the oldest stale ready row."""
        tid = str(task_id)
        budget = (self._default_slice if slice_tokens is None
                  else max(0, int(slice_tokens)))
        row = self._turns.get(tid)
        if row is not None:
            row[self._PRIO], row[self._BUDGET] = float(priority), budget
            self._turns.move_to_end(tid)
            return False
        self._evict_if_full()
        self._seq += 1
        self._turns[tid] = [float(priority), budget, 0, self._seq, False]
        return True

    def dispatch(self) -> "Optional[str]":
        """Pick + mark-running the highest-priority READY turn (FIFO tie-break by
        enqueue order), returning its task_id (None when nothing is ready). This is
        the scheduler 'dispatch the highest-priority ready turn' primitive."""
        best_id, best_key = None, None
        for tid, row in self._turns.items():
            if row[self._RUNNING]:
                continue
            key = (row[self._PRIO], -row[self._SEQ])  # max priority, then earliest
            if best_key is None or key > best_key:
                best_key, best_id = key, tid
        if best_id is not None:
            self._turns[best_id][self._RUNNING] = True
        return best_id

    def account(self, task_id: str, tokens: int) -> bool:
        """Add `tokens` to the turn's CURRENT-slice counter. Returns True iff it
        crossed its slice budget (a slice boundary -- the caller then re-evaluates),
        carrying the remainder into the next slice. A 0/absent budget never trips
        (slicing off). Unknown task / bad count -> False (degrade-open)."""
        row = self._turns.get(str(task_id))
        if row is None:
            return False
        try:
            row[self._USED] += max(0, int(tokens))
        except (TypeError, ValueError):
            return False
        budget = row[self._BUDGET]
        self._turns.move_to_end(str(task_id))       # mark recently used (LRU tracking)
        if budget > 0 and row[self._USED] >= budget:
            row[self._USED] -= budget               # carry the remainder forward
            if self.head_priority(exclude=task_id) is not None:
                row[self._PRIO] = max(0.0, row[self._PRIO] - 1.0)
            return True
        return False

    def head_priority(self, exclude: "Optional[str]" = None) -> "Optional[float]":
        """Highest priority among the READY (not-running) waiters, excluding `exclude`
        (typically the running turn asking 'is anyone above me?'). None when no such
        waiter. Pure (no mutation). This is the queue's 'a higher-priority turn is
        waiting' signal that slice_boundary feeds the turn_boundary mechanism."""
        ex = None if exclude is None else str(exclude)
        best = None
        for tid, row in self._turns.items():
            if row[self._RUNNING] or tid == ex:
                continue
            if best is None or row[self._PRIO] > best:
                best = row[self._PRIO]
        return best

    def requeue(self, task_id: str) -> None:
        """Mark a running turn READY again (it yielded at a slice boundary); the next
        dispatch() re-picks strictly by priority. Idempotent; unknown task ignored."""
        row = self._turns.get(str(task_id))
        if row is not None:
            row[self._RUNNING] = False
            self._turns.move_to_end(str(task_id))

    def remove(self, task_id: str) -> "Optional[list]":
        """Drop a finished/cancelled turn from the queue (idempotent)."""
        return self._turns.pop(str(task_id), None)

    def is_tracked(self, task_id: str) -> bool:
        return str(task_id) in self._turns

    def stats(self) -> dict:
        return {
            "default_slice_tokens": self._default_slice,
            "max_turns": self._cap,
            "turns": len(self._turns),
            "ready": sum(1 for r in self._turns.values() if not r[self._RUNNING]),
            "running": sum(1 for r in self._turns.values() if r[self._RUNNING]),
            "head_priority": self.head_priority(),
        }


_SCHEDULER_FALLBACK = {
    "preempt_enable": False,   # MASTER FLAG (T-019) -- off => turn_boundary is a pass-through no-op
    "queue_enable": False,     # MASTER FLAG (T-020) -- off => slice_boundary is a pass-through no-op
    "max_suspended": 4,        # mirrors PreemptScheduler(max_suspended=...): bounded snapshots
    "quantum_s": 8.0,          # mios_preempt.Quantum limit (turn time-slice; <=0 = unbounded)
    "slice_tokens": 256,       # TokenSliceQueue per-turn slice budget in TOKENS (0 = slicing off)
    "queue_max_turns": 64,     # TokenSliceQueue bounded advisory capacity (0 = unbounded)
    "priority_levels": 0,      # discrete priority buckets (0 = continuous; advisory substrate knob)
    "max_preempt_depth": 1,    # bounded cooperative-yield ticks per boundary (no busy-wait/starvation)
}


def _as_bool(v, default: bool = False) -> bool:
    """Coerce a TOML/env value to bool. A real bool passes through; a string uses
    the same off-token set as the rest of the pipe's flags (a config-literal
    parser, NOT a decision gate on user content); None -> default."""
    if isinstance(v, bool):
        return v
    if v is None:
        return default
    return str(v).strip().lower() not in {"false", "0", "no", "off", ""}


def _scheduler_cfg() -> dict:
    """Resolve the [scheduler] table: layered mios.toml merged over the degrade-open
    fallbacks, then MIOS_SCHEDULER_* env overrides (highest precedence). Pure SSOT
    (mios_config); never raises (missing/broken config -> fallbacks)."""
    out = dict(_SCHEDULER_FALLBACK)
    try:
        sec = _toml_section("scheduler") or {}
    except Exception:  # noqa: BLE001 -- degrade-open: absent/broken config -> fallbacks
        sec = {}
    for k in out:
        if isinstance(sec, dict) and sec.get(k) is not None:
            out[k] = sec[k]

    def _envnum(name, cur, cast):
        v = os.environ.get(name)
        if v in (None, ""):
            return cur
        try:
            return cast(v)
        except (TypeError, ValueError):
            return cur

    _pe = os.environ.get("MIOS_SCHEDULER_PREEMPT_ENABLE")
    out["preempt_enable"] = (_as_bool(_pe) if _pe is not None
                             else _as_bool(out.get("preempt_enable"), False))
    _qe = os.environ.get("MIOS_SCHEDULER_QUEUE_ENABLE")
    out["queue_enable"] = (_as_bool(_qe) if _qe is not None
                           else _as_bool(out.get("queue_enable"), False))
    out["max_suspended"] = _envnum("MIOS_SCHEDULER_MAX_SUSPENDED",
                                   int(out.get("max_suspended") or 4), int)
    out["quantum_s"] = _envnum("MIOS_SCHEDULER_QUANTUM_S",
                               float(out.get("quantum_s") or 0.0), float)
    out["slice_tokens"] = _envnum("MIOS_SCHEDULER_SLICE_TOKENS",
                                  int(out.get("slice_tokens") or 0), int)
    out["queue_max_turns"] = _envnum("MIOS_SCHEDULER_QUEUE_MAX_TURNS",
                                     int(out.get("queue_max_turns") or 0), int)
    out["priority_levels"] = _envnum("MIOS_SCHEDULER_PRIORITY_LEVELS",
                                     int(out.get("priority_levels") or 0), int)
    out["max_preempt_depth"] = _envnum("MIOS_SCHEDULER_MAX_PREEMPT_DEPTH",
                                       int(out.get("max_preempt_depth") or 1), int)
    return out


_CFG = _scheduler_cfg()
PREEMPT_ENABLE = _as_bool(_CFG.get("preempt_enable"), False)
QUEUE_ENABLE = _as_bool(_CFG.get("queue_enable"), False)
TURN_QUANTUM_S = float(_CFG.get("quantum_s") or 0.0)
SLICE_TOKENS = int(_CFG.get("slice_tokens") or 0)
QUEUE_MAX_TURNS = int(_CFG.get("queue_max_turns") or 0)
PRIORITY_LEVELS = int(_CFG.get("priority_levels") or 0)
MAX_PREEMPT_DEPTH = int(_CFG.get("max_preempt_depth") or 1)
_TURN_SCHEDULER: "Optional[PreemptScheduler]" = PreemptScheduler(
    max_suspended=int(_CFG.get("max_suspended") or 4))
_TURN_QUEUE: "Optional[TokenSliceQueue]" = TokenSliceQueue(
    default_slice_tokens=SLICE_TOKENS, max_turns=QUEUE_MAX_TURNS)
_HEAD_PRIORITY = None
_CLOCK = time.monotonic

_INJECTED = frozenset((
    "PREEMPT_ENABLE", "QUEUE_ENABLE", "TURN_QUANTUM_S", "SLICE_TOKENS",
    "PRIORITY_LEVELS", "MAX_PREEMPT_DEPTH",
    "_TURN_SCHEDULER", "_TURN_QUEUE", "_HEAD_PRIORITY", "_CLOCK",
))
_CFG_ALIAS = {
    "preempt_enable": "PREEMPT_ENABLE", "queue_enable": "QUEUE_ENABLE",
    "quantum_s": "TURN_QUANTUM_S", "slice_tokens": "SLICE_TOKENS",
    "priority_levels": "PRIORITY_LEVELS", "max_preempt_depth": "MAX_PREEMPT_DEPTH",
    "turn_scheduler": "_TURN_SCHEDULER", "turn_queue": "_TURN_QUEUE",
    "head_priority": "_HEAD_PRIORITY", "clock": "_CLOCK",
}


def configure(**deps) -> None:
    """Override the turn-boundary wiring under exact names (one-way boundary).

    server.py calls this to inject the live PriorityGate head-priority probe
    (``head_priority=``) so the seam can tell when a higher-priority turn waits;
    tests inject a spy ``turn_scheduler=`` / ``clock=`` / ``preempt_enable=``.
    Friendly aliases (head_priority/turn_scheduler/clock/quantum_s/...) map to the
    module globals. Unknown keys are ignored (partial-injection safe)."""
    g = globals()
    for k, v in deps.items():
        key = _CFG_ALIAS.get(k, k)
        if key in _INJECTED:
            g[key] = v


def _higher_priority_waiting(priority: float,
                             task_id: "Optional[str]" = None) -> bool:
    """True iff a higher-priority turn is waiting. Two OR-combined signals: the
    injected gate head-priority probe (T-019) and -- ONLY when the token-time-sliced
    queue is enabled ([scheduler].queue_enable, T-020) -- the queue's highest-priority
    READY waiter (excluding this turn). False when unwired or on any probe error -- no
    signal => no preemption (degrade-open). With queue_enable OFF this is byte-
    identical to the prior probe-only behaviour."""
    best = None
    probe = _HEAD_PRIORITY
    if probe is not None:
        try:
            h = probe()
            if h is not None:
                best = float(h)
        except Exception:  # noqa: BLE001 -- a flaky probe must never preempt
            best = None
    if QUEUE_ENABLE and _TURN_QUEUE is not None:
        try:
            qh = _TURN_QUEUE.head_priority(exclude=task_id)
            if qh is not None and (best is None or float(qh) > best):
                best = float(qh)
        except Exception:  # noqa: BLE001 -- a flaky queue read must never preempt
            pass
    return best is not None and best > float(priority)


async def turn_boundary(*, task_id: str, priority: float = 5.0,
                        now: "Optional[float]" = None) -> bool:
    """Turn-boundary preemption seam (T-019 / SCHED-01). The dispatch turn loop
    calls this AFTER a turn's AIOS priority is known -- the clean point at which a
    scheduler decides whether to preempt. Returns True iff this turn was preempted
    (snapshotted + yielded + resumed), else False.

    DEFAULT-OFF ([scheduler].preempt_enable=false): returns False IMMEDIATELY --
    the PreemptScheduler is NOT consulted, so the turn runs byte-identically.

    ENABLED: consults the turn-boundary PreemptScheduler via the pure decide()
    primitive (at a boundary the prior slice is spent, so quantum_expired=True ->
    preempt iff a higher-priority turn waits AND a snapshot slot is free, else run
    to completion -- bounded suspension). On PREEMPT it SNAPSHOTS this turn into a
    slot, cooperatively YIELDS the event loop (bounded by max_preempt_depth ticks
    AND the quantum, so a turn is never starved or busy-waited), then RESUMES by
    discharging ITS OWN snapshot -- the snapshot/resume round-trip per the
    PreemptScheduler API. The richer cross-turn blocking policy that later
    schedulers (T-020/T-058) layer on this seam is operator-live-validated.

    DEGRADE-OPEN: ANY scheduler error -> returns False and the turn proceeds
    normally; a best-effort discharge prevents a leaked snapshot. Preemption NEVER
    drops or corrupts a turn."""
    if not PREEMPT_ENABLE or _TURN_SCHEDULER is None:
        return False
    sched = _TURN_SCHEDULER
    try:
        if decide(finished=False, quantum_expired=True,
                  higher_priority_waiting=_higher_priority_waiting(
                      priority, task_id=str(task_id)),
                  can_suspend=sched.can_admit()) != PREEMPT:
            return False
        slot = sched.acquire_slot()
        if slot is None:                       # lost the slot race -> don't preempt
            return False
        if not sched.suspend(Snapshot(str(task_id), float(priority), position=0,
                                      partial="", slot=slot)):
            sched.release_slot(slot)           # already suspended -> release + bail
            return False
        t0 = now if now is not None else _CLOCK()
        q = Quantum(t0, TURN_QUANTUM_S)
        ticks = 0
        while (_higher_priority_waiting(priority, task_id=str(task_id))
               and ticks < max(1, MAX_PREEMPT_DEPTH)
               and not q.expired(_CLOCK())):
            await asyncio.sleep(0)
            ticks += 1
        sched.discharge(str(task_id))
        return True
    except Exception:  # noqa: BLE001 -- DEGRADE-OPEN: never drop/corrupt a turn
        log.debug("turn_boundary preempt consult failed; running turn normally",
                  exc_info=True)
        try:
            sched.discharge(str(task_id))      # best-effort: free any held slot
        except Exception:  # noqa: BLE001
            pass
        return False


async def slice_boundary(*, task_id: str, priority: float = 5.0,
                         tokens: int = 0, text: "Optional[str]" = None,
                         now: "Optional[float]" = None) -> bool:
    """Token-time-slice boundary hook (T-020 / SCHED-02) -- the queueing POLICY on
    top of the T-019 turn_boundary mechanism. The generation loop calls this as a
    dispatched turn produces output: it ACCOUNTS the tokens generated this step
    against the turn's SLICE BUDGET (a token-time quantum -- SLICE_TOKENS tokens, NOT
    wall-clock) and, ONLY when the budget is crossed (a slice boundary), RE-EVALUATES
    via turn_boundary -- snapshot + yield to a higher-priority waiter, or continue.
    Returns True iff the turn was preempted at this boundary.

    Token-time accounting: `tokens` is a count the caller already measured through the
    mios_tokenize seam; alternatively pass `text` and it is counted HERE through the
    SAME seam (never a re-derived chars//N).

    DEFAULT-OFF ([scheduler].queue_enable=false): returns False IMMEDIATELY -- the
    queue is NOT consulted, so the turn runs byte-identically (no interposition).

    ENABLED: accounts the tokens; a slice boundary delegates to turn_boundary (itself
    gated on preempt_enable + a higher-priority waiter -- the queue head is one such
    signal, see _higher_priority_waiting). On a real preempt the turn is REQUEUED
    (ready) so the next dispatch() re-orders it by priority.

    DEGRADE-OPEN: ANY queue/scheduler error -> returns False and the turn runs
    normally; a turn is never dropped or stalled."""
    if not QUEUE_ENABLE or _TURN_QUEUE is None:
        return False
    try:
        n = mios_tokenize.count_text(text) if text is not None else tokens
        if not _TURN_QUEUE.account(str(task_id), n):
            return False                       # still within the slice -> keep running
        preempted = await turn_boundary(task_id=str(task_id), priority=priority,
                                        now=now)
        if preempted:
            _TURN_QUEUE.requeue(str(task_id))  # back to ready -> re-dispatched by priority
        return bool(preempted)
    except Exception:  # noqa: BLE001 -- DEGRADE-OPEN: never drop/stall a turn
        log.debug("slice_boundary consult failed; running turn normally",
                  exc_info=True)
        return False


def turn_scheduler_stats() -> dict:
    """Read-only observability snapshot of the turn-boundary scheduler + the token-
    time-sliced queue: the enabled flags + resolved knobs + the PreemptScheduler
    free-list/suspended state + the TokenSliceQueue ready/running counts. For a
    future /v1/scheduler surface; never mutates."""
    try:
        st = _TURN_SCHEDULER.stats() if _TURN_SCHEDULER is not None else {}
    except Exception:  # noqa: BLE001
        st = {}
    try:
        qst = _TURN_QUEUE.stats() if _TURN_QUEUE is not None else {}
    except Exception:  # noqa: BLE001
        qst = {}
    return {"preempt_enable": bool(PREEMPT_ENABLE),
            "queue_enable": bool(QUEUE_ENABLE),
            "quantum_s": float(TURN_QUANTUM_S),
            "slice_tokens": int(SLICE_TOKENS),
            "priority_levels": int(PRIORITY_LEVELS),
            "max_preempt_depth": int(MAX_PREEMPT_DEPTH),
            "scheduler": st,
            "queue": qst}
