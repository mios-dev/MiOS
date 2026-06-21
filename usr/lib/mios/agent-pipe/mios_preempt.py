# AI-hint: WS-A12 round-robin preemption state machine + generation-snapshot contract. Pure-stdlib core that decides WHEN a running dispatch has used its time-slice (Quantum), holds the snapshot of a preempted generation (Snapshot: partial output + position + priority + slot), and manages a BOUNDED free-list of snapshot slots + a suspended queue with priority-ordered resume (PreemptScheduler). This is the policy/bookkeeping half of RR time-slicing; server.py owns the actual interruptible decode loop + restoring a snapshot into the engine (VM/engine-deep). Pure so it unit-tests in isolation, in the mios_sched / mios_pdp sibling style.
# AI-related: ./mios_sched.py, ./server.py, /usr/share/mios/mios.toml, ./test_mios_preempt.py
# AI-functions: expired, remaining, acquire_slot, release_slot, suspend, resume, can_admit, stats, class Quantum, class Snapshot, class PreemptScheduler
"""mios_preempt -- round-robin preemption policy + snapshot contract (WS-A12, the
AIOS scheduler time-slice layer).

Pure stdlib (time passed in -> deterministic). Strict-priority scheduling can let
a long high-priority generation hog the lane; RR time-slicing preempts it after a
QUANTUM, snapshots its partial state, requeues it, and lets the next waiter run.
This module owns the BOOKKEEPING: quantum expiry, a bounded free-list of snapshot
slots (so suspensions can't grow unbounded), and a priority-ordered suspended
queue. server.py owns the engine-side interruptible decode + snapshot
restore/save (which needs llama.cpp/SGLang support); this is the testable policy.
"""

from __future__ import annotations

import collections
from typing import Dict, List, Optional


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

    def stats(self) -> dict:
        return {
            "max_suspended": self._cap,
            "suspended": len(self._suspended),
            "free_slots": len(self._free),
            "queued_ids": list(self._suspended.keys()),
        }
