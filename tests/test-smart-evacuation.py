#!/usr/bin/env python3
# AI-hint: Automated unit test suite for S.M.A.R.T. Drive Health and CephFS Evacuation (T-639, T-640).
# AI-related: usr/libexec/mios/storage/smart_health.py, tests/test-smart-evacuation.py
"""Automated unit test suite for MiOS S.M.A.R.T. Drive Health and CephFS Evacuation."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "storage"))

from smart_health import SmartHealthMonitor


class TestSmartEvacuation(unittest.TestCase):
    def setUp(self):
        self.monitor = SmartHealthMonitor(dry_run=True)

    def test_healthy_drive_no_action(self):
        """Test healthy drive operates without triggering evacuation."""
        h = self.monitor.evaluate_drive_health(
            "/dev/nvme0n1", {"percentage_used": 20.0, "available_spare": 100.0, "media_errors": 0}
        )
        self.assertFalse(h.is_degraded)
        self.assertEqual(h.action_taken, "none")

    def test_degraded_wear_triggers_evacuation(self):
        """Test percentage_used > 95% triggers automated CephFS OSD out."""
        h = self.monitor.evaluate_drive_health(
            "/dev/nvme1n1", {"percentage_used": 97.0, "available_spare": 100.0, "media_errors": 0}
        )
        self.assertTrue(h.is_degraded)
        self.assertIn("ceph_osd_out", h.action_taken)
        self.assertIn("osd.nvme1n1", self.monitor.evacuated_osds)


if __name__ == "__main__":
    unittest.main()
