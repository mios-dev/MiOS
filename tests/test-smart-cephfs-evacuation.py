#!/usr/bin/env python3
# AI-hint: Automated unit test suite for S.M.A.R.T. Drive Health and CephFS Evacuation (T-639, T-640).
# AI-related: usr/libexec/mios/storage/disk_health.py, tests/test-smart-cephfs-evacuation.py
"""Automated unit test suite for MiOS S.M.A.R.T. Drive Health and CephFS Evacuation."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "storage"))

from disk_health import SmartHealthMonitor, DriveHealth

class TestSmartCephfsEvacuation(unittest.TestCase):
    def setUp(self):
        self.monitor = SmartHealthMonitor(dry_run=True)

    def test_healthy_drive_no_action(self):
        """Test healthy NVMe drive operates without triggering evacuation."""
        h = self.monitor.evaluate_drive_health(
            "/dev/nvme0n1", {"percentage_used": 20.0, "available_spare": 100.0, "media_errors": 0}
        )
        self.assertFalse(h.is_degraded)
        self.assertEqual(h.action_taken, "none")
        self.assertEqual(h.risk_level, "OK")
        self.assertGreater(h.health_score, 80.0)

    def test_degraded_wear_triggers_evacuation(self):
        """Test percentage_used >= 95% triggers automated CephFS OSD out."""
        h = self.monitor.evaluate_drive_health(
            "/dev/nvme1n1", {"percentage_used": 97.0, "available_spare": 100.0, "media_errors": 0}
        )
        self.assertTrue(h.is_degraded)
        self.assertIn("ceph_osd_out", h.action_taken)
        self.assertIn("osd.1n1", self.monitor.evacuated_osds)
        self.assertEqual(h.evacuation_status, "evacuated")

    def test_available_spare_depletion_evacuation(self):
        """Test available_spare <= 10% triggers predictive evacuation."""
        h = self.monitor.evaluate_drive_health(
            "/dev/nvme2n1", {"percentage_used": 50.0, "available_spare": 5.0, "media_errors": 2}
        )
        self.assertTrue(h.is_degraded)
        self.assertIn("ceph_osd_out", h.action_taken)
        self.assertEqual(h.risk_level, "CRITICAL")

    def test_thermal_overheating_evacuation(self):
        """Test drive temperature > 75°C triggers proactive protection."""
        h = self.monitor.evaluate_drive_health(
            "/dev/nvme3n1", {"percentage_used": 10.0, "temperature_c": 78.0}
        )
        self.assertTrue(h.is_degraded)
        self.assertIn("ceph_osd_out", h.action_taken)

    def test_sata_reallocated_sectors_evacuation(self):
        """Test SATA drive with high reallocated sector count triggers drain."""
        mock_sata = {
            "ata_smart_attributes": {
                "table": [
                    {"name": "Reallocated_Sector_Ct", "raw": {"value": 48}},
                    {"name": "Temperature_Celsius", "raw": {"value": 35}},
                ]
            }
        }
        h = self.monitor.evaluate_drive_health("/dev/sda", mock_sata)
        self.assertTrue(h.is_degraded)
        self.assertIn("ceph_osd_out", h.action_taken)

    def test_zero_rebalance_object_loss(self):
        """Test that evacuation events register zero degraded object loss."""
        self.monitor.evaluate_drive_health("/dev/nvme0n1", {"percentage_used": 99.0})
        self.assertGreater(len(self.monitor.evacuation_events), 0)
        for ev in self.monitor.evacuation_events:
            self.assertEqual(ev["rebalance_loss"], 0)

    def test_malformed_smart_json_none_values(self):
        """Test parser resilience against None and malformed fields."""
        malformed_data = {
            "percentage_used": None,
            "available_spare": None,
            "media_errors": "not_an_int",
            "temperature": None,
            "critical_warning": None,
            "ata_smart_attributes": None,
            "reallocated_sectors": None,
        }
        h = self.monitor.parse_smart_json("/dev/nvme0n1", malformed_data)
        self.assertFalse(h.is_degraded)
        self.assertEqual(h.percentage_used, 10.0)
        self.assertEqual(h.available_spare, 100.0)
        self.assertEqual(h.media_errors, 0)
        self.assertEqual(h.temperature_c, 40.0)
        self.assertEqual(h.reallocated_sectors, 0)
        self.assertEqual(h.critical_warning, 0)

if __name__ == "__main__":
    unittest.main()
