#!/usr/bin/env python3
# AI-hint: Automated unit test suite for living wallpaper GLSL/WGSL telemetry modulator.
# AI-related: usr/libexec/mios/ux/living_wallpaper.py, usr/share/mios/mios.toml
"""Unit and integration test suite for LivingWallpaperEngine and living_wallpaper CLI."""

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
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "ux", "living_wallpaper.py")

spec = importlib.util.spec_from_file_location("living_wallpaper", _TARGET_PATH)
if spec and spec.loader:
    living_wallpaper = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = living_wallpaper
    spec.loader.exec_module(living_wallpaper)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")


class TestLivingWallpaper(unittest.TestCase):
    """Test suite for Living Wallpaper shader generation and telemetry modulation."""

    def test_hex_to_rgb_norm(self):
        r, g, b = living_wallpaper.hex_to_rgb_norm("#FFFFFF")
        self.assertAlmostEqual(r, 1.0, places=2)
        self.assertAlmostEqual(g, 1.0, places=2)
        self.assertAlmostEqual(b, 1.0, places=2)

        r0, g0, b0 = living_wallpaper.hex_to_rgb_norm("#000000")
        self.assertAlmostEqual(r0, 0.0, places=2)
        self.assertAlmostEqual(g0, 0.0, places=2)
        self.assertAlmostEqual(b0, 0.0, places=2)

        # Invalid fallback
        fb_r, fb_g, fb_b = living_wallpaper.hex_to_rgb_norm("invalid")
        self.assertEqual((fb_r, fb_g, fb_b), (0.15, 0.13, 0.38))

    def test_engine_init_and_palette(self):
        engine = living_wallpaper.LivingWallpaperEngine(mode="dynamic", fps=120, mock=True)
        self.assertEqual(engine.mode, "dynamic")
        self.assertEqual(engine.fps, 120)
        self.assertTrue(isinstance(engine.palette, dict))
        self.assertIn("bg", engine.palette)
        self.assertIn("accent", engine.palette)
        self.assertIn("cursor", engine.palette)

    def test_sample_telemetry_mock(self):
        engine = living_wallpaper.LivingWallpaperEngine(mock=True)
        telemetry = engine.sample_telemetry()
        self.assertEqual(telemetry.cpu_percent, 32.5)
        self.assertEqual(telemetry.gpu_percent, 45.0)
        self.assertEqual(telemetry.load_factor, 0.38)
        self.assertEqual(telemetry.speed_factor, 1.45)
        self.assertEqual(telemetry.dark_mode, 1.0)

    def test_generate_glsl(self):
        engine = living_wallpaper.LivingWallpaperEngine(mock=True)
        glsl = engine.generate_glsl()
        self.assertIn("#version 330 core", glsl)
        self.assertIn("uniform float u_time;", glsl)
        self.assertIn("uniform float u_load;", glsl)
        self.assertIn("c_bg", glsl)
        self.assertIn("c_accent", glsl)
        self.assertIn("fragColor =", glsl)

    def test_generate_wgsl(self):
        engine = living_wallpaper.LivingWallpaperEngine(mock=True)
        wgsl = engine.generate_wgsl()
        self.assertIn("struct Uniforms", wgsl)
        self.assertIn("@vertex", wgsl)
        self.assertIn("@fragment", wgsl)
        self.assertIn("fs_main", wgsl)

    def test_generate_html(self):
        engine = living_wallpaper.LivingWallpaperEngine(mock=True)
        html = engine.generate_html()
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("<canvas id=\"canvas\">", html)
        self.assertIn("MiOS Telemetry Wallpaper", html)
        self.assertIn("gl.createShader", html)

    def test_run_pipeline(self):
        engine = living_wallpaper.LivingWallpaperEngine(mock=True)
        res = engine.run(render_shader=True, render_wgsl=True, render_html=True)
        self.assertEqual(res["status"], "success")
        self.assertGreater(res["glsl_lines"], 10)
        self.assertGreater(res["wgsl_lines"], 10)
        self.assertGreater(res["html_lines"], 10)
        self.assertTrue(res["mock"])

    def test_cli_render_shader_mock(self):
        test_args = ["living_wallpaper.py", "--render-shader", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = living_wallpaper.main()
            self.assertEqual(exit_code, 0)

    def test_cli_telemetry_mock(self):
        test_args = ["living_wallpaper.py", "--telemetry", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = living_wallpaper.main()
            self.assertEqual(exit_code, 0)

    def test_cli_generate_html_mock(self):
        test_args = ["living_wallpaper.py", "--generate-html", "--render-wgsl", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = living_wallpaper.main()
            self.assertEqual(exit_code, 0)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestLivingWallpaper)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
