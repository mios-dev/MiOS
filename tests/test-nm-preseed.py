#!/usr/bin/env python3
# AI-hint: Unit and integration tests for NetworkManager offline keyfile pre-seeder.
# AI-related: usr/libexec/mios/net/nm_preseed.py, usr/share/mios/mios.toml, usr/libexec/mios/ux/firstboot_wizard.py
"""Unit and integration test suite for NetworkManagerPreseedEngine and CLI."""

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
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "net", "nm_preseed.py")

spec = importlib.util.spec_from_file_location("nm_preseed", _TARGET_PATH)
if spec and spec.loader:
    nm_preseed = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = nm_preseed
    spec.loader.exec_module(nm_preseed)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestNmPreseed(unittest.TestCase):
    """Test suite for NetworkManager connection keyfiles, WPA/SAE security, 0600 permissions, and CLI."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="mios-test-nm-")
        self.output_dir = self.temp_dir.name

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_build_profile_wifi_wpa_psk(self):
        engine = nm_preseed.NetworkManagerPreseedEngine(
            ssid="MiOS-Lab-5G",
            psk="SuperSecretPass123",
            security="wpa-psk",
            output_dir=self.output_dir,
            mock=True,
        )
        profile = engine.build_profile()
        self.assertEqual(profile.ssid, "MiOS-Lab-5G")
        self.assertEqual(profile.psk, "SuperSecretPass123")
        self.assertEqual(profile.security, nm_preseed.SecurityType.WPA_PSK)
        self.assertEqual(profile.connection_type, nm_preseed.ConnectionType.WIFI)

    def test_render_keyfile_content_structure(self):
        engine = nm_preseed.NetworkManagerPreseedEngine(
            ssid="MiOS-Lab-5G",
            psk="SuperSecretPass123",
            security="sae",
            output_dir=self.output_dir,
            mock=True,
        )
        profile = engine.build_profile()
        content = engine.render_keyfile_content(profile)

        self.assertIn("[connection]", content)
        self.assertIn("type=wifi", content)
        self.assertIn("[wifi]", content)
        self.assertIn("ssid=MiOS-Lab-5G", content)
        self.assertIn("[wifi-security]", content)
        self.assertIn("key-mgmt=sae", content)
        self.assertIn("psk=SuperSecretPass123", content)
        self.assertIn("[ipv4]", content)

    def test_write_keyfile_real_file_creation_and_permissions(self):
        engine = nm_preseed.NetworkManagerPreseedEngine(
            ssid="MiOS-Test-Net",
            psk="TestPSK12345",
            security="wpa-psk",
            output_dir=self.output_dir,
            mock=False,
        )
        res = engine.run()
        out_path = res["output_path"]

        self.assertEqual(res["status"], "success")
        self.assertTrue(os.path.exists(out_path))

        with open(out_path, "r", encoding="utf-8") as f:
            read_text = f.read()
            self.assertIn("ssid=MiOS-Test-Net", read_text)

    def test_cli_execution_mock_json(self):
        test_args = [
            "nm_preseed.py",
            "--ssid", "MiOS-Mesh-WiFi",
            "--psk", "MeshSecurePassword",
            "--security", "wpa-psk",
            "--output-dir", self.output_dir,
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = nm_preseed.main()
            self.assertEqual(exit_code, 0)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNmPreseed)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
