#!/usr/bin/env python3
# AI-hint: Unit and integration tests for bootable hybrid ISO generator and serial IPMI console redirection.
# AI-related: usr/libexec/mios/deploy/iso_generate.py, usr/share/mios/mios.toml, usr/libexec/mios/deploy/baremetal_install.py
"""Unit and integration test suite for IsoGeneratorEngine and CLI."""

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
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "deploy", "iso_generate.py")

spec = importlib.util.spec_from_file_location("iso_generate", _TARGET_PATH)
if spec and spec.loader:
    iso_generate = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = iso_generate
    spec.loader.exec_module(iso_generate)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")


class TestIsoGenerate(unittest.TestCase):
    """Test suite for dual UEFI/BIOS ISO staging, isolinux/grub configuration, xorriso arguments, and CLI."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="mios-test-iso-")
        self.staging_dir = os.path.join(self.temp_dir.name, "staging")
        self.output_iso = os.path.join(self.temp_dir.name, "output.iso")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_build_kernel_cmdline_serial_console(self):
        engine = iso_generate.IsoGeneratorEngine(
            serial_baud=115200,
            mock=True,
        )
        cmdline = engine.build_kernel_cmdline()
        self.assertIn("console=tty0", cmdline)
        self.assertIn("console=ttyS0,115200n8", cmdline)
        self.assertIn("mios.live=1", cmdline)

    def test_generate_isolinux_and_grub_cfg(self):
        engine = iso_generate.IsoGeneratorEngine(
            serial_baud=115200,
            mock=True,
        )
        cmdline = engine.build_kernel_cmdline()

        iso_cfg = engine.generate_isolinux_cfg(cmdline)
        self.assertIn("serial 0 115200", iso_cfg)
        self.assertIn(cmdline, iso_cfg)

        grub_cfg = engine.generate_grub_cfg(cmdline)
        self.assertIn("serial --unit=0 --speed=115200", grub_cfg)
        self.assertIn("terminal_input console serial", grub_cfg)
        self.assertIn("terminal_output console serial", grub_cfg)

    def test_plan_and_populate_staging_tree(self):
        engine = iso_generate.IsoGeneratorEngine(
            staging_dir=self.staging_dir,
            output_iso=self.output_iso,
            volid="MIOS_TEST",
            mock=False,
        )
        plan = engine.plan_iso()

        self.assertEqual(plan.volume_id, "MIOS_TEST")
        self.assertTrue(plan.has_uefi_bootloader)
        self.assertTrue(plan.has_bios_bootloader)
        self.assertIn("xorriso", plan.xorriso_command)
        self.assertIn("-isohybrid-gpt-basdat", plan.xorriso_command)

        # Check created config files
        iso_cfg_path = os.path.join(self.staging_dir, "isolinux", "isolinux.cfg")
        grub_cfg_path = os.path.join(self.staging_dir, "EFI", "BOOT", "grub.cfg")
        self.assertTrue(os.path.exists(iso_cfg_path))
        self.assertTrue(os.path.exists(grub_cfg_path))

    def test_execute_iso_build_mock(self):
        engine = iso_generate.IsoGeneratorEngine(
            staging_dir=self.staging_dir,
            output_iso=self.output_iso,
            mock=True,
        )
        res = engine.run()
        self.assertEqual(res["status"], "success")
        self.assertGreaterEqual(len(res["commands_executed"]), 1)
        self.assertIn("xorriso", res["commands_executed"][0])

    def test_cli_execution_mock_json(self):
        test_args = [
            "iso_generate.py",
            "--staging-dir", self.staging_dir,
            "--output-iso", self.output_iso,
            "--volid", "MIOS_LIVE",
            "--serial-baud", "115200",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = iso_generate.main()
            self.assertEqual(exit_code, 0)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestIsoGenerate)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
