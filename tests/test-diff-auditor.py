#!/usr/bin/env python3
# AI-hint: Automated unit test suite for interactive diff auditor and bake staging.
# AI-related: usr/libexec/mios/ux/diff_auditor.py, usr/share/mios/mios.toml
"""Unit and integration test suite for DiffAuditorEngine and diff_auditor CLI."""

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
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "ux", "diff_auditor.py")

spec = importlib.util.spec_from_file_location("diff_auditor", _TARGET_PATH)
if spec and spec.loader:
    diff_auditor = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = diff_auditor
    spec.loader.exec_module(diff_auditor)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")


class TestDiffAuditor(unittest.TestCase):
    """Test suite for accrued diff auditing, operator approval/rejection, and manifest staging."""

    def test_load_ledger_mock(self):
        engine = diff_auditor.DiffAuditorEngine(mock=True)
        ledger = engine.load_ledger()
        self.assertEqual(ledger["total_accrued"], 3)
        self.assertEqual(ledger["safe_count"], 1)
        self.assertEqual(ledger["high_risk_count"], 2)

    def test_list_entries_mock(self):
        engine = diff_auditor.DiffAuditorEngine(mock=True)
        entries = engine.list_entries()
        self.assertEqual(len(entries), 3)
        paths = [e["path"] for e in entries]
        self.assertIn("var/lib/mios/ai/skills/custom-agent.md", paths)
        self.assertIn("etc/pam.d/system-auth", paths)

    def test_process_decisions_approve_safe(self):
        with tempfile.TemporaryDirectory(prefix="mios-audit-test-") as tmpdir:
            staged_file = os.path.join(tmpdir, "staged.json")
            engine = diff_auditor.DiffAuditorEngine(staged_out=staged_file, mock=True)
            manifest = engine.process_decisions(approve_safe=True)
            self.assertEqual(manifest["total_approved"], 1)
            self.assertEqual(manifest["approved_diffs"][0]["path"], "var/lib/mios/ai/skills/custom-agent.md")
            self.assertTrue(manifest["bake_ready"])
            self.assertTrue(os.path.isfile(staged_file))

    def test_process_decisions_approve_paths_and_reject(self):
        with tempfile.TemporaryDirectory(prefix="mios-audit-test-") as tmpdir:
            staged_file = os.path.join(tmpdir, "staged.json")
            engine = diff_auditor.DiffAuditorEngine(staged_out=staged_file, mock=True)
            manifest = engine.process_decisions(
                approve_paths=["etc/mios/profile.toml"],
                reject_paths=["etc/pam.d/system-auth"],
            )
            self.assertEqual(manifest["total_approved"], 1)
            self.assertEqual(manifest["total_rejected"], 1)
            self.assertEqual(manifest["total_pending"], 1)
            self.assertEqual(manifest["approved_diffs"][0]["path"], "etc/mios/profile.toml")
            self.assertEqual(manifest["rejected_diffs"][0]["path"], "etc/pam.d/system-auth")

    def test_process_decisions_approve_all(self):
        with tempfile.TemporaryDirectory(prefix="mios-audit-test-") as tmpdir:
            staged_file = os.path.join(tmpdir, "staged.json")
            engine = diff_auditor.DiffAuditorEngine(staged_out=staged_file, mock=True)
            manifest = engine.process_decisions(approve_all=True)
            self.assertEqual(manifest["total_approved"], 3)
            self.assertEqual(manifest["total_rejected"], 0)
            self.assertEqual(manifest["total_pending"], 0)

    def test_cli_list_mock(self):
        test_args = ["diff_auditor.py", "--list", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = diff_auditor.main()
            self.assertEqual(exit_code, 0)

    def test_cli_approve_safe_mock(self):
        with tempfile.TemporaryDirectory(prefix="mios-audit-cli-") as tmpdir:
            staged_file = os.path.join(tmpdir, "staged.json")
            test_args = ["diff_auditor.py", "--approve-safe", "--staged-out", staged_file, "--mock", "--json"]
            with patch.object(sys, "argv", test_args):
                exit_code = diff_auditor.main()
                self.assertEqual(exit_code, 0)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDiffAuditor)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
