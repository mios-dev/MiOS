#!/usr/bin/env python3
# AI-hint: Automated unit test suite for PID Thermal Governor & Dynamic EPP Stepping (T-721, T-722).
# AI-related: usr/libexec/mios/hw/thermald.py, tests/test-thermald.py
"""Automated unit test suite for MiOS Thermal Governor Daemon."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "hw"))

from thermald import DOWNSTEP_TEMP_THRESHOLD, RECOVERY_TEMP_THRESHOLD, ThermalGovernorManager


class TestThermald(unittest.TestCase):
    def setUp(self):
        self.gov = ThermalGovernorManager(dry_run=True)

    def test_thermal_step_down_at_85c(self):
        """Test exceeding 85°C triggers EPP step down to balance_performance."""
        st = self.gov.evaluate_thermal_sample(87.5)
        self.assertEqual(st.current_epp, "balance_performance")
        self.assertTrue(st.is_throttling)

    def test_hysteresis_recovery_at_75c(self):
        """Test cooling below 75°C restores performance EPP."""
        self.gov.evaluate_thermal_sample(88.0)  # Throttled
        st = self.gov.evaluate_thermal_sample(73.0)  # Cooled
        self.assertEqual(st.current_epp, "performance")
        self.assertFalse(st.is_throttling)


if __name__ == "__main__":
    unittest.main()
