#!/usr/bin/env python3
# AI-hint: Automated unit test suite for secret-redacting cross-platform clipboard synchronizer.
# AI-related: usr/libexec/mios/ux/clipboard_sync.py, usr/share/mios/mios.toml
"""Unit and integration test suite for ClipboardSyncEngine and clipboard_sync CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "ux", "clipboard_sync.py")

spec = importlib.util.spec_from_file_location("clipboard_sync", _TARGET_PATH)
if spec and spec.loader:
    clipboard_sync = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = clipboard_sync
    spec.loader.exec_module(clipboard_sync)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestClipboardSync(unittest.TestCase):
    """Test suite for sensitive token redaction and host-to-guest clipboard synchronization."""

    def test_redact_openai_key(self):
        engine = clipboard_sync.ClipboardSyncEngine(mock=True)
        raw = "My key is sk-1234567890abcdef1234567890 for API calls"
        res = engine.filter_text(raw)
        self.assertNotIn("sk-1234567890abcdef1234567890", res.redacted_text)
        self.assertIn("[REDACTED_SECRET:OPENAI_KEY]", res.redacted_text)
        self.assertIn("OPENAI_KEY", res.detected_categories)
        self.assertEqual(res.redactions_count, 1)

    def test_redact_github_pat(self):
        engine = clipboard_sync.ClipboardSyncEngine(mock=True)
        raw = "git clone https://ghp_1234567890abcdefghijklmnopqrstuv@github.com/repo.git"
        res = engine.filter_text(raw)
        self.assertNotIn("ghp_1234567890abcdefghijklmnopqrstuv", res.redacted_text)
        self.assertIn("[REDACTED_SECRET:GITHUB_PAT]", res.redacted_text)
        self.assertIn("GITHUB_PAT", res.detected_categories)

    def test_redact_aws_keys(self):
        engine = clipboard_sync.ClipboardSyncEngine(mock=True)
        raw = "export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE\nexport AWS_SECRET_ACCESS_KEY='wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'"
        res = engine.filter_text(raw)
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", res.redacted_text)
        self.assertNotIn("wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", res.redacted_text)
        self.assertIn("AWS_ACCESS_KEY", res.detected_categories)
        self.assertIn("AWS_SECRET_KEY", res.detected_categories)

    def test_redact_private_key_block(self):
        engine = clipboard_sync.ClipboardSyncEngine(mock=True)
        raw = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0Y1...\n-----END RSA PRIVATE KEY-----"
        res = engine.filter_text(raw)
        self.assertNotIn("MIIEowIBAAKCAQEA0Y1", res.redacted_text)
        self.assertIn("[REDACTED_SECRET:PRIVATE_KEY]", res.redacted_text)
        self.assertIn("PRIVATE_KEY", res.detected_categories)

    def test_redact_bearer_and_slack_tokens(self):
        engine = clipboard_sync.ClipboardSyncEngine(mock=True)
        raw = "Authorization: Bearer my-super-secret-bearer-token-1234567890\nSlack: xoxb-1234567890-abcdefghij"
        res = engine.filter_text(raw)
        self.assertNotIn("my-super-secret-bearer-token-1234567890", res.redacted_text)
        self.assertNotIn("xoxb-1234567890-abcdefghij", res.redacted_text)
        self.assertIn("BEARER_TOKEN", res.detected_categories)
        self.assertIn("SLACK_TOKEN", res.detected_categories)

    def test_sync_once_mock(self):
        engine = clipboard_sync.ClipboardSyncEngine(mock=True)
        engine.set_mock_clipboard("Normal text with sk-99887766554433221100aabb secret")
        res = engine.sync_once()
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["redactions_count"], 1)
        self.assertIn("OPENAI_KEY", res["detected_categories"])

    def test_get_stats_report(self):
        engine = clipboard_sync.ClipboardSyncEngine(mock=True)
        engine.filter_text("sk-abcdef1234567890abcdef1234")
        report = engine.get_stats_report()
        self.assertEqual(report["status"], "success")
        self.assertGreaterEqual(report["total_redactions"], 1)
        self.assertIn("OPENAI_KEY", report["categories"])

    def test_cli_filter_text_mock(self):
        test_args = ["clipboard_sync.py", "--filter-text", "sk-1234567890abcdef1234567890", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = clipboard_sync.main()
            self.assertEqual(exit_code, 0)

    def test_cli_sync_mock(self):
        test_args = ["clipboard_sync.py", "--sync", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = clipboard_sync.main()
            self.assertEqual(exit_code, 0)

    def test_cli_stats_mock(self):
        test_args = ["clipboard_sync.py", "--stats", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = clipboard_sync.main()
            self.assertEqual(exit_code, 0)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestClipboardSync)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
