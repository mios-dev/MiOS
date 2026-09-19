#!/usr/bin/env python3
"""Adversarial stress testing suite for dev-loop lane isolation, leakage detection,
worktree reuse sanitization, concurrency safety, and subagent traversal defense.
"""

import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

# Add harness scripts to sys.path
HARNESS_DIR = Path("/home/mios-dev/.dev-loop/skills/dev-loop/scripts")
AGENT_PIPE_DIR = Path("/workspaces/MiOS/usr/lib/mios/agent-pipe")
if str(HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(HARNESS_DIR))
if str(AGENT_PIPE_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_PIPE_DIR))

import adapters
import git_lock
import job
from mios_worktree import AgentWorktreeManager


class ChallengerStressHarness(unittest.TestCase):
    """Adversarial stress tests challenging lane isolation, leakage detection, and concurrency."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory(dir="/workspaces/MiOS", prefix="challenger-stress-")
        self.sandbox = Path(self.tmp_dir.name)

        # Initialize clean git repository as base tree
        subprocess.run(["git", "init", "-b", "main"], cwd=self.sandbox, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Challenger"], cwd=self.sandbox, check=True)
        subprocess.run(["git", "config", "user.email", "challenger@example.com"], cwd=self.sandbox, check=True)

        # Base repository files
        (self.sandbox / "AGENTS.md").write_text("# Agents SSOT\n", encoding="utf-8")
        (self.sandbox / "TASKS.md").write_text("# Tasks Ledger\n", encoding="utf-8")
        (self.sandbox / "src").mkdir(parents=True, exist_ok=True)
        (self.sandbox / "src" / "main.py").write_text("def run(): pass\n", encoding="utf-8")
        (self.sandbox / "src" / "util.py").write_text("def helper(): pass\n", encoding="utf-8")

        subprocess.run(["git", "add", "."], cwd=self.sandbox, check=True)
        subprocess.run(["git", "commit", "-m", "Initial base commit"], cwd=self.sandbox, check=True)

        self.allowed = adapters.BASE_TREE_ALWAYS_ALLOWED + (".worktrees/",)

    def tearDown(self) -> None:
        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    # =========================================================================
    # SCENARIO 1: Base Tree Leakage Detection during `adapters.py gate`
    # =========================================================================

    def test_adv_01_stray_untracked_file_in_base_halts_gate_with_exit_2(self) -> None:
        """Adversarial: Untracked file planted in base tree during positive_cmd halts gate with code 2."""
        wt = self.sandbox / ".worktrees" / "lane-1"
        subprocess.run(["git", "worktree", "add", "-b", "lane/1", str(wt)], cwd=self.sandbox, check=True, capture_output=True)

        # Worker edits inside worktree
        (wt / "src" / "feature.py").write_text("# lane 1 feature\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=wt, check=True)

        run_dir = self.sandbox / ".devloop" / "run-1"
        run_dir.mkdir(parents=True, exist_ok=True)
        lane_file = run_dir / "lane.json"

        # Positive command deliberately leaks an untracked file into base repo root
        stray_path = self.sandbox / "STRAY_LEAK_FIXTURE.txt"
        lane_data = {
            "id": "1",
            "owned_paths": ["src/feature.py"],
            "positive_cmd": f"touch '{stray_path}' && true",
            "negative_control_cmd": "exit 1",
            "negative_expect": "",
            "worktree_root": ".worktrees",
        }
        lane_file.write_text(json.dumps(lane_data), encoding="utf-8")

        cmd = [
            sys.executable, str(HARNESS_DIR / "adapters.py"),
            "gate", "--lane", str(lane_file), "--wt", str(wt), "--run", str(run_dir), "--root", str(self.sandbox)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)

        # Gate must halt with exit code 2
        self.assertEqual(res.returncode, 2, f"Gate must exit with code 2 on base leakage, got {res.returncode}")
        self.assertIn("BASE TREE LEAKAGE DETECTED", res.stderr)
        self.assertIn("STRAY_LEAK_FIXTURE.txt", res.stderr)

        # Pre-control worktree diff must be parked
        patch_file = run_dir / "lane-1.patch"
        self.assertTrue(patch_file.exists(), "Diff patch must be preserved when leakage is detected")
        self.assertIn("src/feature.py", patch_file.read_text(encoding="utf-8"))

    def test_adv_02_mutation_to_tracked_base_file_halts_gate_with_exit_2(self) -> None:
        """Adversarial: Modifying a tracked base file during gate halts with code 2 and diagnoses path."""
        wt = self.sandbox / ".worktrees" / "lane-2"
        subprocess.run(["git", "worktree", "add", "-b", "lane/2", str(wt)], cwd=self.sandbox, check=True, capture_output=True)

        (wt / "src" / "feature2.py").write_text("# lane 2 feature\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=wt, check=True)

        run_dir = self.sandbox / ".devloop" / "run-2"
        run_dir.mkdir(parents=True, exist_ok=True)
        lane_file = run_dir / "lane.json"

        # Positive command maliciously corrupts base tree tracked file
        tracked_file = self.sandbox / "src" / "main.py"
        lane_data = {
            "id": "2",
            "owned_paths": ["src/feature2.py"],
            "positive_cmd": f"echo 'CORRUPTED_BASE' >> '{tracked_file}' && true",
            "negative_control_cmd": "exit 1",
            "negative_expect": "",
            "worktree_root": ".worktrees",
        }
        lane_file.write_text(json.dumps(lane_data), encoding="utf-8")

        cmd = [
            sys.executable, str(HARNESS_DIR / "adapters.py"),
            "gate", "--lane", str(lane_file), "--wt", str(wt), "--run", str(run_dir), "--root", str(self.sandbox)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)

        self.assertEqual(res.returncode, 2)
        self.assertIn("BASE TREE LEAKAGE DETECTED", res.stderr)
        self.assertIn("src/main.py", res.stderr)
        self.assertTrue((run_dir / "lane-2.patch").exists())

    def test_adv_03_negative_control_base_leak_halts_gate_with_exit_2(self) -> None:
        """Adversarial: Negative control command leaking a file into base repo halts gate with code 2."""
        wt = self.sandbox / ".worktrees" / "lane-3"
        subprocess.run(["git", "worktree", "add", "-b", "lane/3", str(wt)], cwd=self.sandbox, check=True, capture_output=True)

        (wt / "src" / "feature3.py").write_text("# lane 3\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=wt, check=True)

        run_dir = self.sandbox / ".devloop" / "run-3"
        run_dir.mkdir(parents=True, exist_ok=True)
        lane_file = run_dir / "lane.json"

        stray_neg = self.sandbox / "NEG_CTRL_LEAK.tmp"
        lane_data = {
            "id": "3",
            "owned_paths": ["src/feature3.py"],
            "positive_cmd": "true",
            "negative_control_cmd": f"touch '{stray_neg}' && exit 1",
            "negative_expect": "",
            "worktree_root": ".worktrees",
        }
        lane_file.write_text(json.dumps(lane_data), encoding="utf-8")

        cmd = [
            sys.executable, str(HARNESS_DIR / "adapters.py"),
            "gate", "--lane", str(lane_file), "--wt", str(wt), "--run", str(run_dir), "--root", str(self.sandbox)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)

        self.assertEqual(res.returncode, 2)
        self.assertIn("BASE TREE LEAKAGE DETECTED", res.stderr)
        self.assertIn("NEG_CTRL_LEAK.tmp", res.stderr)

    def test_adv_04_prefix_bypass_flaw_in_stray_base_edits(self) -> None:
        """Adversarial Hardening: stray_base_edits anchored prefix matching on directories.

        In adapters.py:
          not any(path == a or (a.endswith("/") and path.startswith(a)) for a in allowed)
        When a is 'AGENTS.md', exact equality is required, so 'AGENTS.md.bak' is caught as a stray.
        """
        before = {}
        now = {
            "AGENTS.md.bak": "??",
            "TASKS.md.tmp": "??",
            "src/valid_stray.py": "??",
        }
        strays = adapters.stray_base_edits(before, now, self.allowed)

        # All strays including AGENTS.md.bak and TASKS.md.tmp are detected
        self.assertIn("src/valid_stray.py", strays)
        self.assertIn("AGENTS.md.bak", strays)
        self.assertIn("TASKS.md.tmp", strays)
        self.assertEqual(set(strays), {"AGENTS.md.bak", "TASKS.md.tmp", "src/valid_stray.py"})

    # =========================================================================
    # SCENARIO 2: Concurrent Worker Execution under High Contention
    # =========================================================================

    def test_adv_05_concurrent_claude_code_and_agy_workers_under_lock_contention(self) -> None:
        """Adversarial: 6 concurrent workers (3 Claude Code, 3 AGY) operating under heavy lock contention."""
        jobs_root = self.sandbox / ".devloop" / "jobs"
        num_lanes = 6
        lanes = [f"lane-c{i}" for i in range(num_lanes)]
        wts = [self.sandbox / ".worktrees" / lid for lid in lanes]

        # Provision all worktrees
        for lid, wt in zip(lanes, wts):
            subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt), "-b", f"lane/{lid}", "HEAD"], check=True)

        barrier = threading.Barrier(num_lanes)
        errors = []

        def worker_simulation(idx: int, lid: str, wt: Path):
            try:
                # Synchronize workers to start simultaneously to induce peak contention
                barrier.wait(timeout=10)

                if idx % 2 == 0:
                    # Claude Code CLI simulation:
                    # Modifies code, stages, commits via git_lock, writes JSON envelope
                    file_path = wt / "src" / f"claude_mod_{idx}.py"
                    file_path.write_text(f"# Claude Code worker {idx}\n", encoding="utf-8")

                    cp1 = git_lock.run_git_safe(["add", f"src/claude_mod_{idx}.py"], cwd=wt, max_retries=15)
                    if cp1.returncode != 0:
                        errors.append(f"Claude {idx} add failed: {cp1.stderr}")
                    cp2 = git_lock.run_git_safe(["commit", "-m", f"Claude worker {idx} commit"], cwd=wt, max_retries=15)
                    if cp2.returncode != 0:
                        errors.append(f"Claude {idx} commit failed: {cp2.stderr}")

                    envelope = {
                        "status": "success",
                        "response": f"Claude worker {idx} finished task",
                        "num_turns": 3,
                        "permission_denials": []
                    }
                    (wt / "claude_envelope.json").write_text(json.dumps(envelope), encoding="utf-8")
                else:
                    # AGY simulation:
                    # Modifies code, stages, commits via git_lock, writes report
                    file_path = wt / "src" / f"agy_mod_{idx}.py"
                    file_path.write_text(f"# AGY worker {idx}\n", encoding="utf-8")

                    cp1 = git_lock.run_git_safe(["add", f"src/agy_mod_{idx}.py"], cwd=wt, max_retries=15)
                    if cp1.returncode != 0:
                        errors.append(f"AGY {idx} add failed: {cp1.stderr}")
                    cp2 = git_lock.run_git_safe(["commit", "-m", f"AGY worker {idx} commit"], cwd=wt, max_retries=15)
                    if cp2.returncode != 0:
                        errors.append(f"AGY {idx} commit failed: {cp2.stderr}")

                    report = {
                        "status": "done",
                        "summary": f"AGY worker {idx} completed cleanly",
                        "unverified": []
                    }
                    (wt / "report.json").write_text(json.dumps(report), encoding="utf-8")
            except Exception as e:
                errors.append(f"Worker {lid} exception: {e}")

        threads = [
            threading.Thread(target=worker_simulation, args=(i, lanes[i], wts[i]))
            for i in range(num_lanes)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"Concurrent workers encountered errors under contention: {errors}")

        # Sequentially reconcile diffs without index lock conflicts
        for lid in lanes:
            merge_cp = git_lock.run_git_safe(
                ["merge", "--no-ff", "-m", f"Merge {lid}", f"lane/{lid}"], cwd=self.sandbox, max_retries=10
            )
            self.assertEqual(merge_cp.returncode, 0, f"Merge of {lid} failed: {merge_cp.stderr}")

        # Verify all changes exist in base repo
        for i in range(num_lanes):
            if i % 2 == 0:
                self.assertTrue((self.sandbox / "src" / f"claude_mod_{i}.py").exists())
            else:
                self.assertTrue((self.sandbox / "src" / f"agy_mod_{i}.py").exists())

    # =========================================================================
    # SCENARIO 3: Dirty Existing Worktree Reuse Sanitization
    # =========================================================================

    def test_adv_06_dirty_existing_worktree_reuse_sanitization(self) -> None:
        """Adversarial: Existing worktree with untracked files, nested dirs, unstaged & staged edits is fully cleaned."""
        wt = self.sandbox / ".worktrees" / "1"
        subprocess.run(["git", "worktree", "add", "-b", "lane/1", str(wt)], cwd=self.sandbox, check=True, capture_output=True)

        # Plant aggressive dirty state in the existing worktree
        untracked_file = wt / "planted_untracked_junk.txt"
        untracked_file.write_text("rogue untracked file\n", encoding="utf-8")

        nested_dir = wt / "nested_planted_dir" / "deeper"
        nested_dir.mkdir(parents=True, exist_ok=True)
        (nested_dir / "dirty_fixture.sh").write_text("#!/bin/bash\nexit 1\n", encoding="utf-8")

        tracked_file = wt / "src" / "main.py"
        tracked_file.write_text("corrupted content not committed\n", encoding="utf-8")

        staged_file = wt / "src" / "staged_file.py"
        staged_file.write_text("staged in index\n", encoding="utf-8")
        subprocess.run(["git", "add", "src/staged_file.py"], cwd=wt, check=True)

        # Check that dirty status exists
        st_pre = subprocess.run(["git", "status", "--porcelain"], cwd=wt, capture_output=True, text=True).stdout
        self.assertIn("planted_untracked_junk.txt", st_pre)
        self.assertIn("nested_planted_dir/", st_pre)
        self.assertIn("src/main.py", st_pre)
        self.assertIn("src/staged_file.py", st_pre)

        # Execute devloop.sh worktree sanitization sequence:
        # git -C "$WTA" checkout -f "$BR" || git -C "$WTA" checkout -f -B "$BR" "$BASE"
        # git -C "$WTA" reset --hard "$BR" || git -C "$WTA" reset --hard "$BASE" || true
        # git -C "$WTA" clean -ffd
        subprocess.run(["git", "-C", str(wt), "checkout", "-f", "lane/1"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(wt), "reset", "--hard", "lane/1"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(wt), "clean", "-ffd"], check=True, capture_output=True)

        # Assert all dirty state was completely wiped out
        self.assertFalse(untracked_file.exists(), "Untracked file must be removed by clean -ffd")
        self.assertFalse(nested_dir.exists(), "Nested untracked dir must be removed by clean -ffd")
        self.assertFalse(staged_file.exists(), "Staged file must be removed by reset --hard + clean")
        self.assertEqual(
            tracked_file.read_text(encoding="utf-8"),
            "def run(): pass\n",
            "Tracked file must be restored to clean HEAD revision"
        )
        st_post = subprocess.run(["git", "status", "--porcelain"], cwd=wt, capture_output=True, text=True).stdout
        self.assertEqual(st_post.strip(), "", f"Worktree must be completely clean after sanitization, got:\n{st_post}")

    # =========================================================================
    # SCENARIO 4: Subagent ID Traversal Injection in `mios_worktree.py`
    # =========================================================================

    def test_adv_07_subagent_id_path_traversal_injection_rejected(self) -> None:
        """Adversarial: Path traversal and injection subagent_id values are strictly rejected."""
        mgr = AgentWorktreeManager(
            repo_root=str(self.sandbox),
            base_worktree_dir=str(self.sandbox / ".worktrees"),
            base_scratch_dir=str(self.sandbox / "scratch")
        )

        malicious_ids = [
            "../../etc/passwd",
            "../etc/shadow",
            "..",
            "....//",
            "/absolute/root",
            "lane/1",
            "lane\\1",
            "subagent;rm -rf /",
            "subagent$(whoami)",
            "subagent`id`",
            "subagent*wildcard",
            "sub agent with spaces",
            "sub\ttab",
            "sub\nnewline",
            "~subagent",
            "subagent|pipe",
            "subagent&bg",
        ]

        for bad_id in malicious_ids:
            # create_worktree must fail closed
            c_res = mgr.create_worktree(bad_id)
            self.assertEqual(
                c_res["status"], "error",
                f"create_worktree failed to reject malicious id: {bad_id!r}, returned: {c_res}"
            )
            self.assertIn("Invalid subagent_id", c_res["message"])

            # cleanup_worktree must fail closed
            cl_res = mgr.cleanup_worktree(bad_id)
            self.assertEqual(
                cl_res["status"], "error",
                f"cleanup_worktree failed to reject malicious id: {bad_id!r}, returned: {cl_res}"
            )
            self.assertIn("Invalid subagent_id", cl_res["message"])

    def test_adv_08_valid_subagent_ids_accepted(self) -> None:
        """Adversarial: Valid subagent IDs conforming to regex pass validation without false positives."""
        mgr = AgentWorktreeManager(
            repo_root=str(self.sandbox),
            base_worktree_dir=str(self.sandbox / ".worktrees"),
            base_scratch_dir=str(self.sandbox / "scratch"),
            dry_run=True
        )

        valid_ids = [
            "worker-1",
            "worker_impl_2",
            "challenger.3",
            "subagent-42.v1",
            "Lane-A_B-C.D",
        ]

        for good_id in valid_ids:
            c_res = mgr.create_worktree(good_id)
            self.assertEqual(c_res["status"], "dry_run", f"create_worktree rejected valid id {good_id!r}")
            cl_res = mgr.cleanup_worktree(good_id)
            self.assertEqual(cl_res["status"], "dry_run", f"cleanup_worktree rejected valid id {good_id!r}")

    # =========================================================================
    # ADDITIONAL ATTACK VECTORS
    # =========================================================================

    def test_adv_09_claude_permission_denials_downgrades_report(self) -> None:
        """Adversarial: Claude Code CLI worker output with permission_denials downgrades report status to partial."""
        lane = {
            "id": "c1",
            "objective": "test claude denials",
            "worker": {"harness": "claude-code"},
        }
        envelope = {
            "status": "success",
            "response": "Refactored code",
            "permission_denials": ["Bash(git push)", "FileEdit(/etc/hosts)"]
        }
        report = adapters.normalize_report(lane, "claude-code", json.dumps(envelope), 0, False, 2)
        self.assertEqual(report["status"], "partial", f"Status must be downgraded to partial, got {report['status']}")
        self.assertTrue(any("harness denied" in u.lower() or "permission_denials" in u.lower() for u in report["unverified"]))

    def test_adv_10_sentinel_precheck_dead_code_under_worktrees_dir(self) -> None:
        """Adversarial Finding: Sentinel precheck in adapters.py:640 is dead code under .worktrees.

        In cmd_gate:
            _hits = [str(q.relative_to(wt)) for q in wt.rglob(f"*{_sent}*")
                     if ".git" not in q.parts and ".worktrees" not in q.parts]
        Because wt is inside .worktrees/, q.parts ALWAYS contains '.worktrees'.
        Therefore _hits is always empty, and the sentinel precheck NEVER fires.
        """
        wt = self.sandbox / ".worktrees" / "lane-vacuous"
        subprocess.run(["git", "worktree", "add", "-b", "lane/vacuous", str(wt)], cwd=self.sandbox, check=True, capture_output=True)

        sentinel = "DEVLOOP-PLANTED-T999-STRAY"
        planted_file = wt / f"{sentinel}.sh"
        planted_file.write_text("#!/bin/bash\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=wt, check=True)

        # Empirically verify that q.parts contains .worktrees
        q = planted_file
        self.assertIn(".worktrees", q.parts)

        # The buggy check in unpatched cmd_gate would filter out q because '.worktrees' is in q.parts
        hits = [str(q.relative_to(wt)) for q in wt.rglob(f"*{sentinel}*")
                if ".git" not in q.parts and ".worktrees" not in q.parts]
        self.assertEqual(hits, [], "Demonstrates defect: hits is empty despite sentinel existing in worktree!")

        # Correct check examines relative parts:
        relative_hits = [str(q.relative_to(wt)) for q in wt.rglob(f"*{sentinel}*")
                         if ".git" not in q.relative_to(wt).parts and ".worktrees" not in q.relative_to(wt).parts]
        self.assertEqual(relative_hits, [f"{sentinel}.sh"])

        # E2E verification: adapters.py gate now catches the pre-existing sentinel and halts with exit 2
        run_dir = self.sandbox / ".devloop" / "run-vacuous"
        run_dir.mkdir(parents=True, exist_ok=True)
        lane_file = run_dir / "lane.json"
        lane_data = {
            "id": "vacuous",
            "owned_paths": [],
            "positive_cmd": "true",
            "negative_control_cmd": f"test -f {sentinel}.sh && exit 1",
            "negative_expect": "",
            "worktree_root": ".worktrees",
        }
        lane_file.write_text(json.dumps(lane_data), encoding="utf-8")
        gate_cmd = [
            sys.executable, str(HARNESS_DIR / "adapters.py"),
            "gate", "--lane", str(lane_file), "--wt", str(wt), "--run", str(run_dir), "--root", str(self.sandbox)
        ]
        gate_res = subprocess.run(gate_cmd, capture_output=True, text=True)
        self.assertEqual(gate_res.returncode, 2)
        self.assertIn("VACUOUS BEFORE IT RAN", gate_res.stderr)
        self.assertIn(sentinel, gate_res.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)

