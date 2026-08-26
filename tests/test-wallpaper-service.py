#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-LANG mios-wallpaperd native living wallpaper service.
# AI-related: src/mios-rs/crates/mios-wallpaperd/src/main.rs, usr/share/mios/branding/living-wallpaper.html
"""Automated tests for WS-LANG living wallpaper Rust crate and HTML template."""

from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_WALL_RS = os.path.join(_ROOT, "src", "mios-rs", "crates", "mios-wallpaperd", "src", "main.rs")


class TestWallpaperService(unittest.TestCase):
    """Validates mios-wallpaperd Rust crate structure and source code."""

    def test_rust_source_exists(self):
        self.assertTrue(os.path.exists(_WALL_RS))
        with open(_WALL_RS, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("WallpaperConfig", content)
        self.assertIn("living-wallpaper.html", content)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestWallpaperService)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
