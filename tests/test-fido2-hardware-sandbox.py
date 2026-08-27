#!/usr/bin/env python3
# AI-hint: Unit test suite for MiOS FIDO2 Hardware Key Manager and Challenge Sandbox (T-592 / AGY-2190).
# AI-related: usr/libexec/mios/sec/fido2_manager.py, usr/share/doc/mios/manual/sec.md
"""Unit and integration tests for FIDO2SecurityManager."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "sec", "fido2_manager.py")

spec = importlib.util.spec_from_file_location("fido2_manager", _TARGET_PATH)
if spec and spec.loader:
    fido2_manager = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = fido2_manager
    spec.loader.exec_module(fido2_manager)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestFIDO2SecurityManager(unittest.TestCase):
    """Test suite for FIDO2 device discovery, PAM U2F enrollment, and SSH SK key synthesis."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="mios-test-fido2-")
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_discover_devices_mock(self):
        mgr = fido2_manager.FIDO2SecurityManager(mock=True)
        devs = mgr.discover_devices()
        self.assertEqual(len(devs), 2)
        self.assertEqual(devs[0].manufacturer, "Yubico")
        self.assertTrue(devs[0].pin_required)
        self.assertEqual(devs[1].manufacturer, "SoloKeys")

    def test_enroll_pam_u2f_mock(self):
        u2f_out = self.root / "u2f_keys"
        mgr = fido2_manager.FIDO2SecurityManager(mock=True)

        ok, details = mgr.enroll_pam_u2f(username="operator", pin_enforced=True, output_file=str(u2f_out))
        self.assertTrue(ok)
        self.assertEqual(details["username"], "operator")
        self.assertTrue(details["pin_enforced"])
        self.assertTrue(u2f_out.exists())

        content = u2f_out.read_text(encoding="utf-8")
        self.assertIn("operator:mock_key_handle", content)
        self.assertIn("+pin", content)

    def test_generate_ssh_sk_mock(self):
        ssh_out = self.root / ".ssh"
        mgr = fido2_manager.FIDO2SecurityManager(mock=True)

        ok, details = mgr.generate_ssh_sk(output_dir=str(ssh_out))
        self.assertTrue(ok)
        self.assertTrue(details["resident"])
        self.assertTrue(os.path.exists(details["private_key_path"]))
        self.assertTrue(os.path.exists(details["public_key_path"]))

    def test_cli_execution_discover_mock(self):
        test_args = ["fido2_manager.py", "--discover", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = fido2_manager.main()
            self.assertEqual(exit_code, 0)

    def test_cli_execution_enroll_pam_mock(self):
        out_path = str(self.root / "cli_u2f_keys")
        test_args = ["fido2_manager.py", "--enroll-pam", "--username", "testuser", "--output", out_path, "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = fido2_manager.main()
            self.assertEqual(exit_code, 0)
            self.assertTrue(os.path.exists(out_path))

    def test_cli_execution_generate_ssh_sk_mock(self):
        out_dir = str(self.root / "cli_ssh")
        test_args = ["fido2_manager.py", "--generate-ssh-sk", "--output", out_dir, "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = fido2_manager.main()
            self.assertEqual(exit_code, 0)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFIDO2SecurityManager)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
