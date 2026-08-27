#!/usr/bin/env python3
# AI-hint: Automated unit test suite for pre-poweroff diff snapshot hook.
# AI-related: usr/libexec/mios/deploy/diff_snapshot.py, usr/share/mios/mios.toml
"""Unit and integration test suite for DiffSnapshotEngine and diff_snapshot CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "deploy", "diff_snapshot.py")

spec = importlib.util.spec_from_file_location("diff_snapshot", _TARGET_PATH)
if spec and spec.loader:
    diff_snapshot = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = diff_snapshot
    spec.loader.exec_module(diff_snapshot)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestDiffSnapshot(unittest.TestCase):
    """Test suite for pre-poweroff diff capture, risk classification, and secret redaction."""

    def test_classify_risk_rules(self):
        # Safe paths
        self.assertEqual(diff_snapshot.classify_risk("var/lib/mios/ai/skills/custom-agent.md"), "safe")
        self.assertEqual(diff_snapshot.classify_risk("etc/skel/.bashrc"), "safe")
        self.assertEqual(diff_snapshot.classify_risk(".config/mios/theme.toml"), "safe")
        self.assertEqual(diff_snapshot.classify_risk("usr/share/doc/manual.md"), "safe")

        # High-risk paths
        self.assertEqual(diff_snapshot.classify_risk("etc/pam.d/system-auth"), "high-risk")
        self.assertEqual(diff_snapshot.classify_risk("etc/sudoers"), "high-risk")
        self.assertEqual(diff_snapshot.classify_risk("usr/lib/systemd/system/test.service"), "high-risk")
        self.assertEqual(diff_snapshot.classify_risk("etc/kargs.d/01-iommu.conf"), "high-risk")

    def test_redact_secrets(self):
        sample = "api_key = 'sk-1234567890abcdef'\npassword = secret123\nnormal = value"
        sanitized = diff_snapshot.redact_secrets(sample)
        self.assertNotIn("sk-1234567890abcdef", sanitized)
        self.assertNotIn("secret123", sanitized)
        self.assertIn("normal = value", sanitized)

    def test_atomic_write_json(self):
        with tempfile.TemporaryDirectory(prefix="mios-snap-test-") as tmpdir:
            target = os.path.join(tmpdir, "test.json")
            data = {"key": "value", "count": 42}
            diff_snapshot.atomic_write_json(target, data)
            self.assertTrue(os.path.isfile(target))
            with open(target, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            self.assertEqual(loaded, data)

    def test_capture_snapshot_mock(self):
        with tempfile.TemporaryDirectory(prefix="mios-snap-dir-") as tmpdir:
            engine = diff_snapshot.DiffSnapshotEngine(output_dir=tmpdir, boot_id="boot123", mock=True)
            snapshot = engine.capture_snapshot(reason="shutdown")
            self.assertEqual(snapshot["status"], "ok")
            self.assertEqual(snapshot["boot_id"], "boot123")
            self.assertEqual(snapshot["reason"], "shutdown")
            self.assertGreaterEqual(snapshot["total_changes"], 1)
            self.assertIn("snapshot_file", snapshot)
            self.assertTrue(os.path.isfile(snapshot["snapshot_file"]))

    def test_cli_shutdown_mock(self):
        with tempfile.TemporaryDirectory(prefix="mios-snap-cli-") as tmpdir:
            test_args = ["diff_snapshot.py", "--reason", "shutdown", "--output-dir", tmpdir, "--mock", "--json"]
            with patch.object(sys, "argv", test_args):
                exit_code = diff_snapshot.main()
                self.assertEqual(exit_code, 0)

    def test_cli_reboot_dry_run_mock(self):
        test_args = ["diff_snapshot.py", "--reason", "reboot", "--dry-run", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = diff_snapshot.main()
            self.assertEqual(exit_code, 0)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDiffSnapshot)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
