#!/usr/bin/env python3
# AI-hint: Automated unit test suite for GPU ASPM L1.2 & D3cold Wakeup (T-683, T-684).
# AI-related: usr/libexec/mios/hw/gpu_powerd.py, tests/test-gpu-power.py
"""Automated unit test suite for MiOS GPU Power Manager."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "hw"))

from gpu_powerd import MAX_D3COLD_WAKE_MS, GPUPowerManager

class TestGPUPower(unittest.TestCase):
    def setUp(self):
        self.mgr = GPUPowerManager(dry_run=True)

    def test_d3cold_power_consumption_under_3w(self):
        """Test idle GPU enters D3cold with power draw < 3.0W."""
        state = self.mgr.transition_to_d3cold()
        self.assertEqual(state.power_state, "D3cold_Sleep")
        self.assertLess(state.current_wattage, 3.0)
        self.assertEqual(state.aspm_state, "L1.2")

    def test_sub_150ms_d3cold_inference_wakeup(self):
        """Test waking GPU from D3cold completes in <150ms."""
        self.mgr.transition_to_d3cold()
        state = self.mgr.wake_gpu_for_inference()
        self.assertEqual(state.power_state, "D0_Active")
        self.assertLess(state.wake_latency_ms, MAX_D3COLD_WAKE_MS)

if __name__ == "__main__":
    unittest.main()
