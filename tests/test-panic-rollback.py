#!/usr/bin/env python3
# AI-hint: Unit and integration tests for Linux pstore panic monitor and emergency bootc rollback engine.
# AI-related: usr/libexec/mios/sec/panic_rollback.py, usr/share/doc/mios/manual/sec.md
"""Unit and integration test suite for PanicRollbackHandler and CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "sec", "panic_rollback.py")

spec = importlib.util.spec_from_file_location("panic_rollback", _TARGET_PATH)
if spec and spec.loader:
    panic_rollback = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = panic_rollback
    spec.loader.exec_module(panic_rollback)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestPanicRollback(unittest.TestCase):
    """Test suite for pstore crash dump scanning, boot failure persistence, and rollback triggering."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="mios-test-panic-")
        self.state_file = os.path.join(self.temp_dir.name, "boot_fails.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_scan_pstore_mock_with_panic(self):
        handler = panic_rollback.PanicRollbackHandler(mock=True, mock_failures=1)
        panics = handler.scan_pstore()
        self.assertEqual(len(panics), 1)
        self.assertIn("kernel panic", panics[0]["reason"].lower())

    def test_record_failure_and_persistence(self):
        handler = panic_rollback.PanicRollbackHandler(mock=True)
        count1 = handler.record_failure(reason="panic_1", state_file=self.state_file)
        self.assertEqual(count1, 1)

        count2 = handler.record_failure(reason="panic_2", state_file=self.state_file)
        self.assertEqual(count2, 2)

        state = handler.read_state(self.state_file)
        self.assertEqual(state["failure_count"], 2)
        self.assertEqual(len(state["history"]), 2)

    def test_reset_counter(self):
        handler = panic_rollback.PanicRollbackHandler(mock=True)
        handler.record_failure(reason="panic_1", state_file=self.state_file)
        self.assertTrue(handler.reset_counter(state_file=self.state_file))

        state = handler.read_state(self.state_file)
        self.assertEqual(state["failure_count"], 0)

    def test_evaluate_rollback_threshold(self):
        # Under threshold (2 < 3) -> no rollback
        h_healthy = panic_rollback.PanicRollbackHandler(mock=True, mock_failures=2)
        res_healthy = h_healthy.evaluate_rollback(max_failures=3, state_file=self.state_file)
        self.assertEqual(res_healthy["status"], "healthy")
        self.assertFalse(res_healthy["rollback_executed"])

        # At/above threshold (3 >= 3) -> rollback triggered
        h_panic = panic_rollback.PanicRollbackHandler(mock=True, mock_failures=3)
        res_rollback = h_panic.evaluate_rollback(max_failures=3, state_file=self.state_file)
        self.assertEqual(res_rollback["status"], "rollback_triggered")
        self.assertEqual(res_rollback["action"], "bootc_rollback")
        self.assertTrue(res_rollback["rollback_executed"])

    def test_cli_execution_record_failure(self):
        test_args = [
            "panic_rollback.py",
            "--record-failure",
            "--state-file", self.state_file,
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = panic_rollback.main()
            self.assertEqual(exit_code, 0)

    def test_cli_execution_reset_counter(self):
        test_args = [
            "panic_rollback.py",
            "--reset-counter",
            "--state-file", self.state_file,
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = panic_rollback.main()
            self.assertEqual(exit_code, 0)

    def test_cli_execution_evaluate_rollback(self):
        test_args = [
            "panic_rollback.py",
            "--evaluate-rollback",
            "--max-failures", "3",
            "--mock",
            "--mock-failures", "3",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = panic_rollback.main()
            self.assertEqual(exit_code, 0)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPanicRollback)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
