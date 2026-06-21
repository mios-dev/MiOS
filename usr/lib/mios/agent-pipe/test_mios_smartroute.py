#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_smartroute (WS-A16 cost/quality SmartRouting). Pure stdlib, no server.py/network/pytest. Verifies the researched local-first cascade: order_lanes puts ALL local lanes first (cheapest/strongest) then remotes by cost; choose_next prefers an untried local lane, returns a paid remote ONLY on escalate=True AND within the CostLedger budget; should_escalate fires on quality-fail OR local-exhausted; the ledger gates escalation when the budget is spent.
# AI-related: ./mios_smartroute.py
# AI-functions: check, main
"""Unit tests for mios_smartroute (WS-A16)."""

import sys

import mios_smartroute as sr

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def lanes():
    return [
        sr.Lane("local-light", "local", 0.0, 1),
        sr.Lane("local-heavy", "local", 0.0, 3),
        sr.Lane("remote-cheap", "remote", 0.5, 4),
        sr.Lane("remote-strong", "remote", 5.0, 9),
    ]


def t_order():
    o = [x.id for x in sr.order_lanes(lanes())]
    check("order: all local before any remote", o.index("local-heavy") < o.index("remote-cheap"), o)
    check("order: remotes by ascending cost", o.index("remote-cheap") < o.index("remote-strong"), o)
    # equal-cost locals -> stronger first.
    check("order: equal-cost local -> stronger first", o[0] == "local-heavy", o)


def t_local_first():
    nxt = sr.choose_next(lanes(), attempted=[], escalate=False)
    check("local-first: picks a local lane first", nxt.is_local is True)
    # second pick (first attempted) -> the other local, still no escalation.
    nxt2 = sr.choose_next(lanes(), attempted=["local-heavy"], escalate=False)
    check("local-first: second pick still local", nxt2.id == "local-light")
    # both locals attempted, no escalation -> nothing (don't spend without escalation).
    none = sr.choose_next(lanes(), attempted=["local-heavy", "local-light"], escalate=False)
    check("local-first: no escalation -> no paid lane", none is None)


def t_escalation():
    # locals exhausted + escalate -> the CHEAPEST remote.
    nxt = sr.choose_next(lanes(), attempted=["local-heavy", "local-light"], escalate=True)
    check("escalate: -> cheapest remote", nxt.id == "remote-cheap", nxt.id if nxt else None)
    # remote-cheap also attempted -> the stronger remote.
    nxt2 = sr.choose_next(lanes(), attempted=["local-heavy", "local-light", "remote-cheap"], escalate=True)
    check("escalate: next -> stronger remote", nxt2.id == "remote-strong")


def t_budget_gate():
    led = sr.CostLedger(budget=1.0, spent=0.0)
    # remote-cheap (0.5) affordable; remote-strong (5.0) not.
    nxt = sr.choose_next(lanes(), attempted=["local-heavy", "local-light"], ledger=led, escalate=True)
    check("budget: affordable remote chosen", nxt.id == "remote-cheap")
    led.charge(0.9)  # now 0.9 spent, 0.1 remaining
    nxt2 = sr.choose_next(lanes(), attempted=["local-heavy", "local-light", "remote-cheap"], ledger=led, escalate=True)
    check("budget: unaffordable remote skipped -> None", nxt2 is None, nxt2.id if nxt2 else None)
    check("ledger: remaining", round(led.remaining(), 2) == 0.1)
    check("ledger: unlimited (budget 0) affords anything", sr.CostLedger(0.0).can_afford(1e9) is True)


def t_should_escalate():
    check("escalate: quality fail -> True", sr.should_escalate(False, False) is True)
    check("escalate: local exhausted -> True", sr.should_escalate(True, True) is True)
    check("escalate: quality ok + locals left -> False", sr.should_escalate(True, False) is False)


def main():
    t_order()
    t_local_first()
    t_escalation()
    t_budget_gate()
    t_should_escalate()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
