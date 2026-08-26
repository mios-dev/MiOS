# AI-hint: Structured output JSON schema compiler utilizing constrained decoding grammar engines.
# AI-related: usr/lib/mios/agent-pipe/server.py, tests/test-json-grammar-compiler.py
"""
MiOS Agent-Pipe JSON Schema to GBNF Grammar Compiler.
Converts standard JSON Schema definitions into GBNF grammar constraints for llama.cpp / vLLM.
"""

from __future__ import annotations

import json
from typing import Any, Dict


class JsonGrammarCompiler:
    """Compiles JSON schemas to GBNF (Grammar BNF) syntax strings."""

    def compile_schema(self, schema: Dict[str, Any]) -> str:
        """Converts basic JSON schema properties to GBNF grammar rules."""
        schema_type = schema.get("type", "object")
        if schema_type != "object":
            return "root ::= [^\\x00]*"

        properties = schema.get("properties", {})
        required = set(schema.get("required", []))

        rules = ['root ::= "{" ws object-body ws "}"']
        prop_rules = []

        for prop_name, prop_def in properties.items():
            ptype = prop_def.get("type", "string")
            rule_ref = f"prop-{prop_name}"
            if ptype == "string":
                val_rule = '"\"" [^"\\]* "\""'
            elif ptype == "integer" or ptype == "number":
                val_rule = '[0-9]+'
            elif ptype == "boolean":
                val_rule = '("true" | "false")'
            else:
                val_rule = '[^\\x00]*'

            prop_rules.append(f'{rule_ref} ::= "\"{prop_name}\"" ws ":" ws {val_rule}')

        if prop_rules:
            rules.append("object-body ::= " + " ( \",\" ws )? ".join(prop_rules))
            rules.extend(prop_rules)
        else:
            rules.append('object-body ::= ""')

        rules.append('ws ::= [ \t\n\r]*')
        return "\n".join(rules)
