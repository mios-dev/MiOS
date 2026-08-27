#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Hardware Energy Metering and Power Capping (T-633, T-634).
# AI-related: usr/libexec/mios/hw/energyd.py, tests/test-energy-capping.py
"""Automated unit test suite for MiOS Hardware Energy Metering and Power Capping."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "hw"))

from energyd import EnergyCapManager


class TestEnergyCapping(unittest.TestCase):
    def setUp(self):
        self.mgr = EnergyCapManager(
            chassis_cap_watts=600.0,
            min_gpu_power_limit=150.0,
            dry_run=True,
        )

    def test_normal_power_unthrottled(self):
        """Test power draw under cap leaves GPU limits unthrottled."""
        m = self.mgr.evaluate_and_enforce_cap(mock_cpu_w=100.0, mock_gpu_w=300.0)
        self.assertFalse(m.is_throttled)
        self.assertEqual(m.total_watts, 400.0)
        self.assertGreaterEqual(m.applied_gpu_cap_watts, 400.0)

    def test_over_cap_throttles_gpu(self):
        """Test total power exceeding 600W cap clamps GPU power limit."""
        m = self.mgr.evaluate_and_enforce_cap(mock_cpu_w=250.0, mock_gpu_w=450.0)
        self.assertTrue(m.is_throttled)
        self.assertEqual(m.total_watts, 700.0)
        self.assertLess(m.applied_gpu_cap_watts, 400.0)

    def test_min_gpu_power_floor_enforcement(self):
        """Test throttling never lowers GPU below minimum floor (150W)."""
        m = self.mgr.evaluate_and_enforce_cap(mock_cpu_w=500.0, mock_gpu_w=450.0)
        self.assertTrue(m.is_throttled)
        self.assertGreaterEqual(m.applied_gpu_cap_watts, 150.0)


if __name__ == "__main__":
    unittest.main()
