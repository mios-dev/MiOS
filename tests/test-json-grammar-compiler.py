#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-AI JSON schema to GBNF grammar compiler.
# AI-related: usr/lib/mios/agent-pipe/mios_grammar.py
"""Automated tests for WS-AI structured output grammar compilation and rule validation."""

from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "usr", "lib", "mios", "agent-pipe"))

from mios_grammar import JsonGrammarCompiler


class TestJsonGrammarCompiler(unittest.TestCase):
    """Validates GBNF grammar rule generation for JSON schema types."""

    def test_object_schema_compilation(self):
        compiler = JsonGrammarCompiler()
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "active": {"type": "boolean"},
            },
            "required": ["name", "age"]
        }
        gbnf = compiler.compile_schema(schema)
        self.assertIn('root ::=', gbnf)
        self.assertIn('prop-name ::=', gbnf)
        self.assertIn('prop-age ::=', gbnf)
        self.assertIn('prop-active ::=', gbnf)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestJsonGrammarCompiler)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
