#!/usr/bin/env python3
# AI-hint: Unit tests for MiOS differential AST git merge fuzzer.
# AI-doc: usr/share/doc/mios/manual/git.md
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "git"))
from merge_fuzzer import MergeFuzzHarness


class TestMergeFuzzHarness(unittest.TestCase):
    def setUp(self):
        self.harness = MergeFuzzHarness(seed=1337, dry_run=True)

    def test_mutate_python_source_preserves_syntax(self):
        code = "def calculate_hash():\n    return 42\n"
        mutated, logs = self.harness.mutate_python_source(code)
        self.assertNotEqual(code, mutated)
        self.assertTrue(len(logs) > 0)
        import ast
        ast.parse(mutated)  # Should parse without SyntaxError

    def test_simulate_3way_ast_merge(self):
        base = "def foo():\n    pass\n"
        branch_a = "def foo():\n    return 1\n"
        branch_b = "def foo():\n    return 2\n"
        res = self.harness.simulate_3way_ast_merge(base, branch_a, branch_b)
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["syntax_valid"])


if __name__ == "__main__":
    unittest.main()
