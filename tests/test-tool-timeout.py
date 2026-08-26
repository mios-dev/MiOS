#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-AI tool-call latency profiling and dead-lock timeouts.
# AI-related: usr/lib/mios/agent-pipe/mios_tool_timeout.py, tests/test-tool-timeout.py
"""Automated tests for WS-AI tool execution watchdog deadlines and latency measurements."""

from __future__ import annotations

import asyncio
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "usr", "lib", "mios", "agent-pipe"))

from mios_tool_timeout import ToolWatchdog


class TestToolTimeout(unittest.TestCase):
    """Validates watchdog deadline enforcement and latency metrics."""

    def test_successful_tool_execution(self):
        async def fast_tool():
            return "SUCCESS_DATA"

        wd = ToolWatchdog(default_timeout_s=2.0)
        success, res, latency = asyncio.run(wd.execute_with_watchdog(fast_tool))
        self.assertTrue(success)
        self.assertEqual(res, "SUCCESS_DATA")
        self.assertTrue(latency >= 0.0)

    def test_timeout_tool_execution(self):
        async def hanging_tool():
            await asyncio.sleep(1.0)
            return "NEVER_REACHED"

        wd = ToolWatchdog(default_timeout_s=0.1)
        success, res, latency = asyncio.run(wd.execute_with_watchdog(hanging_tool))
        self.assertFalse(success)
        self.assertIn("timed out", res)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestToolTimeout)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
