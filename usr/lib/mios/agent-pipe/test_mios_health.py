# AI-hint: Unit test suite for mios_pipe.health module.
# AI-related: mios_pipe/health.py
"""Unit tests for mios_pipe.health."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from mios_pipe.health import build_health_response, get_system_version


class TestHealth(unittest.TestCase):
    """Test health response builder."""

    def test_build_health_response_defaults(self):
        resp = build_health_response()
        self.assertEqual(resp["status"], "ok")
        self.assertIsNotNone(resp["version"])
        self.assertIsNotNone(resp["backend"])
        self.assertIsInstance(resp["port"], int)

    def test_build_health_response_overrides(self):
        resp = build_health_response(status="healthy", version="0.3.0", backend="http://localhost:8642", port=8640)
        self.assertEqual(resp["status"], "healthy")
        self.assertEqual(resp["version"], "0.3.0")
        self.assertEqual(resp["backend"], "http://localhost:8642")
        self.assertEqual(resp["port"], 8640)

    def test_get_system_version(self):
        v = get_system_version()
        self.assertIsInstance(v, str)


if __name__ == "__main__":
    unittest.main()
