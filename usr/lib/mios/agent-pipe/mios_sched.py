# AI-hint: Provides PriorityGate primitives for the WS-1 agent-pipe to enforce priority-based reordering and anti-starvation logic on concurrent tasks, ensuring high-priority agent dispatches jump ahead of lower-priority ones.
# AI-functions: __init__, cap, available, in_flight, queued, head_priority, stats, _pick, acquire, _release, release, class PriorityGate
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
import time
from typing import Optional


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
