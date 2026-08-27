#!/usr/bin/env python3
# AI-hint: Automated test suite for MiOS Hugepages Automatic Allocation, Memory Compaction, and Teardown Manager (T-418).
# AI-related: usr/libexec/mios/virt/hugepages_mgr.py, usr/share/doc/mios/manual/ch21-looking-glass-b7-and-kvmfr.md
"""
Automated unit tests for dynamic hugepages allocation, kernel memory compaction triggering,
pool status calculation, release teardown, and libvirt XML generation.
"""

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
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "virt", "hugepages_mgr.py")

spec = importlib.util.spec_from_file_location("hugepages_mgr", _TARGET_PATH)
if spec and spec.loader:
    hugepages_mgr = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = hugepages_mgr
    spec.loader.exec_module(hugepages_mgr)
else:
    raise ImportError(f"Could not load hugepages_mgr module from {_TARGET_PATH}")

class TestHugepagesManager(unittest.TestCase):
    """Tests hugepages allocation, compaction trigger, teardown, and XML generation."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="mios-test-hugepages-")
        self.sysfs_root = os.path.join(self.temp_dir, "sys")
        self.proc_root = os.path.join(self.temp_dir, "proc")

        # Setup synthetic 2M and 1G sysfs directories
        for kb in [2048, 1048576]:
            pool_dir = os.path.join(self.sysfs_root, "kernel", "mm", "hugepages", f"hugepages-{kb}kB")
            os.makedirs(pool_dir, exist_ok=True)
            with open(os.path.join(pool_dir, "nr_hugepages"), "w", encoding="utf-8") as f:
                f.write("0\n")
            with open(os.path.join(pool_dir, "free_hugepages"), "w", encoding="utf-8") as f:
                f.write("0\n")

        # Setup synthetic /proc/sys/vm/compact_memory
        vm_dir = os.path.join(self.proc_root, "sys", "vm")
        os.makedirs(vm_dir, exist_ok=True)
        with open(os.path.join(vm_dir, "compact_memory"), "w", encoding="utf-8") as f:
            f.write("0\n")

        # Setup synthetic /proc/meminfo
        with open(os.path.join(self.proc_root, "meminfo"), "w", encoding="utf-8") as f:
            f.write("MemTotal:       32768000 kB\nMemFree:        24000000 kB\nMemAvailable:   26000000 kB\n")

    def tearDown(self) -> None:
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_page_count_calculation_2m(self) -> None:
        mgr = hugepages_mgr.HugepagesManager(mock=True)
        self.assertEqual(mgr.calculate_page_count(8192, page_size="2M"), 4096)
        self.assertEqual(mgr.calculate_page_count(16384, page_size="2M"), 8192)
        with self.assertRaises(ValueError):
            mgr.calculate_page_count(8193, page_size="2M")  # Not multiple of 2

    def test_page_count_calculation_1g(self) -> None:
        mgr = hugepages_mgr.HugepagesManager(mock=True)
        self.assertEqual(mgr.calculate_page_count(8192, page_size="1G"), 8)
        self.assertEqual(mgr.calculate_page_count(16384, page_size="1G"), 16)
        with self.assertRaises(ValueError):
            mgr.calculate_page_count(8190, page_size="1G")  # Not multiple of 1024

    def test_memory_compaction_trigger(self) -> None:
        mgr = hugepages_mgr.HugepagesManager(
            sysfs_root=self.sysfs_root,
            proc_root=self.proc_root,
            mock=False,
        )
        res = mgr.trigger_compaction()
        self.assertTrue(res["compaction_triggered"])
        compact_file = os.path.join(self.proc_root, "sys", "vm", "compact_memory")
        with open(compact_file, "r", encoding="utf-8") as f:
            self.assertEqual(f.read().strip(), "1")

    def test_allocate_and_release_lifecycle(self) -> None:
        mgr = hugepages_mgr.HugepagesManager(
            sysfs_root=self.sysfs_root,
            proc_root=self.proc_root,
            mock=False,
        )
        # Allocate 4096 MB (2048 pages of 2M) with compaction
        alloc_res = mgr.allocate(4096, page_size="2M", compact=True)
        self.assertEqual(alloc_res["status"], "allocated")
        self.assertEqual(alloc_res["requested_pages"], 2048)
        self.assertEqual(alloc_res["target_pages"], 2048)
        self.assertTrue(alloc_res["compaction"]["compaction_triggered"])

        # Verify on synthetic sysfs
        pool_2m = mgr.get_pool_status("2M")
        self.assertEqual(pool_2m["nr_hugepages"], 2048)
        self.assertEqual(pool_2m["allocated_mb"], 4096)

        # Release 4096 MB
        rel_res = mgr.release(4096, page_size="2M")
        self.assertEqual(rel_res["status"], "released")
        self.assertEqual(rel_res["remaining_pages"], 0)

        pool_2m_after = mgr.get_pool_status("2M")
        self.assertEqual(pool_2m_after["nr_hugepages"], 0)

    def test_domain_xml_generation(self) -> None:
        mgr = hugepages_mgr.HugepagesManager(mock=True)
        xml_2m = mgr.generate_domain_xml(8192, page_size="2M")
        self.assertIn('<page size="2048" unit="KiB"/>', xml_2m)
        self.assertIn('<locked/>', xml_2m)

        xml_1g = mgr.generate_domain_xml(8192, page_size="1G")
        self.assertIn('<page size="1048576" unit="KiB"/>', xml_1g)
        self.assertIn('<locked/>', xml_1g)

    def test_mock_status_and_meminfo(self) -> None:
        mgr = hugepages_mgr.HugepagesManager(mock=True)
        mem = mgr.get_meminfo()
        self.assertIn("MemTotal", mem)
        self.assertIn("Hugepagesize", mem)

        st = mgr.get_pool_status("2M")
        self.assertEqual(st["page_size"], "2M")
        self.assertEqual(st["page_size_kb"], 2048)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestHugepagesManager)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
