#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_hopbudget (WS-4 hop-budget guard + effort scaling). Pure stdlib, no server.py/DB/pytest. Verifies the recursion bound (depth_exhausted incl. disabled when max<=0), the Via-chain ops (append_via, is_loop case-insensitive self-detect), seed_depth parse/clamp/default (so the bound crosses an HTTP hop), and effort_width named-tier + float-score mapping clamped to [1,cap].
# AI-related: ./mios_hopbudget.py
# AI-functions: check, main
"""Unit tests for mios_hopbudget (WS-4)."""

import sys

import mios_hopbudget as hb

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_depth():
    check("depth: below bound -> ok", hb.depth_exhausted(2, 4) is False)
    check("depth: at bound -> exhausted", hb.depth_exhausted(4, 4) is True)
    check("depth: above bound -> exhausted", hb.depth_exhausted(5, 4) is True)
    check("depth: max<=0 disables bound", hb.depth_exhausted(99, 0) is False)
    check("depth: bad input -> not exhausted", hb.depth_exhausted("x", 4) is False)


def t_via():
    check("via: append to empty", hb.append_via("", "a") == "a")
    check("via: append to chain", hb.append_via("a,b", "c") == "a,b,c")
    check("via: skip empty self", hb.append_via("a", "") == "a")
    check("loop: self in chain (case-insensitive)", hb.is_loop("A,b,C", "c") is True)
    check("loop: self not in chain", hb.is_loop("a,b", "z") is False)
    check("loop: empty chain", hb.is_loop("", "a") is False)
    check("loop: empty self -> no loop", hb.is_loop("a,b", "") is False)


def t_seed():
    check("seed: parses header", hb.seed_depth("3") == 3)
    check("seed: clamps negative to 0", hb.seed_depth("-2") == 0)
    check("seed: None -> default", hb.seed_depth(None, default=0) == 0)
    check("seed: garbage -> default", hb.seed_depth("abc", default=1) == 1)


def t_effort():
    check("effort: low -> 1", hb.effort_width("low", base=2, cap=6) == 1)
    check("effort: medium -> base", hb.effort_width("medium", base=2, cap=6) == 2)
    check("effort: high -> cap-1", hb.effort_width("high", base=2, cap=6) == 5)
    check("effort: max -> cap", hb.effort_width("max", base=2, cap=6) == 6)
    check("effort: unknown -> base", hb.effort_width("weird", base=3, cap=6) == 3)
    check("effort: float score 0.0 -> 1", hb.effort_width("0.0", cap=6) == 1)
    check("effort: float score 1.0 -> cap", hb.effort_width("1.0", cap=6) == 6)
    check("effort: float score 0.5 -> mid", hb.effort_width("0.5", cap=6) in (3, 4), f"{hb.effort_width('0.5', cap=6)}")
    check("effort: clamps to >=1", hb.effort_width("low", base=1, cap=1) == 1)


def main():
    t_depth()
    t_via()
    t_seed()
    t_effort()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
