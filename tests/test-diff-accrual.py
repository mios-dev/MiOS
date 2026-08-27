#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-DIFFCYCLE shutdown diff snapshotting & boot-cycle accrual.
# AI-doc: usr/share/doc/mios/manual/ch63-diff-snapshotting-boot-accrual-and-hitl-rollin.md
"""Automated tests for WS-DIFFCYCLE shutdown diff snapshotting, risk classification, and accrual."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "usr", "libexec", "mios"))

import importlib.util

_DIFF_TOOL = os.path.join(_ROOT, "usr", "libexec", "mios", "diff", "diff-accrual.py")
spec = importlib.util.spec_from_file_location("diff_accrual", _DIFF_TOOL)
if spec and spec.loader:
    diff_accrual = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(diff_accrual)
else:
    raise ImportError(f"Could not load diff-accrual module from {_DIFF_TOOL}")

class TestDiffAccrual(unittest.TestCase):
    """Verifies diff snapshotting, risk classification, secret redaction, and accrual ledger output."""

    def test_risk_classification(self):
        # Safe classifications
        self.assertEqual(diff_accrual.classify_risk("var/lib/mios/ai/skills/custom-agent.md"), "safe")
        self.assertEqual(diff_accrual.classify_risk("etc/skel/.bashrc"), "safe")
        self.assertEqual(diff_accrual.classify_risk(".config/mios/theme.toml"), "safe")
        self.assertEqual(diff_accrual.classify_risk("etc/NetworkManager/system-connections/home-wifi.nmconnection"), "safe")
        self.assertEqual(diff_accrual.classify_risk("usr/share/mios/themes/default.toml"), "safe")
        self.assertEqual(diff_accrual.classify_risk("usr/share/doc/mios/manual.md"), "safe")

        # High-risk classifications
        self.assertEqual(diff_accrual.classify_risk("etc/pam.d/system-auth"), "high-risk")
        self.assertEqual(diff_accrual.classify_risk("etc/sudoers.d/custom"), "high-risk")
        self.assertEqual(diff_accrual.classify_risk("etc/kargs.d/01-iommu.conf"), "high-risk")
        self.assertEqual(diff_accrual.classify_risk("usr/share/mios/security/egress.nft"), "high-risk")
        self.assertEqual(diff_accrual.classify_risk("usr/bin/custom-root-helper"), "high-risk")
        self.assertEqual(diff_accrual.classify_risk("usr/lib/systemd/system/custom.service"), "high-risk")
        self.assertEqual(diff_accrual.classify_risk("etc/containers/registries.conf"), "high-risk")

        # Interface compatibility helper
        self.assertEqual(diff_accrual.classify_path("etc/pam.d/system-auth"), "high-risk")
        self.assertEqual(diff_accrual.classify_path("var/lib/mios/ai/skills/agent.md"), "safe")

    def test_secret_redaction(self):
        sample = (
            "api_key = 'sk-1234567890abcdef'\n"
            "password: supersecretpassword\n"
            "token: gh_p1234567890\n"
            "normal_var: public_val"
        )
        redacted = diff_accrual.redact_secrets(sample)
        self.assertNotIn("sk-1234567890abcdef", redacted)
        self.assertNotIn("supersecretpassword", redacted)
        self.assertNotIn("gh_p1234567890", redacted)
        self.assertIn("public_val", redacted)

    def test_snapshot_and_accrue_workflow(self):
        with tempfile.TemporaryDirectory(prefix="mios-diff-test-") as tmpdir:
            repo_root = os.path.join(tmpdir, "repo")
            snapshots_dir = os.path.join(tmpdir, "snapshots")
            ledger_path = os.path.join(tmpdir, "accrued-diffs.json")

            os.makedirs(repo_root, exist_ok=True)
            subprocess.run(["git", "-C", repo_root, "init", "-q"], check=True)
            subprocess.run(["git", "-C", repo_root, "config", "user.name", "Test"], check=True)
            subprocess.run(["git", "-C", repo_root, "config", "user.email", "test@mios.local"], check=True)

            # Create initial file & commit
            initial_file = os.path.join(repo_root, "README.md")
            with open(initial_file, "w", encoding="utf-8") as f:
                f.write("# Initial MiOS Tree\n")
            subprocess.run(["git", "-C", repo_root, "add", "README.md"], check=True)
            subprocess.run(["git", "-C", repo_root, "commit", "-q", "-m", "init"], check=True)

            # Introduce changes: 1 safe skill, 1 high-risk pam edit
            skill_path = os.path.join(repo_root, "var", "lib", "mios", "ai", "skills")
            os.makedirs(skill_path, exist_ok=True)
            with open(os.path.join(skill_path, "test-skill.md"), "w", encoding="utf-8") as f:
                f.write("# Test Skill\n")

            pam_path = os.path.join(repo_root, "etc", "pam.d")
            os.makedirs(pam_path, exist_ok=True)
            with open(os.path.join(pam_path, "system-auth"), "w", encoding="utf-8") as f:
                f.write("auth required pam_permit.so\n")

            # 1. Execute snapshot
            res_snap = subprocess.run([
                sys.executable, _DIFF_TOOL, "snapshot",
                "--root", repo_root,
                "--output-dir", snapshots_dir,
                "--boot-id", "testboot01",
            ], capture_output=True, text=True)
            self.assertEqual(res_snap.returncode, 0, f"Snapshot failed: {res_snap.stderr}")

            # Verify snapshot file was created
            snapshot_files = os.listdir(snapshots_dir)
            self.assertEqual(len(snapshot_files), 1)
            with open(os.path.join(snapshots_dir, snapshot_files[0]), "r", encoding="utf-8") as f:
                snap_json = json.load(f)
            self.assertEqual(snap_json["boot_id"], "testboot01")
            self.assertEqual(snap_json["total_changes"], 2)
            self.assertLess(snap_json["duration_ms"], 3000.0)

            # 2. Execute accrue
            res_accrue = subprocess.run([
                sys.executable, _DIFF_TOOL, "accrue",
                "--snapshots-dir", snapshots_dir,
                "--ledger-out", ledger_path,
            ], capture_output=True, text=True)
            self.assertEqual(res_accrue.returncode, 0, f"Accrue failed: {res_accrue.stderr}")

            # Verify ledger
            self.assertTrue(os.path.isfile(ledger_path))
            with open(ledger_path, "r", encoding="utf-8") as f:
                ledger = json.load(f)

            self.assertEqual(ledger["total_diffs"], 2)
            self.assertEqual(ledger["safe_count"], 1)
            self.assertEqual(ledger["high_risk_count"], 1)
            self.assertEqual(ledger["status"], "ready_for_review")

            safe_paths = [x["path"] for x in ledger["safe_diffs"]]
            high_risk_paths = [x["path"] for x in ledger["high_risk_diffs"]]
            self.assertIn("var/lib/mios/ai/skills/test-skill.md", safe_paths)
            self.assertIn("etc/pam.d/system-auth", high_risk_paths)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDiffAccrual)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
