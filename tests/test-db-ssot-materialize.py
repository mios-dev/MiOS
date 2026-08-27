#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-VECTOR database SSOT config TOML materialization.
# AI-related: usr/libexec/mios/materialize-config-toml.py, usr/share/doc/mios/manual/ch66-v5-authority-inversion-and-cephfs-tiering.md
"""Automated tests for WS-VECTOR live database SSOT TOML serialization and formatting."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_MAT_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "materialize-config-toml.py")

spec = importlib.util.spec_from_file_location("materialize_config_toml", _MAT_PATH)
if spec and spec.loader:
    mat = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mat
    spec.loader.exec_module(mat)
else:
    raise ImportError(f"Could not load materialize-config-toml module from {_MAT_PATH}")

class TestDBSSOTMaterialize(unittest.TestCase):
    """Validates TOML key escaping, value formatting, list/dict serialization, and integrity."""

    def test_key_escaping(self):
        self.assertEqual(mat.escape_toml_key("simple_key"), "simple_key")
        self.assertEqual(mat.escape_toml_key("hyphen-key-123"), "hyphen-key-123")
        self.assertEqual(mat.escape_toml_key("dotted.key"), '"dotted.key"')
        self.assertEqual(mat.escape_toml_key("space key"), '"space key"')

    def test_value_formatting(self):
        self.assertEqual(mat.format_toml_value(True), "true")
        self.assertEqual(mat.format_toml_value(False), "false")
        self.assertEqual(mat.format_toml_value(8600), "8600")
        self.assertEqual(mat.format_toml_value("test_val"), '"test_val"')
        self.assertEqual(mat.format_toml_value(["a", "b", 123]), '["a", "b", 123]')
        self.assertEqual(mat.format_toml_value({"port": 8640, "host": "127.0.0.1"}), '{host = "127.0.0.1", port = 8640}')

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDBSSOTMaterialize)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
