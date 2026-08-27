#!/usr/bin/env python3
# AI-hint: Automated unit test suite for screen lock manager with biometric & FIDO2 authentication.
# AI-related: usr/libexec/mios/ux/biometric_lock.py, usr/share/mios/mios.toml
"""Unit and integration test suite for BiometricLockManager and biometric_lock CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "ux", "biometric_lock.py")

spec = importlib.util.spec_from_file_location("biometric_lock", _TARGET_PATH)
if spec and spec.loader:
    biometric_lock = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = biometric_lock
    spec.loader.exec_module(biometric_lock)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")


class TestBiometricLock(unittest.TestCase):
    """Test suite for biometric hardware inspection, PAM stack generation, and lock triggers."""

    def test_biometric_sensor_dataclass(self):
        s = biometric_lock.BiometricSensor(
            sensor_type="fingerprint",
            device_name="Synaptics Prometheus",
            driver="pam_fprintd",
            is_enrolled=True,
            status="ready",
            capabilities=["touch", "verification"],
        )
        self.assertEqual(s.sensor_type, "fingerprint")
        self.assertTrue(s.is_enrolled)
        self.assertEqual(len(s.capabilities), 2)

    def test_check_sensors_mock(self):
        manager = biometric_lock.BiometricLockManager(mock=True)
        res = manager.check_sensors()
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["sensors_detected"], 2)
        sensor_types = [s["sensor_type"] for s in res["sensors"]]
        self.assertIn("fingerprint", sensor_types)
        self.assertIn("fido2_ctap2", sensor_types)

    def test_render_pam_config_with_password_fallback(self):
        manager = biometric_lock.BiometricLockManager(mock=True)
        pam = manager.render_pam_config("swaylock")
        self.assertIn("pam_fprintd.so", pam)
        self.assertIn("pam_u2f.so", pam)
        # Unconditional password fallback guarantee
        self.assertIn("auth        include       system-auth", pam)
        self.assertIn("account     include       system-auth", pam)

    def test_generate_pam_files_mock(self):
        manager = biometric_lock.BiometricLockManager(mock=True)
        res = manager.generate_pam_files(services=["swaylock", "hyprlock"])
        self.assertEqual(res["status"], "success")
        self.assertEqual(len(res["files"]), 2)
        self.assertIn("swaylock", res["previews"])
        self.assertIn("hyprlock", res["previews"])

    def test_lock_screen_mock(self):
        manager = biometric_lock.BiometricLockManager(mock=True)
        res = manager.lock_screen()
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["action"], "lock_screen")
        self.assertIn("swaylock", res["command"])

    def test_cli_check_sensors_mock(self):
        test_args = ["biometric_lock.py", "--check-sensors", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = biometric_lock.main()
            self.assertEqual(exit_code, 0)

    def test_cli_generate_pam_mock(self):
        test_args = ["biometric_lock.py", "--generate-pam", "--target-service", "swaylock", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = biometric_lock.main()
            self.assertEqual(exit_code, 0)

    def test_cli_lock_mock(self):
        test_args = ["biometric_lock.py", "--lock", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = biometric_lock.main()
            self.assertEqual(exit_code, 0)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestBiometricLock)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
