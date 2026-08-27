#!/usr/bin/env python3
# AI-hint: Comprehensive adversarial empirical stress test suite for Milestone 1 (T-389, T-390, T-391, T-400).
# AI-related: usr/libexec/mios/node/hardware.py, usr/libexec/mios/node/cgroups.py, usr/libexec/mios/node/crdt.py, usr/libexec/mios/node/watchdog.py
"""
Milestone 1 Adversarial Stress Verification Suite.
Validates all edge cases, security allowlists, CPU topology invariants, CRDT compaction, and watchdog lifecycles.
"""

import os
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "node")))

from hardware import (
    HardwareAllowlist,
    HardwareErrorCode,
    MockHardwareDriver,
    SandboxedHardwareController,
)
from cgroups import (
    AffinityPolicy,
    CgroupV2Controller,
    NodeResourceLimits,
    WorkerAffinityController,
    filter_safe_worker_cores,
)
from crdt import StateElement, StateStore, VectorClock
from watchdog import MockWatchdogDriver, WatchdogConfig, WatchdogSupervisor

class TestT389HardwareStress(unittest.TestCase):
    """Stress tests for T-389 Hardware HAL and Allowlist constraints."""

    def setUp(self):
        self.allowlist = HardwareAllowlist(
            allowed_gpio_pins={4, 17, 27, 22},
            read_only_gpio_pins={4},
            allowed_i2c_buses={1},
            allowed_i2c_addresses={0x48, 0x68},
            max_i2c_transfer_len=64,
        )
        self.driver = MockHardwareDriver()
        self.controller = SandboxedHardwareController(self.allowlist, self.driver)

    def test_unauthorized_gpio_access_boundaries(self):
        unauthorized = [0, 1, 2, 3, 5, 18, 99, 255, 65535, 100000]
        for pin in unauthorized:
            code, val = self.controller.mios_sys_gpio_read(pin)
            self.assertEqual(code, HardwareErrorCode.PERMISSION_DENIED)
            write_code = self.controller.mios_sys_gpio_write(pin, 1)
            self.assertEqual(write_code, HardwareErrorCode.PERMISSION_DENIED)

    def test_read_only_pin_violation(self):
        self.driver.gpio_write(4, 1)
        code, val = self.controller.mios_sys_gpio_read(4)
        self.assertEqual(code, HardwareErrorCode.SUCCESS)
        self.assertEqual(val, 1)

        write_code = self.controller.mios_sys_gpio_write(4, 0)
        self.assertEqual(write_code, HardwareErrorCode.READ_ONLY_PIN)
        self.assertEqual(self.driver.gpio_read(4), 1)

    def test_i2c_unauthorized_buses_and_addresses(self):
        for bus in [0, 2, 3, 255]:
            code, _ = self.controller.mios_sys_i2c_transfer(bus, 0x68, b"\x00", 1)
            self.assertEqual(code, HardwareErrorCode.PERMISSION_DENIED)

        for addr in [0x00, 0x49, 0x55, 0x77, 0x3FF]:
            code, _ = self.controller.mios_sys_i2c_transfer(1, addr, b"\x00", 1)
            self.assertEqual(code, HardwareErrorCode.PERMISSION_DENIED)

    def test_i2c_buffer_overflow_rejections(self):
        # Max is 64 bytes
        overflow_write = bytes([0] * 65)
        code1, _ = self.controller.mios_sys_i2c_transfer(1, 0x68, overflow_write, 1)
        self.assertEqual(code1, HardwareErrorCode.INVALID_PARAMETER)

        code2, _ = self.controller.mios_sys_i2c_transfer(1, 0x68, b"\x00", 65)
        self.assertEqual(code2, HardwareErrorCode.INVALID_PARAMETER)

        # Boundary 64 bytes succeeds
        boundary_write = bytes([0] * 64)
        code3, res = self.controller.mios_sys_i2c_transfer(1, 0x68, boundary_write, 64)
        self.assertEqual(code3, HardwareErrorCode.SUCCESS)
        self.assertEqual(len(res), 64)

class TestT390CgroupsStress(unittest.TestCase):
    """Stress tests for T-390 CPU Pinning and Cgroups limits."""

    def test_topology_core_zero_isolation(self):
        # 1-core topology
        c1 = filter_safe_worker_cores(1, None, True)
        self.assertEqual(c1, [0], "1-core system must retain Core 0")

        # 2-core topology
        c2 = filter_safe_worker_cores(2, None, True)
        self.assertEqual(c2, [1], "2-core system must strip Core 0")

        # 4-core topology
        c4 = filter_safe_worker_cores(4, None, True)
        self.assertEqual(c4, [1, 2, 3])
        self.assertNotIn(0, c4)

        # 64-core topology
        c64 = filter_safe_worker_cores(64, None, True)
        self.assertEqual(len(c64), 63)
        self.assertEqual(c64[0], 1)
        self.assertEqual(c64[-1], 63)
        self.assertNotIn(0, c64)

        # Out-of-bounds requested filter
        filtered = filter_safe_worker_cores(64, [0, 2, 10, 63, 64, 100], True)
        self.assertEqual(filtered, [2, 10, 63])

    def test_affinity_exhaustion_and_recovery(self):
        ctrl = WorkerAffinityController(4)  # safe: [1, 2, 3]

        c1 = ctrl.allocate_cores_for_policy(AffinityPolicy.EXCLUSIVE, 2)
        self.assertEqual(c1, [1, 2])

        c2 = ctrl.allocate_cores_for_policy(AffinityPolicy.EXCLUSIVE, 1)
        self.assertEqual(c2, [3])

        # Exhaustion
        with self.assertRaises(RuntimeError):
            ctrl.allocate_cores_for_policy(AffinityPolicy.EXCLUSIVE, 1)

        # Release and realloc
        ctrl.release_cores([2])
        c3 = ctrl.allocate_cores_for_policy(AffinityPolicy.EXCLUSIVE, 1)
        self.assertEqual(c3, [2])

        # Low priority & Shared
        low = ctrl.allocate_cores_for_policy(AffinityPolicy.LOW_PRIORITY, 0)
        self.assertEqual(low, [3])
        self.assertNotIn(0, low)

        shared = ctrl.allocate_cores_for_policy(AffinityPolicy.SHARED, 0)
        self.assertEqual(shared, [1, 2, 3])
        self.assertNotIn(0, shared)

    def test_cgroup_format_cpu_max_edge_cases(self):
        self.assertEqual(CgroupV2Controller.format_cpu_max(None, 100_000), "max 100000")
        self.assertEqual(CgroupV2Controller.format_cpu_max(0, 100_000), "0 100000")
        self.assertEqual(CgroupV2Controller.format_cpu_max(80, 100_000), "80000 100000")
        self.assertEqual(CgroupV2Controller.format_cpu_max(400, 100_000), "400000 100000")

class TestT391CrdtCompactionStress(unittest.TestCase):
    """Stress tests for T-391 CRDT Compaction, Tombstone TTL, and Snapshot GC."""

    def test_tombstone_ttl_and_resurrection_resistance(self):
        store = StateStore(10)

        # key_a deleted at t = 1000s
        store.set("key_a", b"val_a")
        store.delete("key_a")
        store.elements["key_a"].timestamp_ns = int(1000 * 1e9)

        # key_b deleted at t = 2000s
        store.set("key_b", b"val_b")
        store.delete("key_b")
        store.elements["key_b"].timestamp_ns = int(2000 * 1e9)

        # key_c active at t = 2500s
        store.set("key_c", b"val_c")
        store.elements["key_c"].timestamp_ns = int(2500 * 1e9)

        # Compact at current_time = 2200s with TTL = 500s
        # key_a age = 1200s > 500s -> purged
        # key_b age = 200s <= 500s -> retained
        stats = store.compact_tombstones(ttl_s=500.0, current_time_s=2200.0)
        self.assertEqual(stats["tombstones_purged"], 1)
        self.assertEqual(stats["tombstones_retained"], 1)
        self.assertEqual(stats["active_elements"], 1)

        self.assertEqual(store.get("key_c"), b"val_c")
        self.assertIsNone(store.get("key_b"))
        self.assertIsNone(store.get("key_a"))

        # Stale update cannot resurrect key_b
        stale_elem = StateElement(
            key="key_b",
            value=b"stale_resurrect",
            timestamp_ns=int(1500 * 1e9),
            originating_node_id=20,
            is_deleted=False,
        )
        applied = store.merge_remote_store(VectorClock(), [stale_elem])
        self.assertEqual(applied, 0)
        self.assertIsNone(store.get("key_b"))

        # Fresh update resurrects key_b
        fresh_elem = StateElement(
            key="key_b",
            value=b"fresh_resurrect",
            timestamp_ns=int(3000 * 1e9),
            originating_node_id=20,
            is_deleted=False,
        )
        applied = store.merge_remote_store(VectorClock(), [fresh_elem])
        self.assertEqual(applied, 1)
        self.assertEqual(store.get("key_b"), b"fresh_resurrect")

    def test_tie_breaking_originating_node_id(self):
        store = StateStore(100)
        local = StateElement(
            key="tie_key",
            value=b"from_node_100",
            timestamp_ns=5000,
            originating_node_id=100,
            is_deleted=False,
        )
        store.merge_remote_store(VectorClock(), [local])

        # Lower node ID (50 < 100) -> rejected
        remote_lower = StateElement(
            key="tie_key",
            value=b"from_node_50",
            timestamp_ns=5000,
            originating_node_id=50,
            is_deleted=False,
        )
        applied = store.merge_remote_store(VectorClock(), [remote_lower])
        self.assertEqual(applied, 0)
        self.assertEqual(store.get("tie_key"), b"from_node_100")

        # Higher node ID (200 > 100) -> accepted
        remote_higher = StateElement(
            key="tie_key",
            value=b"from_node_200",
            timestamp_ns=5000,
            originating_node_id=200,
            is_deleted=False,
        )
        applied = store.merge_remote_store(VectorClock(), [remote_higher])
        self.assertEqual(applied, 1)
        self.assertEqual(store.get("tie_key"), b"from_node_200")

    def test_wal_compaction_and_disk_reloading(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "crdt_store.json")
            store = StateStore(501, persistence_path=path)

            for i in range(100):
                store.set(f"k_{i}", f"v_{i}".encode())

            for i in range(60):
                store.delete(f"k_{i}")
                store.elements[f"k_{i}"].timestamp_ns = int(1000 * 1e9)

            self.assertEqual(store.total_elements_count(), 100)
            self.assertEqual(store.count_tombstones(), 60)

            stats = store.compact_disk_storage(ttl_s=1000.0, current_time_s=10000.0)
            self.assertEqual(stats["tombstones_purged"], 60)
            self.assertEqual(stats["active_elements"], 40)
            self.assertEqual(store.total_elements_count(), 40)

            # Reload
            reloaded = StateStore(501, persistence_path=path)
            self.assertEqual(reloaded.total_elements_count(), 40)
            self.assertEqual(reloaded.count_tombstones(), 0)

            for i in range(60, 100):
                self.assertEqual(reloaded.get(f"k_{i}"), f"v_{i}".encode())
            for i in range(60):
                self.assertIsNone(reloaded.get(f"k_{i}"))

class TestT400WatchdogStress(unittest.TestCase):
    """Stress tests for T-400 Watchdog Supervisor."""

    def test_rapid_sequential_pings(self):
        sup = WatchdogSupervisor()
        self.assertTrue(sup.arm())
        self.assertTrue(sup.is_armed())

        for _ in range(10_000):
            self.assertTrue(sup.ping())

        driver = sup.driver
        self.assertEqual(driver.ping_count, 10_000)
        self.assertFalse(driver.disarmed_safely)

    def test_concurrent_multithreaded_pings(self):
        sup = WatchdogSupervisor()
        self.assertTrue(sup.arm())

        threads = []
        for _ in range(10):
            t = threading.Thread(target=lambda: [sup.ping() for _ in range(500)])
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(sup.driver.ping_count, 5_000)
        self.assertTrue(sup.disarm())
        self.assertFalse(sup.is_armed())
        self.assertTrue(sup.driver.disarmed_safely)

    def test_disarm_rearm_and_missing_recovery(self):
        mock_missing = MockWatchdogDriver(simulated_present=False)
        sup_missing = WatchdogSupervisor(driver=mock_missing)
        self.assertFalse(sup_missing.is_present())
        self.assertFalse(sup_missing.arm())
        self.assertFalse(sup_missing.is_armed())

        sup = WatchdogSupervisor()
        self.assertTrue(sup.arm())
        self.assertTrue(sup.ping())

        self.assertTrue(sup.disarm())
        self.assertFalse(sup.is_armed())
        self.assertTrue(sup.driver.disarmed_safely)
        self.assertFalse(sup.ping())

        # Re-arm
        self.assertTrue(sup.arm())
        self.assertTrue(sup.is_armed())
        self.assertFalse(sup.driver.disarmed_safely)
        self.assertTrue(sup.ping())

if __name__ == "__main__":
    unittest.main()
