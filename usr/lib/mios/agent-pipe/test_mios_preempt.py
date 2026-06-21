#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_preempt (WS-A12 RR-preemption state machine + snapshot contract). Pure stdlib, no server.py/engine/pytest. Verifies Quantum expiry/remaining (incl. limit<=0 = unlimited), the bounded snapshot-slot free-list (acquire to exhaustion, release returns, idempotent), suspend/resume with PRIORITY-ordered resume + FIFO tie-break, the admission cap, and stats.
# AI-related: ./mios_preempt.py
# AI-functions: check, main
"""Unit tests for mios_preempt (WS-A12)."""

import sys

import mios_preempt as pre

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_quantum():
    q = pre.Quantum(t0=100.0, limit_s=5.0)
    check("quantum: not expired before limit", q.expired(104.0) is False)
    check("quantum: expired at limit", q.expired(105.0) is True)
    check("quantum: expired after limit", q.expired(110.0) is True)
    check("quantum: remaining decreases", q.remaining(102.0) == 3.0, f"{q.remaining(102.0)}")
    check("quantum: remaining floors at 0", q.remaining(200.0) == 0.0)
    qinf = pre.Quantum(0.0, 0.0)
    check("quantum: limit<=0 never expires", qinf.expired(1e9) is False)
    check("quantum: limit<=0 remaining inf", qinf.remaining(1e9) == float("inf"))


def t_slots():
    s = pre.PreemptScheduler(max_suspended=2)
    check("slots: can_admit initially", s.can_admit() is True)
    a = s.acquire_slot(); b = s.acquire_slot()
    check("slots: two distinct ids", {a, b} == {0, 1}, f"{a},{b}")
    check("slots: exhausted -> can_admit False", s.can_admit() is False)
    check("slots: acquire when empty -> None", s.acquire_slot() is None)
    s.release_slot(a)
    check("slots: release frees a slot", s.can_admit() is True)
    s.release_slot(a)  # idempotent
    check("slots: double-release idempotent", s.acquire_slot() == a and s.acquire_slot() is None)


def t_suspend_resume():
    s = pre.PreemptScheduler(max_suspended=3)
    # suspend three tasks at different priorities into acquired slots.
    for tid, prio in [("low", 1.0), ("high", 9.0), ("mid", 5.0)]:
        slot = s.acquire_slot()
        ok = s.suspend(pre.Snapshot(tid, prio, position=0, partial="x", slot=slot))
        check(f"suspend: {tid} recorded", ok is True)
    check("suspend: duplicate rejected",
          s.suspend(pre.Snapshot("high", 9.0, 0, "y", 0)) is False)
    r1 = s.resume()
    check("resume: highest priority first (high)", r1.task_id == "high", r1.task_id)
    r2 = s.resume()
    check("resume: next highest (mid)", r2.task_id == "mid", r2.task_id)
    r3 = s.resume()
    check("resume: lowest last (low)", r3.task_id == "low")
    check("resume: empty -> None", s.resume() is None)
    check("resume: slots all freed", s.can_admit() is True and s.stats()["free_slots"] == 3)


def t_fifo_tiebreak():
    s = pre.PreemptScheduler(max_suspended=3)
    for tid in ["a", "b", "c"]:
        s.suspend(pre.Snapshot(tid, 5.0, 0, "x", s.acquire_slot()))  # equal priority
    check("tiebreak: equal priority resumes FIFO (a first)", s.resume().task_id == "a")


def t_stats():
    s = pre.PreemptScheduler(max_suspended=4)
    s.suspend(pre.Snapshot("t1", 5.0, 0, "x", s.acquire_slot()))
    st = s.stats()
    check("stats: shape", st["max_suspended"] == 4 and st["suspended"] == 1
          and st["free_slots"] == 3 and st["queued_ids"] == ["t1"], f"{st}")


def main():
    t_quantum()
    t_slots()
    t_suspend_resume()
    t_fifo_tiebreak()
    t_stats()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
