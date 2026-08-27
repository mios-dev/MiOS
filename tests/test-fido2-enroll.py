#!/usr/bin/env python3
# AI-hint: Unit and integration tests for portable drive LUKS2 FIDO2 / CTAP2 token enrollment helper.
# AI-related: usr/libexec/mios/sec/fido2_enroll.py, usr/share/mios/mios.toml
"""Unit and integration test suite for Fido2EnrollEngine and fido2_enroll CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "sec", "fido2_enroll.py")

spec = importlib.util.spec_from_file_location("fido2_enroll", _TARGET_PATH)
if spec and spec.loader:
    fido2_enroll = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = fido2_enroll
    spec.loader.exec_module(fido2_enroll)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")


class TestFido2Enroll(unittest.TestCase):
    """Test suite for FIDO2 token discovery, LUKS2 verification, and keyslot enrollment."""

    def test_discover_tokens_mock(self):
        engine = fido2_enroll.Fido2EnrollEngine(mock=True)
        tokens = engine.discover_tokens()
        self.assertGreaterEqual(len(tokens), 1)
        self.assertTrue(any("YubiKey" in t.product_name for t in tokens))
        self.assertTrue(any(t.has_up for t in tokens))

    def test_inspect_device_luks2(self):
        engine = fido2_enroll.Fido2EnrollEngine(mock=True)
        res = engine.inspect_device("/dev/sdb2")
        self.assertEqual(res.status, "ok")
        self.assertTrue(res.is_luks2)
        self.assertEqual(res.label, "MiOS-Cat-Storage")
        self.assertIn("uuid", res.to_dict())
        self.assertFalse(res.fido2_enrolled)

    def test_inspect_device_already_enrolled(self):
        engine = fido2_enroll.Fido2EnrollEngine(mock=True)
        res = engine.inspect_device("/dev/sdc1")
        self.assertEqual(res.status, "ok")
        self.assertTrue(res.is_luks2)
        self.assertTrue(res.fido2_enrolled)
        self.assertGreaterEqual(len(res.keyslots), 2)

    def test_inspect_device_non_luks2(self):
        engine = fido2_enroll.Fido2EnrollEngine(mock=True)
        res = engine.inspect_device("/dev/sdd1")
        self.assertEqual(res.status, "not_luks2")
        self.assertFalse(res.is_luks2)

    def test_inspect_device_missing_raises_or_errors(self):
        engine = fido2_enroll.Fido2EnrollEngine(mock=True)
        res = engine.inspect_device("/dev/nonexistent")
        self.assertEqual(res.status, "error")

    def test_enroll_fido2_token_success(self):
        engine = fido2_enroll.Fido2EnrollEngine(mock=True)
        res = engine.enroll_fido2(
            device_path="/dev/sdb2",
            fido2_device="/dev/hidraw0",
            require_pin=True,
            require_touch=True,
            require_user_verification=False,
            recovery_key=True,
        )
        self.assertEqual(res.status, "success")
        self.assertEqual(res.device, "/dev/sdb2")
        self.assertIsNotNone(res.keyslot)
        self.assertIsNotNone(res.recovery_key)
        self.assertIn("systemd-cryptenroll", res.command_executed)
        self.assertIn("--fido2-with-client-pin=yes", res.command_executed)
        self.assertIn("--recovery-key", res.command_executed)

        # Inspect to verify keyslot state
        post_status = engine.inspect_device("/dev/sdb2")
        self.assertTrue(post_status.fido2_enrolled)
        self.assertTrue(post_status.recovery_enrolled)

    def test_enroll_fido2_non_luks2_fails(self):
        engine = fido2_enroll.Fido2EnrollEngine(mock=True)
        res = engine.enroll_fido2(device_path="/dev/sdd1")
        self.assertEqual(res.status, "error")
        self.assertIn("not a valid LUKS2 volume", res.message)

    def test_wipe_keyslot_fido2(self):
        engine = fido2_enroll.Fido2EnrollEngine(mock=True)
        # sdc1 has FIDO2 keyslot 1
        wipe_res = engine.wipe_keyslot("/dev/sdc1", wipe_spec="fido2")
        self.assertEqual(wipe_res["status"], "success")
        self.assertIn(1, wipe_res["wiped_slots"])

        post_status = engine.inspect_device("/dev/sdc1")
        self.assertFalse(post_status.fido2_enrolled)

    def test_wipe_keyslot_by_id(self):
        engine = fido2_enroll.Fido2EnrollEngine(mock=True)
        wipe_res = engine.wipe_keyslot("/dev/sdc1", wipe_spec="0")
        self.assertEqual(wipe_res["status"], "success")
        self.assertIn(0, wipe_res["wiped_slots"])

    def test_test_unlock_mock_success_and_failure(self):
        engine = fido2_enroll.Fido2EnrollEngine(mock=True)
        # sdc1 has FIDO2 enrolled
        unlock_ok = engine.test_unlock("/dev/sdc1")
        self.assertEqual(unlock_ok["status"], "success")
        self.assertTrue(unlock_ok["unlocked"])

        # sdb2 does not have FIDO2 initially
        unlock_fail = engine.test_unlock("/dev/sdb2")
        self.assertEqual(unlock_fail["status"], "error")
        self.assertFalse(unlock_fail["unlocked"])

    def test_cli_list_tokens(self):
        test_args = ["fido2_enroll.py", "--list-tokens", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = fido2_enroll.main()
            self.assertEqual(exit_code, 0)

    def test_cli_status(self):
        test_args = ["fido2_enroll.py", "--device", "/dev/sdb2", "--status", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = fido2_enroll.main()
            self.assertEqual(exit_code, 0)

    def test_cli_enroll(self):
        test_args = [
            "fido2_enroll.py",
            "--device", "/dev/sdb2",
            "--fido2-device", "auto",
            "--require-pin",
            "--recovery-key",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = fido2_enroll.main()
            self.assertEqual(exit_code, 0)

    def test_cli_wipe_slot(self):
        test_args = [
            "fido2_enroll.py",
            "--device", "/dev/sdc1",
            "--wipe-slot", "fido2",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = fido2_enroll.main()
            self.assertEqual(exit_code, 0)

    def test_cli_test_unlock(self):
        test_args = [
            "fido2_enroll.py",
            "--device", "/dev/sdc1",
            "--test-unlock",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = fido2_enroll.main()
            self.assertEqual(exit_code, 0)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFido2Enroll)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
