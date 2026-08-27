#!/usr/bin/env python3
# AI-hint: Automated unit test suite for T-421 guest battery and ACPI power passthrough daemon.
# AI-related: usr/libexec/mios/hw/battery_passthrough.py
"""Automated tests for MiOS Guest Virtual ACPI Battery Passthrough Daemon (T-421)."""

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
_MODULE_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "hw", "battery_passthrough.py")

spec = importlib.util.spec_from_file_location("battery_passthrough", _MODULE_PATH)
if spec and spec.loader:
    battery_passthrough = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = battery_passthrough
    spec.loader.exec_module(battery_passthrough)
else:
    raise ImportError(f"Could not load battery_passthrough module from {_MODULE_PATH}")

class TestBatteryPassthrough(unittest.TestCase):
    """Validates power supply discovery, battery telemetry calculations, rate-limiting, and QMP formatting."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp(prefix="mios_test_bat_")
        self.sysfs_root = self.tmp_dir
        self.ps_dir = os.path.join(self.sysfs_root, "sys", "class", "power_supply")
        os.makedirs(self.ps_dir, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _create_battery(
        self,
        name: str = "BAT0",
        status: str = "Discharging",
        capacity: int = 75,
        voltage_uv: int = 12000000,
        current_ua: int = 1500000,
        charge_now: int | None = None,
        charge_full: int | None = 5000000,
        energy_now: int | None = None,
        energy_full: int | None = None,
    ) -> str:
        if charge_now is None and charge_full is not None:
            charge_now = int(charge_full * (capacity / 100.0))
        bdir = os.path.join(self.ps_dir, name)
        os.makedirs(bdir, exist_ok=True)
        with open(os.path.join(bdir, "type"), "w") as f:
            f.write("Battery\n")
        with open(os.path.join(bdir, "status"), "w") as f:
            f.write(f"{status}\n")
        with open(os.path.join(bdir, "capacity"), "w") as f:
            f.write(f"{capacity}\n")
        with open(os.path.join(bdir, "voltage_now"), "w") as f:
            f.write(f"{voltage_uv}\n")
        with open(os.path.join(bdir, "current_now"), "w") as f:
            f.write(f"{current_ua}\n")
        if charge_now is not None:
            with open(os.path.join(bdir, "charge_now"), "w") as f:
                f.write(f"{charge_now}\n")
        if charge_full is not None:
            with open(os.path.join(bdir, "charge_full"), "w") as f:
                f.write(f"{charge_full}\n")
        if energy_now is not None:
            with open(os.path.join(bdir, "energy_now"), "w") as f:
                f.write(f"{energy_now}\n")
        if energy_full is not None:
            with open(os.path.join(bdir, "energy_full"), "w") as f:
                f.write(f"{energy_full}\n")
        with open(os.path.join(bdir, "model_name"), "w") as f:
            f.write("MiOS-SmartBat\n")
        return bdir

    def _create_ac_adapter(self, name: str = "ACAD", online: int = 0) -> str:
        adir = os.path.join(self.ps_dir, name)
        os.makedirs(adir, exist_ok=True)
        with open(os.path.join(adir, "type"), "w") as f:
            f.write("Mains\n")
        with open(os.path.join(adir, "online"), "w") as f:
            f.write(f"{online}\n")
        return adir

    def test_discover_supplies(self) -> None:
        self._create_battery("BAT0")
        self._create_ac_adapter("ACAD")

        reader = battery_passthrough.BatteryTelemetryReader(sysfs_root=self.sysfs_root)
        supplies = reader.discover_supplies()
        self.assertEqual(supplies["batteries"], ["BAT0"])
        self.assertEqual(supplies["ac_adapters"], ["ACAD"])

    def test_discharging_telemetry_and_runtime(self) -> None:
        # 3.75 Ah charge_now / 1.5 A current_now = 2.5 hours = 150 minutes
        self._create_battery("BAT0", status="Discharging", capacity=75, current_ua=1500000, charge_now=3750000)
        self._create_ac_adapter("ACAD", online=0)

        reader = battery_passthrough.BatteryTelemetryReader(sysfs_root=self.sysfs_root)
        snapshot = reader.get_full_power_snapshot()

        self.assertFalse(snapshot["ac_online"])
        self.assertTrue(snapshot["battery_present"])
        self.assertEqual(snapshot["status"], "Discharging")
        self.assertEqual(snapshot["capacity_percent"], 75.0)
        self.assertTrue(snapshot["is_discharging"])
        self.assertFalse(snapshot["is_charging"])
        self.assertAlmostEqual(snapshot["estimated_runtime_minutes"], 150.0, places=1)

    def test_charging_telemetry(self) -> None:
        self._create_battery("BAT0", status="Charging", capacity=50, charge_now=2500000, charge_full=5000000, current_ua=2000000)
        self._create_ac_adapter("ACAD", online=1)

        reader = battery_passthrough.BatteryTelemetryReader(sysfs_root=self.sysfs_root)
        snapshot = reader.get_full_power_snapshot()

        self.assertTrue(snapshot["ac_online"])
        self.assertEqual(snapshot["status"], "Charging")
        self.assertTrue(snapshot["is_charging"])
        self.assertFalse(snapshot["is_discharging"])

    def test_rate_limiting_invariant_clamp(self) -> None:
        """Enforces: Do NOT poll power supply sysfs files faster than once every 5 seconds."""
        # Test values less than 5.0 are clamped to 5.0
        self.assertEqual(battery_passthrough.BatteryPassthroughDaemon.validate_and_clamp_poll_interval(1.0), 5.0)
        self.assertEqual(battery_passthrough.BatteryPassthroughDaemon.validate_and_clamp_poll_interval(0.1), 5.0)
        self.assertEqual(battery_passthrough.BatteryPassthroughDaemon.validate_and_clamp_poll_interval(-10.0), 5.0)
        self.assertEqual(battery_passthrough.BatteryPassthroughDaemon.validate_and_clamp_poll_interval(4.99), 5.0)

        # Values >= 5.0 are preserved
        self.assertEqual(battery_passthrough.BatteryPassthroughDaemon.validate_and_clamp_poll_interval(5.0), 5.0)
        self.assertEqual(battery_passthrough.BatteryPassthroughDaemon.validate_and_clamp_poll_interval(10.0), 10.0)

    def test_qmp_payload_formatting(self) -> None:
        self._create_battery("BAT0", status="Discharging", capacity=82)
        self._create_ac_adapter("ACAD", online=0)

        daemon = battery_passthrough.BatteryPassthroughDaemon(
            sysfs_root=self.sysfs_root,
            domain="win11-laptop",
            dry_run=True,
        )
        res = daemon.sync_once()

        self.assertEqual(res["domain"], "win11-laptop")
        self.assertTrue(res["qmp_delivered"])
        qmp_event = res["qmp_event"]
        self.assertEqual(qmp_event["execute"], "guest-exec")
        self.assertIn(f"--capacity={res['snapshot']['capacity_percent']}", qmp_event["arguments"]["arg"])
        self.assertIn("--status=Discharging", qmp_event["arguments"]["arg"])
        self.assertEqual(qmp_event["telemetry_payload"]["event"], "ACPI_POWER_STATUS_CHANGE")
        self.assertFalse(qmp_event["telemetry_payload"]["data"]["ac_online"])

    def test_multi_battery_aggregation(self) -> None:
        self._create_battery("BAT0", status="Discharging", capacity=50, energy_now=25000000, energy_full=50000000)
        self._create_battery("BAT1", status="Discharging", capacity=90, energy_now=45000000, energy_full=50000000)
        self._create_ac_adapter("AC", online=0)

        reader = battery_passthrough.BatteryTelemetryReader(sysfs_root=self.sysfs_root)
        snapshot = reader.get_full_power_snapshot()

        self.assertTrue(snapshot["battery_present"])
        # Aggregated: (25M + 45M) / (50M + 50M) = 70.0%
        self.assertEqual(snapshot["capacity_percent"], 70.0)
        self.assertEqual(snapshot["status"], "Discharging")
        self.assertEqual(len(snapshot["battery_details"]["batteries"]), 2)

    def test_desktop_no_battery_environment(self) -> None:
        # No battery created, AC adapter online
        self._create_ac_adapter("AC", online=1)

        reader = battery_passthrough.BatteryTelemetryReader(sysfs_root=self.sysfs_root)
        snapshot = reader.get_full_power_snapshot()

        self.assertTrue(snapshot["ac_online"])
        self.assertFalse(snapshot["battery_present"])
        self.assertEqual(snapshot["capacity_percent"], 100.0)

    def test_daemon_single_iteration_loop(self) -> None:
        self._create_battery("BAT0", status="Full", capacity=100)
        daemon = battery_passthrough.BatteryPassthroughDaemon(
            sysfs_root=self.sysfs_root,
            domain="test-vm",
            dry_run=True,
        )
        # Should execute 1 cycle and terminate cleanly
        daemon.run_daemon(max_iterations=1)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestBatteryPassthrough)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
