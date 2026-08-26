#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-AI asynchronous tool execution batcher.
# AI-related: usr/lib/mios/agent-pipe/mios_tool_batch.py
"""Automated tests for WS-AI parallel tool partitioning and batch execution."""

from __future__ import annotations

import asyncio
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "usr", "lib", "mios", "agent-pipe"))

from mios_tool_batch import ToolBatcher


class TestToolBatch(unittest.TestCase):
    """Validates tool call partitioning and concurrent batch execution."""

    def test_partitioning(self):
        batcher = ToolBatcher()
        calls = [
            {"name": "view_file", "path": "test.txt"},
            {"name": "search_web", "query": "python"},
            {"name": "write_to_file", "path": "out.txt"},
        ]
        parallel, seq = batcher.partition_tool_calls(calls)
        self.assertEqual(len(parallel), 2)
        self.assertEqual(len(seq), 1)
        self.assertEqual(seq[0]["name"], "write_to_file")

    def test_batch_execution(self):
        batcher = ToolBatcher()
        executed_order = []

        async def mock_exec(call):
            executed_order.append(call["name"])
            return f"OK_{call['name']}"

        calls = [
            {"name": "view_file", "path": "a.txt"},
            {"name": "grep_search", "path": "b.txt"},
            {"name": "replace_file_content", "path": "c.txt"},
        ]

        results = asyncio.run(batcher.execute_batch(calls, mock_exec))
        self.assertEqual(len(results), 3)
        self.assertIn("OK_view_file", results)
        self.assertIn("OK_replace_file_content", results)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestToolBatch)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
