#!/usr/bin/env python3
"""
test_lane_isolation_leakage.py — Controls for Milestones M1, M2, and M3:
- Strict worktree isolation and worktree reuse clean/reset (M1)
- Base tree state snapshotting, gate leakage detection, base-audit CLI, and diagnostic stray path reporting (M2)
- Multi-lane concurrency and git lock safe retry backoff (M3)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "dev-loop" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import adapters
import git_lock


def init_repo() -> Path:
    d = Path(tempfile.mkdtemp(prefix="leakage-repo-"))
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "init", "-q", "-b", "main", str(d)], check=True)
    (d / "shipped.txt").write_text("shipped content\n")
    (d / "calc.py").write_text("def add(a, b): return a + b\n")
    subprocess.run(["git", "-C", str(d), "add", "."], check=True)
    subprocess.run(["git", "-C", str(d), "commit", "-qm", "init"], check=True, env=env)
    return d


class TestBaseTreeAuditCLI(unittest.TestCase):
    def test_base_snapshot_and_clean_audit(self):
        repo = init_repo()
        snap = repo / "snap.json"
        # Test base-snapshot
        cp = subprocess.run([sys.executable, str(SCRIPTS / "adapters.py"), "base-snapshot", "--root", str(repo), "--out", str(snap)],
                            capture_output=True, text=True)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertTrue(snap.exists())
        data = json.loads(snap.read_text())
        self.assertEqual(data, {})

        # Test base-audit on clean repo
        cp_audit = subprocess.run([sys.executable, str(SCRIPTS / "adapters.py"), "base-audit", "--root", str(repo), "--before", str(snap)],
                                  capture_output=True, text=True)
        self.assertEqual(cp_audit.returncode, 0, cp_audit.stderr)
        self.assertIn("base tree audit ok", cp_audit.stdout)

    def test_base_audit_allows_metadata_paths(self):
        repo = init_repo()
        snap = repo / "snap.json"
        subprocess.run([sys.executable, str(SCRIPTS / "adapters.py"), "base-snapshot", "--root", str(repo), "--out", str(snap)],
                       check=True)

        # Create allowed files in base tree
        os.makedirs(repo / ".devloop", exist_ok=True)
        (repo / ".devloop" / "LEDGER.md").write_text("entry\n")
        (repo / "AGENTS.md").write_text("contracts\n")
        (repo / "TASKS.md").write_text("tasks\n")
        os.makedirs(repo / ".worktrees" / "lane-1", exist_ok=True)
        (repo / ".worktrees" / "lane-1" / "work.txt").write_text("lane data\n")

        cp_audit = subprocess.run([sys.executable, str(SCRIPTS / "adapters.py"), "base-audit", "--root", str(repo), "--before", str(snap)],
                                  capture_output=True, text=True)
        self.assertEqual(cp_audit.returncode, 0, cp_audit.stderr)

    def test_base_audit_detects_planted_stray_file(self):
        repo = init_repo()
        snap = repo / "snap.json"
        subprocess.run([sys.executable, str(SCRIPTS / "adapters.py"), "base-snapshot", "--root", str(repo), "--out", str(snap)],
                       check=True)

        # Plant a stray leaked file in base repo
        (repo / "leaked_fixture.sh").write_text("echo root:pass | chpasswd\n")

        cp_audit = subprocess.run([sys.executable, str(SCRIPTS / "adapters.py"), "base-audit", "--root", str(repo), "--before", str(snap)],
                                  capture_output=True, text=True)
        self.assertEqual(cp_audit.returncode, 6, "Must exit with code 6 on stray base edits")
        self.assertIn("leaked_fixture.sh", cp_audit.stderr)
        self.assertIn("BASE TREE LEAKAGE DETECTED", cp_audit.stderr)

    def test_base_audit_detects_mutation_to_tracked_file(self):
        repo = init_repo()
        snap = repo / "snap.json"
        subprocess.run([sys.executable, str(SCRIPTS / "adapters.py"), "base-snapshot", "--root", str(repo), "--out", str(snap)],
                       check=True)

        # Mutate tracked shipped.txt
        (repo / "shipped.txt").write_text("tampered content\n")

        cp_audit = subprocess.run([sys.executable, str(SCRIPTS / "adapters.py"), "base-audit", "--root", str(repo), "--before", str(snap)],
                                  capture_output=True, text=True)
        self.assertEqual(cp_audit.returncode, 6)
        self.assertIn("shipped.txt", cp_audit.stderr)


class TestGateBaseTreeLeakage(unittest.TestCase):
    def setUp(self):
        self.repo = init_repo()
        self.wt = self.repo / ".worktrees" / "lane-1"
        self.wt.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "-C", str(self.repo), "worktree", "add", "-q", str(self.wt), "-b", "lane/1", "main"], check=True)
        self.run_dir = self.repo / ".devloop" / "run-test"
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def test_gate_passes_when_no_leakage(self):
        lane = {
            "id": "1",
            "worktree_root": ".worktrees",
            "owned_paths": ["calc.py"],
            "positive_cmd": "python3 -c 'import calc; assert calc.add(2,3) == 5'",
            "negative_control_cmd": "python3 -c 'import calc; assert calc.add(2,3) == 0'",
            "negative_expect": "AssertionError"
        }
        lane_file = self.run_dir / "lane-1.json"
        lane_file.write_text(json.dumps(lane))

        cp = subprocess.run([
            sys.executable, str(SCRIPTS / "adapters.py"), "gate",
            "--lane", str(lane_file),
            "--wt", str(self.wt),
            "--run", str(self.run_dir),
            "--root", str(self.repo)
        ], capture_output=True, text=True)
        self.assertEqual(cp.returncode, 0, f"Expected pass, got exit {cp.returncode}:\n{cp.stdout}\n{cp.stderr}")
        self.assertIn("positive: PASS", cp.stdout)
        self.assertIn("negative: FAILED for the expected reason", cp.stdout)

    def test_gate_halts_and_reports_leakage_when_negative_control_mutates_base_tree(self):
        # Negative control deliberately leaks a fixture into base tree repo root
        stray_file = self.repo / "leaked_negative_fixture.py"
        lane = {
            "id": "1",
            "worktree_root": ".worktrees",
            "owned_paths": ["calc.py"],
            "positive_cmd": "python3 -c 'import calc; assert calc.add(2,3) == 5'",
            "negative_control_cmd": f"echo 'planted = 1' > {stray_file} && python3 -c 'import calc; assert calc.add(2,3) == 0'",
            "negative_expect": "AssertionError"
        }
        lane_file = self.run_dir / "lane-1.json"
        lane_file.write_text(json.dumps(lane))

        cp = subprocess.run([
            sys.executable, str(SCRIPTS / "adapters.py"), "gate",
            "--lane", str(lane_file),
            "--wt", str(self.wt),
            "--run", str(self.run_dir),
            "--root", str(self.repo)
        ], capture_output=True, text=True)

        self.assertEqual(cp.returncode, 2, f"Gate must exit 2 on base tree leakage, got {cp.returncode}")
        self.assertIn("BASE TREE LEAKAGE DETECTED", cp.stderr)
        self.assertIn("leaked_negative_fixture.py", cp.stderr)
        # Pre-control patch must be parked
        self.assertTrue((self.run_dir / "lane-1.patch").exists(), "Pre-control patch must be parked on failure")

    def test_gate_halts_when_positive_cmd_mutates_base_tree(self):
        stray_file = self.repo / "positive_leaked.txt"
        lane = {
            "id": "1",
            "worktree_root": ".worktrees",
            "owned_paths": ["calc.py"],
            "positive_cmd": f"echo 'leak' > {stray_file} && python3 -c 'import calc; assert calc.add(2,3) == 5'",
            "negative_control_cmd": "python3 -c 'import calc; assert calc.add(2,3) == 0'",
            "negative_expect": "AssertionError"
        }
        lane_file = self.run_dir / "lane-1.json"
        lane_file.write_text(json.dumps(lane))

        cp = subprocess.run([
            sys.executable, str(SCRIPTS / "adapters.py"), "gate",
            "--lane", str(lane_file),
            "--wt", str(self.wt),
            "--run", str(self.run_dir),
            "--root", str(self.repo)
        ], capture_output=True, text=True)

        self.assertEqual(cp.returncode, 2)
        self.assertIn("BASE TREE LEAKAGE DETECTED", cp.stderr)
        self.assertIn("positive_leaked.txt", cp.stderr)


class TestWorktreeReuseSanitization(unittest.TestCase):
    def test_reusing_dirty_worktree_is_cleaned_and_reset(self):
        repo = init_repo()
        wt = repo / ".worktrees" / "lane-1"
        wt.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "-C", str(repo), "worktree", "add", "-q", str(wt), "-b", "lane/1", "main"], check=True)

        # Plant dirty modified file and untracked file in worktree
        (wt / "calc.py").write_text("corrupted content\n")
        (wt / "untracked_junk.txt").write_text("junk\n")

        # Test the reset/clean commands used in devloop.sh
        subprocess.run(["git", "-C", str(wt), "checkout", "-f", "lane/1"], check=True)
        subprocess.run(["git", "-C", str(wt), "reset", "--hard", "lane/1"], check=True)
        subprocess.run(["git", "-C", str(wt), "clean", "-ffd"], check=True)

        # Assert worktree is restored clean
        self.assertFalse((wt / "untracked_junk.txt").exists())
        self.assertEqual((wt / "calc.py").read_text(), "def add(a, b): return a + b\n")
        status = subprocess.check_output(["git", "-C", str(wt), "status", "--porcelain"], text=True)
        self.assertEqual(status.strip(), "")


class TestGitLockSafe(unittest.TestCase):
    def test_run_git_safe_resolves_and_runs(self):
        repo = init_repo()
        cp = git_lock.run_git_safe(["status", "--porcelain"], cwd=repo)
        self.assertEqual(cp.returncode, 0)

    def test_run_git_safe_cleans_stale_index_lock(self):
        repo = init_repo()
        lock_file = repo / ".git" / "index.lock"
        lock_file.write_text("fake lock")
        # Backdate mtime by 50 seconds (> 45s stale threshold)
        past = time.time() - 50
        os.utime(lock_file, (past, past))
        self.assertTrue(lock_file.exists())

        # run_git_safe should detect stale lock, evict it, and succeed
        cp = git_lock.run_git_safe(["status", "--porcelain"], cwd=repo)
        self.assertEqual(cp.returncode, 0)
class TestDevLoopE2ELeakageAndConcurrency(unittest.TestCase):
    def test_devloop_halts_on_stray_base_tree_mutation(self):
        repo = init_repo()
        # Create a lanes plan outside the repo tree to keep repo status clean at start
        lanes_dir = repo.parent
        stray_planted = repo / "stray_leak.txt"
        lanes_doc = {
            "version": "2",
            "base_ref": "main",
            "worktree_root": ".worktrees",
            "lanes": [
                {
                    "id": "leaker",
                    "owned_paths": ["calc.py"],
                    "objective": "fix calc.py but leak to base tree",
                    "positive_cmd": "python3 -c 'import calc; assert calc.add(2,3) == 5'",
                    "negative_control_cmd": f"echo 'leaked' > {stray_planted} && python3 -c 'import calc; assert calc.add(2,3) == 0'",
                    "negative_expect": "AssertionError"
                }
            ]
        }
        lanes_path = lanes_dir / "lanes.leak.json"
        lanes_path.write_text(json.dumps(lanes_doc))

        cp = subprocess.run(["sh", str(SCRIPTS / "devloop.sh"), str(lanes_path), "--layout", "headless"],
                            cwd=repo, capture_output=True, text=True, timeout=60)
        self.assertNotEqual(cp.returncode, 0, "devloop.sh must exit non-zero when stray leakage is detected")
        combined = cp.stdout + cp.stderr
        self.assertIn("BASE TREE LEAKAGE DETECTED", combined)
        self.assertIn("stray_leak.txt", combined)

    def test_devloop_concurrent_multi_lane_clean_merge(self):
        repo = init_repo()
        (repo / "calc.py").write_text("def add(a, b): return a - b\n")
        (repo / "util.py").write_text("def shout(s): return s.lower()\n")
        subprocess.run(["git", "-C", str(repo), "add", "calc.py", "util.py"], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-qm", "seeded bugs"], check=True)

        worker_calc = "sh -c \"printf 'def add(a, b): return a + b\\n' > '{wt}/calc.py' && python3 -c \\\"import json; r = {{'status': 'done', 'objective': 'fix calc', 'changed_paths': ['calc.py']}}; open('{report}','w').write(json.dumps(r)); print(json.dumps({{'devloop_report': r}}))\\\"\""
        worker_util = "sh -c \"printf 'def shout(s): return s.upper()\\n' > '{wt}/util.py' && python3 -c \\\"import json; r = {{'status': 'done', 'objective': 'fix util', 'changed_paths': ['util.py']}}; open('{report}','w').write(json.dumps(r)); print(json.dumps({{'devloop_report': r}}))\\\"\""

        lanes_dir = repo.parent
        lanes_doc = {
            "version": "2",
            "base_ref": "main",
            "worktree_root": ".worktrees",
            "terminal_layout": "detached",
            "lanes": [
                {
                    "id": "lane-calc",
                    "owned_paths": ["calc.py"],
                    "objective": "fix calc",
                    "worker": {"harness": "custom", "command": worker_calc},
                    "positive_cmd": "python3 -c 'import calc; assert calc.add(2,3) == 5'",
                    "negative_control_cmd": "cp calc.py .nc.bak; trap 'mv .nc.bak calc.py' EXIT; printf 'def add(a,b): return 0\\n' > calc.py; python3 -c 'import calc; assert calc.add(2,3) == 5'",
                    "negative_expect": "AssertionError"
                },
                {
                    "id": "lane-util",
                    "owned_paths": ["util.py"],
                    "objective": "fix util",
                    "worker": {"harness": "custom", "command": worker_util},
                    "positive_cmd": "python3 -c 'import util; assert util.shout(\"hi\") == \"HI\"'",
                    "negative_control_cmd": "cp util.py .nc.bak; trap 'mv .nc.bak util.py' EXIT; printf 'def shout(s): return \"bad\"\\n' > util.py; python3 -c 'import util; assert util.shout(\"hi\") == \"HI\"'",
                    "negative_expect": "AssertionError"
                }
            ]
        }
        lanes_path = lanes_dir / "lanes.concurrent.json"
        lanes_path.write_text(json.dumps(lanes_doc))

        cp = subprocess.run(["sh", str(SCRIPTS / "devloop.sh"), str(lanes_path), "--layout", "detached"],
                            cwd=repo, capture_output=True, text=True, timeout=60)
        combined = cp.stdout + cp.stderr
        self.assertEqual(cp.returncode, 0, f"Concurrent lanes must succeed and exit 0:\n{combined}")
        self.assertIn("merged lane/lane-calc", combined)
        self.assertIn("merged lane/lane-util", combined)
        # Verify base repo tree has both fixes cleanly merged
        self.assertEqual((repo / "calc.py").read_text().strip(), "def add(a, b): return a + b")
        self.assertEqual((repo / "util.py").read_text().strip(), "def shout(s): return s.upper()")


if __name__ == "__main__":
    unittest.main()
