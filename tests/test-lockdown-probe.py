#!/usr/bin/env python3
# AI-hint: Unit and integration tests for Linux kernel lockdown mode probe and module signing checks.
# AI-related: usr/libexec/mios/sec/lockdown_probe.py, usr/share/doc/mios/manual/sec.md
"""Unit and integration test suite for LockdownProbe and CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "sec", "lockdown_probe.py")

spec = importlib.util.spec_from_file_location("lockdown_probe", _TARGET_PATH)
if spec and spec.loader:
    lockdown_probe = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = lockdown_probe
    spec.loader.exec_module(lockdown_probe)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")


class TestLockdownProbe(unittest.TestCase):
    """Test suite for kernel lockdown modes, SecureBoot validation, and compliance evaluation."""

    def test_read_lockdown_mode_brackets(self):
        probe = lockdown_probe.LockdownProbe(mock=True)
        # Integrity mode
        mode_int = probe.read_lockdown_mode(mock_content="none [integrity] confidentiality")
        self.assertEqual(mode_int, "integrity")

        # Confidentiality mode
        mode_conf = probe.read_lockdown_mode(mock_content="none integrity [confidentiality]")
        self.assertEqual(mode_conf, "confidentiality")

        # None mode
        mode_none = probe.read_lockdown_mode(mock_content="[none] integrity confidentiality")
        self.assertEqual(mode_none, "none")

    def test_check_secureboot_and_module_signing_mock(self):
        probe = lockdown_probe.LockdownProbe(mock=True)
        self.assertTrue(probe.check_secureboot(mock_state=True))
        self.assertFalse(probe.check_secureboot(mock_state=False))
        self.assertTrue(probe.check_module_signing(mock_state=True))
        self.assertFalse(probe.check_module_signing(mock_state=False))

    def test_evaluate_lockdown_compliance_pass_and_fail(self):
        probe_integrity = lockdown_probe.LockdownProbe(mock=True, mock_mode="integrity")
        res_pass = probe_integrity.evaluate_lockdown_compliance(required_mode="integrity")
        self.assertEqual(res_pass["status"], "pass")
        self.assertTrue(res_pass["compliant"])
        self.assertEqual(res_pass["lockdown_mode"], "integrity")

        probe_none = lockdown_probe.LockdownProbe(mock=True, mock_mode="none")
        res_fail = probe_none.evaluate_lockdown_compliance(required_mode="integrity")
        self.assertEqual(res_fail["status"], "fail")
        self.assertFalse(res_fail["compliant"])
        self.assertEqual(res_fail["lockdown_mode"], "none")

    def test_cli_execution_probe_mock_integrity(self):
        test_args = [
            "lockdown_probe.py",
            "--probe",
            "--require-mode", "integrity",
            "--mock",
            "--mock-mode", "integrity",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = lockdown_probe.main()
            self.assertEqual(exit_code, 0)

    def test_cli_execution_probe_mock_none_exits_1(self):
        test_args = [
            "lockdown_probe.py",
            "--probe",
            "--require-mode", "integrity",
            "--mock",
            "--mock-mode", "none",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = lockdown_probe.main()
            self.assertEqual(exit_code, 1)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestLockdownProbe)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
