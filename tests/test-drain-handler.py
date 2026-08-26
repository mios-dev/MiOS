#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-AI graceful worker shutdown and drain handler.
# AI-related: usr/lib/mios/agent-pipe/mios_drain_handler.py
"""Automated tests for WS-AI worker drain mode, admission rejection, and safe termination."""

from __future__ import annotations

import asyncio
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "usr", "lib", "mios", "agent-pipe"))

from mios_drain_handler import GracefulDrainManager


class TestDrainHandler(unittest.TestCase):
    """Validates graceful drain transitions and active request draining."""

    def test_drain_admission_rejection(self):
        drain = GracefulDrainManager(drain_timeout_s=1.0)
        self.assertTrue(drain.acquire_slot())
        self.assertEqual(drain.active_requests, 1)

        drain.start_drain()
        # New admission rejected during drain
        self.assertFalse(drain.acquire_slot())

        drain.release_slot()
        self.assertEqual(drain.active_requests, 0)

    def test_wait_for_drain_success(self):
        drain = GracefulDrainManager(drain_timeout_s=2.0)
        drain.acquire_slot()
        drain.start_drain()

        async def finish_request():
            await asyncio.sleep(0.1)
            drain.release_slot()

        async def run_test():
            asyncio.create_task(finish_request())
            return await drain.wait_for_drain()

        success = asyncio.run(run_test())
        self.assertTrue(success)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDrainHandler)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
