#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_ctxpack (WS-A5 priority token-budget packer). Pure stdlib, no server.py/DB/pytest. Verifies pack() keeps the highest-priority items that fit the budget, drops the rest, never exceeds the budget, preserves ORIGINAL order in the kept set, skips an over-budget item to admit a smaller lower-priority one, and honours reserve + custom text_of/priority_of accessors.
# AI-related: ./mios_ctxpack.py, ./mios_tokenize.py
# AI-functions: check, main
"""Unit tests for mios_ctxpack (WS-A5)."""

import sys

import mios_ctxpack as cp

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def item(text, pri):
    return {"text": text, "priority": pri}


def t_basic():
    # Each "xxxx" (4 chars) == 1 token under the heuristic.
    items = [item("a" * 40, 1), item("b" * 40, 9), item("c" * 40, 5)]  # 10 tokens each
    r = cp.pack(items, budget=20)
    check("pack: keeps 2 of 3 within budget", len(r.kept) == 2, f"{r.to_dict()}")
    check("pack: never exceeds budget", r.used_tokens <= 20)
    kept_pri = [k["priority"] for k in r.kept]
    check("pack: kept the two HIGHEST priorities (9,5)", set(kept_pri) == {9, 5}, f"{kept_pri}")
    check("pack: kept in ORIGINAL order", kept_pri == [9, 5], f"{kept_pri}")
    check("pack: dropped the lowest (1)", r.dropped[0]["priority"] == 1)


def t_all_fit():
    items = [item("a" * 8, 1), item("b" * 8, 2)]  # 2 tokens each
    r = cp.pack(items, budget=100)
    check("pack: all fit -> none dropped", not r.dropped and len(r.kept) == 2)


def t_skip_oversize():
    # A huge high-priority item that can't fit must be SKIPPED so smaller
    # lower-priority items still get admitted (not a hard stop).
    items = [item("z" * 4000, 10), item("a" * 8, 1), item("b" * 8, 2)]  # 1000, 2, 2 tokens
    r = cp.pack(items, budget=10)
    check("pack: oversize top-priority skipped", all(len(k["text"]) < 100 for k in r.kept), f"{r.to_dict()}")
    check("pack: smaller items still admitted", len(r.kept) == 2)


def t_reserve():
    items = [item("a" * 40, 1)]  # 10 tokens
    r = cp.pack(items, budget=12, reserve=5)  # avail = 7 < 10 -> dropped
    check("pack: reserve shrinks budget", len(r.kept) == 0 and r.budget == 7, f"{r.to_dict()}")


def t_accessors():
    items = [("low", 1), ("high", 9)]
    r = cp.pack(items, budget=100, text_of=lambda t: t[0], priority_of=lambda t: t[1])
    check("pack: custom accessors work", len(r.kept) == 2)
    check("pack: tuple items kept in order", r.kept == [("low", 1), ("high", 9)])


def t_empty():
    r = cp.pack([], budget=50)
    check("pack: empty -> empty result", r.kept == [] and r.dropped == [] and r.used_tokens == 0)


def main():
    t_basic()
    t_all_fit()
    t_skip_oversize()
    t_reserve()
    t_accessors()
    t_empty()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
