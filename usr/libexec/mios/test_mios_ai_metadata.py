#!/usr/bin/env python3
# AI-hint: Characterization tests for MiOS native AI metadata extractor and validator.
# AI-related: usr/libexec/mios/mios-ai-metadata.py, usr/lib/mios/schemas/ai_metadata.schema.json
# AI-functions: TestAIMetadata, main

import io
import contextlib
import tempfile
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
# AI-doc: usr/share/doc/mios/manual/tests.md

def foo(): pass
"""
        meta = mios_ai_metadata.extract_ai_header_metadata(content, "usr/lib/test.py")
        self.assertIsNotNone(meta)
        self.assertEqual(meta["hint"], "Test python module purpose.")
        self.assertEqual(meta["related"], ["/etc/mios/foo.conf", "mios-service"])
        self.assertEqual(meta["functions"], ["foo", "bar", "BazClass"])
        self.assertEqual(meta["doc"], "usr/share/doc/mios/manual/tests.md")
        self.assertEqual(meta["comment_style"], "hash")
        self.assertTrue(meta["has_shebang"])

    def test_extract_markdown_metadata(self):
        content = """<!-- AI-hint: Markdown guide for operators. -->
<!-- AI-related: /usr/share/doc/mios/concepts/architecture.md -->
# Guide Title
"""
        meta = mios_ai_metadata.extract_ai_header_metadata(content, "docs/guide.md")
        self.assertIsNotNone(meta)
        self.assertEqual(meta["hint"], "Markdown guide for operators.")
        self.assertEqual(meta["related"], ["/usr/share/doc/mios/concepts/architecture.md"])
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

    def _catalog(self, hint):
        return {
            "format": "openai_strict_schema_v1",
            "total_metadata_entries": 1,
            "entries": [
                {
                    "path": "usr/lib/a.sh",
                    "hint": hint,
                    "related": [],
                    "functions": [],
                    "doc": None,
                    "comment_style": "hash",
                    "has_shebang": True,
                }
            ],
        }

    def _write(self, d, text):
        path = os.path.join(d, "metadata.json")
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        return path

    def test_check_fresh_passes_on_identical_export(self):
        cat = self._catalog("same")
        with tempfile.TemporaryDirectory() as d:
            path = self._write(d, mios_ai_metadata.render_catalog_json(cat))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(mios_ai_metadata.check_export_fresh(cat, path), 0)

    def test_check_fresh_names_the_stale_entry(self):
        stale = mios_ai_metadata.render_catalog_json(self._catalog("old"))
        with tempfile.TemporaryDirectory() as d:
            path = self._write(d, stale)
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                rc = mios_ai_metadata.check_export_fresh(self._catalog("new"), path)
        self.assertEqual(rc, 1)
        self.assertIn("entry usr/lib/a.sh: differs in hint", err.getvalue())

    def test_check_fresh_catches_formatting_only_drift(self):
        cat = self._catalog("same")
        with tempfile.TemporaryDirectory() as d:
            path = self._write(d, mios_ai_metadata.render_catalog_json(cat) + "\n")
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                rc = mios_ai_metadata.check_export_fresh(cat, path)
        self.assertEqual(rc, 1)
        self.assertIn("formatting drift", err.getvalue())

    def test_diff_reports_added_and_removed_entries(self):
        old = self._catalog("x")
        new = self._catalog("x")
        new["entries"][0] = dict(new["entries"][0], path="usr/lib/b.sh")
        lines = mios_ai_metadata.diff_catalog_entries(old, new)
        self.assertIn("entry usr/lib/b.sh: has an AI header but is missing from the tracked file", lines)
        self.assertTrue(any(l.startswith("entry usr/lib/a.sh: in the tracked file") for l in lines))


if __name__ == "__main__":
    unittest.main()
