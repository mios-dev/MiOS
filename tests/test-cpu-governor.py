#!/usr/bin/env python3
# AI-hint: Automated unit test suite for T-420 CPU governor manager and libvirt hook integration.
# AI-related: usr/libexec/mios/hw/cpu_governor.py, /etc/libvirt/hooks/qemu
"""Automated tests for MiOS CPU Governor Manager and Libvirt Hook Integration (T-420)."""

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
_MODULE_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "hw", "cpu_governor.py")

spec = importlib.util.spec_from_file_location("cpu_governor", _MODULE_PATH)
if spec and spec.loader:
    cpu_governor = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = cpu_governor
    spec.loader.exec_module(cpu_governor)
else:
    raise ImportError(f"Could not load cpu_governor module from {_MODULE_PATH}")


class TestCPUGovernor(unittest.TestCase):
    """Validates CPU governor discovery, switching, state persistence, and hook dispatch."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp(prefix="mios_test_cpu_")
        self.sysfs_root = self.tmp_dir
        self.state_file = os.path.join(self.tmp_dir, "cpu_governor_state.json")

        # Create synthetic sysfs CPU hierarchy for cpu0, cpu1, cpu2, cpu3
        self.cpu_base = os.path.join(self.sysfs_root, "sys", "devices", "system", "cpu")
        for i in range(4):
            cpufreq_dir = os.path.join(self.cpu_base, f"cpu{i}", "cpufreq")
            os.makedirs(cpufreq_dir, exist_ok=True)
            with open(os.path.join(cpufreq_dir, "scaling_governor"), "w") as f:
                f.write("powersave\n")
            with open(os.path.join(cpufreq_dir, "scaling_available_governors"), "w") as f:
                f.write("powersave performance schedutil ondemand\n")
            with open(os.path.join(cpufreq_dir, "scaling_cur_freq"), "w") as f:
                f.write("1800000\n")
            with open(os.path.join(cpufreq_dir, "scaling_min_freq"), "w") as f:
                f.write("800000\n")
            with open(os.path.join(cpufreq_dir, "scaling_max_freq"), "w") as f:
                f.write("4200000\n")
            with open(os.path.join(cpufreq_dir, "scaling_driver"), "w") as f:
                f.write("intel_pstate\n")
            with open(os.path.join(cpufreq_dir, "energy_performance_preference"), "w") as f:
                f.write("balance_power\n")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_cpu_discovery(self) -> None:
        mgr = cpu_governor.CPUGovernorManager(sysfs_root=self.sysfs_root, state_file=self.state_file)
        cpus = mgr.get_online_cpu_ids()
        self.assertEqual(cpus, [0, 1, 2, 3])

    def test_cpu_info_parsing(self) -> None:
        mgr = cpu_governor.CPUGovernorManager(sysfs_root=self.sysfs_root, state_file=self.state_file)
        info = mgr.get_cpu_info(0)
        self.assertEqual(info["cpu_id"], 0)
        self.assertEqual(info["governor"], "powersave")
        self.assertIn("performance", info["available_governors"])
        self.assertEqual(info["cur_freq_khz"], 1800000)
        self.assertEqual(info["driver"], "intel_pstate")
        self.assertEqual(info["epp"], "balance_power")

    def test_set_governor_performance(self) -> None:
        mgr = cpu_governor.CPUGovernorManager(sysfs_root=self.sysfs_root, state_file=self.state_file)
        res = mgr.set_governor(governor="performance", epp="performance")
        self.assertEqual(res["status"], "ok")
        self.assertEqual(len(res["success_cpus"]), 4)

        # Verify sysfs content updated
        for i in range(4):
            gov_file = os.path.join(self.cpu_base, f"cpu{i}", "cpufreq", "scaling_governor")
            with open(gov_file, "r") as f:
                self.assertEqual(f.read().strip(), "performance")
            epp_file = os.path.join(self.cpu_base, f"cpu{i}", "cpufreq", "energy_performance_preference")
            with open(epp_file, "r") as f:
                self.assertEqual(f.read().strip(), "performance")

    def test_vm_lifecycle_switch_and_restore(self) -> None:
        mgr = cpu_governor.CPUGovernorManager(sysfs_root=self.sysfs_root, state_file=self.state_file)

        # Step 1: Start VM 'win11' -> switch to performance
        switch_res = mgr.switch_to_performance(domain="win11", governor="performance")
        self.assertEqual(switch_res["domain"], "win11")
        self.assertEqual(switch_res["active_domains_count"], 1)

        # Check all CPUs are performance
        for i in range(4):
            gov_file = os.path.join(self.cpu_base, f"cpu{i}", "cpufreq", "scaling_governor")
            with open(gov_file, "r") as f:
                self.assertEqual(f.read().strip(), "performance")

        # Step 2: Start second VM 'fedora-dev'
        mgr.switch_to_performance(domain="fedora-dev", governor="performance")
        persisted = mgr.load_persisted_state()
        self.assertIn("win11", persisted["active_domains"])
        self.assertIn("fedora-dev", persisted["active_domains"])

        # Step 3: Stop 'win11' -> 'fedora-dev' still active, should remain performance
        res_stop1 = mgr.restore_governor(domain="win11")
        self.assertFalse(res_stop1["restored"])
        for i in range(4):
            gov_file = os.path.join(self.cpu_base, f"cpu{i}", "cpufreq", "scaling_governor")
            with open(gov_file, "r") as f:
                self.assertEqual(f.read().strip(), "performance")

        # Step 4: Stop 'fedora-dev' -> no VMs active, should restore powersave
        res_stop2 = mgr.restore_governor(domain="fedora-dev")
        self.assertTrue(res_stop2["restored"])
        for i in range(4):
            gov_file = os.path.join(self.cpu_base, f"cpu{i}", "cpufreq", "scaling_governor")
            with open(gov_file, "r") as f:
                self.assertEqual(f.read().strip(), "powersave")
            epp_file = os.path.join(self.cpu_base, f"cpu{i}", "cpufreq", "energy_performance_preference")
            with open(epp_file, "r") as f:
                self.assertEqual(f.read().strip(), "balance_power")

    def test_libvirt_hook_dispatch(self) -> None:
        mgr = cpu_governor.CPUGovernorManager(sysfs_root=self.sysfs_root, state_file=self.state_file)

        # Hook: prepare begin
        res_start = mgr.handle_libvirt_hook(domain="gaming-vm", phase="prepare", operation="begin")
        self.assertEqual(res_start["target_governor"], "performance")

        # Hook: release end
        res_stop = mgr.handle_libvirt_hook(domain="gaming-vm", phase="release", operation="end")
        self.assertTrue(res_stop["restored"])

        # Hook: unhandled phase
        res_ignored = mgr.handle_libvirt_hook(domain="gaming-vm", phase="migrate", operation="begin")
        self.assertEqual(res_ignored["status"], "ignored")

    def test_offline_cpu_handling(self) -> None:
        # Mark cpu3 as offline
        online_file = os.path.join(self.cpu_base, "cpu3", "online")
        with open(online_file, "w") as f:
            f.write("0\n")

        mgr = cpu_governor.CPUGovernorManager(sysfs_root=self.sysfs_root, state_file=self.state_file)
        cpus = mgr.get_online_cpu_ids()
        self.assertEqual(cpus, [0, 1, 2])

    def test_specific_cpu_ids_targeting(self) -> None:
        mgr = cpu_governor.CPUGovernorManager(sysfs_root=self.sysfs_root, state_file=self.state_file)
        res = mgr.set_governor("performance", cpu_ids=[1, 2])
        self.assertEqual(res["success_cpus"], [1, 2])

        # Verify cpu0 is still powersave, but cpu1 and cpu2 are performance
        gov0 = os.path.join(self.cpu_base, "cpu0", "cpufreq", "scaling_governor")
        with open(gov0, "r") as f:
            self.assertEqual(f.read().strip(), "powersave")
        gov1 = os.path.join(self.cpu_base, "cpu1", "cpufreq", "scaling_governor")
        with open(gov1, "r") as f:
            self.assertEqual(f.read().strip(), "performance")

    def test_corrupted_state_file_recovery(self) -> None:
        # Write corrupted JSON to state file
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, "w") as f:
            f.write("{corrupt json content!!")

        mgr = cpu_governor.CPUGovernorManager(sysfs_root=self.sysfs_root, state_file=self.state_file)
        state = mgr.load_persisted_state()
        self.assertEqual(state, {"active_domains": {}, "saved_states": {}})


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCPUGovernor)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
