#!/usr/bin/env python3
# AI-hint: Unit and integration tests for Windows Wi-Fi, Ethernet & VirtIO driver slipstream servicer.
# AI-related: usr/libexec/mios/win/driver_slipstream.py, usr/share/mios/mios.toml, usr/libexec/mios/win/unattend_gen.py
"""Unit and integration test suite for DriverSlipstreamEngine and CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "win", "driver_slipstream.py")

spec = importlib.util.spec_from_file_location("driver_slipstream", _TARGET_PATH)
if spec and spec.loader:
    driver_slipstream = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = driver_slipstream
    spec.loader.exec_module(driver_slipstream)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")


class TestDriverSlipstream(unittest.TestCase):
    """Test suite for driver .inf parsing, vendor mapping, DISM command planning, and CLI."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="mios-test-driver-")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_parse_inf_file_real_synthetic(self):
        inf_path = os.path.join(self.temp_dir.name, "test_net.inf")
        with open(inf_path, "w", encoding="utf-8") as f:
            f.write(
                "[Version]\n"
                'Signature = "$Windows NT$"\n'
                "Class = Net\n"
                'ClassGuid = "{4d36e972-e325-11ce-bfc1-08002be10318}"\n'
                'Provider = "Intel Corporation"\n'
                'DriverVer = 01/15/2026, 23.30.0.6\n\n'
                "[Intel.NTamd64]\n"
                '%Intel.DeviceDesc% = Install, PCI\\VEN_8086&DEV_2725\n'
            )

        engine = driver_slipstream.DriverSlipstreamEngine(mock=False)
        pkg = engine.parse_inf_file(inf_path)

        self.assertEqual(pkg.filename, "test_net.inf")
        self.assertEqual(pkg.provider, "Intel Corporation")
        self.assertEqual(pkg.driver_class, "Net")
        self.assertEqual(pkg.vendor, "Intel")
        self.assertIn("PCI\\VEN_8086&DEV_2725", pkg.hardware_ids)

    def test_scan_driver_catalog_mock(self):
        engine = driver_slipstream.DriverSlipstreamEngine(mock=True)
        drivers = engine.scan_driver_catalog()
        self.assertGreaterEqual(len(drivers), 4)

        vendors = [d.vendor for d in drivers]
        self.assertIn("Intel", vendors)
        self.assertIn("Realtek", vendors)
        self.assertIn("Red Hat VirtIO", vendors)

    def test_build_dism_plans(self):
        engine = driver_slipstream.DriverSlipstreamEngine(
            wim_path="M:\\sources\\boot.wim",
            indices="1,2",
            driver_dir="M:\\drivers",
            mount_dir="C:\\scratch\\mount",
            mock=True,
        )
        plans = engine.build_dism_plans()
        self.assertEqual(len(plans), 2)
        self.assertEqual(plans[0].index, 1)
        self.assertEqual(plans[1].index, 2)
        self.assertIn("/Add-Driver /Driver:M:\\drivers /Recurse", plans[0].add_driver_command)
        self.assertIn("/Commit", plans[0].unmount_command)

    def test_run_mock_execution(self):
        engine = driver_slipstream.DriverSlipstreamEngine(mock=True)
        res = engine.run()
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["drivers_indexed"], 4)
        self.assertEqual(len(res["dism_plans"]), 2)
        self.assertGreaterEqual(len(res["commands_executed"]), 6)

    def test_cli_execution_mock_json(self):
        test_args = [
            "driver_slipstream.py",
            "--wim-path", "M:\\sources\\boot.wim",
            "--indices", "1,2",
            "--driver-dir", "M:\\drivers",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = driver_slipstream.main()
            self.assertEqual(exit_code, 0)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDriverSlipstream)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
