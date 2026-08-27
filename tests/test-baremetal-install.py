#!/usr/bin/env python3
# AI-hint: Unit and integration tests for baremetal NVMe hardware discovery and bootc installer.
# AI-related: usr/libexec/mios/deploy/baremetal_install.py, usr/share/mios/mios.toml, usr/libexec/mios/deploy/usb_format.py
"""Unit and integration test suite for BareMetalInstaller, HardwareDiscoveryEngine, and CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "deploy", "baremetal_install.py")

spec = importlib.util.spec_from_file_location("baremetal_install", _TARGET_PATH)
if spec and spec.loader:
    baremetal_install = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = baremetal_install
    spec.loader.exec_module(baremetal_install)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestBaremetalInstall(unittest.TestCase):
    """Test suite for NVMe disk ranking, safety assertion, bootc command synthesis, and CLI."""

    def test_discovery_scan_disks_ranking(self):
        discovery = baremetal_install.HardwareDiscoveryEngine(mock=True)
        disks = discovery.scan_disks()
        self.assertGreaterEqual(len(disks), 3)

        # Fastest eligible drive (NVMe) must rank first
        self.assertEqual(disks[0].bus_type, "nvme")
        self.assertEqual(disks[0].device_path, "/dev/nvme0n1")
        self.assertEqual(disks[0].status, "eligible")
        self.assertGreater(disks[0].score, disks[1].score)

        # Boot USB disk must be ineligible
        boot_usb = next(d for d in disks if d.device_path == "/dev/sdb")
        self.assertEqual(boot_usb.status, "ineligible_current_boot")
        self.assertEqual(boot_usb.score, 0)

    def test_plan_install_auto_select(self):
        installer = baremetal_install.BareMetalInstaller(
            auto_select=True,
            image_ref="ghcr.io/ublue-os/ucore-hci:latest",
            filesystem="btrfs",
            yes=True,
            mock=True,
        )
        plan = installer.plan_install()
        self.assertEqual(plan.target_disk.device_path, "/dev/nvme0n1")
        self.assertTrue(plan.uefi_supported)
        self.assertEqual(plan.filesystem, "btrfs")
        self.assertIn("bootc", plan.bootc_command)
        self.assertIn("install", plan.bootc_command)
        self.assertIn("/dev/nvme0n1", plan.bootc_command)

    def test_plan_install_current_boot_rejected(self):
        installer = baremetal_install.BareMetalInstaller(
            target_disk="/dev/sdb",  # Live boot device
            yes=True,
            force=False,
            mock=True,
        )
        with self.assertRaises(ValueError) as ctx:
            installer.plan_install()
        self.assertIn("SAFETY VIOLATION", str(ctx.exception))

    def test_execute_install_mock(self):
        installer = baremetal_install.BareMetalInstaller(auto_select=True, yes=True, mock=True)
        res = installer.run()
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["target"]["device_path"], "/dev/nvme0n1")
        self.assertTrue(res["uefi"])
        self.assertGreaterEqual(len(res["commands_executed"]), 3)

    def test_cli_execution_auto_select_mock_json(self):
        test_args = [
            "baremetal_install.py",
            "--auto-select",
            "--image-ref", "ghcr.io/ublue-os/ucore-hci:latest",
            "--filesystem", "btrfs",
            "--yes",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = baremetal_install.main()
            self.assertEqual(exit_code, 0)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestBaremetalInstall)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
