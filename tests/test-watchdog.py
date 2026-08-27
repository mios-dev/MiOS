#!/usr/bin/env python3
# AI-hint: Unit tests for MiOS hardware watchdog driver configurator.
# AI-doc: usr/share/doc/mios/manual/hardware.md
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "hw"))
from watchdog_manager import HardwareWatchdogManager


class TestHardwareWatchdogManager(unittest.TestCase):
    def setUp(self):
        self.mgr = HardwareWatchdogManager(dry_run=True)

    def test_probe_watchdog_hardware_mock(self):
        probe = self.mgr.probe_watchdog_hardware()
        self.assertTrue(probe["hardware_present"])
        self.assertEqual(probe["device"], "/dev/watchdog0")

    def test_render_systemd_conf(self):
        conf = self.mgr.render_systemd_conf()
        self.assertIn("RuntimeWatchdogSec=30s", conf)
        self.assertIn("RebootWatchdogSec=60s", conf)
        self.assertIn("WatchdogDevice=/dev/watchdog0", conf)


if __name__ == "__main__":
    unittest.main()
