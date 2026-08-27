#!/usr/bin/env python3
# AI-hint: Automated unit test suite for GBNF Grammar Constrained Decoding (T-685, T-686).
# AI-related: usr/lib/mios/ai/grammar_decode.py, tests/test-grammar-decode.py
"""Automated unit test suite for MiOS GBNF Grammar Compiler."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "lib", "mios", "ai"))

from grammar_decode import GBNFGrammarCompiler

class TestGrammarDecode(unittest.TestCase):
    def setUp(self):
        self.compiler = GBNFGrammarCompiler(dry_run=True)

    def test_schema_compilation_to_gbnf(self):
        """Test compiling JSON schema produces valid GBNF rules and schema-compliant JSON."""
        schema = {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "priority": {"type": "integer"},
                "is_active": {"type": "boolean"},
            },
            "required": ["task_id", "priority"],
        }
        res = self.compiler.compile_schema_to_gbnf("task_schema", schema)
        self.assertTrue(res.is_valid_grammar)
        self.assertGreater(res.gbnf_rules_count, 0)
        self.assertTrue(self.compiler.validate_constrained_json(res.sample_valid_json))

    def test_zero_syntax_errors_across_100_synthetic_schemas(self):
        """Test 100 generated JSON schemas all parse with 0 syntax errors."""
        for i in range(100):
            schema = {
                "type": "object",
                "properties": {
                    f"field_{j}": {"type": "string" if j % 2 == 0 else "integer"}
                    for j in range(5)
                },
            }
            res = self.compiler.compile_schema_to_gbnf(f"schema_{i}", schema)
            self.assertTrue(self.compiler.validate_constrained_json(res.sample_valid_json))

if __name__ == "__main__":
    unittest.main()
