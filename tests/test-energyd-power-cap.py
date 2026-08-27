#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Hardware Energy Metering and Power Capping (T-633, T-634).
# AI-related: usr/libexec/mios/hw/energyd.py, tests/test-energyd-power-cap.py
"""Automated unit test suite for MiOS Hardware Energy Metering and Power Capping."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "hw"))

from energyd import EnergyCapManager, PowerMetrics


class TestEnergydPowerCap(unittest.TestCase):
    def setUp(self):
        self.mgr = EnergyCapManager(
            chassis_cap_watts=600.0,
            min_gpu_power_limit=150.0,
            max_gpu_power_limit=450.0,
            thermal_limit_c=85.0,
            dry_run=True,
        )

    def test_normal_power_unthrottled(self):
        """Test power draw under cap leaves GPU and CPU unthrottled."""
        m = self.mgr.evaluate_and_enforce_cap(
            mock_cpu_w=100.0, mock_gpu_w=300.0, mock_cpu_temp=45.0, mock_gpu_temp=50.0
        )
        self.assertFalse(m.is_throttled)
        self.assertEqual(m.total_watts, 400.0)
        self.assertGreaterEqual(m.applied_gpu_cap_watts, 400.0)
        self.assertEqual(m.cgroup_cpu_quota_pct, 100.0)
        self.assertEqual(m.throttle_reason, "none")

    def test_over_cap_throttles_gpu_and_cgroups(self):
        """Test total power exceeding 600W cap clamps GPU power limit and throttles cgroups."""
        m = self.mgr.evaluate_and_enforce_cap(
            mock_cpu_w=250.0, mock_gpu_w=450.0, mock_cpu_temp=50.0, mock_gpu_temp=60.0
        )
        self.assertTrue(m.is_throttled)
        self.assertEqual(m.total_watts, 700.0)
        self.assertLess(m.applied_gpu_cap_watts, 400.0)
        self.assertLess(m.cgroup_cpu_quota_pct, 100.0)
        self.assertIn("power_cap_exceeded", m.throttle_reason)

    def test_min_gpu_power_floor_enforcement(self):
        """Test severe power overload never drops GPU below minimum floor (150W)."""
        m = self.mgr.evaluate_and_enforce_cap(
            mock_cpu_w=600.0, mock_gpu_w=450.0, mock_cpu_temp=50.0, mock_gpu_temp=60.0
        )
        self.assertTrue(m.is_throttled)
        self.assertGreaterEqual(m.applied_gpu_cap_watts, 150.0)

    def test_thermal_throttling_trigger(self):
        """Test junction temperature exceeding 85°C triggers thermal throttle."""
        m = self.mgr.evaluate_and_enforce_cap(
            mock_cpu_w=100.0, mock_gpu_w=200.0, mock_cpu_temp=88.0, mock_gpu_temp=90.0
        )
        self.assertTrue(m.is_throttled)
        self.assertIn("thermal_throttle", m.throttle_reason)
        self.assertLess(m.applied_gpu_cap_watts, 450.0)

    def test_unthrottle_recovery_hysteresis(self):
        """Test that after throttling, power limit recovers smoothly when load drops."""
        self.mgr.evaluate_and_enforce_cap(mock_cpu_w=300.0, mock_gpu_w=450.0)
        clamped_limit = self.mgr.current_gpu_limit

        m_rec = self.mgr.evaluate_and_enforce_cap(
            mock_cpu_w=50.0, mock_gpu_w=100.0, mock_cpu_temp=40.0, mock_gpu_temp=45.0
        )
        self.assertFalse(m_rec.is_throttled)
        self.assertGreater(m_rec.applied_gpu_cap_watts, clamped_limit)

    def test_telemetry_export(self):
        """Test telemetry export produces structured records with all required fields."""
        self.mgr.evaluate_and_enforce_cap(mock_cpu_w=100.0, mock_gpu_w=200.0)
        self.mgr.evaluate_and_enforce_cap(mock_cpu_w=300.0, mock_gpu_w=400.0)
        telemetry = self.mgr.export_telemetry()
        self.assertEqual(len(telemetry), 2)
        for entry in telemetry:
            self.assertIn("timestamp", entry)
            self.assertIn("cpu_watts", entry)
            self.assertIn("gpu_watts", entry)
            self.assertIn("total_watts", entry)
            self.assertIn("cap_watts", entry)
            self.assertIn("cpu_temp_c", entry)
            self.assertIn("gpu_temp_c", entry)
            self.assertIn("applied_gpu_cap_watts", entry)
            self.assertIn("cgroup_cpu_quota_pct", entry)
            self.assertIn("is_throttled", entry)

    def test_carbon_aware_mode(self):
        """Test carbon-aware scheduling mode applies energy saving ceiling."""
        self.mgr.carbon_aware_mode = True
        m = self.mgr.evaluate_and_enforce_cap(mock_cpu_w=50.0, mock_gpu_w=100.0)
        self.assertLessEqual(m.applied_gpu_cap_watts, 450.0 * 0.8)
        self.assertEqual(m.cgroup_cpu_quota_pct, 80.0)


if __name__ == "__main__":
    unittest.main()
