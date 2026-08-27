#!/usr/bin/env python3
# AI-hint: Unit test suite for MiOS Git pre-commit linter and hook manager (T-584 / AGY-2182).
# AI-related: usr/libexec/mios/git/pre_commit.py, usr/share/doc/mios/manual/automation.md
"""Unit and integration tests for PreCommitLinter."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "git", "pre_commit.py")

spec = importlib.util.spec_from_file_location("pre_commit", _TARGET_PATH)
if spec and spec.loader:
    pre_commit = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = pre_commit
    spec.loader.exec_module(pre_commit)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")


class TestPreCommitLinter(unittest.TestCase):
    """Unit tests for PreCommitLinter."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="mios-test-precommit-")
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_mock_pre_commit_pass(self):
        linter = pre_commit.PreCommitLinter(repo_root=str(self.root), mock=True)
        res = linter.run_pre_commit()
        self.assertEqual(res.status, "pass")
        self.assertEqual(len(res.findings), 0)
        self.assertEqual(res.files_checked, 3)

    def test_python_syntax_error_detection(self):
        linter = pre_commit.PreCommitLinter(repo_root=str(self.root), mock=False)
        bad_py = "def broken(\n    return 42\n"
        findings = linter.lint_python_content("bad.py", bad_py)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule, "python-syntax")

    def test_json_syntax_error_detection(self):
        linter = pre_commit.PreCommitLinter(repo_root=str(self.root), mock=False)
        bad_json = '{"key": "value", trailing: }'
        findings = linter.lint_json_content("bad.json", bad_json)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule, "json-syntax")

    def test_forbidden_vendor_ai_url_detection(self):
        linter = pre_commit.PreCommitLinter(repo_root=str(self.root), mock=False)
        bad_content = 'url = "https://api.openai.com/v1/chat/completions"\n'
        findings = linter.lint_security_and_vendor("client.py", bad_content)
        self.assertTrue(any(f.rule == "unified-ai-redirects" for f in findings))

    def test_secret_detection(self):
        linter = pre_commit.PreCommitLinter(repo_root=str(self.root), mock=False)
        bad_content = 'token = "sk-abcdef12345678901234567890"\n'
        findings = linter.lint_security_and_vendor("secret.py", bad_content)
        self.assertTrue(any(f.rule == "no-hardcoded-secrets" for f in findings))

    def test_conventional_commit_validation(self):
        linter = pre_commit.PreCommitLinter(repo_root=str(self.root), mock=True)

        valid_msgs = [
            "feat(gpu): add declarative MIG slicer and CDI generator",
            "fix(ci): wire radosgw port into ssot quadlet allowlists",
            "docs: update architecture manual with edge mesh diagrams",
            "refactor(agent-pipe): optimize temporal decay vector scoring",
        ]
        for msg in valid_msgs:
            ok, err = linter.validate_commit_message(msg)
            self.assertTrue(ok, f"Expected '{msg}' to be valid, got err: {err}")

        invalid_msgs = [
            "WIP: random changes",
            "fixed bug",
            "",
            "unknown_type: do something",
        ]
        for msg in invalid_msgs:
            ok, _ = linter.validate_commit_message(msg)
            self.assertFalse(ok, f"Expected '{msg}' to be invalid")

    def test_cli_execution_check_mock(self):
        test_args = ["pre_commit.py", "--check", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = pre_commit.main()
            self.assertEqual(exit_code, 0)

    def test_cli_execution_install_hook_mock(self):
        test_args = ["pre_commit.py", "--install-hook", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = pre_commit.main()
            self.assertEqual(exit_code, 0)

    def test_cli_execution_validate_msg_mock(self):
        test_args = ["pre_commit.py", "--validate-msg", "feat(sec): add fido2 enrollment", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = pre_commit.main()
            self.assertEqual(exit_code, 0)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPreCommitLinter)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
