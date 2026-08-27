#!/usr/bin/env python3
# AI-hint: Unit and integration tests for Windows 11 autounattend.xml generator.
# AI-related: usr/libexec/mios/win/unattend_gen.py, usr/share/mios/mios.toml, usr/libexec/mios/win/ps_policy_config.py
"""Unit and integration test suite for UnattendGenerator and CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "win", "unattend_gen.py")

spec = importlib.util.spec_from_file_location("unattend_gen", _TARGET_PATH)
if spec and spec.loader:
    unattend_gen = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = unattend_gen
    spec.loader.exec_module(unattend_gen)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestUnattendGen(unittest.TestCase):
    """Test suite for Windows 11 XML answer file generation, pass structure, bypasses, and presets."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="mios-test-unattend-")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_generate_xml_tree_structure(self):
        cfg = unattend_gen.UnattendConfig(
            preset=unattend_gen.Preset.DEVELOPER,
            username="mios",
            computer_name="MiOS-DevNode",
            driver_path="M:\\drivers",
            bypass_tpm=True,
            bypass_secure_boot=True,
            disable_telemetry=True,
            enable_dev_mode=True,
            enable_wsl2=True,
        )
        gen = unattend_gen.UnattendGenerator(cfg, mock=True)
        xml_str = gen.generate_xml_string()

        self.assertIn("<?xml", xml_str)
        self.assertIn(unattend_gen.UNATTEND_NS, xml_str)
        self.assertIn("BypassTPMCheck", xml_str)
        self.assertIn("BypassSecureBootCheck", xml_str)
        self.assertIn("AllowTelemetry", xml_str)
        self.assertIn("AllowDevelopmentWithoutDevLicense", xml_str)
        self.assertIn("AutoLogon", xml_str)
        self.assertIn("MiOS-DevNode", xml_str)

    def test_run_writes_valid_xml_file(self):
        out_file = os.path.join(self.temp_dir.name, "autounattend.xml")
        cfg = unattend_gen.UnattendConfig(
            preset=unattend_gen.Preset.MINIMAL,
            username="operator",
        )
        gen = unattend_gen.UnattendGenerator(cfg, mock=False)
        res = gen.run(output_path=out_file)

        self.assertEqual(res["status"], "success")
        self.assertTrue(os.path.exists(out_file))

        # Verify XML parses cleanly
        tree = ET.parse(out_file)
        root = tree.getroot()
        self.assertEqual(root.tag.split("}")[-1], "unattend")

    def test_cli_execution_mock_json(self):
        test_args = [
            "unattend_gen.py",
            "--preset", "developer",
            "--username", "mios",
            "--computer-name", "MiOS-Test",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = unattend_gen.main()
            self.assertEqual(exit_code, 0)

    def test_cli_execution_emit_xml(self):
        test_args = [
            "unattend_gen.py",
            "--emit-xml",
            "--mock",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = unattend_gen.main()
            self.assertEqual(exit_code, 0)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUnattendGen)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
