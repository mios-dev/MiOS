#!/usr/bin/env python3
# AI-hint: Automated unit test suite for USBGuard Policy Generator and Device Blocking (T-643, T-644).
# AI-related: usr/libexec/mios/sec/usbguard.py, tests/test-usbguard-policy.py
"""Automated unit test suite for MiOS USBGuard Policy Manager."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "sec"))

from usbguard import USBGuardPolicyManager


class TestUSBGuardPolicy(unittest.TestCase):
    def setUp(self):
        self.mgr = USBGuardPolicyManager(dry_run=True)
        self.mgr.enroll_device("046d", "c52b", "SN_AUTH_01", "Logitech Keyboard")

    def test_enrolled_device_allowed(self):
        """Test pre-enrolled peripheral communicates cleanly."""
        allowed = self.mgr.handle_device_insertion(
            "usb1", "046d", "c52b", "SN_AUTH_01", "03:01:01", "Logitech Keyboard"
        )
        self.assertTrue(allowed)
        self.assertEqual(len(self.mgr.blocked_attempts), 0)

    def test_unauthorized_badusb_blocked(self):
        """Test unauthorized rogue USB HID device is blocked by default."""
        allowed = self.mgr.handle_device_insertion(
            "usb2", "1234", "5678", "SN_ROGUE_99", "03:01:01", "Rogue Rubber Ducky"
        )
        self.assertFalse(allowed)
        self.assertEqual(len(self.mgr.blocked_attempts), 1)

    def test_interactive_authorization_and_rule_generation(self):
        """Test operator approval unlocks device and updates generated rules.conf."""
        self.mgr.handle_device_insertion("usb3", "04b4", "f138", "SN_NEW_02", "03:00:00", "Custom Controller")
        ok = self.mgr.authorize_device_interactively("usb3")
        self.assertTrue(ok)

        rules = self.mgr.generate_rules_conf()
        self.assertIn("04b4:f138", rules)
        self.assertIn("SN_NEW_02", rules)


if __name__ == "__main__":
    unittest.main()
