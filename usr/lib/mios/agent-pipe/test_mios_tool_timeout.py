#!/usr/bin/env python3
# AI-hint: Standalone unit test for mios_tool_timeout sibling module.
# AI-doc: usr/share/doc/mios/manual/agent-pipe.md
"""Unit tests for mios_tool_timeout."""

import asyncio
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from mios_tool_timeout import ToolWatchdog

_fails = 0

def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))

def main():
    dog = ToolWatchdog(default_timeout_s=1.0)

    async def fast_task():
        return "fast_result"

    async def slow_task():
        await asyncio.sleep(2.0)
        return "slow_result"

    success, res, latency = asyncio.run(dog.execute_with_watchdog(fast_task))
    check("fast task succeeded", success and res == "fast_result")

    success2, err, latency2 = asyncio.run(dog.execute_with_watchdog(slow_task, timeout_s=0.1))
    check("slow task timed out", not success2 and "timed out" in err)

    if _fails > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
