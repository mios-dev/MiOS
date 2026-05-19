#!/usr/bin/env python3
"""Smoke-test _substitute_ek_refs.

Verifies the ReWOO #E<id> placeholder substitution across the
shapes a planner might emit:
  * simple string substitution
  * multiple refs in one arg
  * refs to non-existent ids (preserved literal so dispatch errors)
  * non-string args (passed through)
"""
from __future__ import annotations
import sys

sys.path.insert(0, "/usr/lib/mios/agent-pipe")
import server


def main() -> int:
    results = {
        "n1": {"output": "Kingdom Come: Deliverance II", "success": True},
        "n2": {"output": "Steam", "success": True},
        "n3": {"output": "long output that exceeds the per-ref cap " * 50,
               "success": True},
    }

    cases = [
        ("simple string substitution",
         {"name": "#En1"},
         {"name": "Kingdom Come: Deliverance II"}),
        ("two refs in one arg",
         {"query": "launch #En1 via #En2"},
         {"query": "launch Kingdom Come: Deliverance II via Steam"}),
        ("missing ref preserved literal",
         {"name": "#Eghost"},
         {"name": "#Eghost"}),
        ("non-string arg passes through",
         {"count": 5, "alive": True, "tags": ["a", "b"]},
         {"count": 5, "alive": True, "tags": ["a", "b"]}),
        ("empty args",
         {},
         {}),
    ]
    fails = 0
    for label, inp, expected in cases:
        got = server._substitute_ek_refs(inp, results)
        if got != expected:
            print(f"  FAIL  {label}")
            print(f"        input:    {inp}")
            print(f"        expected: {expected}")
            print(f"        got:      {got}")
            fails += 1
        else:
            print(f"  PASS  {label}")

    # Output-cap check: an upstream node dumping 50 * 41 = 2050 chars
    # gets capped at 1024 in the substituted arg.
    got = server._substitute_ek_refs({"x": "#En3"}, results)
    if len(got["x"]) != 1024:
        print(f"  FAIL  output-cap: got len={len(got['x'])}, expected 1024")
        fails += 1
    else:
        print("  PASS  output-cap (1024 chars)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
