#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Hyprland and Sway window manager configuration generator.
# AI-related: usr/libexec/mios/ux/wm_config_gen.py, usr/share/mios/mios.toml
"""Unit and integration test suite for WmConfigGenEngine and wm_config_gen CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "ux", "wm_config_gen.py")

spec = importlib.util.spec_from_file_location("wm_config_gen", _TARGET_PATH)
if spec and spec.loader:
    wm_config_gen = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = wm_config_gen
    spec.loader.exec_module(wm_config_gen)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestWmConfigGen(unittest.TestCase):
    """Test suite for Hyprland and Sway compositor config generation and hot-reloading."""

    def test_engine_init_and_palette(self):
        engine = wm_config_gen.WmConfigGenEngine(gaps_inner=6, gaps_outer=12, border_size=3, mock=True)
        self.assertEqual(engine.gaps_inner, 6)
        self.assertEqual(engine.gaps_outer, 12)
        self.assertEqual(engine.border_size, 3)
        self.assertIn("bg", engine.palette)
        self.assertIn("accent", engine.palette)
        self.assertIn("cursor", engine.palette)

    def test_generate_hyprland_conf(self):
        engine = wm_config_gen.WmConfigGenEngine(mock=True)
        conf = engine.generate_hyprland_conf()
        self.assertIn("# MiOS Hyprland Configuration", conf)
        self.assertIn("monitor=,preferred,auto,1", conf)
        self.assertIn("general {", conf)
        self.assertIn("gaps_in = 5", conf)
        self.assertIn("gaps_out = 10", conf)
        self.assertIn("col.active_border =", conf)
        self.assertIn("decoration {", conf)
        self.assertIn("animations {", conf)
        self.assertIn("bind = $mod, Return, exec, alacritty", conf)

    def test_generate_sway_config(self):
        engine = wm_config_gen.WmConfigGenEngine(mock=True)
        conf = engine.generate_sway_config()
        self.assertIn("# MiOS Sway Configuration", conf)
        self.assertIn("set $mod Mod4", conf)
        self.assertIn("font pango:DejaVu Sans Mono 10", conf)
        self.assertIn("gaps inner 5", conf)
        self.assertIn("client.focused", conf)
        self.assertIn("bindsym $mod+Return exec alacritty", conf)

    def test_trigger_reload_mock(self):
        engine = wm_config_gen.WmConfigGenEngine(mock=True)
        res_h = engine.trigger_reload("hyprland")
        self.assertTrue(res_h["reloaded"])
        res_s = engine.trigger_reload("sway")
        self.assertTrue(res_s["reloaded"])

    def test_run_pipeline(self):
        engine = wm_config_gen.WmConfigGenEngine(mock=True)
        res = engine.run(wm="all", reload_active=True)
        self.assertEqual(res["status"], "success")
        self.assertGreater(res["hyprland_lines"], 20)
        self.assertGreater(res["sway_lines"], 20)
        self.assertIn("hyprland", res["reload"])
        self.assertIn("sway", res["reload"])
        self.assertTrue(res["mock"])

    def test_cli_hyprland_mock(self):
        test_args = ["wm_config_gen.py", "--wm", "hyprland", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = wm_config_gen.main()
            self.assertEqual(exit_code, 0)

    def test_cli_sway_mock(self):
        test_args = ["wm_config_gen.py", "--wm", "sway", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = wm_config_gen.main()
            self.assertEqual(exit_code, 0)

    def test_cli_all_reload_mock(self):
        test_args = ["wm_config_gen.py", "--wm", "all", "--reload", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = wm_config_gen.main()
            self.assertEqual(exit_code, 0)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestWmConfigGen)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
