#!/usr/bin/env python3
# AI-hint: Regression controls for agent argv boundaries and bounded input normalization; never invokes a model.
# AI-related: usr/lib/mios/agents/opencode-gateway/server.py, usr/lib/mios/agent-pipe/mios_dispatch.py, usr/lib/mios/agent-pipe/mios_ast_diff.py
"""Exercise production input handling without network or model subprocesses."""
import ast
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATEWAY = load("usr/lib/mios/agents/opencode-gateway/server.py", "gateway_input_safety")
DIFF = load("usr/lib/mios/agent-pipe/mios_ast_diff.py", "diff_input_safety")
DISPATCH_SOURCE = (ROOT / "usr/lib/mios/agent-pipe/mios_dispatch.py").read_text(encoding="utf-8")
DISPATCH_AST = ast.parse(DISPATCH_SOURCE)
NORMALIZER = next(node for node in DISPATCH_AST.body if isinstance(node, ast.FunctionDef) and node.name == "_normalize_tool_name")
namespace = {}
exec(compile(ast.Module(body=[NORMALIZER], type_ignores=[]), "dispatcher-normalizer", "exec"), namespace)
normalize = namespace["_normalize_tool_name"]


class InputSafety(unittest.TestCase):
    def test_prompt_is_one_positional_argument(self):
        response = SimpleNamespace(stdout=json.dumps({"part": {"type": "text", "text": "answer"}}), stderr="", returncode=0)
        for prompt in ("ordinary task", "--command=touch /tmp/unwanted", "--attach=http://remote", "--auto", "-m other/model", "a\nb 'quoted'"):
            with self.subTest(prompt=prompt), patch.object(GATEWAY.subprocess, "run", return_value=response) as run:
                self.assertEqual(GATEWAY._run_opencode(prompt, "local/model"), "answer")
                argv = run.call_args.args[0]
                self.assertEqual(argv[-4:], ["-m", "local/model", "--", prompt])
                self.assertNotIn("shell", run.call_args.kwargs)
                self.assertEqual(run.call_args.kwargs["env"]["OPENCODE_CONFIG"], GATEWAY.OPENCODE_CONFIG)

    def test_invalid_selector_never_launches(self):
        for model in ("-flag/model", "local/line\nbreak", "local/carriage\rreturn", "local/nul\0value"):
            with self.subTest(model=model), patch.object(GATEWAY.subprocess, "run") as run:
                with self.assertRaisesRegex(ValueError, "invalid opencode model selector"):
                    GATEWAY._run_opencode("task", model)
                run.assert_not_called()
        self.assertEqual(GATEWAY._selector("model"), GATEWAY.OPENCODE_PROVIDER + "/model")

    def test_dispatcher_compatibility(self):
        for tool in (None, "", " web_search(query) ", "`web_search`", "'tool'", "tool(a(b))", "tool(a)\n", "tool(a\nb)", "tool(a)\nsecond(b)", "tool(a) trailing", "tool(()\r\n", "tool(a)\n\n"):
            with self.subTest(tool=tool):
                legacy = re.sub(r"\(.*?\)\s*$", "", str(tool or "").strip()).strip().strip("`'\"")
                self.assertEqual(normalize(tool), legacy)
        for name in ("_dispatch_bounded", "_dispatch_mios_verb_inner_raw"):
            function = next(node for node in DISPATCH_AST.body if isinstance(node, ast.AsyncFunctionDef) and node.name == name)
            self.assertTrue(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_normalize_tool_name" for node in ast.walk(function)))

    def test_real_comments_are_cosmetic(self):
        engine = DIFF.AstDiffEngine()
        for lang, original, modified in (
            ("rust", "fn f<'a>(x: &'a str) { // before\n x; }", "fn f<'a>(x: &'a str) { /* after */\n x; }"),
            ("typescript", 'let url = "https://local/a"; // before\n', 'let url = "https://local/a"; /* after */\n'),
            ("go", 'var s = `/* literal */ // literal`; // before\n', 'var s = `/* literal */ // literal`; // after\n'),
        ):
            with self.subTest(lang=lang):
                self.assertTrue(engine.compute_ast_diff(original, modified, lang)["is_purely_cosmetic"])

    def test_comment_markers_inside_strings_remain_semantic(self):
        engine = DIFF.AstDiffEngine()
        for before, after in (('"https://local/a"', '"https://local/b"'), ('"/* before */"', '"/* after */"'), ('`// before`', '`// after`'), ('"escaped \\\" // before"', '"escaped \\\" // after"')):
            with self.subTest(before=before):
                self.assertTrue(engine.compute_ast_diff("let x = " + before + ";", "let x = " + after + ";", "typescript")["has_semantic_diff"])

    def test_adversarial_inputs_finish_in_child_deadline(self):
        # Bound the complete production calls, not merely a regex microbenchmark.
        code = ast.get_source_segment(DISPATCH_SOURCE, NORMALIZER)
        script = "import importlib.util\n" + code + "\n"
        script += "value = '(' * 200000 + 'x'\nassert _normalize_tool_name(value) == value\n"
        script += "spec = importlib.util.spec_from_file_location('bounded_diff', " + repr(str(ROOT / "usr/lib/mios/agent-pipe/mios_ast_diff.py")) + ")\n"
        script += "m = importlib.util.module_from_spec(spec)\nspec.loader.exec_module(m)\n"
        script += "value = '/* unclosed ' * 30000\nassert m._strip_comments(value) == value\nprint('bounded input controls executed')\n"
        result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=5, check=True)
        self.assertIn("bounded input controls executed", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
