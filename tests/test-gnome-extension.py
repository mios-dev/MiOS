#!/usr/bin/env python3
# AI-hint: Automated unit test suite for GNOME Shell top panel extension generator and validator.
# AI-related: usr/libexec/mios/ux/gnome_extension.py, usr/share/mios/mios.toml
"""Unit and integration test suite for GnomeExtensionManager and gnome_extension CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "ux", "gnome_extension.py")

spec = importlib.util.spec_from_file_location("gnome_extension", _TARGET_PATH)
if spec and spec.loader:
    gnome_extension = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = gnome_extension
    spec.loader.exec_module(gnome_extension)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestGnomeExtension(unittest.TestCase):
    """Test suite for GNOME Shell extension metadata, stylesheet, and GJS asynchronous code generation."""

    def test_manager_init_and_palette(self):
        manager = gnome_extension.GnomeExtensionManager(mock=True)
        self.assertEqual(manager.uuid, "mios-status@mios-dev.org")
        palette = manager._get_palette()
        self.assertIn("bg", palette)
        self.assertIn("accent", palette)
        self.assertIn("cursor", palette)

    def test_render_metadata(self):
        manager = gnome_extension.GnomeExtensionManager(mock=True)
        meta = manager.render_metadata()
        self.assertEqual(meta["uuid"], "mios-status@mios-dev.org")
        self.assertEqual(meta["name"], "MiOS Agent Status")
        self.assertIn("45", meta["shell-version"])
        self.assertIn("46", meta["shell-version"])
        self.assertIn("47", meta["shell-version"])
        self.assertIn("48", meta["shell-version"])

    def test_render_stylesheet(self):
        manager = gnome_extension.GnomeExtensionManager(mock=True)
        css = manager.render_stylesheet()
        self.assertIn(".mios-status-button", css)
        self.assertIn(".mios-status-icon", css)
        self.assertIn(".mios-status-menu", css)
        self.assertIn(".mios-quick-link", css)

    def test_render_extension_js(self):
        manager = gnome_extension.GnomeExtensionManager(mock=True)
        js = manager.render_extension_js()
        self.assertIn("import Soup from 'gi://Soup';", js)
        self.assertIn("const MiOSStatusIndicator = GObject.registerClass(", js)
        self.assertIn("export default class MiOSStatusExtension extends Extension", js)
        self.assertIn("enable()", js)
        self.assertIn("disable()", js)

    def test_generate_and_validate_mock(self):
        manager = gnome_extension.GnomeExtensionManager(mock=True)
        gen_res = manager.generate()
        self.assertEqual(gen_res["status"], "success")
        self.assertEqual(len(gen_res["files"]), 3)

        val_res = manager.validate()
        self.assertEqual(val_res["status"], "valid")
        self.assertEqual(len(val_res["errors"]), 0)

    def test_install_mock(self):
        manager = gnome_extension.GnomeExtensionManager(mock=True)
        inst_res = manager.install(user_mode=True)
        self.assertEqual(inst_res["status"], "success")
        self.assertTrue(inst_res["user_mode"])

    def test_cli_generate_mock(self):
        test_args = ["gnome_extension.py", "--generate", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = gnome_extension.main()
            self.assertEqual(exit_code, 0)

    def test_cli_validate_mock(self):
        test_args = ["gnome_extension.py", "--validate", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = gnome_extension.main()
            self.assertEqual(exit_code, 0)

    def test_cli_install_mock(self):
        test_args = ["gnome_extension.py", "--install", "--user", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = gnome_extension.main()
            self.assertEqual(exit_code, 0)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGnomeExtension)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
