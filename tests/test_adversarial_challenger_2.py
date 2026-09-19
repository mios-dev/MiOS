#!/usr/bin/env python3
"""
tests/test_adversarial_challenger_2.py — Adversarial Edge Case Probes for Challenger 2.

Covers:
- Probe 1: Unanchored prefix probes (.devloop-fake/, .worktrees-fake/, and AGENTS.md.bak file prefix leak)
- Probe 2: Deleted file probes (tracked vs untracked file deletion)
- Probe 3: Inherited dirty base tree probes (pre-existing dirty/untracked files baseline)
- Probe 4: Claude Code CLI envelope probes (permission_denials, denied_actions, is_error, stream noise)
- Probe 5: Drift check isolation probes (.worktrees pruning across all 5 checks + negative control)
- Worktree security validation: subagent_id sanitization in mios_worktree.py
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Add dev-loop scripts and agent-pipe to sys.path
DEVLOOP_SCRIPTS = Path("/home/mios-dev/.dev-loop/skills/dev-loop/scripts")
AGENT_PIPE_DIR = Path("/workspaces/MiOS/usr/lib/mios/agent-pipe")
TOOLS_DIR = Path("/workspaces/MiOS/tools")

sys.path.insert(0, str(DEVLOOP_SCRIPTS))
sys.path.insert(0, str(AGENT_PIPE_DIR))
sys.path.insert(0, str(TOOLS_DIR))

import adapters
from git_lock import run_git_safe, resolve_git_dir, resolve_main_git_dir
import mios_worktree


class TestProbe1UnanchoredPrefixes(unittest.TestCase):
    """Probe 1: Unanchored prefix probe."""

    def test_directory_devloop_fake_caught_as_stray(self):
        """Directory .devloop-fake/ must be caught as stray and not allowed by .devloop/."""
        before = {}
        now = {".devloop-fake/stray.txt": "??"}
        strays = adapters.stray_base_edits(before, now, adapters.BASE_TREE_ALWAYS_ALLOWED)
        self.assertEqual(strays, [".devloop-fake/stray.txt"])

    def test_directory_worktrees_fake_caught_as_stray(self):
        """Directory .worktrees-fake/ must be caught as stray and not allowed by .worktrees/."""
        before = {}
        now = {".worktrees-fake/lane-1/code.py": "??"}
        allowed = adapters.BASE_TREE_ALWAYS_ALLOWED + (".worktrees/",)
        strays = adapters.stray_base_edits(before, now, allowed)
        self.assertEqual(strays, [".worktrees-fake/lane-1/code.py"])

    def test_allowed_prefixes_permitted(self):
        """Designated metadata paths must be permitted."""
        before = {}
        now = {
            ".devloop/run-1/log.txt": "??",
            ".devloop/LEDGER.md": " M",
            "AGENTS.md": " M",
            "TASKS.md": " M",
            ".worktrees/lane-1/file.py": "??",
        }
        allowed = adapters.BASE_TREE_ALWAYS_ALLOWED + (".worktrees/",)
        strays = adapters.stray_base_edits(before, now, allowed)
        self.assertEqual(strays, [])

    def test_adversarial_file_prefix_leak_agents_md_bak(self):
        """
        Adversarial probe: AGENTS.md.bak in base tree must be caught as stray.
        Prefix matching must be anchored to directories ending with '/', so AGENTS.md.bak is rejected.
        """
        before = {}
        now = {"AGENTS.md.bak": "??"}
        strays = adapters.stray_base_edits(before, now, adapters.BASE_TREE_ALWAYS_ALLOWED)
        self.assertEqual(strays, ["AGENTS.md.bak"])

    def test_adversarial_file_prefix_leak_tasks_md_bak(self):
        """
        Adversarial probe: TASKS.md.old in base tree must be caught as stray.
        """
        before = {}
        now = {"TASKS.md.old": "??"}
        strays = adapters.stray_base_edits(before, now, adapters.BASE_TREE_ALWAYS_ALLOWED)
        self.assertEqual(strays, ["TASKS.md.old"])

    def test_e2e_base_audit_agents_md_bak_leak_repro(self):
        """
        E2E verification: Planting AGENTS.md.bak in base tree is caught by base-audit with exit 6.
        """
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Tester"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "tester@test.local"], check=True)
            (repo / "AGENTS.md").write_text("# Agents\n", "utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=True)

            snap_file = repo / "snap.json"
            subprocess.run([
                sys.executable, str(DEVLOOP_SCRIPTS / "adapters.py"),
                "base-snapshot", "--root", str(repo), "--out", str(snap_file)
            ], check=True, capture_output=True)

            # Plant AGENTS.md.bak
            (repo / "AGENTS.md.bak").write_text("leaked copy\n", "utf-8")

            # Run base-audit: base-audit must exit 6 and diagnose AGENTS.md.bak on stderr!
            audit = subprocess.run([
                sys.executable, str(DEVLOOP_SCRIPTS / "adapters.py"),
                "base-audit", "--root", str(repo), "--before", str(snap_file)
            ], capture_output=True, text=True)

            self.assertEqual(audit.returncode, 6, f"Expected exit 6 but got {audit.returncode}: {audit.stderr}")
            self.assertIn("AGENTS.md.bak", audit.stderr)
            self.assertIn("BASE TREE LEAKAGE DETECTED", audit.stderr)


class TestProbe2DeletedFiles(unittest.TestCase):
    """Probe 2: Deleted file probe."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="challenger2-deleted-")
        self.repo = Path(self.tmpdir)
        subprocess.run(["git", "init", "-b", "main", str(self.repo)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.name", "Tester"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.email", "tester@example.com"], check=True)

        # Create tracked file
        (self.repo / "src").mkdir(parents=True)
        (self.repo / "src" / "app.py").write_text("print('hello')\n", "utf-8")
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.repo), "commit", "-m", "init"], check=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_tracked_file_deletion_filesystem_intercepted(self):
        """Deleting a tracked file from filesystem produces ' D' and is intercepted as a mutation."""
        snap_file = self.repo / "before.json"
        res = subprocess.run([
            sys.executable, str(DEVLOOP_SCRIPTS / "adapters.py"),
            "base-snapshot", "--root", str(self.repo), "--out", str(snap_file)
        ], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

        # Delete tracked file
        (self.repo / "src" / "app.py").unlink()

        # Run base-audit
        audit = subprocess.run([
            sys.executable, str(DEVLOOP_SCRIPTS / "adapters.py"),
            "base-audit", "--root", str(self.repo), "--before", str(snap_file)
        ], capture_output=True, text=True)
        self.assertEqual(audit.returncode, 6)
        self.assertIn("src/app.py", audit.stderr)

    def test_tracked_file_staged_deletion_intercepted(self):
        """Staged deletion ('git rm') produces 'D ' and is intercepted as a mutation."""
        snap_file = self.repo / "before.json"
        subprocess.run([
            sys.executable, str(DEVLOOP_SCRIPTS / "adapters.py"),
            "base-snapshot", "--root", str(self.repo), "--out", str(snap_file)
        ], check=True, capture_output=True)

        subprocess.run(["git", "-C", str(self.repo), "rm", "src/app.py"], check=True, capture_output=True)

        audit = subprocess.run([
            sys.executable, str(DEVLOOP_SCRIPTS / "adapters.py"),
            "base-audit", "--root", str(self.repo), "--before", str(snap_file)
        ], capture_output=True, text=True)
        self.assertEqual(audit.returncode, 6)
        self.assertIn("src/app.py", audit.stderr)

    def test_untracked_file_deleted_during_run(self):
        """
        Adversarial probe: Pre-existing untracked file deleted during run.
        Before: '?? scratch.txt'. Now: deleted, so not in git status.
        Does stray_base_edits flag it or only scan now.items()?
        """
        before = {"scratch.txt": "??"}
        now = {}
        strays = adapters.stray_base_edits(before, now, adapters.BASE_TREE_ALWAYS_ALLOWED)
        # Empirical test: stray_base_edits only loops over now.items(), so strays is empty!
        self.assertEqual(strays, [])


class TestProbe3InheritedDirtyBaseTree(unittest.TestCase):
    """Probe 3: Inherited dirty base tree probe."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="challenger2-dirty-")
        self.repo = Path(self.tmpdir)
        subprocess.run(["git", "init", "-b", "main", str(self.repo)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.name", "Tester"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.email", "tester@example.com"], check=True)

        (self.repo / "tracked.txt").write_text("v1\n", "utf-8")
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.repo), "commit", "-m", "init"], check=True)

        # Create pre-existing dirty files: 1 modified, 1 untracked
        (self.repo / "tracked.txt").write_text("v2 uncommitted\n", "utf-8")
        (self.repo / "untracked_note.txt").write_text("developer notes\n", "utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_pre_existing_dirty_files_do_not_cause_false_alarms(self):
        """Pre-existing dirty files captured in baseline snapshot must not trigger false alarms."""
        snap_file = self.repo / "before.json"
        res = subprocess.run([
            sys.executable, str(DEVLOOP_SCRIPTS / "adapters.py"),
            "base-snapshot", "--root", str(self.repo), "--out", str(snap_file)
        ], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

        # Verify snapshot content
        snap_data = json.loads(snap_file.read_text("utf-8"))
        self.assertIn("tracked.txt", snap_data)
        self.assertIn("untracked_note.txt", snap_data)

        # Run base-audit without any subsequent changes
        audit = subprocess.run([
            sys.executable, str(DEVLOOP_SCRIPTS / "adapters.py"),
            "base-audit", "--root", str(self.repo), "--before", str(snap_file)
        ], capture_output=True, text=True)
        self.assertEqual(audit.returncode, 0)
        self.assertIn("base tree audit ok", audit.stdout)

    def test_subsequent_stray_triggers_while_pre_existing_survives(self):
        """When an actual stray is added, only the stray is flagged; pre-existing dirt is not blamed."""
        snap_file = self.repo / "before.json"
        subprocess.run([
            sys.executable, str(DEVLOOP_SCRIPTS / "adapters.py"),
            "base-snapshot", "--root", str(self.repo), "--out", str(snap_file)
        ], check=True, capture_output=True)

        # Plant actual stray
        (self.repo / "stray_leak.py").write_text("bad code\n", "utf-8")

        audit = subprocess.run([
            sys.executable, str(DEVLOOP_SCRIPTS / "adapters.py"),
            "base-audit", "--root", str(self.repo), "--before", str(snap_file)
        ], capture_output=True, text=True)
        self.assertEqual(audit.returncode, 6)
        self.assertIn("stray_leak.py", audit.stderr)
        self.assertNotIn("untracked_note.txt", audit.stderr)
        self.assertNotIn("tracked.txt", audit.stderr)


class TestProbe4ClaudeCodeEnvelope(unittest.TestCase):
    """Probe 4: Claude Code CLI envelope probe."""

    def test_permission_denials_downgrades_done_to_partial(self):
        """Envelope with permission_denials must downgrade status from done to partial."""
        lane = {"id": "lane-1", "objective": "test objective", "worker": {"max_turns": 5, "timeout_s": 60}}
        stdout = json.dumps({
            "result": "Completed task\n```json\n{\"devloop_report\": {\"status\": \"done\", \"objective\": \"test objective\", \"positive_controls\": [\"pass\"]}}\n```",
            "num_turns": 2,
            "permission_denials": [{"action": "Bash", "detail": "blocked"}]
        })
        rep = adapters.normalize_report(lane, "claude-code", stdout, exit_code=0, timed_out=False, turns=2)
        self.assertEqual(rep["status"], "partial")
        self.assertTrue(any("permission_denials" in u for u in rep["unverified"]))

    def test_denied_actions_downgrades_done_to_partial(self):
        """Envelope with denied_actions (antigravity/agy) must downgrade status to partial."""
        lane = {"id": "lane-1", "objective": "test objective", "worker": {"max_turns": 5, "timeout_s": 60}}
        stdout = json.dumps({
            "response": "Done\n```json\n{\"devloop_report\": {\"status\": \"done\", \"objective\": \"test objective\", \"positive_controls\": [\"pass\"]}}\n```",
            "status": "SUCCESS",
            "usage": {"total_tokens": 100},
            "denied_actions": [{"display_name": "WriteFile"}]
        })
        rep = adapters.normalize_report(lane, "antigravity", stdout, exit_code=0, timed_out=False, turns=1)
        self.assertEqual(rep["status"], "partial")
        self.assertTrue(any("denied_actions" in u for u in rep["unverified"]))

    def test_empty_permission_denials_keeps_done(self):
        """Empty permission_denials list does not downgrade status."""
        lane = {"id": "lane-1", "objective": "test objective", "worker": {"max_turns": 5, "timeout_s": 60}}
        stdout = json.dumps({
            "result": "Done\n```json\n{\"devloop_report\": {\"status\": \"done\", \"objective\": \"test objective\", \"positive_controls\": [\"pass\"]}}\n```",
            "num_turns": 1,
            "permission_denials": []
        })
        rep = adapters.normalize_report(lane, "claude-code", stdout, exit_code=0, timed_out=False, turns=1)
        self.assertEqual(rep["status"], "done")

    def test_cmd_denials_cli_exit_codes(self):
        """adapters.py denials CLI must exit 3 on denials and 0 when clean."""
        with tempfile.TemporaryDirectory() as td:
            denied_file = Path(td) / "denied.json"
            clean_file = Path(td) / "clean.json"

            denied_file.write_text(json.dumps({
                "result": "Done",
                "num_turns": 2,
                "permission_denials": [{"action": "Bash"}]
            }), "utf-8")

            clean_file.write_text(json.dumps({
                "result": "Done successfully",
                "num_turns": 2,
                "permission_denials": []
            }), "utf-8")

            res_denied = subprocess.run([
                sys.executable, str(DEVLOOP_SCRIPTS / "adapters.py"),
                "denials", str(denied_file)
            ], capture_output=True, text=True)
            self.assertEqual(res_denied.returncode, 3)

            res_clean = subprocess.run([
                sys.executable, str(DEVLOOP_SCRIPTS / "adapters.py"),
                "denials", str(clean_file)
            ], capture_output=True, text=True)
            self.assertEqual(res_clean.returncode, 0)

    def test_stream_noise_tolerance(self):
        """Brace balancing must recover envelope even when noise / stderr precedes it in stream."""
        noise_stream = "jetski: 2 tool calls auto-denied\n" + json.dumps({
            "result": "Done",
            "num_turns": 1,
            "permission_denials": [{"action": "Write"}]
        })
        env = adapters.find_envelope(noise_stream)
        self.assertIsNotNone(env)
        self.assertIn("permission_denials", env)


class TestProbe5DriftCheckIsolation(unittest.TestCase):
    """Probe 5: Drift check worktree isolation probe."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="challenger2-drift-")
        self.root = Path(self.tmpdir)

        # Setup minimal mios repo structure
        (self.root / "usr" / "share" / "mios").mkdir(parents=True)
        (self.root / "usr" / "share" / "mios" / "mios.toml").write_bytes(
            b'[packages]\npkgs = ["bootc"]\n\n[ports]\nllm_light = 8080\n'
        )

        # check_containerfile_pinned_clones requires at least 5 Containerfiles to pass
        for i in range(1, 6):
            cdir = self.root / "containers" / f"app{i}"
            cdir.mkdir(parents=True, exist_ok=True)
            (cdir / "Containerfile").write_text(f"FROM fedora:41\nRUN git clone --branch v1.0 https://github.com/org/repo{i}.git\n", "utf-8")

        # Setup active mock worktree under .worktrees/
        self.wt = self.root / ".worktrees" / "active-worker-lane"
        self.wt.mkdir(parents=True)

        # Intentionally plant violations in .worktrees/
        (self.wt / "Containerfile").write_text("FROM fedora:41\nRUN git clone https://github.com/unpinned/repo.git\n", "utf-8")
        (self.wt / "leak.ps1").write_text("-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----\n", "utf-8")
        (self.wt / "db.ps1").write_text("user=admin password=secret_root_password dbname=mios\n", "utf-8")
        (self.wt / "bad_enc.ps1").write_bytes("Write-Output 'café'\n".encode("utf-8")) # Non-ascii without BOM
        (self.wt / "ascii_bom.ps1").write_bytes(b"\xef\xbb\xbfWrite-Output 'pure ascii'\n") # ASCII with BOM
        (self.wt / "bad_port.ps1").write_text("Get-PortFromSsot 'key' 'llm_light' 9999\n", "utf-8")
        (self.wt / "bad_regex.ps1").write_text("$m = (?s)\\[packages\\]\n", "utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_all_drift_checks_prune_worktrees(self):
        """Running the drift check functions against root must ignore .worktrees/ violations."""
        env = {**os.environ, "MIOS_DRIFT_ROOT": str(self.root)}

        orig_env = os.environ.get("MIOS_DRIFT_ROOT")
        try:
            os.environ["MIOS_DRIFT_ROOT"] = str(self.root)
            import importlib.util
            spec = importlib.util.spec_from_file_location("drift_checks", str(TOOLS_DIR / "drift-checks.py"))
            drift_checks = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(drift_checks)

            # 1. check_containerfile_pinned_clones
            c1 = drift_checks.check_containerfile_pinned_clones()
            self.assertEqual(c1, 0, "check_containerfile_pinned_clones failed on .worktrees")

            # 2. check_secret_handling (secret scanner)
            c2 = drift_checks.check_secret_handling()
            self.assertEqual(c2, 0, "check_secret_handling failed on .worktrees")

            # 3. check_adhoc_toml_parsers
            c3 = drift_checks.check_adhoc_toml_parsers()
            self.assertEqual(c3, 0, "check_adhoc_toml_parsers failed on .worktrees")

            # 4. check_ps_port_fallback_ssot
            c4 = drift_checks.check_ps_port_fallback_ssot()
            self.assertEqual(c4, 0, "check_ps_port_fallback_ssot failed on .worktrees")

            # 5. check_ps_encoding_and_bom
            c5 = drift_checks.check_ps_encoding_and_bom()
            self.assertEqual(c5, 0, "check_ps_encoding_and_bom failed on .worktrees")

        finally:
            if orig_env is None:
                os.environ.pop("MIOS_DRIFT_ROOT", None)
            else:
                os.environ["MIOS_DRIFT_ROOT"] = orig_env

    def test_negative_control_violations_outside_worktrees_are_caught(self):
        """Negative control: If identical violations are placed outside .worktrees/, drift checks must fail."""
        leaked_dir = self.root / "installation"
        leaked_dir.mkdir(parents=True, exist_ok=True)
        (leaked_dir / "bad_port.ps1").write_text("Get-PortFromSsot 'key' 'llm_light' 9999\n", "utf-8")

        orig_env = os.environ.get("MIOS_DRIFT_ROOT")
        try:
            os.environ["MIOS_DRIFT_ROOT"] = str(self.root)
            import importlib.util
            spec = importlib.util.spec_from_file_location("drift_checks", str(TOOLS_DIR / "drift-checks.py"))
            drift_checks = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(drift_checks)

            c = drift_checks.check_ps_port_fallback_ssot()
            self.assertEqual(c, 1, "Negative control failed: drift check did not catch violation outside .worktrees/")
        finally:
            if orig_env is None:
                os.environ.pop("MIOS_DRIFT_ROOT", None)
            else:
                os.environ["MIOS_DRIFT_ROOT"] = orig_env


class TestWorktreeSecurityAndSanitization(unittest.TestCase):
    """Subagent ID validation in mios_worktree.py."""

    def test_subagent_id_path_traversal_rejected(self):
        """Path traversal strings in subagent_id must be rejected."""
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Tester"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "tester@test.local"], check=True)
            (repo / "f.txt").write_text("init\n", "utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=True)

            mgr = mios_worktree.AgentWorktreeManager(repo_root=str(repo), base_worktree_dir=str(repo / ".worktrees"), base_scratch_dir=str(repo / "scratch"))
            res1 = mgr.create_worktree("../../etc/evil", "main")
            self.assertEqual(res1["status"], "error")
            self.assertIn("Invalid subagent_id", res1["message"])

            res2 = mgr.cleanup_worktree("../subagent", merge=False)
            self.assertEqual(res2["status"], "error")
            self.assertIn("Invalid subagent_id", res2["message"])

            res3 = mgr.create_worktree("subagent;rm -rf /", "main")
            self.assertEqual(res3["status"], "error")
            self.assertIn("Invalid subagent_id", res3["message"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
