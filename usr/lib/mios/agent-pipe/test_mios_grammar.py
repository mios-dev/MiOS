#!/usr/bin/env python3
# AI-hint: Standalone unit test for mios_grammar sibling module.
# AI-doc: usr/share/doc/mios/manual/agent-pipe.md
"""Unit tests for mios_grammar."""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from mios_grammar import JsonGrammarCompiler

_fails = 0

def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))

def main():
    compiler = JsonGrammarCompiler()
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"}
        },
        "required": ["name"]
    }
    gbnf = compiler.compile_schema(schema)
    check("gbnf generated", isinstance(gbnf, str) and len(gbnf) > 0)
    check("root rule present", "root ::=" in gbnf)

    if _fails > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
