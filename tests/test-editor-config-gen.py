#!/usr/bin/env python3
# AI-hint: Automated unit test suite for VS Code, Cursor, and Continue local AI config generator.
# AI-related: usr/libexec/mios/ux/editor_config_gen.py, usr/share/mios/mios.toml
"""Unit and integration test suite for EditorConfigGen and editor_config_gen CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "ux", "editor_config_gen.py")

spec = importlib.util.spec_from_file_location("editor_config_gen", _TARGET_PATH)
if spec and spec.loader:
    editor_config_gen = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = editor_config_gen
    spec.loader.exec_module(editor_config_gen)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")


class TestEditorConfigGen(unittest.TestCase):
    """Test suite for developer editor (VS Code, Cursor, Continue) local AI redirection generation."""

    def test_editor_config_gen_init(self):
        gen = editor_config_gen.EditorConfigGen(
            inference_endpoint="http://localhost:11450/v1",
            embed_model="nomic-embed-text",
            mock=True,
        )
        self.assertTrue(gen.agent_endpoint.startswith("http://localhost:"))
        self.assertEqual(gen.inference_endpoint, "http://localhost:11450/v1")
        self.assertTrue(len(gen.default_model) > 0)
        self.assertEqual(gen.embed_model, "nomic-embed-text")

    def test_render_vscode_settings(self):
        gen = editor_config_gen.EditorConfigGen(mock=True)
        vscode = gen.render_vscode_settings()
        self.assertIn("github.copilot.advanced", vscode)
        self.assertIn("openai.apiBase", vscode)
        self.assertIn("openai.model", vscode)
        self.assertEqual(vscode["openai.apiBase"], gen.agent_endpoint)
        self.assertEqual(vscode["openai.model"], gen.default_model)

    def test_render_cursor_settings(self):
        gen = editor_config_gen.EditorConfigGen(mock=True)
        cursor = gen.render_cursor_settings()
        self.assertIn("cursor.general.openAiBaseUrl", cursor)
        self.assertIn("cursor.general.customModels", cursor)
        custom_models = [m["name"] for m in cursor["cursor.general.customModels"]]
        self.assertIn(gen.default_model, custom_models)
        self.assertIn("mios-llm-light", custom_models)

    def test_render_continue_config(self):
        gen = editor_config_gen.EditorConfigGen(mock=True)
        cont = gen.render_continue_config()
        self.assertIn("models", cont)
        self.assertIn("tabAutocompleteModel", cont)
        self.assertIn("embeddingsProvider", cont)
        self.assertEqual(cont["embeddingsProvider"]["model"], "nomic-embed-text")

    def test_generate_all_targets(self):
        gen = editor_config_gen.EditorConfigGen(mock=True)
        res = gen.generate(target="all")
        self.assertEqual(res["status"], "success")
        self.assertIn("vscode", res["configurations"])
        self.assertIn("cursor", res["configurations"])
        self.assertIn("continue", res["configurations"])
        self.assertEqual(len(res["files"]), 3)

    def test_check_mock(self):
        gen = editor_config_gen.EditorConfigGen(mock=True)
        check_res = gen.check("mock-settings.json")
        self.assertEqual(check_res["status"], "compliant")
        self.assertTrue(check_res["local_endpoint"])
        self.assertFalse(check_res["cloud_keys_detected"])

    def test_cli_generate_all_mock(self):
        test_args = ["editor_config_gen.py", "--generate", "--target", "all", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = editor_config_gen.main()
            self.assertEqual(exit_code, 0)

    def test_cli_target_vscode_mock(self):
        test_args = ["editor_config_gen.py", "--generate", "--target", "vscode", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = editor_config_gen.main()
            self.assertEqual(exit_code, 0)

    def test_cli_check_mock(self):
        test_args = ["editor_config_gen.py", "--check", "settings.json", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = editor_config_gen.main()
            self.assertEqual(exit_code, 0)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestEditorConfigGen)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
