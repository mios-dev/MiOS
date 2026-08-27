#!/usr/bin/env python3
# AI-hint: Automated unit test suite for T-550 Cockpit CephFS integration module.
# AI-related: usr/libexec/mios/storage/cockpit_ceph.py, tests/test-cockpit-ceph.py
"""Automated tests for Cockpit CephFS & Storage Telemetry Backend (T-550)."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_MODULE_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "storage", "cockpit_ceph.py")

spec = importlib.util.spec_from_file_location("cockpit_ceph", _MODULE_PATH)
if spec and spec.loader:
    cockpit_ceph = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = cockpit_ceph
    spec.loader.exec_module(cockpit_ceph)
else:
    raise ImportError(f"Could not load cockpit_ceph module from {_MODULE_PATH}")


class TestCockpitCeph(unittest.TestCase):
    """Validates CephFS pool metrics, drive encryption telemetry, and Cockpit manifest generation."""

    def setUp(self) -> None:
        self.mgr = cockpit_ceph.CockpitCephManager(mock=True)
        self.tmp_dir = tempfile.mkdtemp(prefix="mios_test_ceph_")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_get_ceph_status_mock(self) -> None:
        """Asserts correct retrieval of mock CephFS cluster status and tiered pools."""
        status = self.mgr.get_ceph_status()
        self.assertEqual(status.health_status, "HEALTH_OK")
        self.assertEqual(len(status.pools), 3)

        hot_pool = next(p for p in status.pools if p.pool_name == "cephfs-data-hot")
        self.assertEqual(hot_pool.tier_type, "hot_nvme")
        self.assertEqual(hot_pool.pg_num, 128)
        self.assertGreater(hot_pool.read_iops, 1000)

        cold_pool = next(p for p in status.pools if p.pool_name == "cephfs-data-cold")
        self.assertEqual(cold_pool.tier_type, "cold_hdd")

    def test_get_smart_metrics_mock(self) -> None:
        """Asserts SMART metrics and encryption status for physical drives."""
        drives = self.mgr.get_smart_metrics()
        self.assertEqual(len(drives), 2)
        
        nvme = next(d for d in drives if d.device == "/dev/nvme0n1")
        self.assertEqual(nvme.type, "opal2")
        self.assertTrue(nvme.locked)
        self.assertEqual(nvme.smart_health, "PASSED")

        sda = next(d for d in drives if d.device == "/dev/sda")
        self.assertEqual(sda.type, "luks2")
        self.assertTrue(sda.tpm_sealed)

    def test_generate_cockpit_manifest(self) -> None:
        """Asserts generation of Cockpit manifest JSON."""
        out_file = os.path.join(self.tmp_dir, "manifest.json")
        manifest = self.mgr.generate_cockpit_manifest(output_path=out_file)
        self.assertEqual(manifest["name"], "mios-storage")
        self.assertIn("tools", manifest)
        self.assertTrue(os.path.exists(out_file))

        with open(out_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["name"], "mios-storage")

    def test_cli_pools_json(self) -> None:
        """Asserts CLI execution with --pools --mock --json."""
        with patch("sys.argv", ["cockpit_ceph.py", "--pools", "--mock", "--json"]):
            with patch("builtins.print") as mock_print:
                ret = cockpit_ceph.main()
                self.assertEqual(ret, 0)
                mock_print.assert_called()
                parsed = json.loads(mock_print.call_args[0][0])
                self.assertEqual(parsed["status"], "ok")
                self.assertIn("pools", parsed)

    def test_cli_smart_json(self) -> None:
        """Asserts CLI execution with --smart --mock --json."""
        with patch("sys.argv", ["cockpit_ceph.py", "--smart", "--mock", "--json"]):
            with patch("builtins.print") as mock_print:
                ret = cockpit_ceph.main()
                self.assertEqual(ret, 0)
                mock_print.assert_called()
                parsed = json.loads(mock_print.call_args[0][0])
                self.assertEqual(parsed["status"], "ok")
                self.assertIn("drives", parsed)


if __name__ == "__main__":
    unittest.main()
