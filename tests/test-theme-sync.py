#!/usr/bin/env python3
# AI-hint: Automated unit test suite for cross-platform theme and palette synchronizer.
# AI-related: usr/libexec/mios/ux/theme_sync.py, usr/share/mios/mios.toml
"""Unit and integration test suite for ThemeSyncEngine and theme_sync CLI."""

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
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "ux", "theme_sync.py")

spec = importlib.util.spec_from_file_location("theme_sync", _TARGET_PATH)
if spec and spec.loader:
    theme_sync = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = theme_sync
    spec.loader.exec_module(theme_sync)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")


class TestThemeSync(unittest.TestCase):
    """Test suite for Windows Registry, GTK3, and GTK4 theme generation and synchronization."""

    def test_hex_to_dword_conversions(self):
        # 0x00BBGGRR for Windows Console
        # Blue=#1A407F -> r=0x1A, g=0x40, b=0x7F -> (0x7F << 16) | (0x40 << 8) | 0x1A
        bgr = theme_sync.hex_to_dword_bgr("#1A407F")
        self.assertEqual(bgr, (0x7F << 16) | (0x40 << 8) | 0x1A)

        # 0xAABBGGRR for Windows DWM
        abgr = theme_sync.hex_to_dword_abgr("#1A407F", alpha=0xFF)
        self.assertEqual(abgr, (0xFF << 24) | (0x7F << 16) | (0x40 << 8) | 0x1A)

    def test_engine_init_and_palette(self):
        engine = theme_sync.ThemeSyncEngine(target="all", dark_mode=True, mock=True)
        self.assertEqual(engine.target, "all")
        self.assertTrue(engine.dark_mode)
        self.assertIn("bg", engine.palette)
        self.assertIn("accent", engine.palette)
        self.assertIn("ansi_0_black", engine.palette)

    def test_generate_windows_reg(self):
        engine = theme_sync.ThemeSyncEngine(mock=True)
        reg = engine.generate_windows_reg()
        self.assertIn("Windows Registry Editor Version 5.00", reg)
        self.assertIn("[HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize]", reg)
        self.assertIn("[HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\DWM]", reg)
        self.assertIn("[HKEY_CURRENT_USER\\Console\\MiOS]", reg)
        self.assertIn('"ColorTable00"=', reg)
        self.assertIn('"ColorTable15"=', reg)

    def test_generate_gtk3_css(self):
        engine = theme_sync.ThemeSyncEngine(mock=True)
        css = engine.generate_gtk3_css()
        self.assertIn("/* MiOS GTK3 Theme Definitions", css)
        self.assertIn("@define-color mios_bg", css)
        self.assertIn("@define-color mios_accent", css)
        self.assertIn("@define-color theme_bg_color", css)
        self.assertIn("window {", css)

    def test_generate_gtk4_css(self):
        engine = theme_sync.ThemeSyncEngine(mock=True)
        css = engine.generate_gtk4_css()
        self.assertIn("/* MiOS GTK4 Theme Definitions", css)
        self.assertIn(":root {", css)
        self.assertIn("--mios-bg:", css)
        self.assertIn("--accent-color:", css)
        self.assertIn("--window-bg-color:", css)

    def test_run_sync_pipeline(self):
        engine = theme_sync.ThemeSyncEngine(mock=True)
        res = engine.run()
        self.assertEqual(res["status"], "success")
        self.assertGreater(res["windows_reg_lines"], 10)
        self.assertGreater(res["gtk3_lines"], 10)
        self.assertGreater(res["gtk4_lines"], 10)
        self.assertTrue(res["mock"])

    def test_cli_sync_mock(self):
        test_args = ["theme_sync.py", "--sync", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = theme_sync.main()
            self.assertEqual(exit_code, 0)

    def test_cli_target_windows_mock(self):
        test_args = ["theme_sync.py", "--target", "windows", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = theme_sync.main()
            self.assertEqual(exit_code, 0)

    def test_cli_target_gtk_mock(self):
        test_args = ["theme_sync.py", "--target", "gtk3", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = theme_sync.main()
            self.assertEqual(exit_code, 0)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestThemeSync)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
