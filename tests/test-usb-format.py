#!/usr/bin/env python3
# AI-hint: Unit and integration tests for MiOS-Cat removable USB hybrid GPT/MBR partition formatter.
# AI-related: usr/libexec/mios/deploy/usb_format.py, usr/share/mios/mios.toml, cat/MiOS-Cat.sh
"""Unit and integration test suite for UsbFormatEngine and CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "deploy", "usb_format.py")

spec = importlib.util.spec_from_file_location("usb_format", _TARGET_PATH)
if spec and spec.loader:
    usb_format = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = usb_format
    spec.loader.exec_module(usb_format)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestUsbFormat(unittest.TestCase):
    """Test suite for USB probing, removable safety verification, partition geometry, and CLI."""

    def test_probe_device_mock(self):
        engine = usb_format.UsbFormatEngine(target_dev="/dev/sdb", mock=True)
        dev = engine.probe_device()
        self.assertEqual(dev.device_path, "/dev/sdb")
        self.assertTrue(dev.is_removable)
        self.assertEqual(dev.bus_type, "usb")
        self.assertEqual(dev.size_gb, 32.0)

    def test_validate_safety_removable_drive_passes(self):
        engine = usb_format.UsbFormatEngine(target_dev="/dev/sdb", mock=True)
        dev = engine.probe_device()
        safe, reason = engine.validate_safety(dev)
        self.assertTrue(safe)
        self.assertIsNone(reason)

    def test_validate_safety_system_drive_rejected_without_force(self):
        engine = usb_format.UsbFormatEngine(target_dev="/dev/nvme0n1", force=False, mock=True)
        # Create non-removable mock device simulating system NVMe
        sys_dev = usb_format.DeviceInfo(
            device_path="/dev/nvme0n1",
            model="System NVMe Drive",
            size_bytes=1000 * 1024 * 1024 * 1024,
            size_gb=1000.0,
            is_removable=False,
            bus_type="nvme",
        )
        safe, reason = engine.validate_safety(sys_dev)
        self.assertFalse(safe)
        self.assertIn("Refusing to format potential system disk", reason)

    def test_plan_layout_geometry_and_guids(self):
        engine = usb_format.UsbFormatEngine(target_dev="/dev/sdb", repo_size_mb=2048, mock=True)
        dev = engine.probe_device()
        layout = engine.plan_layout(dev)

        self.assertEqual(len(layout), 2)

        # Partition 1: EFI / Repo
        repo_part = layout[0]
        self.assertEqual(repo_part.name, "MiOS-Repo")
        self.assertEqual(repo_part.filesystem, "vfat")
        self.assertEqual(repo_part.type_guid, usb_format.ESP_GUID)
        self.assertTrue(repo_part.bootable)
        self.assertEqual(repo_part.start_sector, 2048)  # 1MB alignment

        # Partition 2: Data
        data_part = layout[1]
        self.assertEqual(data_part.name, "MiOS-Data")
        self.assertEqual(data_part.filesystem, "exfat")
        self.assertEqual(data_part.type_guid, usb_format.BASIC_DATA_GUID)
        self.assertFalse(data_part.bootable)
        self.assertGreater(data_part.start_sector, repo_part.end_sector)

    def test_run_mock_execution(self):
        engine = usb_format.UsbFormatEngine(target_dev="/dev/sdb", mock=True)
        res = engine.run()
        self.assertEqual(res["status"], "success")
        self.assertEqual(len(res["layout"]), 2)
        self.assertGreaterEqual(len(res["commands_planned"]), 4)

    def test_cli_execution_mock_json(self):
        test_args = [
            "usb_format.py",
            "--target-dev", "/dev/sdb",
            "--repo-size-mb", "2048",
            "--label-repo", "MiOS-Repo",
            "--label-data", "MiOS-Data",
            "--fs-data", "exfat",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = usb_format.main()
            self.assertEqual(exit_code, 0)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUsbFormat)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
