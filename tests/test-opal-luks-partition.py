#!/usr/bin/env python3
# AI-hint: Automated unit test suite for T-549 Hardware OPAL 2.0 SED / LUKS2 Partitioning Engine.
# AI-related: usr/libexec/mios/storage/opal_luks_partition.py, tests/test-opal-luks-partition.py
"""Automated tests for Hardware OPAL 2.0 SED / LUKS2 Partitioning Engine (T-549)."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_MODULE_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "storage", "opal_luks_partition.py")

spec = importlib.util.spec_from_file_location("opal_luks_partition", _MODULE_PATH)
if spec and spec.loader:
    opal_luks = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = opal_luks
    spec.loader.exec_module(opal_luks)
else:
    raise ImportError(f"Could not load opal_luks_partition module from {_MODULE_PATH}")


class TestOpalLuksPartition(unittest.TestCase):
    """Unit tests for OPAL 2.0 SED detection, LUKS2 TPM enrollment, and GPT partitioning."""

    def setUp(self) -> None:
        self.engine = opal_luks.OpalLuksPartitionEngine(mock=True)

    def test_scan_mock_drives(self) -> None:
        """Asserts discovery of mock NVMe (OPAL 2.0 SED) and SATA (Standard LUKS2) drives."""
        drives = self.engine.scan_drives()
        self.assertEqual(len(drives), 2)
        
        nvme = next(d for d in drives if d.path == "/dev/nvme0n1")
        self.assertTrue(nvme.is_opal2)
        self.assertTrue(nvme.is_sed)
        self.assertFalse(nvme.is_locked)

        sata = next(d for d in drives if d.path == "/dev/sda")
        self.assertFalse(sata.is_opal2)
        self.assertEqual(sata.luks_version, 2)
        self.assertTrue(sata.tpm_bound)

    def test_setup_opal_sed_success(self) -> None:
        """Asserts successful activation of OPAL 2.0 Locking Range 0 on supported drive."""
        res = self.engine.setup_opal_sed("/dev/nvme0n1", admin_password="TestPassword123!")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["locking_range"], 0)
        self.assertTrue(res["locked"])

        # Check that state updated
        drives = self.engine.scan_drives()
        nvme = next(d for d in drives if d.path == "/dev/nvme0n1")
        self.assertTrue(nvme.is_locked)

    def test_setup_opal_sed_unsupported_error(self) -> None:
        """Asserts error when attempting OPAL 2.0 configuration on non-SED drive."""
        with self.assertRaises(RuntimeError):
            self.engine.setup_opal_sed("/dev/sda", admin_password="TestPassword123!")

    def test_setup_luks2_tpm(self) -> None:
        """Asserts LUKS2 volume initialization and TPM 2.0 PCR enrollment."""
        res = self.engine.setup_luks2_tpm("/dev/nvme0n1p2", pcr_list=[7, 11])
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["luks_version"], 2)
        self.assertTrue(res["tpm_bound"])
        self.assertEqual(res["pcrs"], [7, 11])

    def test_apply_partition_layout_default(self) -> None:
        """Asserts default partition layout generation (ESP, Root, Home, Data)."""
        res = self.engine.apply_partition_layout("/dev/nvme0n1")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["partitions_created"], 4)
        self.assertEqual(res["table_type"], "gpt")

    def test_apply_partition_layout_custom(self) -> None:
        """Asserts custom partition specification application."""
        custom_layout = [
            opal_luks.PartitionSpec(name="ESP", size_gb=0.5, fs_type="vfat", mount_point="/boot/efi", part_num=1),
            opal_luks.PartitionSpec(name="Ceph-OSD", size_gb=0.0, fs_type="raw", mount_point="/var/lib/ceph", part_num=2),
        ]
        res = self.engine.apply_partition_layout("/dev/nvme0n1", layout=custom_layout)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["partitions_created"], 2)

    def test_cli_scan_json(self) -> None:
        """Asserts CLI execution with --scan --mock --json."""
        with patch("sys.argv", ["opal_luks_partition.py", "--scan", "--mock", "--json"]):
            with patch("builtins.print") as mock_print:
                ret = opal_luks.main()
                self.assertEqual(ret, 0)
                mock_print.assert_called()
                output_str = mock_print.call_args[0][0]
                parsed = json.loads(output_str)
                self.assertEqual(parsed["status"], "ok")
                self.assertIn("drives", parsed)


if __name__ == "__main__":
    unittest.main()
