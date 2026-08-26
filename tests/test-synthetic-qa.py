#!/usr/bin/env python3
# AI-hint: Automated unit test suite for T-383 Synthetic Training Q&A Data Pipeline.
# AI-related: usr/libexec/mios/ai/synthetic_qa.py, usr/share/doc/mios/
"""
Automated unit tests for hierarchical markdown header parsing, context preservation,
multi-turn Q&A synthesis, secret and token redaction, and JSONL dataset generation.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_SYNTH_QA_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "ai", "synthetic_qa.py")

spec = importlib.util.spec_from_file_location("synthetic_qa", _SYNTH_QA_PATH)
if spec and spec.loader:
    synthetic_qa = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = synthetic_qa
    spec.loader.exec_module(synthetic_qa)
else:
    raise ImportError(f"Could not load synthetic_qa module from {_SYNTH_QA_PATH}")


class TestSyntheticQAPipeline(unittest.TestCase):
    """Validates markdown parsing, secret redaction, Q&A synthesis, and JSONL export."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="mios_test_synqa_")
        self.output_jsonl = os.path.join(self.temp_dir, "synthetic_dataset.jsonl")
        self.parser = synthetic_qa.MarkdownHierarchicalParser()
        self.redactor = synthetic_qa.SecretRedactor()
        self.synthesizer = synthetic_qa.QASynthesizer()
        self.pipeline = synthetic_qa.SyntheticQAPipeline(
            parser=self.parser,
            redactor=self.redactor,
            synthesizer=self.synthesizer,
        )

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_hierarchical_markdown_parsing(self):
        sample_md = """# MiOS Architectural Specification

Overview of the immutable bootc Fedora workstation and local AI operating system.

## Memory Subsystem

The memory subsystem manages pgvector persistence and KV-cache paging.

### PostgreSQL and PgVector Configuration

Here is the setup configuration for pgvector:

```toml
[pgvector]
port = 5432
data_dir = "/var/lib/mios/pgvector"
```

| Parameter | Default | Purpose |
| --- | --- | --- |
| port | 5432 | Database port |
| mode | dedicated | Service lifecycle |
"""
        chunks = self.parser.parse_text(sample_md, doc_path="doc/arch.md")
        self.assertGreaterEqual(len(chunks), 2)

        # Find the pgvector subsection chunk
        pg_chunk = next(c for c in chunks if "PostgreSQL" in c.section_title)
        self.assertEqual(pg_chunk.section_title, "PostgreSQL and PgVector Configuration")
        self.assertIn("Memory Subsystem", pg_chunk.hierarchy)
        self.assertEqual(len(pg_chunk.code_blocks), 1)
        self.assertEqual(pg_chunk.code_blocks[0]["lang"], "toml")
        self.assertIn("port = 5432", pg_chunk.code_blocks[0]["code"])
        self.assertEqual(len(pg_chunk.tables), 1)

    def test_secret_and_token_redaction(self):
        raw_text = (
            "Connecting to cluster using api_key = 'sk-abcdef1234567890abcdef1234567890' "
            "with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secret and password='SuperSecretPassword123!'."
        )
        redacted = self.redactor.redact(raw_text)
        self.assertNotIn("sk-abcdef1234567890", redacted)
        self.assertNotIn("SuperSecretPassword123!", redacted)
        self.assertIn("<REDACTED_API_KEY>", redacted)
        self.assertIn("<REDACTED_SECRET>", redacted)

    def test_private_key_redaction(self):
        key_text = (
            "-----BEGIN OPENSSH PRIVATE KEY-----\n"
            "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAACFwAAAAdzc2gtcn\n"
            "-----END OPENSSH PRIVATE KEY-----"
        )
        redacted = self.redactor.redact(f"Host key: {key_text}")
        self.assertNotIn("b3BlbnNzaC", redacted)
        self.assertIn("<REDACTED_PRIVATE_KEY>", redacted)

    def test_qa_synthesis_format_and_roles(self):
        chunk = synthetic_qa.MarkdownChunk(
            doc_path="cat/ADR-0008.md",
            doc_title="ADR 0008",
            section_title="Unified Installer Surface",
            hierarchy=["ADR 0008", "Unified Installer Surface"],
            content="The unified installer coordinates Total Root Merge in Phase-1, overlaying bootstrap files on target root.",
            code_blocks=[{"lang": "bash", "code": "bash install.sh --merge-root"}],
        )

        records = self.synthesizer.synthesize_qa_pairs(chunk)
        self.assertGreaterEqual(len(records), 2)

        for rec in records:
            self.assertIn("messages", rec)
            self.assertIn("metadata", rec)
            msgs = rec["messages"]
            self.assertEqual(msgs[0]["role"], "system")
            self.assertEqual(msgs[1]["role"], "user")
            self.assertEqual(msgs[2]["role"], "assistant")
            self.assertIn("MiOS", msgs[0]["content"])

    def test_end_to_end_harvest_and_jsonl_export(self):
        doc_file = os.path.join(self.temp_dir, "test_guide.md")
        with open(doc_file, "w", encoding="utf-8") as f:
            f.write(
                "# Node Discovery Protocol\n\n"
                "Nodes communicate over 16-byte fixed binary frames using UDP gossip and TCP framing.\n\n"
                "## Frame Header Structure\n\n"
                "The header structure contains magic 0x4D49, version, opcode, node ID, payload len, and CRC32.\n\n"
                "```rust\npub struct FrameHeader {\n    magic: u16,\n    version: u8,\n}\n```\n"
            )

        chunks = self.pipeline.harvest_docs([self.temp_dir])
        self.assertGreaterEqual(len(chunks), 1)

        records = self.pipeline.generate_dataset(chunks, max_samples=5)
        self.assertGreaterEqual(len(records), 1)

        exported_count = self.pipeline.export_jsonl(records, self.output_jsonl)
        self.assertEqual(exported_count, len(records))
        self.assertTrue(os.path.exists(self.output_jsonl))

        # Validate valid JSON on every line
        with open(self.output_jsonl, "r", encoding="utf-8") as f:
            lines = f.readlines()
        self.assertEqual(len(lines), len(records))
        for line in lines:
            parsed = json.loads(line)
            self.assertIn("messages", parsed)
            self.assertGreaterEqual(len(parsed["messages"]), 3)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSyntheticQAPipeline)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
