#!/usr/bin/env python3
# AI-hint: Automated unit test suite for multi-surface live theme rendering and DBus/socket broadcast (T-499, T-500).
# AI-doc: usr/share/doc/mios/manual/ch68-living-wallpaper-shaders-and-ssot-theme-engine.md
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_RENDER_BIN = os.path.join(_ROOT, "usr", "libexec", "mios", "mios-theme-render")
_BROADCAST_BIN = os.path.join(_ROOT, "usr", "libexec", "mios", "mios-theme-broadcast")


class TestThemeLiveRender(unittest.TestCase):
    """Validates mios-theme-render and mios-theme-broadcast."""

    def test_binaries_exist_and_executable(self):
        self.assertTrue(os.path.isfile(_RENDER_BIN), f"Missing {_RENDER_BIN}")
        self.assertTrue(os.access(_RENDER_BIN, os.X_OK), f"Not executable {_RENDER_BIN}")
        self.assertTrue(os.path.isfile(_BROADCAST_BIN), f"Missing {_BROADCAST_BIN}")
        self.assertTrue(os.access(_BROADCAST_BIN, os.X_OK), f"Not executable {_BROADCAST_BIN}")

    def test_theme_render_dry_run_json(self):
        res = subprocess.run(
            [sys.executable, _RENDER_BIN, "--dry-run", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(res.stdout)
        self.assertEqual(data.get("status"), "success")
        self.assertTrue(data.get("dry_run"))

        colors = data.get("colors", {})
        self.assertIn("bg", colors)
        self.assertIn("fg", colors)
        self.assertIn("accent", colors)

        surfaces = data.get("surfaces", {})
        self.assertIn("gtk", surfaces)
        self.assertIn("qt", surfaces)
        self.assertIn("pty", surfaces)

        # Check GTK targets
        gtk_targets = surfaces["gtk"]
        self.assertTrue(any("gtk-4.0" in p for p in gtk_targets))
        self.assertTrue(any("gtk-3.0" in p for p in gtk_targets))

    def test_theme_broadcast_dry_run_json(self):
        res = subprocess.run(
            [sys.executable, _BROADCAST_BIN, "--dry-run", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(res.stdout)
        self.assertEqual(data.get("status"), "success")
        self.assertIn(data.get("color_scheme"), ["prefer-dark", "default"])
        self.assertTrue(data.get("is_dark"))

        dbus_res = data.get("dbus", {})
        self.assertEqual(dbus_res.get("color_scheme"), "prefer-dark")
        self.assertTrue(dbus_res.get("dry_run"))

        sock_res = data.get("wallpaper_socket", {})
        self.assertIn("mios-wallpaper", sock_res.get("socket_path", ""))
        self.assertTrue(sock_res.get("dry_run"))

        self.assertTrue(data.get("theme_render_triggered"))


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestThemeLiveRender)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
