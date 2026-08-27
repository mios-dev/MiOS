#!/usr/bin/env python3
# AI-hint: Automated unit test suite for fastfetch JSONC configuration generator.
# AI-related: usr/libexec/mios/ux/fastfetch_gen.py, usr/share/mios/mios.toml
"""Unit and integration test suite for FastfetchGenEngine and fastfetch_gen CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "ux", "fastfetch_gen.py")

spec = importlib.util.spec_from_file_location("fastfetch_gen", _TARGET_PATH)
if spec and spec.loader:
    fastfetch_gen = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = fastfetch_gen
    spec.loader.exec_module(fastfetch_gen)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestFastfetchGen(unittest.TestCase):
    """Test suite for Fastfetch JSONC configuration and hardware/AI module generation."""

    def test_engine_init_and_palette(self):
        engine = fastfetch_gen.FastfetchGenEngine(logo_type="auto", mock=True)
        self.assertEqual(engine.logo_type, "auto")
        self.assertIn("bg", engine.palette)
        self.assertIn("accent", engine.palette)

    def test_inspect_system_metadata_mock(self):
        engine = fastfetch_gen.FastfetchGenEngine(mock=True)
        meta = engine.inspect_system_metadata()
        self.assertEqual(meta["os_name"], "MiOS Linux (bootc/OCI workstation)")
        self.assertIn("llama-swap", meta["ai_engine"])
        self.assertEqual(meta["active_model"], "Qwen2.5-Coder-7B-Instruct-GGUF")
        self.assertIn("ghcr.io/mios-dev/mios", meta["bootc_image"])

    def test_generate_jsonc_validity(self):
        engine = fastfetch_gen.FastfetchGenEngine(mock=True)
        jsonc_str = engine.generate_jsonc()
        parsed = json.loads(jsonc_str)
        self.assertIn("$schema", parsed)
        self.assertIn("modules", parsed)
        module_types = [m.get("type") for m in parsed["modules"]]
        self.assertIn("os", module_types)
        self.assertIn("cpu", module_types)
        self.assertIn("gpu", module_types)
        self.assertIn("memory", module_types)
        self.assertIn("custom", module_types)

    def test_run_pipeline(self):
        engine = fastfetch_gen.FastfetchGenEngine(mock=True)
        res = engine.run()
        self.assertEqual(res["status"], "success")
        self.assertGreater(res["jsonc_lines"], 10)
        self.assertTrue(res["mock"])

    def test_cli_generate_mock(self):
        test_args = ["fastfetch_gen.py", "--generate", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = fastfetch_gen.main()
            self.assertEqual(exit_code, 0)

    def test_cli_logo_type_mock(self):
        test_args = ["fastfetch_gen.py", "--logo-type", "none", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = fastfetch_gen.main()
            self.assertEqual(exit_code, 0)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFastfetchGen)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
