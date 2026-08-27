#!/usr/bin/env python3
# AI-hint: Unit and integration tests for non-destructive dual-boot partitioning and NTFS resize planner.
# AI-related: usr/libexec/mios/deploy/partition_dualboot.py, usr/share/mios/mios.toml, usr/libexec/mios/deploy/baremetal_install.py
"""Unit and integration test suite for DualBootPartitionEngine and CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "deploy", "partition_dualboot.py")

spec = importlib.util.spec_from_file_location("partition_dualboot", _TARGET_PATH)
if spec and spec.loader:
    partition_dualboot = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = partition_dualboot
    spec.loader.exec_module(partition_dualboot)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")


class TestPartitionDualboot(unittest.TestCase):
    """Test suite for NTFS volume health audits, dirty bit checks, dual-boot partition geometry, and CLI."""

    def test_check_ntfs_health_clean_mock(self):
        engine = partition_dualboot.DualBootPartitionEngine(mock=True, simulate_dirty_bit=False)
        health = engine.check_ntfs_health()
        self.assertTrue(health.is_clean)
        self.assertFalse(health.dirty_bit_set)
        self.assertEqual(health.total_gb, 500.0)

    def test_check_ntfs_health_dirty_mock(self):
        engine = partition_dualboot.DualBootPartitionEngine(mock=True, simulate_dirty_bit=True)
        health = engine.check_ntfs_health()
        self.assertFalse(health.is_clean)
        self.assertTrue(health.dirty_bit_set)

    def test_plan_dualboot_dirty_bit_rejected_without_force(self):
        engine = partition_dualboot.DualBootPartitionEngine(mock=True, simulate_dirty_bit=True, force=False)
        health = engine.check_ntfs_health()
        with self.assertRaises(ValueError) as ctx:
            engine.plan_dualboot(health)
        self.assertIn("Volume dirty bit is SET", str(ctx.exception))

    def test_plan_dualboot_clean_volume_generates_xbootldr_and_root(self):
        engine = partition_dualboot.DualBootPartitionEngine(
            disk="/dev/nvme0n1",
            ntfs_part="/dev/nvme0n1p3",
            shrink_gb=64,
            fs_type="btrfs",
            mock=True,
        )
        health = engine.check_ntfs_health()
        plan = engine.plan_dualboot(health)

        self.assertEqual(plan.original_ntfs_size_gb, 500.0)
        self.assertEqual(plan.new_ntfs_size_gb, 436.0)
        self.assertEqual(plan.shrink_amount_gb, 64.0)
        self.assertTrue(plan.needs_xbootldr)
        self.assertEqual(plan.xbootldr_size_mb, 1024)
        self.assertEqual(plan.root_size_gb, 63.0)
        self.assertEqual(plan.root_fs_type, "btrfs")

        # Confirm bootloader entries generated
        self.assertIn("/boot/loader/entries/windows.conf", plan.systemd_boot_entries)
        self.assertIn("bootmgfw.efi", plan.systemd_boot_entries["/boot/loader/entries/windows.conf"])

    def test_run_mock_execution(self):
        engine = partition_dualboot.DualBootPartitionEngine(mock=True)
        res = engine.run()
        self.assertEqual(res["status"], "success")
        self.assertIn("health", res)
        self.assertIn("plan", res)

    def test_cli_execution_mock_json(self):
        test_args = [
            "partition_dualboot.py",
            "--disk", "/dev/nvme0n1",
            "--ntfs-part", "/dev/nvme0n1p3",
            "--shrink-gb", "64",
            "--fs-type", "btrfs",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = partition_dualboot.main()
            self.assertEqual(exit_code, 0)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPartitionDualboot)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
