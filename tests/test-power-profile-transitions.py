#!/usr/bin/env python3
# AI-hint: Automated unit test suite for MiOS power supply detector and inference downscaler (T-573 / T-574).
# AI-related: usr/libexec/mios/hw/powerd.py, usr/lib/systemd/system/mios-powerd.service
"""Automated tests for MiOS Power Profile Transitions & Inference Downscaler (T-573 / T-574)."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_MODULE_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "hw", "powerd.py")

spec = importlib.util.spec_from_file_location("powerd", _MODULE_PATH)
if spec and spec.loader:
    powerd = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = powerd
    spec.loader.exec_module(powerd)
else:
    raise ImportError(f"Could not load powerd module from {_MODULE_PATH}")


class TestPowerProfileTransitions(unittest.TestCase):
    """Validates AC/DC power supply telemetry, CPU EPP scaling, model switching, and CLI contracts."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp(prefix="mios_test_powerd_")
        self.sysfs_root = self.tmp_dir
        self.state_file = os.path.join(self.tmp_dir, "powerd_state.json")

        # Setup synthetic sysfs power_supply hierarchy
        self.power_supply_dir = os.path.join(self.sysfs_root, "sys", "class", "power_supply")
        self.ac_dir = os.path.join(self.power_supply_dir, "ACAD")
        self.bat_dir = os.path.join(self.power_supply_dir, "BAT0")
        os.makedirs(self.ac_dir, exist_ok=True)
        os.makedirs(self.bat_dir, exist_ok=True)

        with open(os.path.join(self.ac_dir, "type"), "w", encoding="utf-8") as f:
            f.write("Mains\n")
        with open(os.path.join(self.ac_dir, "online"), "w", encoding="utf-8") as f:
            f.write("1\n")

        with open(os.path.join(self.bat_dir, "type"), "w", encoding="utf-8") as f:
            f.write("Battery\n")
        with open(os.path.join(self.bat_dir, "capacity"), "w", encoding="utf-8") as f:
            f.write("85\n")
        with open(os.path.join(self.bat_dir, "status"), "w", encoding="utf-8") as f:
            f.write("Charging\n")

        # Setup synthetic sysfs CPU hierarchy (cpu0..cpu3)
        self.cpu_base = os.path.join(self.sysfs_root, "sys", "devices", "system", "cpu")
        for i in range(4):
            cpufreq_dir = os.path.join(self.cpu_base, f"cpu{i}", "cpufreq")
            power_dir = os.path.join(self.cpu_base, f"cpu{i}", "power")
            os.makedirs(cpufreq_dir, exist_ok=True)
            os.makedirs(power_dir, exist_ok=True)

            with open(os.path.join(cpufreq_dir, "scaling_governor"), "w", encoding="utf-8") as f:
                f.write("performance\n")
            with open(os.path.join(cpufreq_dir, "energy_performance_preference"), "w", encoding="utf-8") as f:
                f.write("balance_performance\n")
            with open(os.path.join(power_dir, "energy_performance_preference"), "w", encoding="utf-8") as f:
                f.write("balance_performance\n")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_initial_state_ac(self) -> None:
        daemon = powerd.PowerDaemon(
            sysfs_root=self.sysfs_root,
            state_file=self.state_file,
            mock=True,
        )
        state = daemon.get_status()
        self.assertEqual(state.power_source, "AC")
        self.assertEqual(state.cpu_epp, "balance_performance")
        self.assertEqual(state.active_model_tier, "heavy")
        self.assertEqual(state.governor, "performance")
        self.assertEqual(state.paused_containers, [])
        self.assertTrue(state.ac_online)
        self.assertEqual(state.gpu_power_state, "high")

    def test_ac_to_dc_transition(self) -> None:
        daemon = powerd.PowerDaemon(
            sysfs_root=self.sysfs_root,
            state_file=self.state_file,
            mock=True,
        )
        # Apply DC transition
        state = daemon.apply_profile("DC")
        self.assertEqual(state.power_source, "BATTERY")
        self.assertEqual(state.cpu_epp, "power")
        self.assertEqual(state.governor, "powersave")
        self.assertEqual(state.active_model_tier, "light_3b")
        self.assertEqual(state.gpu_power_state, "low")
        self.assertFalse(state.ac_online)
        self.assertIn("mios-finetune", state.paused_containers)
        self.assertIn("mios-embed-backfill", state.paused_containers)

    def test_dc_to_ac_restoration(self) -> None:
        daemon = powerd.PowerDaemon(
            sysfs_root=self.sysfs_root,
            state_file=self.state_file,
            mock=True,
        )
        # Transition to DC first
        daemon.apply_profile("DC")
        self.assertEqual(daemon.state.power_source, "BATTERY")

        # Transition back to AC
        state = daemon.apply_profile("AC")
        self.assertEqual(state.power_source, "AC")
        self.assertEqual(state.cpu_epp, "balance_performance")
        self.assertEqual(state.governor, "performance")
        self.assertEqual(state.active_model_tier, "heavy")
        self.assertEqual(state.gpu_power_state, "high")
        self.assertTrue(state.ac_online)
        self.assertEqual(state.paused_containers, [])

    def test_sysfs_telemetry_reading(self) -> None:
        daemon = powerd.PowerDaemon(
            sysfs_root=self.sysfs_root,
            state_file=self.state_file,
            mock=False,
        )
        # Read initial AC telemetry
        telemetry = daemon.read_telemetry()
        self.assertTrue(telemetry["ac_online"])
        self.assertEqual(telemetry["power_source"], "AC")
        self.assertEqual(telemetry["battery_pct"], 85)
        self.assertEqual(telemetry["battery_status"], "Charging")

        # Simulate unplugging AC adapter
        with open(os.path.join(self.ac_dir, "online"), "w", encoding="utf-8") as f:
            f.write("0\n")
        with open(os.path.join(self.bat_dir, "status"), "w", encoding="utf-8") as f:
            f.write("Discharging\n")
        with open(os.path.join(self.bat_dir, "capacity"), "w", encoding="utf-8") as f:
            f.write("72\n")

        telemetry_dc = daemon.read_telemetry()
        self.assertFalse(telemetry_dc["ac_online"])
        self.assertEqual(telemetry_dc["power_source"], "BATTERY")
        self.assertEqual(telemetry_dc["battery_pct"], 72)
        self.assertEqual(telemetry_dc["battery_status"], "Discharging")

    def test_multi_battery_average_capacity(self) -> None:
        # Create second battery BAT1
        bat1_dir = os.path.join(self.power_supply_dir, "BAT1")
        os.makedirs(bat1_dir, exist_ok=True)
        with open(os.path.join(bat1_dir, "type"), "w", encoding="utf-8") as f:
            f.write("Battery\n")
        with open(os.path.join(bat1_dir, "capacity"), "w", encoding="utf-8") as f:
            f.write("55\n")
        with open(os.path.join(bat1_dir, "status"), "w", encoding="utf-8") as f:
            f.write("Discharging\n")

        with open(os.path.join(self.bat_dir, "capacity"), "w", encoding="utf-8") as f:
            f.write("65\n")

        daemon = powerd.PowerDaemon(
            sysfs_root=self.sysfs_root,
            state_file=self.state_file,
            mock=False,
        )
        telemetry = daemon.read_telemetry()
        # Average of 65 and 55 = 60
        self.assertEqual(telemetry["battery_pct"], 60)

    def test_desktop_no_battery_fallback(self) -> None:
        # Remove all power supply devices (simulate desktop workstation / VM without batteries)
        empty_tmp = tempfile.mkdtemp(prefix="mios_empty_ps_")
        try:
            os.makedirs(os.path.join(empty_tmp, "sys", "class", "power_supply"), exist_ok=True)
            daemon = powerd.PowerDaemon(
                sysfs_root=empty_tmp,
                state_file=os.path.join(empty_tmp, "state.json"),
                mock=False,
            )
            telemetry = daemon.read_telemetry()
            self.assertTrue(telemetry["ac_online"])
            self.assertEqual(telemetry["power_source"], "AC")
            self.assertEqual(telemetry["battery_pct"], 100)
            self.assertEqual(telemetry["battery_status"], "Full")
        finally:
            shutil.rmtree(empty_tmp, ignore_errors=True)

    def test_sysfs_cpu_epp_and_governor_writing(self) -> None:
        daemon = powerd.PowerDaemon(
            sysfs_root=self.sysfs_root,
            state_file=self.state_file,
            mock=False,
        )
        # Transition to DC on synthetic sysfs
        daemon.apply_profile("DC")
        for i in range(4):
            epp_file = os.path.join(self.cpu_base, f"cpu{i}", "cpufreq", "energy_performance_preference")
            with open(epp_file, "r", encoding="utf-8") as f:
                self.assertEqual(f.read().strip(), "power")
            gov_file = os.path.join(self.cpu_base, f"cpu{i}", "cpufreq", "scaling_governor")
            with open(gov_file, "r", encoding="utf-8") as f:
                self.assertEqual(f.read().strip(), "powersave")

        # Transition to AC on synthetic sysfs
        daemon.apply_profile("AC")
        for i in range(4):
            epp_file = os.path.join(self.cpu_base, f"cpu{i}", "cpufreq", "energy_performance_preference")
            with open(epp_file, "r", encoding="utf-8") as f:
                self.assertEqual(f.read().strip(), "balance_performance")
            gov_file = os.path.join(self.cpu_base, f"cpu{i}", "cpufreq", "scaling_governor")
            with open(gov_file, "r", encoding="utf-8") as f:
                self.assertEqual(f.read().strip(), "performance")

    def test_state_persistence_and_reloading(self) -> None:
        daemon1 = powerd.PowerDaemon(
            sysfs_root=self.sysfs_root,
            state_file=self.state_file,
            mock=False,
        )
        daemon1.apply_profile("DC")
        self.assertTrue(os.path.isfile(self.state_file))

        # Create new daemon instance loading state from disk
        daemon2 = powerd.PowerDaemon(
            sysfs_root=self.sysfs_root,
            state_file=self.state_file,
            mock=False,
        )
        self.assertEqual(daemon2.state.power_source, "BATTERY")
        self.assertEqual(daemon2.state.cpu_epp, "power")
        self.assertEqual(daemon2.state.active_model_tier, "light_3b")
        self.assertIn("mios-finetune", daemon2.state.paused_containers)

    def test_poll_and_sync_trigger(self) -> None:
        daemon = powerd.PowerDaemon(
            sysfs_root=self.sysfs_root,
            state_file=self.state_file,
            mock=False,
        )
        # Verify initial AC state
        self.assertEqual(daemon.state.power_source, "AC")

        # Simulate AC disconnect in sysfs
        with open(os.path.join(self.ac_dir, "online"), "w", encoding="utf-8") as f:
            f.write("0\n")
        with open(os.path.join(self.bat_dir, "status"), "w", encoding="utf-8") as f:
            f.write("Discharging\n")

        # Polling detects change and triggers DC downscale
        synced_state = daemon.poll_and_sync()
        self.assertEqual(synced_state.power_source, "BATTERY")
        self.assertEqual(synced_state.cpu_epp, "power")
        self.assertEqual(synced_state.active_model_tier, "light_3b")

        # Simulate AC reconnect in sysfs
        with open(os.path.join(self.ac_dir, "online"), "w", encoding="utf-8") as f:
            f.write("1\n")
        with open(os.path.join(self.bat_dir, "status"), "w", encoding="utf-8") as f:
            f.write("Charging\n")

        synced_state_ac = daemon.poll_and_sync()
        self.assertEqual(synced_state_ac.power_source, "AC")
        self.assertEqual(synced_state_ac.cpu_epp, "balance_performance")
        self.assertEqual(synced_state_ac.active_model_tier, "heavy")

    def test_cli_status_json_contract(self) -> None:
        cmd = [
            sys.executable,
            _MODULE_PATH,
            "--mock",
            "--status",
            "--json",
            "--state-file",
            self.state_file,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(res.returncode, 0, f"CLI execution failed: {res.stderr}")
        data = json.loads(res.stdout)

        # Check strict contract fields from PROJECT.md
        self.assertIn("power_source", data)
        self.assertIn("cpu_epp", data)
        self.assertIn("active_model_tier", data)
        self.assertIn("paused_containers", data)
        self.assertIn(data["power_source"], ["AC", "BATTERY"])
        self.assertIn(data["cpu_epp"], ["balance_performance", "power"])
        self.assertIn(data["active_model_tier"], ["heavy", "light_3b"])
        self.assertIsInstance(data["paused_containers"], list)

    def test_cli_set_state_transitions(self) -> None:
        # Test set-state dc
        cmd_dc = [
            sys.executable,
            _MODULE_PATH,
            "--mock",
            "--set-state",
            "dc",
            "--json",
            "--state-file",
            self.state_file,
        ]
        res_dc = subprocess.run(cmd_dc, capture_output=True, text=True, timeout=10)
        self.assertEqual(res_dc.returncode, 0, f"CLI set-state dc failed: {res_dc.stderr}")
        data_dc = json.loads(res_dc.stdout)
        self.assertEqual(data_dc["power_source"], "BATTERY")
        self.assertEqual(data_dc["cpu_epp"], "power")
        self.assertEqual(data_dc["active_model_tier"], "light_3b")
        self.assertIn("mios-finetune", data_dc["paused_containers"])

        # Test set-state ac
        cmd_ac = [
            sys.executable,
            _MODULE_PATH,
            "--mock",
            "--set-state",
            "ac",
            "--json",
            "--state-file",
            self.state_file,
        ]
        res_ac = subprocess.run(cmd_ac, capture_output=True, text=True, timeout=10)
        self.assertEqual(res_ac.returncode, 0, f"CLI set-state ac failed: {res_ac.stderr}")
        data_ac = json.loads(res_ac.stdout)
        self.assertEqual(data_ac["power_source"], "AC")
        self.assertEqual(data_ac["cpu_epp"], "balance_performance")
        self.assertEqual(data_ac["active_model_tier"], "heavy")
        self.assertEqual(data_ac["paused_containers"], [])


if __name__ == "__main__":
    unittest.main()
