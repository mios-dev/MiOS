#!/usr/bin/env python3
# AI-hint: Automated unit test suite for T-424 GPU thermal watchdog and fan curve controller.
# AI-related: usr/libexec/mios/hw/gpu_thermal_watchdog.py
"""Automated tests for MiOS GPU Thermal, Junction Temperature & Fan Watchdog (T-424)."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_MODULE_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "hw", "gpu_thermal_watchdog.py")

spec = importlib.util.spec_from_file_location("gpu_thermal_watchdog", _MODULE_PATH)
if spec and spec.loader:
    gpu_thermal_watchdog = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = gpu_thermal_watchdog
    spec.loader.exec_module(gpu_thermal_watchdog)
else:
    raise ImportError(f"Could not load gpu_thermal_watchdog module from {_MODULE_PATH}")

class TestGPUThermalWatchdog(unittest.TestCase):
    """Validates GPU thermal parsing, dynamic fan curve calculations, and the non-zero fan floor invariant."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp(prefix="mios_test_gpu_")
        self.sysfs_root = self.tmp_dir
        self.hwmon_dir = os.path.join(self.sysfs_root, "sys", "class", "drm", "card0", "device", "hwmon", "hwmon0")
        os.makedirs(self.hwmon_dir, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _setup_hwmon_gpu(
        self,
        name: str = "amdgpu",
        junction_temp_mc: int = 72000,
        edge_temp_mc: int = 58000,
        mem_temp_mc: int = 64000,
        pwm_val: int = 128,
        fan_rpm: int = 1650,
    ) -> str:
        with open(os.path.join(self.hwmon_dir, "name"), "w") as f:
            f.write(f"{name}\n")
        with open(os.path.join(self.hwmon_dir, "temp1_input"), "w") as f:
            f.write(f"{edge_temp_mc}\n")
        with open(os.path.join(self.hwmon_dir, "temp1_label"), "w") as f:
            f.write("edge\n")
        with open(os.path.join(self.hwmon_dir, "temp2_input"), "w") as f:
            f.write(f"{junction_temp_mc}\n")
        with open(os.path.join(self.hwmon_dir, "temp2_label"), "w") as f:
            f.write("junction\n")
        with open(os.path.join(self.hwmon_dir, "temp3_input"), "w") as f:
            f.write(f"{mem_temp_mc}\n")
        with open(os.path.join(self.hwmon_dir, "temp3_label"), "w") as f:
            f.write("mem\n")
        with open(os.path.join(self.hwmon_dir, "pwm1"), "w") as f:
            f.write(f"{pwm_val}\n")
        with open(os.path.join(self.hwmon_dir, "pwm1_enable"), "w") as f:
            f.write("2\n")
        with open(os.path.join(self.hwmon_dir, "fan1_input"), "w") as f:
            f.write(f"{fan_rpm}\n")
        return self.hwmon_dir

    def test_gpu_telemetry_reading(self) -> None:
        self._setup_hwmon_gpu(junction_temp_mc=72000, edge_temp_mc=58000, mem_temp_mc=64000)

        wd = gpu_thermal_watchdog.GPUThermalWatchdog(sysfs_root=self.sysfs_root)
        gpus = wd.scan_hwmon_gpus()
        self.assertEqual(len(gpus), 1)

        gpu = gpus[0]
        self.assertEqual(gpu.vendor, "amdgpu")
        self.assertEqual(gpu.junction_temp_c, 72.0)
        self.assertEqual(gpu.edge_temp_c, 58.0)
        self.assertEqual(gpu.memory_temp_c, 64.0)
        self.assertEqual(gpu.peak_temperature_c, 72.0)
        self.assertEqual(gpu.current_fan_rpm, 1650)

    def test_non_zero_fan_floor_invariant(self) -> None:
        """Enforces: Do NOT set fan speeds to 0% under any operational thermal condition."""
        # 1. Floor configuration <= 0 is automatically clamped to DEFAULT_MIN_FAN_FLOOR_PERCENT
        wd_zero = gpu_thermal_watchdog.GPUThermalWatchdog(sysfs_root=self.sysfs_root, min_fan_floor_percent=0.0)
        self.assertGreater(wd_zero.min_fan_floor_percent, 0.0)
        self.assertEqual(wd_zero.min_fan_floor_percent, 25.0)

        wd_neg = gpu_thermal_watchdog.GPUThermalWatchdog(sysfs_root=self.sysfs_root, min_fan_floor_percent=-15.0)
        self.assertGreater(wd_neg.min_fan_floor_percent, 0.0)

        # 2. Dynamic curve evaluation at freezing temperatures (0°C, 20°C) NEVER yields 0%
        wd = gpu_thermal_watchdog.GPUThermalWatchdog(sysfs_root=self.sysfs_root, min_fan_floor_percent=30.0)
        self.assertEqual(wd.calculate_fan_curve_duty_cycle(0.0), 30.0)
        self.assertEqual(wd.calculate_fan_curve_duty_cycle(20.0), 30.0)
        self.assertEqual(wd.calculate_fan_curve_duty_cycle(35.0), 30.0)

    def test_dynamic_fan_curve_scaling(self) -> None:
        wd = gpu_thermal_watchdog.GPUThermalWatchdog(
            sysfs_root=self.sysfs_root,
            target_junction_temp_c=80.0,
            min_fan_floor_percent=25.0,
        )

        # Idle (< 40°C) -> 25% floor
        self.assertEqual(wd.calculate_fan_curve_duty_cycle(30.0), 25.0)

        # Mid Load (52.5°C) -> halfway between 25% and 60% = 42.5%
        self.assertAlmostEqual(wd.calculate_fan_curve_duty_cycle(52.5), 42.5, places=1)

        # High Load (72.5°C) -> halfway between 60% and 100% = 80%
        self.assertAlmostEqual(wd.calculate_fan_curve_duty_cycle(72.5), 80.0, places=1)

        # Peak Threshold (80°C and above) -> 100% full blast
        self.assertEqual(wd.calculate_fan_curve_duty_cycle(80.0), 100.0)
        self.assertEqual(wd.calculate_fan_curve_duty_cycle(95.0), 100.0)

    def test_check_and_adjust_throttling_warning(self) -> None:
        # GPU junction at 85°C (> 80°C threshold)
        self._setup_hwmon_gpu(junction_temp_mc=85000, edge_temp_mc=75000)

        wd = gpu_thermal_watchdog.GPUThermalWatchdog(sysfs_root=self.sysfs_root, target_junction_temp_c=80.0)
        res = wd.check_and_adjust_all()

        self.assertEqual(res["status"], "warning")
        self.assertTrue(len(res["throttling_warnings"]) > 0)
        self.assertIn("exceeds target threshold", res["throttling_warnings"][0])

        gpu_res = res["gpus"][0]
        self.assertEqual(gpu_res["target_fan_percent"], 100.0)
        self.assertTrue(gpu_res["fan_adjusted"])

        # Check PWM was written to sysfs
        with open(os.path.join(self.hwmon_dir, "pwm1"), "r") as f:
            self.assertEqual(f.read().strip(), "255")
        with open(os.path.join(self.hwmon_dir, "pwm1_enable"), "r") as f:
            self.assertEqual(f.read().strip(), "1")

    def test_multi_gpu_and_fallback_peak_temp(self) -> None:
        # Create second GPU without explicit junction sensor (e.g. Intel Arc / iGPU)
        card1_hwmon = os.path.join(self.sysfs_root, "sys", "class", "drm", "card1", "device", "hwmon", "hwmon1")
        os.makedirs(card1_hwmon, exist_ok=True)
        with open(os.path.join(card1_hwmon, "name"), "w") as f:
            f.write("i915\n")
        with open(os.path.join(card1_hwmon, "temp1_input"), "w") as f:
            f.write("62000\n")  # 62°C
        with open(os.path.join(card1_hwmon, "pwm1"), "w") as f:
            f.write("100\n")

        self._setup_hwmon_gpu(junction_temp_mc=50000, edge_temp_mc=45000)

        wd = gpu_thermal_watchdog.GPUThermalWatchdog(sysfs_root=self.sysfs_root)
        gpus = wd.scan_hwmon_gpus()
        self.assertEqual(len(gpus), 2)

        res = wd.check_and_adjust_all()
        self.assertEqual(res["gpus_monitored"], 2)
        self.assertEqual(res["status"], "ok")

    def test_daemon_single_cycle_run(self) -> None:
        self._setup_hwmon_gpu(junction_temp_mc=55000, edge_temp_mc=50000)
        wd = gpu_thermal_watchdog.GPUThermalWatchdog(sysfs_root=self.sysfs_root)
        # Should run 1 cycle and exit
        wd.run_daemon(poll_interval=0.01, max_cycles=1)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGPUThermalWatchdog)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
