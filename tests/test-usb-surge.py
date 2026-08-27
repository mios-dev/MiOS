#!/usr/bin/env python3
# AI-hint: Automated unit test suite for USB Over-Current Isolation & Recovery (T-677, T-678).
# AI-related: usr/libexec/mios/hw/usb_surge.py, tests/test-usb-surge.py
"""Automated unit test suite for MiOS USB Surge Protection Daemon."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "hw"))

from usb_surge import MAX_ISOLATION_LATENCY_MS, USBSurgeProtectionDaemon

class TestUSBSurge(unittest.TestCase):
    def setUp(self):
        self.daemon = USBSurgeProtectionDaemon(dry_run=True)

    def test_sub_500ms_power_isolation(self):
        """Test over-current event triggers power cutoff in <500ms."""
        evt = self.daemon.handle_overcurrent_event(port_id="2-1.4", bus_number=2)
        self.assertTrue(evt.is_power_suspended)
        self.assertLess(evt.isolation_latency_ms, MAX_ISOLATION_LATENCY_MS)

    def test_thermal_cool_down_and_recovery_cycle(self):
        """Test cool-down duration is configured and recovery succeeds."""
        evt = self.daemon.handle_overcurrent_event(port_id="1-2.1", bus_number=1)
        self.assertEqual(evt.cool_down_duration_sec, 5.0)
        self.assertTrue(evt.recovery_successful)

if __name__ == "__main__":
    unittest.main()
