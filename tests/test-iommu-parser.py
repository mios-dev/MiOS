#!/usr/bin/env python3
# AI-hint: Automated test suite for MiOS IOMMU Group Parser and PCIe ACS Override Topology Auditor (T-413).
# AI-related: usr/libexec/mios/virt/iommu_parser.py, usr/share/doc/mios/manual/ch21-looking-glass-b7-and-kvmfr.md
"""
Automated unit tests for IOMMU group parser, multifunction device detection,
isolation conflict auditing, and UKI-baked ACS override recommendation.
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
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "virt", "iommu_parser.py")

spec = importlib.util.spec_from_file_location("iommu_parser", _TARGET_PATH)
if spec and spec.loader:
    iommu_parser = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = iommu_parser
    spec.loader.exec_module(iommu_parser)
else:
    raise ImportError(f"Could not load iommu_parser module from {_TARGET_PATH}")


class TestIOMMUParser(unittest.TestCase):
    """Tests IOMMU group parsing and isolation auditing using mock and synthetic sysfs trees."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="mios-test-iommu-")

    def tearDown(self) -> None:
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_synthetic_pci_device(
        self,
        sysfs_root: str,
        group_id: int,
        bdf: str,
        vendor: str,
        device: str,
        class_code: str,
        driver: str | None = None,
        boot_vga: bool = False,
    ) -> None:
        fs_bdf = iommu_parser.IOMMUParser.sanitize_bdf_for_fs(bdf)
        dev_dir = os.path.join(sysfs_root, "kernel", "iommu_groups", str(group_id), "devices", fs_bdf)
        os.makedirs(dev_dir, exist_ok=True)
        with open(os.path.join(dev_dir, "vendor"), "w", encoding="utf-8") as f:
            f.write(f"{vendor}\n")
        with open(os.path.join(dev_dir, "device"), "w", encoding="utf-8") as f:
            f.write(f"{device}\n")
        with open(os.path.join(dev_dir, "class"), "w", encoding="utf-8") as f:
            f.write(f"{class_code}\n")
        with open(os.path.join(dev_dir, "boot_vga"), "w", encoding="utf-8") as f:
            f.write(f"{'1' if boot_vga else '0'}\n")

        # Also create sysfs bus/pci/devices entry
        bus_dev_dir = os.path.join(sysfs_root, "bus", "pci", "devices", fs_bdf)
        os.makedirs(bus_dev_dir, exist_ok=True)
        for fname in ["vendor", "device", "class", "boot_vga"]:
            src = os.path.join(dev_dir, fname)
            dst = os.path.join(bus_dev_dir, fname)
            if os.path.exists(src) and not os.path.exists(dst):
                with open(src, "r", encoding="utf-8") as rf, open(dst, "w", encoding="utf-8") as wf:
                    wf.write(rf.read())

    def test_bdf_normalization(self) -> None:
        dom, bus, slot, func = iommu_parser.IOMMUParser.parse_bdf("0000:01:00.0")
        self.assertEqual((dom, bus, slot, func), ("0000", "01", "00", "0"))

        dom, bus, slot, func = iommu_parser.IOMMUParser.parse_bdf("01:00.1")
        self.assertEqual((dom, bus, slot, func), ("0000", "01", "00", "1"))

        dom, bus, slot, func = iommu_parser.IOMMUParser.parse_bdf("0000_01_00.0")
        self.assertEqual((dom, bus, slot, func), ("0000", "01", "00", "0"))

        with self.assertRaises(ValueError):
            iommu_parser.IOMMUParser.parse_bdf("invalid-bdf")

    def test_decode_pci_class(self) -> None:
        self.assertEqual(iommu_parser.decode_pci_class("0x030000"), "VGA compatible controller")
        self.assertEqual(iommu_parser.decode_pci_class("0x040300"), "Audio device (HD Audio / Soundwire)")
        self.assertEqual(iommu_parser.decode_pci_class("0x060400"), "PCI bridge (Root Port / Switch)")
        self.assertEqual(iommu_parser.decode_pci_class("0x010802"), "Non-Volatile memory controller (NVMe)")

    def test_mock_isolation_pass(self) -> None:
        parser = iommu_parser.IOMMUParser(mock=True)
        report = parser.audit_isolation("0000:01:00.0")

        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["isolated"])
        self.assertEqual(report["iommu_group"], 13)
        self.assertEqual(len(report["companions"]), 2)  # VGA (0000:01:00.0) + Audio (0000:01:00.1)
        self.assertEqual(len(report["conflicts"]), 0)
        self.assertIn("Clean hardware IOMMU isolation", report["recommendation"])
        self.assertIsNone(report["uki_kargs"])

    def test_synthetic_isolated_group(self) -> None:
        # Create group 5 with isolated GPU (0000:02:00.0 VGA and 0000:02:00.1 Audio)
        self._create_synthetic_pci_device(
            self.temp_dir, 5, "0000:02:00.0", "0x10de", "0x2484", "0x030000", boot_vga=False
        )
        self._create_synthetic_pci_device(
            self.temp_dir, 5, "0000:02:00.1", "0x10de", "0x228b", "0x040300", boot_vga=False
        )

        parser = iommu_parser.IOMMUParser(sysfs_root=self.temp_dir, mock=False)
        report = parser.audit_isolation("0000:02:00.0")

        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["isolated"])
        self.assertEqual(report["iommu_group"], 5)
        self.assertEqual(len(report["conflicts"]), 0)
        self.assertEqual(len(report["companions"]), 2)

    def test_synthetic_conflicting_group_requires_acs_override(self) -> None:
        # Create group 7 with GPU (0000:03:00.0) sharing group with PCIe Root Port (0000:00:01.0) and SATA (0000:00:17.0)
        self._create_synthetic_pci_device(
            self.temp_dir, 7, "0000:03:00.0", "0x10de", "0x2484", "0x030000", boot_vga=False
        )
        self._create_synthetic_pci_device(
            self.temp_dir, 7, "0000:00:01.0", "0x8086", "0x460d", "0x060400", boot_vga=False
        )
        self._create_synthetic_pci_device(
            self.temp_dir, 7, "0000:00:17.0", "0x8086", "0x7a62", "0x010601", boot_vga=False
        )

        parser = iommu_parser.IOMMUParser(sysfs_root=self.temp_dir, mock=False)
        report = parser.audit_isolation("0000:03:00.0")

        self.assertEqual(report["status"], "conflict")
        self.assertFalse(report["isolated"])
        self.assertEqual(report["iommu_group"], 7)
        self.assertEqual(len(report["companions"]), 1)  # Target itself
        self.assertEqual(len(report["conflicts"]), 2)   # Root Port + SATA
        self.assertEqual(report["uki_kargs"], "pcie_acs_override=downstream,multifunction")
        self.assertIn("Unified Kernel Image (UKI)", report["recommendation"])
        self.assertIn("not injected via runtime MOK", report["recommendation"])
        self.assertIsNotNone(report["security_warning"])

    def test_device_not_found(self) -> None:
        parser = iommu_parser.IOMMUParser(mock=True)
        report = parser.audit_isolation("0000:99:00.0")
        self.assertEqual(report["status"], "not_found")
        self.assertFalse(report["isolated"])

    def test_invalid_bdf_error(self) -> None:
        parser = iommu_parser.IOMMUParser(mock=True)
        report = parser.audit_isolation("bad-bdf-str")
        self.assertEqual(report["status"], "error")
        self.assertFalse(report["isolated"])

    def test_list_groups_mock(self) -> None:
        parser = iommu_parser.IOMMUParser(mock=True)
        groups = parser.parse_groups()
        self.assertIn(0, groups)
        self.assertIn(1, groups)
        self.assertIn(13, groups)
        self.assertEqual(len(groups[13]), 2)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestIOMMUParser)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
