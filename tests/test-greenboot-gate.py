#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Greenboot post-bake health gate, automated rollback, and quarantine.
# AI-related: usr/libexec/mios/sec/greenboot_gate.py, usr/share/mios/mios.toml
"""Unit and integration test suite for GreenbootGateEngine and greenboot_gate CLI."""

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
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "sec", "greenboot_gate.py")

spec = importlib.util.spec_from_file_location("greenboot_gate", _TARGET_PATH)
if spec and spec.loader:
    greenboot_gate = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = greenboot_gate
    spec.loader.exec_module(greenboot_gate)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestGreenbootGate(unittest.TestCase):
    """Test suite for Greenboot post-bake health verification, rollback triggering, and quarantine recording."""

    def test_load_history_mock(self):
        engine = greenboot_gate.GreenbootGateEngine(mock=True)
        history = engine.load_history()
        self.assertEqual(history["total_bakes"], 1)
        self.assertIsNotNone(history["latest_bake"])

    def test_detect_pending_bake_mock(self):
        engine = greenboot_gate.GreenbootGateEngine(mock=True)
        pending = engine.detect_pending_bake()
        self.assertIsNotNone(pending)
        self.assertEqual(pending["bake_id"], "mock-bake-01")

    def test_check_service_health_success_mock(self):
        engine = greenboot_gate.GreenbootGateEngine(mock=True, mock_failure=False)
        report = engine.check_service_health()
        self.assertTrue(report["healthy"])
        self.assertEqual(len(report["failing_services"]), 0)
        self.assertTrue(report["endpoint_healthy"])

    def test_check_service_health_failure_mock(self):
        engine = greenboot_gate.GreenbootGateEngine(mock=True, mock_failure=True)
        report = engine.check_service_health()
        self.assertFalse(report["healthy"])
        self.assertIn("agent-pipe.service", report["failing_services"])
        self.assertFalse(report["endpoint_healthy"])

    def test_execute_rollback_mock(self):
        engine = greenboot_gate.GreenbootGateEngine(mock=True)
        res = engine.execute_rollback()
        self.assertEqual(res["status"], "rollback_executed")
        self.assertIn("bootc rollback", res["command"])

    def test_quarantine_diffs_recording(self):
        with tempfile.TemporaryDirectory(prefix="mios-greenboot-quarantine-") as tmpdir:
            quarantine_file = os.path.join(tmpdir, "quarantine.json")
            engine = greenboot_gate.GreenbootGateEngine(quarantine_path=quarantine_file, mock=True)
            bake_record = {
                "bake_id": "test-fail-bake",
                "commit_sha": "bad123",
                "image_tag": "localhost/mios:bad123",
                "staged_files": ["etc/pam.d/system-auth"],
            }
            entry = engine.quarantine_diffs(
                bake_record,
                reason="PAM segmentation fault",
                failing_services=["systemd-logind.service"],
            )
            self.assertEqual(entry["bake_id"], "test-fail-bake")
            self.assertTrue(os.path.isfile(quarantine_file))
            with open(quarantine_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["total_quarantined"], 1)

    def test_verify_gate_healthy_pass(self):
        with tempfile.TemporaryDirectory(prefix="mios-greenboot-pass-") as tmpdir:
            hist_file = os.path.join(tmpdir, "history.json")
            engine = greenboot_gate.GreenbootGateEngine(
                history_path=hist_file,
                mock=True,
                mock_failure=False,
            )
            res = engine.verify_gate()
            self.assertEqual(res["status"], "pass")
            self.assertTrue(res["health"]["healthy"])

    def test_verify_gate_failure_triggers_rollback_and_quarantine(self):
        with tempfile.TemporaryDirectory(prefix="mios-greenboot-fail-") as tmpdir:
            hist_file = os.path.join(tmpdir, "history.json")
            quarantine_file = os.path.join(tmpdir, "quarantine.json")
            engine = greenboot_gate.GreenbootGateEngine(
                history_path=hist_file,
                quarantine_path=quarantine_file,
                mock=True,
                mock_failure=True,
            )
            res = engine.verify_gate()
            self.assertEqual(res["status"], "failed_rolled_back")
            self.assertIn("rollback", res)
            self.assertIn("quarantine", res)
            self.assertTrue(os.path.isfile(quarantine_file))

    def test_cli_check_mock(self):
        test_args = ["greenboot_gate.py", "--check", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = greenboot_gate.main()
            self.assertEqual(exit_code, 0)

    def test_cli_status_mock(self):
        test_args = ["greenboot_gate.py", "--status", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = greenboot_gate.main()
            self.assertEqual(exit_code, 0)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGreenbootGate)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
