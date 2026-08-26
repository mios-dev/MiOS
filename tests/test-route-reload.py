#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-AI model route table hot-reload.
# AI-related: usr/lib/mios/agent-pipe/mios_route_reload.py
"""Automated tests for WS-AI thread-safe route table hot-reloading and versioning."""

from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "usr", "lib", "mios", "agent-pipe"))

from mios_route_reload import RouteTableManager


class TestRouteReload(unittest.TestCase):
    """Validates atomic route replacement, model lookup, and version bumps."""

    def test_hot_reload_lifecycle(self):
        manager = RouteTableManager({"granite": {"port": 11450}})
        self.assertEqual(manager.version, 1)
        self.assertEqual(manager.get_route("granite")["port"], 11450)

        # Reload with new route map
        new_v = manager.reload_routes({"granite": {"port": 11450}, "lfm2": {"port": 11451}})
        self.assertEqual(new_v, 2)
        self.assertIn("lfm2", manager.list_models())
        self.assertEqual(manager.get_route("lfm2")["port"], 11451)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRouteReload)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
