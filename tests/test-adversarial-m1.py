#!/usr/bin/env python3
# AI-hint: Comprehensive adversarial stress tests for Milestone 1 Python components in mios-node.
# AI-related: usr/libexec/mios/node/hardware.py, usr/libexec/mios/node/cgroups.py, usr/libexec/mios/node/crdt.py, usr/libexec/mios/node/watchdog.py, usr/libexec/mios/node/wasm_sandbox.py

import json
import os
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE_LIB_DIR = os.path.join(REPO_ROOT, "usr", "libexec", "mios", "node")
sys.path.insert(0, NODE_LIB_DIR)

from cgroups import (
    AffinityPolicy,
    CgroupV2Controller,
    NodeResourceLimits,
    WorkerAffinityController,
    filter_safe_worker_cores,
)
from crdt import StateElement, StateStore, VectorClock
from hardware import (
    HardwareAllowlist,
    HardwareErrorCode,
    LinuxSysfsHardwareDriver,
    MockHardwareDriver,
    SandboxedHardwareController,
)
from wasm_sandbox import HostImports, WasmSandboxEngine
from watchdog import (
    LinuxHardwareWatchdog,
    MockWatchdogDriver,
    WatchdogConfig,
    WatchdogSupervisor,
)


class TestAdversarialHardware(unittest.TestCase):
    """Adversarial testing of Hardware HAL and SandboxedController."""

    def test_allowlist_pin_boundaries_and_read_only(self):
        allowlist = HardwareAllowlist(
            allowed_gpio_pins={17, 27},
            read_only_gpio_pins={27},
            allowed_i2c_buses={1},
            allowed_i2c_addresses={0x68},
            max_i2c_transfer_len=8,
        )
        mock = MockHardwareDriver()
        ctrl = SandboxedHardwareController(allowlist=allowlist, driver=mock)

        # 1. Unallowed Pins
        code, val = ctrl.mios_sys_gpio_read(0)
        self.assertEqual(code, HardwareErrorCode.PERMISSION_DENIED)
        self.assertEqual(ctrl.mios_sys_gpio_write(0, 1), HardwareErrorCode.PERMISSION_DENIED)

        code, val = ctrl.mios_sys_gpio_read(999999)
        self.assertEqual(code, HardwareErrorCode.PERMISSION_DENIED)
        self.assertEqual(ctrl.mios_sys_gpio_write(999999, 1), HardwareErrorCode.PERMISSION_DENIED)

        # 2. Read-Only Pin
        code, val = ctrl.mios_sys_gpio_read(27)
        self.assertEqual(code, HardwareErrorCode.SUCCESS)
        self.assertEqual(val, 0)
        self.assertEqual(ctrl.mios_sys_gpio_write(27, 1), HardwareErrorCode.READ_ONLY_PIN)

        # 3. Read/Write Pin
        self.assertEqual(ctrl.mios_sys_gpio_write(17, 1), HardwareErrorCode.SUCCESS)
        code, val = ctrl.mios_sys_gpio_read(17)
        self.assertEqual(code, HardwareErrorCode.SUCCESS)
        self.assertEqual(val, 1)

    def test_i2c_transfer_len_limits_and_wrapping(self):
        allowlist = HardwareAllowlist(
            allowed_i2c_buses={1},
            allowed_i2c_addresses={0x68},
            max_i2c_transfer_len=8,
        )
        mock = MockHardwareDriver()
        ctrl = SandboxedHardwareController(allowlist=allowlist, driver=mock)

        # Transfer len <= 8 is OK
        code, res = ctrl.mios_sys_i2c_transfer(1, 0x68, b"\x10\x01\x02", 4)
        self.assertEqual(code, HardwareErrorCode.SUCCESS)
        self.assertEqual(len(res), 4)

        # Write data > 8 bytes -> InvalidParameter
        code, res = ctrl.mios_sys_i2c_transfer(1, 0x68, b"\x00" * 9, 0)
        self.assertEqual(code, HardwareErrorCode.INVALID_PARAMETER)

        # Read len > 8 bytes -> InvalidParameter
        code, res = ctrl.mios_sys_i2c_transfer(1, 0x68, b"\x00", 9)
        self.assertEqual(code, HardwareErrorCode.INVALID_PARAMETER)

        # Disallowed bus / addr
        code, _ = ctrl.mios_sys_i2c_transfer(2, 0x68, b"\x00", 1)
        self.assertEqual(code, HardwareErrorCode.PERMISSION_DENIED)

        code, _ = ctrl.mios_sys_i2c_transfer(1, 0x55, b"\x00", 1)
        self.assertEqual(code, HardwareErrorCode.PERMISSION_DENIED)

        # Wrapping register address
        ctrl.mios_sys_i2c_transfer(1, 0x68, b"\xff\xaa\xbb\xcc", 0) # writes to 255, 0, 1
        code, wrap_read = ctrl.mios_sys_i2c_transfer(1, 0x68, b"\xff", 3)
        self.assertEqual(code, HardwareErrorCode.SUCCESS)
        self.assertEqual(wrap_read, b"\xaa\xbb\xcc")


class TestAdversarialCgroups(unittest.TestCase):
    """Adversarial testing of CPU Core Pinning and Cgroups."""

    def test_core_zero_exclusion_invariant_matrix(self):
        # 0 cores
        self.assertEqual(filter_safe_worker_cores(0, None, True), [])

        # 1 core
        self.assertEqual(filter_safe_worker_cores(1, None, True), [0])
        self.assertEqual(filter_safe_worker_cores(1, None, False), [0])

        # 2 cores
        self.assertEqual(filter_safe_worker_cores(2, None, True), [1])
        self.assertEqual(filter_safe_worker_cores(2, None, False), [0, 1])

        # 64 cores
        cores_64 = filter_safe_worker_cores(64, None, True)
        self.assertEqual(len(cores_64), 63)
        self.assertNotIn(0, cores_64)

        # Out-of-bounds requested cores
        req = [0, 1, 2, 999]
        self.assertEqual(filter_safe_worker_cores(4, req, True), [1, 2])

    def test_worker_affinity_allocation_exhaustion(self):
        limits = NodeResourceLimits(worker_cores=[1, 2, 3])
        controller = WorkerAffinityController(4, limits)
        self.assertEqual(controller.available_worker_cores, [1, 2, 3])

        # Allocate 2 cores
        c1 = controller.allocate_cores_for_policy(AffinityPolicy.EXCLUSIVE, 2)
        self.assertEqual(c1, [1, 2])

        # Allocate 1 core
        c2 = controller.allocate_cores_for_policy(AffinityPolicy.EXCLUSIVE, 1)
        self.assertEqual(c2, [3])

        # Exhausted -> throws RuntimeError
        with self.assertRaises(RuntimeError):
            controller.allocate_cores_for_policy(AffinityPolicy.EXCLUSIVE, 1)

        # Release core 2 and re-allocate
        controller.release_cores([2])
        c_re = controller.allocate_cores_for_policy(AffinityPolicy.EXCLUSIVE, 1)
        self.assertEqual(c_re, [2])

        # Low priority returns highest core
        self.assertEqual(
            controller.allocate_cores_for_policy(AffinityPolicy.LOW_PRIORITY, 0), [3]
        )

    def test_format_cpu_max_ratios(self):
        self.assertEqual(CgroupV2Controller.format_cpu_max(0, 100_000), "0 100000")
        self.assertEqual(CgroupV2Controller.format_cpu_max(80, 100_000), "80000 100000")
        self.assertEqual(CgroupV2Controller.format_cpu_max(250, 100_000), "250000 100000")
        self.assertEqual(CgroupV2Controller.format_cpu_max(None, 50_000), "max 50000")


class TestAdversarialCrdt(unittest.TestCase):
    """Adversarial testing of CRDT LWW-Element-Set and Tombstone Compaction."""

    def test_tombstone_gc_future_skew_and_exact_ttl(self):
        store = StateStore(101)

        # 1. Future timestamp tombstone (skew)
        future_elem = StateElement("future.tomb", b"", 2_000_000_000_000, 101, is_deleted=True)
        store.elements["future.tomb"] = future_elem

        # Compact with current_time = 1000s, TTL = 100s
        stats = store.compact_tombstones(ttl_s=100.0, current_time_s=1000.0)
        self.assertEqual(stats["tombstones_purged"], 0)
        self.assertEqual(stats["tombstones_retained"], 1)
        self.assertIn("future.tomb", store.elements)

        # 2. Exact TTL boundary
        retained_elem = StateElement("retained.tomb", b"", 900_000_000_000, 101, is_deleted=True) # age = 100s
        purged_elem = StateElement("purged.tomb", b"", 899_000_000_000, 101, is_deleted=True) # age = 101s > 100s
        store.elements["retained.tomb"] = retained_elem
        store.elements["purged.tomb"] = purged_elem

        stats2 = store.compact_tombstones(ttl_s=100.0, current_time_s=1000.0)
        self.assertEqual(stats2["tombstones_purged"], 1)
        self.assertNotIn("purged.tomb", store.elements)
        self.assertIn("retained.tomb", store.elements)

        # 3. Ancient live key must not die
        live_elem = StateElement("live.key", b"active_data", 1, 101, is_deleted=False)
        store.elements["live.key"] = live_elem

        stats3 = store.compact_tombstones(ttl_s=100.0, current_time_s=1000.0)
        self.assertEqual(store.get("live.key"), b"active_data")
        self.assertEqual(stats3["active_elements"], 1)

    def test_crdt_scale_and_disk_wal_truncation(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        try:
            if os.path.exists(path):
                os.remove(path)

            store = StateStore(node_id=1, persistence_path=path)

            for i in range(200):
                store.set(f"k_{i}", f"val_{i}".encode())

            for i in range(200, 400):
                k = f"tomb_{i}"
                store.set(k, b"temp")
                store.delete(k)
                elem = store.elements[k]
                if i < 300:
                    elem.timestamp_ns = 100_000_000_000 # Stale
                else:
                    elem.timestamp_ns = 950_000_000_000 # Fresh

            self.assertEqual(store.total_elements_count(), 400)
            self.assertEqual(store.count_tombstones(), 200)

            stats = store.compact_disk_storage(ttl_s=200.0, current_time_s=1000.0)
            self.assertEqual(stats["tombstones_purged"], 100)
            self.assertEqual(stats["tombstones_retained"], 100)
            self.assertEqual(store.total_elements_count(), 300)

            # Reload and verify consistency
            reloaded = StateStore(node_id=1, persistence_path=path)
            self.assertEqual(reloaded.total_elements_count(), 300)
            self.assertEqual(reloaded.get("k_0"), b"val_0")
            self.assertEqual(reloaded.get("k_199"), b"val_199")
        finally:
            if os.path.exists(path):
                os.remove(path)
            if os.path.exists(path + ".log"):
                os.remove(path + ".log")


class TestAdversarialWatchdog(unittest.TestCase):
    """Adversarial testing of Watchdog supervisor and device handling."""

    def test_mock_supervisor_and_safe_disarm(self):
        config = WatchdogConfig(enabled=True, timeout_secs=10, ping_interval_secs=2)
        mock = MockWatchdogDriver(simulated_present=True, timeout_secs=10)
        supervisor = WatchdogSupervisor(config=config, driver=mock)

        self.assertTrue(supervisor.is_present())
        self.assertFalse(supervisor.is_armed())
        self.assertFalse(supervisor.ping(), "Ping on disarmed watchdog must fail")

        # Arm and ping
        self.assertTrue(supervisor.arm())
        self.assertTrue(supervisor.is_armed())

        for _ in range(5):
            self.assertTrue(supervisor.ping())

        self.assertEqual(mock.ping_count, 5)
        self.assertFalse(mock.disarmed_safely)

        # Disarm with 'V' invariant
        self.assertTrue(supervisor.disarm())
        self.assertFalse(supervisor.is_armed())
        self.assertTrue(mock.disarmed_safely)

        # Post-disarm ping fails
        self.assertFalse(supervisor.ping())

    def test_absent_linux_watchdog_exception_safety(self):
        driver = LinuxHardwareWatchdog("/tmp/non_existent_watchdog_xyz", 30)
        self.assertFalse(driver.is_hardware_present())
        self.assertFalse(driver.is_armed())

        with self.assertRaises(FileNotFoundError):
            driver.arm()

        with self.assertRaises(RuntimeError):
            driver.ping()

        # Disarm does not crash
        driver.disarm_and_close()


if __name__ == "__main__":
    unittest.main()
