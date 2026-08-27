#!/usr/bin/env python3
# AI-hint: Unit tests for MiOS IOMMU DMA remapper and PCIe ACS validator.
# AI-doc: usr/share/doc/mios/manual/hardware.md
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "hw"))
from iommu_validator import IOMMUValidator

class TestIOMMUValidator(unittest.TestCase):
    def setUp(self):
        self.validator = IOMMUValidator(dry_run=True)

    def test_scan_iommu_groups_mock(self):
        scan = self.validator.scan_iommu_groups()
        self.assertEqual(scan["status"], "success")
        self.assertTrue(scan["iommu_enabled"])
        self.assertGreater(scan["total_groups"], 0)
        self.assertIn("1", scan["groups"])

    def test_validate_device_isolation_clean_group(self):
        res = self.validator.validate_device_isolation("0000:01:00.0")
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["isolated"])
        self.assertEqual(res["group_id"], "1")

if __name__ == "__main__":
    unittest.main()
