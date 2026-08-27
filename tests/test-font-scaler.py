#!/usr/bin/env python3
# AI-hint: Automated unit test suite for High-DPI dynamic font size scaler.
# AI-related: usr/libexec/mios/ux/font_scaler.py, usr/share/mios/mios.toml
"""Unit and integration test suite for FontScalerEngine and font_scaler CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "ux", "font_scaler.py")

spec = importlib.util.spec_from_file_location("font_scaler", _TARGET_PATH)
if spec and spec.loader:
    font_scaler = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = font_scaler
    spec.loader.exec_module(font_scaler)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")


class TestFontScaler(unittest.TestCase):
    """Test suite for High-DPI font metric calculation and fontconfig XML generation."""

    def test_display_metrics_dataclass(self):
        m = font_scaler.DisplayMetrics(width=3840, height=2160, dpi=192.0, scale_factor=2.0)
        self.assertEqual(m.width, 3840)
        self.assertEqual(m.dpi, 192.0)
        self.assertEqual(m.scale_factor, 2.0)

    def test_detect_metrics_mock(self):
        engine = font_scaler.FontScalerEngine(mock=True)
        metrics = engine.detect_metrics()
        self.assertEqual(metrics.dpi, 192.0)
        self.assertEqual(metrics.scale_factor, 2.0)

    def test_calculate_font_config(self):
        engine = font_scaler.FontScalerEngine(mock=True)
        # 192 DPI (2x scaling)
        metrics_4k = font_scaler.DisplayMetrics(width=3840, height=2160, dpi=192.0, scale_factor=2.0)
        cfg_4k = engine.calculate_font_config(metrics_4k)
        self.assertEqual(cfg_4k.scale_factor, 2.0)
        self.assertAlmostEqual(cfg_4k.terminal_font_pt, 22.0, places=1)
        self.assertAlmostEqual(cfg_4k.desktop_font_pt, 20.0, places=1)
        self.assertEqual(cfg_4k.cursor_size_px, 48)

        # 96 DPI (1x standard)
        metrics_1080p = font_scaler.DisplayMetrics(width=1920, height=1080, dpi=96.0, scale_factor=1.0)
        cfg_1080p = engine.calculate_font_config(metrics_1080p)
        self.assertEqual(cfg_1080p.scale_factor, 1.0)
        self.assertAlmostEqual(cfg_1080p.terminal_font_pt, 11.0, places=1)
        self.assertEqual(cfg_1080p.cursor_size_px, 24)

    def test_render_fontconfig_xml(self):
        engine = font_scaler.FontScalerEngine(mock=True)
        cfg = font_scaler.ScaledFontConfig(
            dpi=192.0,
            scale_factor=2.0,
            terminal_font_pt=22.0,
            desktop_font_pt=20.0,
            code_font_pt=24.0,
            cursor_size_px=48,
            font_family="JetBrains Mono",
            text_scaling_factor=2.0,
        )
        xml = engine.render_fontconfig_xml(cfg)
        self.assertIn("<?xml version=\"1.0\"?>", xml)
        self.assertIn("<double>192.0</double>", xml)
        self.assertIn("<family>JetBrains Mono</family>", xml)
        self.assertIn("<edit name=\"antialias\" mode=\"assign\">", xml)

    def test_apply_mock(self):
        engine = font_scaler.FontScalerEngine(mock=True)
        res = engine.apply(override_dpi=144.0, override_scale=1.5)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["scaled_config"]["dpi"], 144.0)
        self.assertTrue(res["mock"])

    def test_cli_auto_mock(self):
        test_args = ["font_scaler.py", "--auto", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = font_scaler.main()
            self.assertEqual(exit_code, 0)

    def test_cli_dpi_override_mock(self):
        test_args = ["font_scaler.py", "--dpi", "192", "--scale", "2.0", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = font_scaler.main()
            self.assertEqual(exit_code, 0)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFontScaler)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
