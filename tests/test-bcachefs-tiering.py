#!/usr/bin/env python3
# AI-hint: Unit tests for MiOS Bcachefs multi-device storage tiering configurator.
# AI-doc: usr/share/doc/mios/manual/storage.md
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "storage"))
from bcachefs_tier import BcachefsTierManager


class TestBcachefsTierManager(unittest.TestCase):
    def test_multi_device_format_command_rendering(self):
        mgr = BcachefsTierManager(
            nvme_devices=["/dev/nvme0n1"],
            hdd_devices=["/dev/sda", "/dev/sdb"],
            mount_point="/srv/storage",
            compression="zstd:3",
            replicas=1,
            dry_run=True,
        )
        cmd = mgr.render_format_command()
        cmd_str = " ".join(cmd)

        self.assertIn("bcachefs format", cmd_str)
        self.assertIn("--foreground_target=nvme.hot", cmd_str)
        self.assertIn("--promote_target=nvme.hot", cmd_str)
        self.assertIn("--background_target=hdd.bulk", cmd_str)
        self.assertIn("--label=nvme.hot /dev/nvme0n1", cmd_str)
        self.assertIn("--label=hdd.bulk /dev/sda", cmd_str)
        self.assertIn("--label=hdd.bulk /dev/sdb", cmd_str)

    def test_single_nvme_volume_format(self):
        mgr = BcachefsTierManager(
            nvme_devices=["/dev/nvme0n1"],
            hdd_devices=[],
            dry_run=True,
        )
        cmd = mgr.render_format_command()
        cmd_str = " ".join(cmd)

        self.assertIn("--foreground_target=nvme.hot", cmd_str)
        self.assertNotIn("hdd.bulk", cmd_str)

    def test_fstab_entry_generation(self):
        mgr = BcachefsTierManager(
            nvme_devices=["/dev/nvme0n1"],
            hdd_devices=["/dev/sda"],
            mount_point="/var/lib/mios/models",
            dry_run=True,
        )
        fstab = mgr.render_fstab_entry(uuid="12345678-abcd-ef01-2345-6789abcdef01")
        self.assertIn("UUID=12345678-abcd-ef01-2345-6789abcdef01", fstab)
        self.assertIn("/var/lib/mios/models", fstab)
        self.assertIn("bcachefs", fstab)
        self.assertIn("promote_target=nvme.hot", fstab)
        self.assertIn("background_target=hdd.bulk", fstab)

    def test_empty_devices_raises_error(self):
        mgr = BcachefsTierManager(nvme_devices=[], hdd_devices=[], dry_run=True)
        with self.assertRaises(ValueError):
            mgr.render_format_command()


if __name__ == "__main__":
    unittest.main()
