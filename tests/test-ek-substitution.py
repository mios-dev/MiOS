#!/usr/bin/env python3
# AI-hint: Smoke-test script for the `_substitute_ek_refs` function in `server` to verify ReWOO #E<id> placeholder substitution logic, including multi...
# AI-doc: usr/share/doc/mios/manual/tests.md
from __future__ import annotations
import sys

import _agentpipe_path  # noqa: F401
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

    got = server._substitute_ek_refs({"x": "#En3"}, results)
    if len(got["x"]) != 1024:
        print(f"  FAIL  output-cap: got len={len(got['x'])}, expected 1024")
        fails += 1
    else:
        print("  PASS  output-cap (1024 chars)")
    return 1 if fails else 0

if __name__ == "__main__":
    sys.exit(main())
