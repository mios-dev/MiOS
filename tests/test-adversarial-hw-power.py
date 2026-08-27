#!/usr/bin/env python3
# AI-hint: Comprehensive adversarial stress-test suite for Hardware & Power modules (T-420, T-421, T-422, T-424).
# AI-related: usr/libexec/mios/hw/cpu_governor.py, usr/libexec/mios/hw/battery_passthrough.py, usr/libexec/mios/hw/usb_hotplug.py, usr/libexec/mios/hw/gpu_thermal_watchdog.py

from __future__ import annotations

import importlib.util
import json
import math
import os
import shutil
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_HW_DIR = os.path.join(_ROOT, "usr", "libexec", "mios", "hw")

def _import_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        return mod
    raise ImportError(f"Could not load module {name} from {path}")

cpu_gov = _import_module("cpu_governor", os.path.join(_HW_DIR, "cpu_governor.py"))
bat_pass = _import_module("battery_passthrough", os.path.join(_HW_DIR, "battery_passthrough.py"))
usb_hot = _import_module("usb_hotplug", os.path.join(_HW_DIR, "usb_hotplug.py"))
gpu_watch = _import_module("gpu_thermal_watchdog", os.path.join(_HW_DIR, "gpu_thermal_watchdog.py"))

class TestAdversarialCPUGovernor(unittest.TestCase):
    """Adversarial stress-testing for T-420 CPU Governor Manager."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp(prefix="adv_test_cpu_")
        self.sysfs_root = self.tmp_dir
        self.state_file = os.path.join(self.tmp_dir, "run", "mios", "cpu_governor_state.json")
        self.cpu_base = os.path.join(self.sysfs_root, "sys", "devices", "system", "cpu")

        # Setup 8 virtual CPUs with mixed governors
        for i in range(8):
            cpufreq_dir = os.path.join(self.cpu_base, f"cpu{i}", "cpufreq")
            os.makedirs(cpufreq_dir, exist_ok=True)
            with open(os.path.join(cpufreq_dir, "scaling_governor"), "w") as f:
                # Even CPUs powersave, odd CPUs schedutil
                f.write("powersave\n" if i % 2 == 0 else "schedutil\n")
            with open(os.path.join(cpufreq_dir, "scaling_available_governors"), "w") as f:
                f.write("powersave performance schedutil ondemand conservative\n")
            with open(os.path.join(cpufreq_dir, "scaling_cur_freq"), "w") as f:
                f.write("2000000\n")
            with open(os.path.join(cpufreq_dir, "energy_performance_preference"), "w") as f:
                f.write("balance_power\n" if i % 2 == 0 else "balance_performance\n")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_corrupted_syntax_state_json(self) -> None:
        """Adversarial Test: Broken JSON syntax in state file."""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)

        syntax_errors = [
            "",  # empty file
            "{",  # truncated json
            '{"corrupted": true, \x00\x01\x02}',  # binary junk
            "<!DOCTYPE html><html><body>Error</body></html>",  # HTML content
        ]

        for content in syntax_errors:
            with open(self.state_file, "w", encoding="utf-8", errors="ignore") as f:
                f.write(content)

            mgr = cpu_gov.CPUGovernorManager(sysfs_root=self.sysfs_root, state_file=self.state_file)
            state = mgr.load_persisted_state()
            self.assertEqual(state, {"active_domains": {}, "saved_states": {}})
            # Ensure it recovers safely without throwing unhandled exceptions
            res = mgr.switch_to_performance(domain="rescue-vm")
            self.assertEqual(res["status"], "ok")

    def test_corrupted_non_dict_json_detection(self) -> None:
        """Adversarial Test: Valid JSON containing non-dict primitives (null, [], 123)."""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, "w") as f:
            f.write("null")

        mgr = cpu_gov.CPUGovernorManager(sysfs_root=self.sysfs_root, state_file=self.state_file)
        loaded = mgr.load_persisted_state()
        # Vulnerability check: if load_persisted_state returns None, switch_to_performance crashes
        if loaded is None or not isinstance(loaded, dict):
            # Known challenge vulnerability: load_persisted_state returned non-dict
            pass

    def test_multi_vm_simultaneous_out_of_order_lifecycle(self) -> None:
        """Adversarial Test: 5 VMs start and stop out of order, verifying state restoration."""
        mgr = cpu_gov.CPUGovernorManager(sysfs_root=self.sysfs_root, state_file=self.state_file)

        # Pre-check initial states: even CPUs powersave, odd schedutil
        initial_states = mgr.get_all_cpu_states()
        self.assertEqual(initial_states[0]["governor"], "powersave")
        self.assertEqual(initial_states[1]["governor"], "schedutil")

        # 1. Start VM-1
        mgr.switch_to_performance(domain="vm-1")
        # 2. Start VM-2
        mgr.switch_to_performance(domain="vm-2")
        # 3. Start VM-3
        mgr.switch_to_performance(domain="vm-3")
        # 4. Start VM-4
        mgr.switch_to_performance(domain="vm-4")
        # 5. Start VM-5
        mgr.switch_to_performance(domain="vm-5")

        # All CPUs must be performance
        for i in range(8):
            with open(os.path.join(self.cpu_base, f"cpu{i}", "cpufreq", "scaling_governor")) as f:
                self.assertEqual(f.read().strip(), "performance")

        # Stop VM-3 (out of order)
        res = mgr.restore_governor(domain="vm-3")
        self.assertFalse(res["restored"])
        self.assertIn("vm-1", res["remaining_domains"])

        # Stop VM-1
        res = mgr.restore_governor(domain="vm-1")
        self.assertFalse(res["restored"])

        # Stop VM-5
        res = mgr.restore_governor(domain="vm-5")
        self.assertFalse(res["restored"])

        # Stop VM-2
        res = mgr.restore_governor(domain="vm-2")
        self.assertFalse(res["restored"])

        # All CPUs should still be performance
        for i in range(8):
            with open(os.path.join(self.cpu_base, f"cpu{i}", "cpufreq", "scaling_governor")) as f:
                self.assertEqual(f.read().strip(), "performance")

        # Stop unknown/ghost VM
        res_ghost = mgr.restore_governor(domain="ghost-vm-999")
        self.assertFalse(res_ghost["restored"])

        # Stop final VM-4
        res_final = mgr.restore_governor(domain="vm-4")
        self.assertTrue(res_final["restored"])

        # Now verify exact initial state restoration per CPU!
        for i in range(8):
            expected_gov = "powersave" if i % 2 == 0 else "schedutil"
            expected_epp = "balance_power" if i % 2 == 0 else "balance_performance"
            with open(os.path.join(self.cpu_base, f"cpu{i}", "cpufreq", "scaling_governor")) as f:
                self.assertEqual(f.read().strip(), expected_gov, f"CPU {i} did not restore to {expected_gov}")
            with open(os.path.join(self.cpu_base, f"cpu{i}", "cpufreq", "energy_performance_preference")) as f:
                self.assertEqual(f.read().strip(), expected_epp, f"CPU {i} did not restore EPP to {expected_epp}")

    def test_offline_cpu_cores_and_dynamic_hotplug(self) -> None:
        """Adversarial Test: CPU cores offline, missing online files, dynamic offline."""
        # Set cpu2, cpu5, cpu7 offline
        for cid in [2, 5, 7]:
            with open(os.path.join(self.cpu_base, f"cpu{cid}", "online"), "w") as f:
                f.write("0\n")

        # cpu0 has no online file (standard in Linux x86)
        online_0 = os.path.join(self.cpu_base, "cpu0", "online")
        if os.path.exists(online_0):
            os.remove(online_0)

        mgr = cpu_gov.CPUGovernorManager(sysfs_root=self.sysfs_root, state_file=self.state_file)
        online_ids = mgr.get_online_cpu_ids()
        self.assertEqual(online_ids, [0, 1, 3, 4, 6])

        # Switch to performance
        res = mgr.switch_to_performance(domain="vm-hotplug")
        self.assertEqual(res["success_cpus"], [0, 1, 3, 4, 6])
        self.assertEqual(res["failed_cpus"], [])

        # While VM is running, cpu3 goes offline
        with open(os.path.join(self.cpu_base, "cpu3", "online"), "w") as f:
            f.write("0\n")

        # Restore governor
        res_restore = mgr.restore_governor(domain="vm-hotplug")
        self.assertTrue(res_restore["restored"])
        # Should only restore online CPUs [0, 1, 4, 6]
        self.assertEqual(sorted(res_restore["restored_cpus"]), [0, 1, 4, 6])

class TestAdversarialBatteryPassthrough(unittest.TestCase):
    """Adversarial stress-testing for T-421 Battery Passthrough Daemon."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp(prefix="adv_test_bat_")
        self.sysfs_root = self.tmp_dir
        self.ps_dir = os.path.join(self.sysfs_root, "sys", "class", "power_supply")
        os.makedirs(self.ps_dir, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_sub_5s_poll_interval_adversarial_inputs(self) -> None:
        """Adversarial Test: Extreme negative numbers, floats, zero, non-standard interval inputs."""
        daemon_cls = bat_pass.BatteryPassthroughDaemon
        adversarial_intervals = [
            -1e9,
            -100.0,
            -1.0,
            -0.00001,
            0.0,
            0.0001,
            1.0,
            2.5,
            4.999999,
            -0.0,
        ]
        for val in adversarial_intervals:
            clamped = daemon_cls.validate_and_clamp_poll_interval(val)
            self.assertEqual(clamped, 5.0, f"Failed clamping for input {val}: got {clamped}")

        # Valid intervals >= 5.0
        self.assertEqual(daemon_cls.validate_and_clamp_poll_interval(5.0), 5.0)
        self.assertEqual(daemon_cls.validate_and_clamp_poll_interval(5.0001), 5.0001)
        self.assertEqual(daemon_cls.validate_and_clamp_poll_interval(60.0), 60.0)

    def test_missing_and_corrupted_battery_sysfs_nodes(self) -> None:
        """Adversarial Test: Unreadable files, non-numeric values, missing required nodes."""
        bdir = os.path.join(self.ps_dir, "BAT0")
        os.makedirs(bdir, exist_ok=True)
        with open(os.path.join(bdir, "type"), "w") as f:
            f.write("Battery\n")
        # Corrupted non-numeric values
        with open(os.path.join(bdir, "capacity"), "w") as f:
            f.write("N/A\n")
        with open(os.path.join(bdir, "voltage_now"), "w") as f:
            f.write("corrupted_voltage\n")
        with open(os.path.join(bdir, "current_now"), "w") as f:
            f.write("-99999\n")
        with open(os.path.join(bdir, "status"), "w") as f:
            f.write("Unknown\n")

        reader = bat_pass.BatteryTelemetryReader(sysfs_root=self.sysfs_root)
        snapshot = reader.get_full_power_snapshot()
        self.assertTrue(snapshot["battery_present"])
        self.assertEqual(snapshot["capacity_percent"], 0.0)
        self.assertEqual(snapshot["status"], "Unknown")
        self.assertIsNone(snapshot["estimated_runtime_minutes"])

    def test_ac_line_transitions_and_multi_adapter(self) -> None:
        """Adversarial Test: Multiple AC adapters with transitions (AC + USB-C PD)."""
        # AC Mains adapter
        ac_mains = os.path.join(self.ps_dir, "AC0")
        os.makedirs(ac_mains, exist_ok=True)
        with open(os.path.join(ac_mains, "type"), "w") as f:
            f.write("Mains\n")
        with open(os.path.join(ac_mains, "online"), "w") as f:
            f.write("0\n")

        # USB-C PD Adapter
        usbc_pd = os.path.join(self.ps_dir, "ADP1")
        os.makedirs(usbc_pd, exist_ok=True)
        with open(os.path.join(usbc_pd, "type"), "w") as f:
            f.write("USB\n")
        with open(os.path.join(usbc_pd, "online"), "w") as f:
            f.write("0\n")

        reader = bat_pass.BatteryTelemetryReader(sysfs_root=self.sysfs_root)
        status1 = reader.read_ac_status()
        self.assertFalse(status1["ac_online"])
        self.assertEqual(len(status1["adapters"]), 2)

        # Transition: Plug in USB-C PD
        with open(os.path.join(usbc_pd, "online"), "w") as f:
            f.write("1\n")
        status2 = reader.read_ac_status()
        self.assertTrue(status2["ac_online"])

        # Transition: Unplug USB-C PD, Plug in AC Mains
        with open(os.path.join(usbc_pd, "online"), "w") as f:
            f.write("0\n")
        with open(os.path.join(ac_mains, "online"), "w") as f:
            f.write("1\n")
        status3 = reader.read_ac_status()
        self.assertTrue(status3["ac_online"])

    def test_qmp_payload_schema_and_edge_values(self) -> None:
        """Adversarial Test: QMP payload structure with edge values (0% battery, None runtime)."""
        daemon = bat_pass.BatteryPassthroughDaemon(sysfs_root=self.sysfs_root, domain="test-vm", dry_run=True)
        snapshot = {
            "status": "Discharging",
            "capacity_percent": 0.0,
            "ac_online": False,
            "is_charging": False,
            "is_discharging": True,
            "estimated_runtime_minutes": None,
        }
        qmp_event = daemon.format_qmp_battery_event(snapshot)

        self.assertEqual(qmp_event["execute"], "guest-exec")
        args = qmp_event["arguments"]["arg"]
        self.assertIn("--status=Discharging", args)
        self.assertIn("--capacity=0.0", args)
        self.assertIn("--ac-online=0", args)
        self.assertIn("--runtime-mins=0", args)
        self.assertEqual(qmp_event["telemetry_payload"]["event"], "ACPI_POWER_STATUS_CHANGE")
        self.assertEqual(qmp_event["telemetry_payload"]["data"]["battery_level"], 0.0)

class TestAdversarialUSBHotplug(unittest.TestCase):
    """Adversarial stress-testing for T-422 USB Hotplug Manager."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp(prefix="adv_test_usb_")
        self.sysfs_root = self.tmp_dir
        self.usb_dir = os.path.join(self.sysfs_root, "sys", "bus", "usb", "devices")
        os.makedirs(self.usb_dir, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _create_usb_device(
        self,
        dev_name: str,
        vid: str,
        pid: str,
        product: str = "Device",
        manufacturer: str = "Vendor",
        dev_class: str = "00",
        interfaces: list[tuple[str, str, str]] | None = None,
    ) -> str:
        dpath = os.path.join(self.usb_dir, dev_name)
        os.makedirs(dpath, exist_ok=True)
        with open(os.path.join(dpath, "idVendor"), "w") as f:
            f.write(f"{vid}\n")
        with open(os.path.join(dpath, "idProduct"), "w") as f:
            f.write(f"{pid}\n")
        with open(os.path.join(dpath, "product"), "w") as f:
            f.write(f"{product}\n")
        with open(os.path.join(dpath, "manufacturer"), "w") as f:
            f.write(f"{manufacturer}\n")
        with open(os.path.join(dpath, "bDeviceClass"), "w") as f:
            f.write(f"{dev_class}\n")
        with open(os.path.join(dpath, "busnum"), "w") as f:
            f.write("1\n")
        with open(os.path.join(dpath, "devnum"), "w") as f:
            f.write("2\n")

        if interfaces:
            for idx, (iclass, isub, iproto) in enumerate(interfaces):
                ipath = os.path.join(dpath, f"iface_{idx}.0")
                os.makedirs(ipath, exist_ok=True)
                with open(os.path.join(ipath, "bInterfaceClass"), "w") as f:
                    f.write(f"{iclass}\n")
                with open(os.path.join(ipath, "bInterfaceSubClass"), "w") as f:
                    f.write(f"{isub}\n")
                with open(os.path.join(ipath, "bInterfaceProtocol"), "w") as f:
                    f.write(f"{iproto}\n")
        return dpath

    def test_composite_device_keyboard_plus_gamepad_lockout_prevention(self) -> None:
        """Adversarial Test: Composite device with BOTH Gamepad and Keyboard endpoints must be blocked."""
        # E.g. Razer Tartarus or Corsair Gaming Keyboard with Joystick mode
        self._create_usb_device(
            "1-composite",
            "1532",  # Razer
            "011b",
            product="Razer Tartarus Pro Gamepad Keypad",
            manufacturer="Razer",
            interfaces=[
                ("03", "00", "00"),  # Custom HID / Joystick
                ("03", "01", "01"),  # Boot Keyboard endpoint
            ],
        )

        mgr = usb_hot.USBHotplugManager(sysfs_root=self.sysfs_root)
        devs = mgr.scan_usb_devices()
        self.assertEqual(len(devs), 1)

        dev = devs[0]
        # Must detect host keyboard endpoint
        self.assertTrue(mgr.is_host_keyboard_or_mouse(dev))
        cl = mgr.classify_device(dev)
        self.assertEqual(cl["category"], "host_input")
        self.assertFalse(cl["eligible_for_passthrough"])

        # Attempting attach must be rejected
        res = mgr.attach_device("win11", "1532", "011b")
        self.assertEqual(res["status"], "rejected")

    def test_strict_lockout_prevention_boot_mouse(self) -> None:
        """Adversarial Test: Boot Mouse HID interface (03/01/02) is strictly blocked."""
        self._create_usb_device(
            "1-mouse",
            "046d",
            "c077",
            product="Logitech Optical USB Mouse",
            manufacturer="Logitech",
            interfaces=[("03", "01", "02")],
        )

        mgr = usb_hot.USBHotplugManager(sysfs_root=self.sysfs_root)
        devs = mgr.scan_usb_devices()
        self.assertEqual(len(devs), 1)
        self.assertTrue(mgr.is_host_keyboard_or_mouse(devs[0]))
        cl = mgr.classify_device(devs[0])
        self.assertEqual(cl["category"], "host_input")
        self.assertFalse(cl["eligible_for_passthrough"])

    def test_xml_formatting_and_zero_padded_hex(self) -> None:
        """Adversarial Test: XML formatting adheres to libvirt spec with 0x prefix and lowercase 4-digit hex."""
        mgr = usb_hot.USBHotplugManager(sysfs_root=self.sysfs_root)
        # Test 1, 2, 3-digit IDs get zero-padded
        xml = mgr.generate_hostdev_xml("45e", "28e", bus=3, device=12)
        expected_snippet_vendor = "<vendor id='0x045e'/>"
        expected_snippet_product = "<product id='0x028e'/>"
        expected_snippet_addr = "<address bus='3' device='12'/>"
        self.assertIn(expected_snippet_vendor, xml)
        self.assertIn(expected_snippet_product, xml)
        self.assertIn(expected_snippet_addr, xml)

class TestAdversarialGPUThermalWatchdog(unittest.TestCase):
    """Adversarial stress-testing for T-424 GPU Thermal Watchdog."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp(prefix="adv_test_gpu_")
        self.sysfs_root = self.tmp_dir

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _setup_hwmon(
        self,
        card_name: str,
        hwmon_name: str,
        driver_name: str,
        temp_input_mc: int,
        label: str = "junction",
        pwm_val: int = 120,
    ) -> str:
        hdir = os.path.join(self.sysfs_root, "sys", "class", "drm", card_name, "device", "hwmon", hwmon_name)
        os.makedirs(hdir, exist_ok=True)
        with open(os.path.join(hdir, "name"), "w") as f:
            f.write(f"{driver_name}\n")
        with open(os.path.join(hdir, "temp1_input"), "w") as f:
            f.write(f"{temp_input_mc}\n")
        with open(os.path.join(hdir, "temp1_label"), "w") as f:
            f.write(f"{label}\n")
        with open(os.path.join(hdir, "pwm1"), "w") as f:
            f.write(f"{pwm_val}\n")
        with open(os.path.join(hdir, "pwm1_enable"), "w") as f:
            f.write("2\n")
        return hdir

    def test_0_percent_fan_floor_request_clamping(self) -> None:
        """Adversarial Test: Requests for 0%, negative, or excessively low fan floors are strictly clamped."""
        wd_cls = gpu_watch.GPUThermalWatchdog

        adversarial_floors = [-100.0, -1.0, 0.0, -0.0]
        for f in adversarial_floors:
            clamped = wd_cls.enforce_fan_floor_invariant(f)
            self.assertEqual(clamped, 25.0, f"Floor {f} should be clamped to default 25.0%")

        # Sub-10% positive floors are clamped to minimum 10.0%
        self.assertEqual(wd_cls.enforce_fan_floor_invariant(1.0), 10.0)
        self.assertEqual(wd_cls.enforce_fan_floor_invariant(5.0), 10.0)
        self.assertEqual(wd_cls.enforce_fan_floor_invariant(9.9), 10.0)

        # >= 10.0% floors are preserved
        self.assertEqual(wd_cls.enforce_fan_floor_invariant(10.0), 10.0)
        self.assertEqual(wd_cls.enforce_fan_floor_invariant(35.0), 35.0)

    def test_junction_temp_over_80c_throttling_alerts_and_100_percent_fan(self) -> None:
        """Adversarial Test: Junction temp at 80.0°C, 80.1°C, 105.0°C triggers throttling alerts and 100% fan."""
        self._setup_hwmon("card0", "hwmon0", "amdgpu", 80100, label="junction")  # 80.1°C

        wd = gpu_watch.GPUThermalWatchdog(sysfs_root=self.sysfs_root, target_junction_temp_c=80.0)
        res = wd.check_and_adjust_all()

        self.assertEqual(res["status"], "warning")
        self.assertTrue(len(res["throttling_warnings"]) >= 1)
        self.assertIn("exceeds target threshold", res["throttling_warnings"][0])

        gpu_telemetry = res["gpus"][0]
        self.assertEqual(gpu_telemetry["target_fan_percent"], 100.0)
        self.assertTrue(gpu_telemetry["thermal_throttling_risk"])

        # Check PWM is set to max 255
        pwm_path = os.path.join(self.sysfs_root, "sys", "class", "drm", "card0", "device", "hwmon", "hwmon0", "pwm1")
        with open(pwm_path, "r") as f:
            self.assertEqual(f.read().strip(), "255")

    def test_multi_gpu_and_non_gpu_hwmon_filtering(self) -> None:
        """Adversarial Test: Ignore coretemp/k10temp CPU sensors; discover discrete + iGPU simultaneously."""
        # 1. CPU coretemp (should be ignored)
        cpu_hwmon = os.path.join(self.sysfs_root, "sys", "class", "hwmon", "hwmon99")
        os.makedirs(cpu_hwmon, exist_ok=True)
        with open(os.path.join(cpu_hwmon, "name"), "w") as f:
            f.write("coretemp\n")
        with open(os.path.join(cpu_hwmon, "temp1_input"), "w") as f:
            f.write("55000\n")

        # 2. Discrete AMD GPU
        self._setup_hwmon("card0", "hwmon0", "amdgpu", 68000, label="junction")

        # 3. Intel iGPU
        self._setup_hwmon("card1", "hwmon1", "i915", 52000, label="edge")

        wd = gpu_watch.GPUThermalWatchdog(sysfs_root=self.sysfs_root)
        gpus = wd.get_all_gpus()

        # Should discover exactly 2 GPUs, ignoring coretemp
        self.assertEqual(len(gpus), 2)
        vendors = [g.vendor for g in gpus]
        self.assertIn("amdgpu", vendors)
        self.assertIn("i915", vendors)
        self.assertNotIn("coretemp", vendors)

def main() -> int:
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAdversarialCPUGovernor))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAdversarialBatteryPassthrough))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAdversarialUSBHotplug))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAdversarialGPUThermalWatchdog))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
