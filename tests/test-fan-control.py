#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Multi-zone PID Fan Controller (T-623, T-624).
# AI-related: usr/libexec/mios/hw/fand.py, tests/test-fan-control.py
"""Automated unit test suite for MiOS Multi-zone PID Fan Controller."""

import os
import sys
import tempfile
import unittest
from typing import Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "hw"))

from fand import MultiZonePIDFanController, FanZoneConfig


class TestFanControl(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="mios-fan-test-")
        self.state_file = os.path.join(self.tmp_dir, "fan_state.json")
        self.controller = MultiZonePIDFanController(
            sysfs_root=self.tmp_dir,
            state_file=self.state_file,
            dry_run=True,
            hysteresis_deg=5.0,
            max_pwm_ramp_per_sec=25.0,
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _create_mock_sysfs(self):
        hwmon0 = os.path.join(self.tmp_dir, "sys", "class", "hwmon", "hwmon0")
        os.makedirs(hwmon0, exist_ok=True)
        with open(os.path.join(hwmon0, "name"), "w") as f:
            f.write("coretemp\n")
        with open(os.path.join(hwmon0, "temp1_input"), "w") as f:
            f.write("55000\n")  # 55.0 C
        with open(os.path.join(hwmon0, "pwm1"), "w") as f:
            f.write("100\n")
        with open(os.path.join(hwmon0, "pwm1_enable"), "w") as f:
            f.write("1\n")
        return hwmon0

    def test_sensor_discovery(self):
        """Test discovery of hwmon sensors and PWM controls from sysfs."""
        hwmon0 = self._create_mock_sysfs()
        devs = self.controller.discover_hwmon_devices()
        self.assertIn("hwmon0_temp1_input", devs["sensors"])
        self.assertIn("hwmon0_pwm1", devs["pwms"])
        self.assertEqual(devs["sensors"]["hwmon0_temp1_input"]["device_name"], "coretemp")

    def test_sensor_temp_read(self):
        """Test reading and converting millidegree temperature values."""
        hwmon0 = self._create_mock_sysfs()
        temp_file = os.path.join(hwmon0, "temp1_input")
        temp = self.controller.read_sensor_temp(temp_file)
        self.assertIsNotNone(temp)
        self.assertAlmostEqual(temp, 55.0, places=1)

    def test_pid_monotonic_ramp_rate_limiting(self):
        """Test that large step temperature jumps result in rate-limited PWM ramp transitions."""
        # Initial step at target temp 65C -> initial base PWM
        res1 = self.controller.compute_pid_pwm("cpu", current_temp=65.0, dt=1.0)
        
        # Step temperature to 80C (> target 65C)
        res2 = self.controller.compute_pid_pwm("cpu", current_temp=80.0, dt=1.0)
        
        # Ramp should increase, but step delta must be bounded by max_pwm_ramp_per_sec (25.0)
        pwm_delta = res2 - res1
        self.assertGreater(pwm_delta, 0)
        self.assertLessEqual(pwm_delta, 25.0 + 1.0)

    def test_hysteresis_deadband_stability(self):
        """Test 5°C hysteresis damping prevents rapid oscillations when temperature drops in deadband."""
        # Warm up to 68C (above target 65C)
        self.controller.compute_pid_pwm("cpu", current_temp=68.0, dt=1.0)
        pwm_warm = self.controller.compute_pid_pwm("cpu", current_temp=68.0, dt=1.0)

        # Drop slightly to 64C (within 5C hysteresis deadband of target 65C)
        pwm_dropped = self.controller.compute_pid_pwm("cpu", current_temp=64.0, dt=1.0)

        # Ensure PWM transitions smoothly without erratic sudden drop to minimum
        self.assertGreaterEqual(pwm_dropped, self.controller.zones["cpu"].min_pwm)
        self.assertLessEqual(abs(pwm_dropped - pwm_warm), 26.0)

    def test_critical_temperature_override(self):
        """Test that temperature at or above critical threshold immediately forces 100% PWM (255)."""
        res = self.controller.compute_pid_pwm("cpu", current_temp=86.0, dt=1.0)  # critical is 85.0
        self.assertEqual(res, 255)

    def test_multi_zone_independent_simulation(self):
        """Test multi-zone regulation (CPU, GPU, NVMe, Chassis) with varied thermal loads."""
        loads = {
            "cpu": 72.0,
            "gpu": 80.0,
            "nvme": 50.0,
            "chassis": 45.0,
        }
        res = self.controller.step_simulation(loads, dt=1.0)
        self.assertIn("cpu", res)
        self.assertIn("gpu", res)
        self.assertIn("nvme", res)
        self.assertIn("chassis", res)
        self.assertGreaterEqual(res["gpu"]["pwm"], res["nvme"]["pwm"])

    def test_state_persistence(self):
        """Test saving and serializing fan controller status."""
        self.controller.save_state()
        self.assertTrue(os.path.isfile(self.state_file))
        status = self.controller.get_status()
        self.assertEqual(status["hysteresis_deg"], 5.0)
        self.assertIn("cpu", status["zones"])


if __name__ == "__main__":
    unittest.main()
