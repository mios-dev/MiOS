#!/usr/bin/env python3
# AI-hint: Standalone unit test for mios_tool_batch sibling module.
# AI-doc: usr/share/doc/mios/manual/agent-pipe.md
"""Unit tests for mios_tool_batch."""

import asyncio
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from mios_tool_batch import ToolBatcher

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def main():
    batcher = ToolBatcher()
    calls = [
        {"name": "view_file", "args": {"path": "/etc/mios/mios.toml"}},
        {"name": "write_to_file", "args": {"path": "/tmp/test"}},
        {"name": "grep_search", "args": {"query": "test"}}
    ]
    p_calls, s_calls = batcher.partition_tool_calls(calls)
    check("parallel batch has 2 items", len(p_calls) == 2)
    check("sequential batch has 1 item", len(s_calls) == 1)

    if _fails > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
