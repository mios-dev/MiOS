#!/usr/bin/env python3
# AI-hint: Unit tests for MiOS Libei synthetic input injector.
# AI-doc: usr/share/doc/mios/manual/desktop.md
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "ui"))
from libei_input import LibeiInputInjector

class TestLibeiInputInjector(unittest.TestCase):
    def setUp(self):
        self.injector = LibeiInputInjector(display_width=1920, display_height=1080, dry_run=True)

    def test_normalize_normalized_coordinates(self):
        px, py = self.injector.normalize_coordinates(0.5, 0.5)
        self.assertEqual(px, 960)
        self.assertEqual(py, 540)

    def test_normalize_absolute_and_clamped_coordinates(self):
        px, py = self.injector.normalize_coordinates(500, 300)
        self.assertEqual(px, 500)
        self.assertEqual(py, 300)

        # Clamping out-of-bounds
        px, py = self.injector.normalize_coordinates(2500, -100)
        self.assertEqual(px, 1919)
        self.assertEqual(py, 0)

    def test_emit_click_dry_run(self):
        res = self.injector.emit_click(0.25, 0.75, button="BTN_RIGHT")
        self.assertEqual(res["status"], "dry_run")
        self.assertEqual(res["button"], "BTN_RIGHT")
        self.assertEqual(res["coordinates"]["x"], 480)
        self.assertEqual(res["coordinates"]["y"], 810)
        self.assertTrue(res["ripple_animated"])

    def test_emit_type_dry_run(self):
        res = self.injector.emit_type("git status")
        self.assertEqual(res["status"], "dry_run")
        self.assertEqual(res["text_length"], 10)

if __name__ == "__main__":
    unittest.main()
