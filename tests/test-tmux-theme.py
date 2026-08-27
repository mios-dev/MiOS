#!/usr/bin/env python3
# AI-hint: Automated unit test suite for tmux theme and status line generator.
# AI-related: usr/libexec/mios/ux/tmux_theme.py, usr/share/mios/mios.toml
"""Unit and integration test suite for TmuxThemeEngine and tmux_theme CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "ux", "tmux_theme.py")

spec = importlib.util.spec_from_file_location("tmux_theme", _TARGET_PATH)
if spec and spec.loader:
    tmux_theme = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = tmux_theme
    spec.loader.exec_module(tmux_theme)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestTmuxTheme(unittest.TestCase):
    """Test suite for tmux theme rendering across powerline, rounded, and minimal styles."""

    def test_engine_init_and_palette(self):
        engine = tmux_theme.TmuxThemeEngine(style="powerline", status_position="top", mock=True)
        self.assertEqual(engine.style, "powerline")
        self.assertEqual(engine.status_position, "top")
        self.assertIn("bg", engine.palette)
        self.assertIn("accent", engine.palette)
        self.assertIn("cursor", engine.palette)

    def test_generate_powerline_config(self):
        engine = tmux_theme.TmuxThemeEngine(style="powerline", mock=True)
        cfg = engine.generate_config()
        self.assertIn("# MiOS Canonical Tmux Theme", cfg)
        self.assertIn("set -g status on", cfg)
        self.assertIn("set -g pane-active-border-style", cfg)
        self.assertIn("", cfg)
        self.assertIn("", cfg)

    def test_generate_rounded_config(self):
        engine = tmux_theme.TmuxThemeEngine(style="rounded", mock=True)
        cfg = engine.generate_config()
        self.assertIn("", cfg)
        self.assertIn("", cfg)

    def test_generate_minimal_config(self):
        engine = tmux_theme.TmuxThemeEngine(style="minimal", mock=True)
        cfg = engine.generate_config()
        self.assertIn("# Minimal Status Line Formatting", cfg)
        self.assertIn("set -g status-left", cfg)

    def test_run_pipeline(self):
        engine = tmux_theme.TmuxThemeEngine(mock=True)
        res = engine.run()
        self.assertEqual(res["status"], "success")
        self.assertGreater(res["config_lines"], 15)
        self.assertTrue(res["mock"])

    def test_cli_render_powerline_mock(self):
        test_args = ["tmux_theme.py", "--render", "--style", "powerline", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = tmux_theme.main()
            self.assertEqual(exit_code, 0)

    def test_cli_render_rounded_mock(self):
        test_args = ["tmux_theme.py", "--render", "--style", "rounded", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = tmux_theme.main()
            self.assertEqual(exit_code, 0)

    def test_cli_render_minimal_mock(self):
        test_args = ["tmux_theme.py", "--render", "--style", "minimal", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = tmux_theme.main()
            self.assertEqual(exit_code, 0)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTmuxTheme)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
