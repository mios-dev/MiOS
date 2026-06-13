# AI-hint: Standalone unit test for mios_sched.PriorityGate to verify concurrency logic, permit capping, and priority-based reordering without requiring the full agent-pipe runtime.
# AI-related: mios_sched
# AI-functions: _check, t_basic_bound, third, t_priority_reorder, worker, t_fifo_tiebreak, t_anti_starvation, t_cancel_while_queued, t_cancel_after_grant, t_cap_never_exceeded, main
"""Standalone unit test for mios_sched.PriorityGate (WS-1).

Pure stdlib + the sibling module only -- no server.py import, so it runs on any
Python 3.10+ without the agent-pipe runtime deps (httpx/fastapi/...). Mirrors the
_execute_dag_saturated standalone-test pattern: a mock-free asyncio harness with
explicit asserts and a PASS/FAIL summary; exit code != 0 on any failure.

Run:  python test_mios_sched.py
"""

import asyncio
import sys

from mios_sched import PriorityGate

_RESULTS: list = []


def _check(name: str, ok: bool, detail: str = "") -> None:
    _RESULTS.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


async def t_basic_bound() -> None:
    """cap permits issue immediately; the (cap+1)th blocks until a release."""
    g = PriorityGate(2)
    await g.acquire(5)
    await g.acquire(5)
    _check("basic: cap reached", g.available == 0 and g.in_flight == 2,
           f"avail={g.available} in_flight={g.in_flight}")
    got = []

    async def third():
        await g.acquire(5)
        got.append(1)
        g.release()

    t = asyncio.create_task(third())
    await asyncio.sleep(0.03)
    _check("basic: 3rd blocks", got == [] and g.queued == 1, f"queued={g.queued}")
    g.release()                       # frees one -> hands to the waiter
    await asyncio.gather(t)
    _check("basic: 3rd ran after release", got == [1])
    g.release()
    _check("basic: drained to full", g.available == g.cap, f"avail={g.available}")


async def t_priority_reorder() -> None:
    """A later HIGH-priority waiter is served before an earlier LOW one."""
    g = PriorityGate(1)
    await g.acquire(5)                # hold the only permit
    order = []

    async def worker(p, label):
        await g.acquire(p)
        order.append(label)
        g.release()

    t_low = asyncio.create_task(worker(2, "low"))
    await asyncio.sleep(0.01)         # low enqueues first
    t_high = asyncio.create_task(worker(8, "high"))
    await asyncio.sleep(0.01)         # high enqueues second
    _check("priority: both queued", g.queued == 2, f"queued={g.queued}")
    g.release()                       # next slot must go to HIGH despite arriving later
    await asyncio.gather(t_low, t_high)
    _check("priority: high before low", order == ["high", "low"], f"order={order}")


async def t_fifo_tiebreak() -> None:
    """Equal priority -> earliest arrival wins."""
    g = PriorityGate(1)
    await g.acquire(5)
    order = []

    async def worker(label):
        await g.acquire(5)
        order.append(label)
        g.release()

    a = asyncio.create_task(worker("a"))
    await asyncio.sleep(0.01)
    b = asyncio.create_task(worker("b"))
    await asyncio.sleep(0.01)
    g.release()
    await asyncio.gather(a, b)
    _check("fifo tie-break: a before b", order == ["a", "b"], f"order={order}")


async def t_anti_starvation() -> None:
    """An aged low-priority waiter is served ahead of a fresh high-priority one."""
    g = PriorityGate(1, starvation_s=0.1)
    await g.acquire(5)
    order = []

    async def worker(p, label):
        await g.acquire(p)
        order.append(label)
        g.release()

    t_low = asyncio.create_task(worker(2, "low"))
    await asyncio.sleep(0.15)         # low ages past the 0.1s starvation threshold
    t_high = asyncio.create_task(worker(9, "high"))
    await asyncio.sleep(0.01)         # high is fresh
    g.release()                       # aging must serve LOW first despite lower prio
    await asyncio.gather(t_low, t_high)
    _check("anti-starvation: aged low first", order == ["low", "high"],
           f"order={order}")


async def t_cancel_while_queued() -> None:
    """Cancelling a still-queued waiter (case a) leaks no permit."""
    g = PriorityGate(1)
    await g.acquire(5)

    async def worker():
        await g.acquire(5)

    t = asyncio.create_task(worker())
    await asyncio.sleep(0.02)
    _check("cancel-queued: enqueued", g.queued == 1, f"queued={g.queued}")
    t.cancel()
    try:
        await t
    except asyncio.CancelledError:
        pass
    await asyncio.sleep(0.01)
    _check("cancel-queued: dequeued", g.queued == 0, f"queued={g.queued}")
    g.release()
    _check("cancel-queued: no leak", g.available == 1, f"avail={g.available}")


async def t_cancel_after_grant() -> None:
    """Cancelling a just-granted waiter (case b) hands the permit back."""
    g = PriorityGate(1)
    await g.acquire(5)

    async def worker():
        await g.acquire(5)
        g.release()

    t = asyncio.create_task(worker())
    await asyncio.sleep(0.02)
    # release() (synchronous) grants the permit to t; cancel BEFORE t resumes ->
    # the awaiting task raises CancelledError even though its future is done.
    g.release()
    t.cancel()
    try:
        await t
    except asyncio.CancelledError:
        pass
    await asyncio.sleep(0.01)
    _check("cancel-granted: no leak",
           g.queued == 0 and g.available == 1,
           f"queued={g.queued} avail={g.available}")


async def t_cap_never_exceeded() -> None:
    """Under heavy mixed-priority load the cap is never exceeded."""
    cap = 3
    g = PriorityGate(cap, starvation_s=0.02)
    cur = 0
    peak = 0
    done = 0

    async def worker(p):
        nonlocal cur, peak, done
        await g.acquire(p)
        cur += 1
        peak = max(peak, cur)
        await asyncio.sleep(0.005)
        cur -= 1
        done += 1
        g.release()

    tasks = [asyncio.create_task(worker(float((i % 9) + 1))) for i in range(40)]
    await asyncio.gather(*tasks)
    _check("load: peak <= cap", peak <= cap, f"peak={peak} cap={cap}")
    _check("load: all completed", done == 40, f"done={done}")
    _check("load: drained to full", g.available == cap, f"avail={g.available}")


async def main() -> int:
    for t in (t_basic_bound, t_priority_reorder, t_fifo_tiebreak,
              t_anti_starvation, t_cancel_while_queued, t_cancel_after_grant,
              t_cap_never_exceeded):
        await t()
    passed = sum(1 for _, ok, _ in _RESULTS if ok)
    total = len(_RESULTS)
    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
