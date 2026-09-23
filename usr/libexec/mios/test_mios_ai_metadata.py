#!/usr/bin/env python3
# AI-hint: Characterization tests for MiOS native AI metadata extractor and validator.
# AI-related: usr/libexec/mios/mios-ai-metadata.py, usr/lib/mios/schemas/ai_metadata.schema.json
# AI-functions: TestAIMetadata, main

import unittest
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import importlib.util
spec = importlib.util.spec_from_file_location("mios_ai_metadata", os.path.join(_HERE, "mios-ai-metadata.py"))
mios_ai_metadata = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mios_ai_metadata)


class TestAIMetadata(unittest.TestCase):
    def test_extract_python_metadata(self):
        content = """#!/usr/bin/env python3
# AI-hint: Test python module purpose.
# AI-related: /etc/mios/foo.conf, mios-service
# AI-functions: foo, bar, BazClass
# AI-doc: usr/share/doc/mios/manual/test.md

def foo(): pass
"""
        meta = mios_ai_metadata.extract_ai_header_metadata(content, "usr/lib/test.py")
        self.assertIsNotNone(meta)
        self.assertEqual(meta["hint"], "Test python module purpose.")
        self.assertEqual(meta["related"], ["/etc/mios/foo.conf", "mios-service"])
        self.assertEqual(meta["functions"], ["foo", "bar", "BazClass"])
        self.assertEqual(meta["doc"], "usr/share/doc/mios/manual/test.md")
        self.assertEqual(meta["comment_style"], "hash")
        self.assertTrue(meta["has_shebang"])

    def test_extract_markdown_metadata(self):
        content = """<!-- AI-hint: Markdown guide for operators. -->
<!-- AI-related: /usr/share/doc/mios/concept.md -->
# Guide Title
"""
        meta = mios_ai_metadata.extract_ai_header_metadata(content, "docs/guide.md")
        self.assertIsNotNone(meta)
        self.assertEqual(meta["hint"], "Markdown guide for operators.")
        self.assertEqual(meta["related"], ["/usr/share/doc/mios/concept.md"])
        self.assertEqual(meta["comment_style"], "xml")
        self.assertFalse(meta["has_shebang"])

    def test_extract_typescript_metadata(self):
        content = """// AI-hint: TypeScript service schema.
// AI-related: schema.ts
// AI-functions: buildSchema, validate

export function buildSchema() {}
"""
        meta = mios_ai_metadata.extract_ai_header_metadata(content, "src/schema.ts")
        self.assertIsNotNone(meta)
        self.assertEqual(meta["hint"], "TypeScript service schema.")
        self.assertEqual(meta["related"], ["schema.ts"])
        self.assertEqual(meta["functions"], ["buildSchema", "validate"])
        self.assertEqual(meta["comment_style"], "slash")

    def test_schema_compliance_predicate(self):
        catalog = {
            "format": "openai_strict_schema_v1",
            "entries": [
                {
                    "path": "test/path.sh",
                    "hint": "Test hint",
                    "related": ["dep.sh"],
                    "functions": ["run"],
                    "doc": None,
                    "comment_style": "hash",
                    "has_shebang": True,
                }
            ],
        }
        self.assertTrue(mios_ai_metadata.validate_schema_compliance(catalog))


if __name__ == "__main__":
    unittest.main()
