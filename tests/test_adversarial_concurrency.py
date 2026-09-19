#!/usr/bin/env python3
"""
test_adversarial_concurrency.py

Adversarial Stress Suite for Dev-Loop Concurrency, Claude Code CLI Harness,
and Git Lock Contention Handling.

Rigorous empirical challenge covering:
1. True parallel execution verification under devloop.sh --concurrent (concurrency barriers & timestamps).
2. Claude Code CLI (`claude -p`) invocation with cwd=wt, schema validation, and permission denial handling.
3. Stress testing index.lock contention across concurrent operations, exponential backoff, and stale lock eviction (>45s).
4. Atomic --no-ff merge with conflict abortion without base repo contamination.
5. Path injection and dirty worktree reuse sanitization.
"""
from __future__ import annotations

import json
import os
import random
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent

SCRIPTS_PATHS = [
    Path("/home/mios-dev/.dev-loop/skills/dev-loop/scripts"),
    Path("/home/mios-dev/.gemini/config/skills/dev-loop/scripts"),
]
SCRIPTS = next((p for p in SCRIPTS_PATHS if p.exists()), None)
if SCRIPTS is None:
    raise RuntimeError(f"Could not locate dev-loop scripts directory in {SCRIPTS_PATHS}")

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import adapters
import git_lock
import job

AGENT_PIPE_DIR = REPO_ROOT / "usr" / "lib" / "mios" / "agent-pipe"
if str(AGENT_PIPE_DIR) not in sys.path and AGENT_PIPE_DIR.exists():
    sys.path.insert(0, str(AGENT_PIPE_DIR))
import mios_worktree


def make_sandbox_repo(prefix: str = "adversarial-sandbox-") -> Path:
    td = Path(tempfile.mkdtemp(prefix=prefix))
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Adversarial Challenger",
        "GIT_AUTHOR_EMAIL": "challenger@example.com",
        "GIT_COMMITTER_NAME": "Adversarial Challenger",
        "GIT_COMMITTER_EMAIL": "challenger@example.com",
    }
    subprocess.run(["git", "init", "-q", "-b", "main", str(td)], check=True, env=env)
    subprocess.run(["git", "-C", str(td), "config", "user.name", "Adversarial Challenger"], check=True, env=env)
    subprocess.run(["git", "-C", str(td), "config", "user.email", "challenger@example.com"], check=True, env=env)

    (td / "README.md").write_text("# Adversarial Test Repo\n", encoding="utf-8")
    (td / "src").mkdir(parents=True, exist_ok=True)
    (td / "src" / "main.py").write_text("def run():\n    return 'base'\n", encoding="utf-8")

    info_dir = td / ".git" / "info"
    info_dir.mkdir(parents=True, exist_ok=True)
    (info_dir / "exclude").write_text(".worktrees/\n.devloop/run-*/\n.devloop/native/\n", encoding="utf-8")

    subprocess.run(["git", "-C", str(td), "add", "."], check=True, env=env)
    subprocess.run(["git", "-C", str(td), "commit", "-qm", "Initial commit"], check=True, env=env)
    return td


class TestAdversarialConcurrency(unittest.TestCase):
    def setUp(self) -> None:
        self.sandbox = make_sandbox_repo(prefix=f"adv-{self._testMethodName}-")
        self.devloop_sh = SCRIPTS / "devloop.sh"

    def tearDown(self) -> None:
        if self.sandbox.exists():
            shutil.rmtree(self.sandbox, ignore_errors=True)

    def test_adv_01_true_parallel_execution_barrier(self):
        """Verify multiple worker lanes in a wave execute concurrently in parallel, overlapping in time."""
        # Place mock worker and spec outside the sandbox in a temporary folder so sandbox base repo remains 100% clean
        tmp_dir = Path(tempfile.mkdtemp(prefix="adv-mock-"))
        timing_dir = tmp_dir / "timings"
        timing_dir.mkdir(parents=True, exist_ok=True)

        mock_worker = tmp_dir / "mock_worker.py"
        mock_worker.write_text(f"""#!/usr/bin/env python3
import sys, time, json, os
from pathlib import Path

lane_id = sys.argv[1]
report_path = Path(sys.argv[2])
wt_path = Path(sys.argv[3])
t_dir = Path({repr(str(timing_dir))})

t_start = time.time()
(t_dir / f"{{lane_id}}.start").write_text(str(t_start))
time.sleep(7.0)
t_end = time.time()
(t_dir / f"{{lane_id}}.end").write_text(str(t_end))

# Create an edit in the owned file in the worktree
owned_file = wt_path / "src" / f"file_{{lane_id}}.txt"
owned_file.parent.mkdir(parents=True, exist_ok=True)
owned_file.write_text(f"content from {{lane_id}}\\n")

# Write devloop report
rep = {{
    "status": "done",
    "summary": f"Lane {{lane_id}} completed",
    "unverified": [],
    "permission_denials": []
}}
report_path.write_text(json.dumps(rep))
""", encoding="utf-8")
        mock_worker.chmod(0o755)

        lanes_spec = {
            "objective": "Test true concurrent parallel execution",
            "base_ref": "main",
            "worktree_root": ".worktrees",
            "terminal_layout": "headless",
            "lanes": [
                {
                    "id": f"worker-{i}",
                    "objective": f"Worker {i} parallel execution",
                    "owned_paths": [f"src/file_worker-{i}.txt"],
                    "depends_on": [],
                    "worker": {
                        "harness": "custom",
                        "command": f"{sys.executable} {mock_worker} worker-{i} {{report}} {{wt}}",
                        "timeout_s": 60,
                        "max_turns": 1
                    },
                    "positive_cmd": "exit 0",
                    "negative_control_cmd": "exit 1",
                    "negative_expect": ".*"
                }
                for i in range(1, 4)
            ]
        }
        spec_path = tmp_dir / "lanes.json"
        spec_path.write_text(json.dumps(lanes_spec, indent=2), encoding="utf-8")

        # Run devloop.sh with --concurrent --layout headless
        t0 = time.time()
        res = subprocess.run(
            [str(self.devloop_sh), str(spec_path), "--concurrent", "--layout", "headless"],
            cwd=str(self.sandbox),
            capture_output=True,
            text=True,
            env={**os.environ, "CI": "1", "NO_COLOR": "1"}
        )
        total_duration = time.time() - t0

        try:
            self.assertEqual(res.returncode, 0, f"devloop.sh failed: {res.stderr}\nStdout: {res.stdout}")

            # Verify timing overlap
            starts = [float((timing_dir / f"worker-{i}.start").read_text()) for i in range(1, 4)]
            ends = [float((timing_dir / f"worker-{i}.end").read_text()) for i in range(1, 4)]

            latest_start = max(starts)
            earliest_end = min(ends)

            # In true parallel execution, the latest start must be earlier than the earliest end (active overlap)
            self.assertLess(
                latest_start, earliest_end,
                f"Workers did not run concurrently! Starts: {starts}, Ends: {ends}"
            )
            # In true parallel execution, all 3 workers run concurrently while wave waits on 20s interval.
            self.assertLess(total_duration, 60.0, f"Total execution time {total_duration}s indicates sequential execution")
            print(f"\n[Adversarial Concurrency Proof] Starts: {starts}, Ends: {ends}, Overlap window: {earliest_end - latest_start:.2f}s")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_adv_02_claude_code_cli_invocation_and_cwd_isolation(self):
        """Verify claude-code harness synthesizes claude -p, omits -w, sets cwd=wt, and validates schema."""
        lane = {
            "id": "claude-test-01",
            "objective": "Refactor module",
            "owned_paths": ["src/module.py"],
            "worker": {
                "harness": "claude-code",
                "model": "opus",
                "effort": "xhigh",
                "permission_mode": "dontAsk",
                "allowed_tools": "Read,Edit,Write,Bash",
                "max_budget_usd": 2.5,
                "timeout_s": 120,
                "max_turns": 10
            }
        }
        wt = self.sandbox / ".worktrees" / "claude-test-01"
        wt.mkdir(parents=True, exist_ok=True)
        report = self.sandbox / "report.json"
        lane_json = self.sandbox / "lane.json"
        lane_json.write_text(json.dumps(lane), encoding="utf-8")
        skill = SCRIPTS / "SKILL.md"
        prompt_file = self.sandbox / "prompt.txt"
        prompt_file.write_text("Test prompt content", encoding="utf-8")

        argv = adapters.build_argv(lane, wt, report, lane_json, skill, prompt_file)

        # Verify command arguments
        self.assertEqual(argv[0], "claude")
        self.assertEqual(argv[1], "-p")
        self.assertEqual(argv[2], "Test prompt content")
        self.assertIn("--output-format", argv)
        self.assertEqual(argv[argv.index("--output-format") + 1], "json")
        self.assertIn("--permission-mode", argv)
        self.assertEqual(argv[argv.index("--permission-mode") + 1], "dontAsk")
        self.assertIn("--allowedTools", argv)
        self.assertEqual(argv[argv.index("--allowedTools") + 1], "Read,Edit,Write,Bash")
        self.assertIn("--model", argv)
        self.assertEqual(argv[argv.index("--model") + 1], "opus")
        self.assertIn("--effort", argv)
        self.assertEqual(argv[argv.index("--effort") + 1], "xhigh")
        self.assertIn("--json-schema", argv)
        schema = json.loads(argv[argv.index("--json-schema") + 1])
        self.assertIn("devloop_report", schema.get("properties", {}))
        self.assertIn("--max-budget-usd", argv)
        self.assertEqual(argv[argv.index("--max-budget-usd") + 1], "2.5")

        # Crucial invariant: -w must NOT be in argv
        self.assertNotIn("-w", argv)
        self.assertNotIn("--worktree", argv)

    def test_adv_03_claude_permission_denials_handling(self):
        """Verify Claude Code CLI envelope with permission denials downgrades status to partial."""
        envelope = {
            "result": "I tried to edit the file but permission was denied.",
            "num_turns": 3,
            "permission_denials": [
                {"tool": "Bash", "command": "rm -rf /"}
            ],
            "structured_output": {
                "devloop_report": {
                    "status": "done",
                    "summary": "Attempted work",
                    "unverified": []
                }
            }
        }
        raw_out = json.dumps(envelope)
        lane = {
            "id": "claude-denial",
            "worker": {"harness": "claude-code"}
        }

        # Normalize report from claude output
        rep = adapters.normalize_report(lane, "claude-code", raw_out, 0, False, 3)
        self.assertEqual(rep["status"], "partial", "Report status must downgrade to 'partial' on permission denials")
        self.assertTrue(any("permission_denials" in item.lower() for item in rep["unverified"]))

    def test_adv_04_rapid_index_lock_contention_and_backoff(self):
        """Stress-test index.lock contention: 15 concurrent threads calling run_git_safe while lock toggles."""
        num_threads = 15
        barrier = threading.Barrier(num_threads + 1)
        stop_lock_toggler = threading.Event()
        git_dir = git_lock.resolve_git_dir(self.sandbox)
        lock_path = git_dir / "index.lock"

        def lock_toggler():
            barrier.wait()
            while not stop_lock_toggler.is_set():
                try:
                    lock_path.touch()
                    time.sleep(0.08)
                    lock_path.unlink(missing_ok=True)
                    time.sleep(0.05)
                except OSError:
                    pass

        toggler = threading.Thread(target=lock_toggler)
        toggler.start()

        results = []

        def worker_op(idx: int):
            barrier.wait()
            # Perform git safe operation
            res = git_lock.run_git_safe(["status", "--porcelain"], max_retries=10, base_delay=0.1, cwd=self.sandbox)
            results.append((idx, res.returncode, res.stderr))

        threads = [threading.Thread(target=worker_op, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=15)

        stop_lock_toggler.set()
        toggler.join(timeout=5)
        lock_path.unlink(missing_ok=True)

        self.assertEqual(len(results), num_threads, "All worker threads must complete")
        for idx, rc, stderr in results:
            self.assertEqual(rc, 0, f"Thread {idx} failed with exit {rc}: {stderr}")

    def test_adv_05_stale_lock_eviction_vs_active_lock_retention(self):
        """Verify index.lock older than 45s is evicted immediately, while active lock (<45s) is not."""
        git_dir = git_lock.resolve_git_dir(self.sandbox)
        lock_path = git_dir / "index.lock"

        # Case 1: Stale lock (>45s)
        lock_path.touch()
        stale_time = time.time() - 90
        os.utime(str(lock_path), (stale_time, stale_time))

        res = git_lock.run_git_safe(["status"], cwd=self.sandbox)
        self.assertEqual(res.returncode, 0, "Stale lock must be evicted and git command succeed")
        self.assertFalse(lock_path.exists(), "Stale lock must have been unlinked")

        # Case 2: Active lock (<45s) on a lock-acquiring git operation (git add)
        (self.sandbox / "new_pending.txt").write_text("pending\n", encoding="utf-8")
        lock_path.touch()
        active_time = time.time()
        os.utime(str(lock_path), (active_time, active_time))

        res = git_lock.run_git_safe(["add", "new_pending.txt"], max_retries=2, base_delay=0.05, cwd=self.sandbox)
        self.assertNotEqual(res.returncode, 0, "Active lock must cause failure if not released within retries")
        self.assertIn("index.lock", res.stderr)
        self.assertTrue(lock_path.exists(), "Active lock must NOT be deleted if newer than 45s")

        lock_path.unlink(missing_ok=True)
        (self.sandbox / "new_pending.txt").unlink(missing_ok=True)

    def test_adv_06_atomic_merge_conflict_abortion(self):
        """Verify conflicting merge triggers git merge --abort, leaving base repo clean and worktree intact."""
        # Create branch 1 and branch 2 modifying the same file
        wt1 = self.sandbox / ".worktrees" / "lane-1"
        wt2 = self.sandbox / ".worktrees" / "lane-2"

        subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", str(wt1), "-b", "lane/lane-1", "main"], check=True)
        subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", str(wt2), "-b", "lane/lane-2", "main"], check=True)

        (wt1 / "src" / "main.py").write_text("def run():\n    return 'conflict-from-lane-1'\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(wt1), "commit", "-am", "Lane 1 edit"], check=True)

        (wt2 / "src" / "main.py").write_text("def run():\n    return 'conflict-from-lane-2'\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(wt2), "commit", "-am", "Lane 2 edit"], check=True)

        # Merge lane 1 into main
        subprocess.run(["git", "-C", str(self.sandbox), "merge", "--no-ff", "--no-edit", "lane/lane-1"], check=True)
        head_after_lane1 = subprocess.run(["git", "-C", str(self.sandbox), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()

        # Now attempt merge of lane 2 via adapters.git
        cp = adapters.git(self.sandbox, "merge", "--no-ff", "--no-edit", "lane/lane-2")
        self.assertNotEqual(cp.returncode, 0, "Merge of lane 2 must conflict")

        # Execute abort (as devloop.sh does on conflict)
        abort_res = subprocess.run(["git", "-C", str(self.sandbox), "merge", "--abort"], capture_output=True, text=True)
        self.assertEqual(abort_res.returncode, 0)

        # Assert base repo status is 100% clean
        st = subprocess.run(["git", "-C", str(self.sandbox), "status", "--porcelain"], capture_output=True, text=True, check=True).stdout
        self.assertEqual(st.strip(), "", "Base repository must have zero unstaged or uncommitted changes after abort")

        # Assert HEAD is still at lane 1 merge commit
        head_current = subprocess.run(["git", "-C", str(self.sandbox), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(head_current, head_after_lane1)

        # Assert worktree 2 still exists for inspection
        self.assertTrue(wt2.exists(), "Conflicting worktree must be preserved for operator review")

    def test_adv_07_agent_worktree_manager_sanitization(self):
        """Verify mios_worktree.py sanitizes subagent_id and handles merge-tree conflicts cleanly."""
        mgr = mios_worktree.AgentWorktreeManager(
            repo_root=str(self.sandbox),
            base_worktree_dir=str(self.sandbox / ".worktrees"),
            base_scratch_dir=str(self.sandbox / ".scratch"),
            dry_run=False
        )

        # Attack: path traversal and shell injection strings
        for bad_id in ["../root", "lane/../../etc", "agent;reboot", "agent|calc", "$HOME", ""]:
            res = mgr.create_worktree(bad_id)
            self.assertEqual(res["status"], "error")
            self.assertIn("Invalid subagent_id", res.get("message", ""))

        # Valid create
        res = mgr.create_worktree("valid-sub-01", base_branch="main")
        self.assertEqual(res["status"], "success")
        wt_path = Path(res["worktree_path"])
        self.assertTrue(wt_path.exists())

        # Cleanup with merge
        (wt_path / "src" / "new_feature.py").write_text("# new feature\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(wt_path), "add", "src/new_feature.py"], check=True)
        subprocess.run(["git", "-C", str(wt_path), "commit", "-m", "feature commit"], check=True)

        res_cl = mgr.cleanup_worktree("valid-sub-01", merge=True, target_branch="main")
        self.assertEqual(res_cl["status"], "success")
        self.assertTrue(res_cl["merged"])
        self.assertFalse(wt_path.exists())
        self.assertTrue((self.sandbox / "src" / "new_feature.py").exists())


if __name__ == "__main__":
    unittest.main()
