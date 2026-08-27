#!/usr/bin/env python3
# AI-hint: Standalone unit test for mios_drain_handler sibling module.
# AI-doc: usr/share/doc/mios/manual/agent-pipe.md
"""Unit tests for mios_drain_handler."""

import asyncio
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from mios_drain_handler import GracefulDrainManager

_fails = 0

def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))

def main():
    drain = GracefulDrainManager(drain_timeout_s=1.0)
    check("acquire slot", drain.acquire_slot())
    check("active count is 1", drain.active_requests == 1)

    drain.start_drain()
    check("reject new admission during drain", not drain.acquire_slot())
    drain.release_slot()
    check("active count is 0", drain.active_requests == 0)

    if _fails > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
