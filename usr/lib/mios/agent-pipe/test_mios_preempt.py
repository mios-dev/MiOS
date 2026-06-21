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


def t_discharge():
    """discharge() frees a SPECIFIC task's slot (self-resume) without disturbing
    other suspended gens -- unlike resume() which pops the global highest."""
    s = pre.PreemptScheduler(max_suspended=3)
    for tid, prio in [("a", 1.0), ("b", 9.0)]:
        s.suspend(pre.Snapshot(tid, prio, 0, "x", s.acquire_slot()))
    check("discharge: a is suspended", s.is_suspended("a") is True)
    snap = s.discharge("a")
    check("discharge: returns the specific task (a, not the higher-prio b)",
          snap is not None and snap.task_id == "a", snap and snap.task_id)
    check("discharge: a no longer suspended", s.is_suspended("a") is False)
    check("discharge: b untouched", s.is_suspended("b") is True)
    check("discharge: a's slot freed, b's held", s.stats()["free_slots"] == 2)
    check("discharge: unknown task -> None", s.discharge("zzz") is None)


def t_decide():
    d = pre.decide
    # finished always wins, regardless of waiters/quantum/slots.
    check("decide: finished -> COMPLETE",
          d(finished=True, quantum_expired=True, higher_priority_waiting=True,
            can_suspend=True) == pre.COMPLETE)
    check("decide: finished -> COMPLETE even when idle",
          d(finished=True, quantum_expired=False, higher_priority_waiting=False,
            can_suspend=False) == pre.COMPLETE)
    # PREEMPT requires ALL THREE: quantum spent + a waiter + a free snapshot slot.
    check("decide: quantum+waiter+slot -> PREEMPT",
          d(finished=False, quantum_expired=True, higher_priority_waiting=True,
            can_suspend=True) == pre.PREEMPT)
    check("decide: no waiter -> CONTINUE",
          d(finished=False, quantum_expired=True, higher_priority_waiting=False,
            can_suspend=True) == pre.CONTINUE)
    check("decide: quantum not spent -> CONTINUE",
          d(finished=False, quantum_expired=False, higher_priority_waiting=True,
            can_suspend=True) == pre.CONTINUE)
    check("decide: no free slot -> CONTINUE (bounded suspension)",
          d(finished=False, quantum_expired=True, higher_priority_waiting=True,
            can_suspend=False) == pre.CONTINUE)


def t_rr_simulation():
    """End-to-end RR preemption over the pure primitives: a long LOW-priority
    generation is preempted when a HIGH-priority one appears -- snapshotting its
    partial -- HIGH completes first, then LOW resumes from EXACTLY its partial
    (no token lost or reprocessed) and finishes. Proves the snapshot contract
    preserves progress and that decide()+suspend()+resume() compose."""
    sched = pre.PreemptScheduler(max_suspended=2)
    SLICE, low_total, high_total = 4, 20, 8

    # Phase 1: LOW runs slices; a HIGH-priority waiter appears at t>=2 -> preempt.
    low_out = ""
    q = pre.Quantum(t0=0.0, limit_s=1.0)
    now = 0.0
    preempted = False
    while True:
        now += 1.0
        low_out += "L" * min(SLICE, low_total - len(low_out))
        high_waiting = now >= 2.0
        action = pre.decide(finished=len(low_out) >= low_total,
                            quantum_expired=q.expired(now),
                            higher_priority_waiting=high_waiting,
                            can_suspend=sched.can_admit())
        if action == pre.PREEMPT:
            slot = sched.acquire_slot()
            sched.suspend(pre.Snapshot("low", 1.0, position=len(low_out),
                                       partial=low_out, slot=slot))
            preempted = True
            break
        if action == pre.COMPLETE:
            break
    check("rr: LOW preempted before finishing", preempted and len(low_out) < low_total,
          f"out_len={len(low_out)}")
    check("rr: snapshot captured 1 suspended gen", sched.stats()["suspended"] == 1)

    # Phase 2: HIGH runs to completion on the freed lane (nothing above it).
    high_out = ""
    qh = pre.Quantum(t0=now, limit_s=1.0)
    nowh = now
    while len(high_out) < high_total:
        nowh += 1.0
        high_out += "H" * min(SLICE, high_total - len(high_out))
        if pre.decide(finished=len(high_out) >= high_total,
                      quantum_expired=qh.expired(nowh),
                      higher_priority_waiting=False,
                      can_suspend=sched.can_admit()) == pre.COMPLETE:
            break
    check("rr: HIGH completed first", len(high_out) == high_total)

    # Phase 3: resume LOW from its snapshot; finish with NO token lost/reprocessed.
    snap = sched.resume()
    check("rr: resume returns LOW", snap.task_id == "low", snap.task_id)
    check("rr: resume starts at snapshot position", len(snap.partial) == snap.position)
    resumed = snap.partial
    while len(resumed) < low_total:
        resumed += "L" * min(SLICE, low_total - len(resumed))
    check("rr: LOW finished after resume (exact length, no dup)",
          len(resumed) == low_total, f"len={len(resumed)}")
    check("rr: LOW = partial + continuation (no reprocess)",
          resumed.startswith(snap.partial) and set(resumed) == {"L"})
    check("rr: slot freed after resume", sched.stats()["free_slots"] == 2)


def t_bounded_no_preempt():
    """No free snapshot slot -> decide() refuses to preempt, so the running gen
    finishes rather than being dropped (the bounded-suspension safety rule)."""
    sched = pre.PreemptScheduler(max_suspended=1)
    sched.suspend(pre.Snapshot("x", 5.0, 0, "p", sched.acquire_slot()))  # fill only slot
    action = pre.decide(finished=False, quantum_expired=True,
                        higher_priority_waiting=True, can_suspend=sched.can_admit())
    check("bounded: full slots -> CONTINUE (don't drop the gen)",
          action == pre.CONTINUE)


def main():
    t_quantum()
    t_slots()
    t_suspend_resume()
    t_fifo_tiebreak()
    t_stats()
    t_discharge()
    t_decide()
    t_rr_simulation()
    t_bounded_no_preempt()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
