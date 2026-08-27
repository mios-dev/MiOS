#!/usr/bin/env python3
# AI-hint: Automated unit test suite for btop system monitor theme renderer.
# AI-related: usr/libexec/mios/ux/btop_theme.py, usr/share/mios/mios.toml
"""Unit and integration test suite for BtopThemeRenderer and btop_theme CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "ux", "btop_theme.py")

spec = importlib.util.spec_from_file_location("btop_theme", _TARGET_PATH)
if spec and spec.loader:
    btop_theme = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = btop_theme
    spec.loader.exec_module(btop_theme)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestBtopTheme(unittest.TestCase):
    """Test suite for btop theme rendering and exact RGB hex palette mapping."""

    def test_renderer_init_and_palette(self):
        renderer = btop_theme.BtopThemeRenderer(mock=True)
        palette = renderer.get_palette()
        self.assertIn("bg", palette)
        self.assertIn("accent", palette)
        self.assertIn("cursor", palette)

    def test_build_theme_mapping(self):
        renderer = btop_theme.BtopThemeRenderer(mock=True)
        mapping = renderer.build_theme_mapping()
        self.assertIn("main_bg", mapping)
        self.assertIn("main_fg", mapping)
        self.assertIn("cpu_box", mapping)
        self.assertIn("mem_box", mapping)
        self.assertIn("temp_start", mapping)
        self.assertIn("temp_end", mapping)
        self.assertIn("upload_start", mapping)
        self.assertIn("download_start", mapping)

    def test_render_theme_text_and_validate(self):
        renderer = btop_theme.BtopThemeRenderer(mock=True)
        text = renderer.render_theme_text()
        self.assertIn('# MiOS Btop System Monitor Theme', text)
        self.assertIn('theme[main_bg]=', text)
        self.assertIn('theme[main_fg]=', text)
        valid, errors = renderer.validate_theme_content(text)
        self.assertTrue(valid, f"Theme validation failed: {errors}")
        self.assertEqual(len(errors), 0)

    def test_validate_theme_content_invalid(self):
        renderer = btop_theme.BtopThemeRenderer(mock=True)
        invalid_text = 'theme[main_bg]="NOT_A_HEX"'
        valid, errors = renderer.validate_theme_content(invalid_text)
        self.assertFalse(valid)
        self.assertGreater(len(errors), 0)

    def test_render_mock(self):
        renderer = btop_theme.BtopThemeRenderer(mock=True)
        res = renderer.render()
        self.assertEqual(res["status"], "success")
        self.assertGreater(res["theme_len"], 100)
        self.assertTrue(res["mock"])

    def test_check_mock(self):
        renderer = btop_theme.BtopThemeRenderer(mock=True)
        check_res = renderer.check()
        self.assertEqual(check_res["status"], "valid")
        self.assertTrue(check_res["mock"])

    def test_cli_render_mock(self):
        test_args = ["btop_theme.py", "--render", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = btop_theme.main()
            self.assertEqual(exit_code, 0)

    def test_cli_check_mock(self):
        test_args = ["btop_theme.py", "--check", "mios.theme", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = btop_theme.main()
            self.assertEqual(exit_code, 0)

    def test_cli_user_flag_mock(self):
        test_args = ["btop_theme.py", "--render", "--user", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = btop_theme.main()
            self.assertEqual(exit_code, 0)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestBtopTheme)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
