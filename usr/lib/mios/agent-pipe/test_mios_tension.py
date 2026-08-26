#!/usr/bin/env python3
# AI-hint: Standalone unit test for mios_tension sibling module.
# AI-doc: usr/share/doc/mios/manual/agent-pipe.md
"""Unit tests for mios_tension."""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from mios_tension import TensionLedger

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def main():
    ledger = TensionLedger()
    tid = ledger.record_objection("challenger_1", "claim_10", "high", "Memory boundary violation")
    check("tension recorded", tid == 0)
    check("has unresolvable tensions", not ledger.is_consensus_ready())

    ledger.resolve_tension(tid, resolution="Fixed buffer allocation")
    check("consensus ready after resolution", ledger.is_consensus_ready())

    if _fails > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
