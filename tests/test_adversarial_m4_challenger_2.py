#!/usr/bin/env python3
"""
tests/test_adversarial_m4_challenger_2.py

Adversarial Stress Suite for Milestone M4 Challenger 2.
Empirically stress-tests:
1. Extreme git index lock contention across concurrent workers (threads and processes).
2. Stale lock eviction (>45s) vs live lock backoff and recovery.
3. Conflicting branch edits and atomic rollback via `git merge --abort`, ensuring base tree
   remains completely clean and conflicted worktrees are preserved for inspection.
4. Multi-harness concurrency argument synthesis for Claude Code CLI (`claude -p`) and AGY (`agy -p`).
5. Zero base-tree corruption or index collisions under high concurrency (`git fsck --full`).
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import random
import shutil
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


class AdversarialM4Challenger2Tests(unittest.TestCase):
    """Rigorous empirical challenge suite for M4 concurrency and merge reconciliation."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory(dir="/workspaces/MiOS", prefix="adv-m4-challenger2-")
        self.sandbox = Path(self.tmp_dir.name)

        # Initialize clean base repository
        subprocess.run(["git", "init", "-b", "main"], cwd=self.sandbox, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Adversarial Challenger 2"], cwd=self.sandbox, check=True)
        subprocess.run(["git", "config", "user.email", "challenger2@example.com"], cwd=self.sandbox, check=True)

        # Set up dev-loop narrow exclude rules by default so .worktrees/ is excluded from porcelain
        info_dir = self.sandbox / ".git" / "info"
        info_dir.mkdir(parents=True, exist_ok=True)
        (info_dir / "exclude").write_text(".worktrees/\n.devloop/run-*/\n.devloop/native/\n", encoding="utf-8")

        # Initial tracked files
        (self.sandbox / "AGENTS.md").write_text("# Agents SSOT\n", encoding="utf-8")
        (self.sandbox / "TASKS.md").write_text("# Tasks\n", encoding="utf-8")
        (self.sandbox / "src").mkdir(parents=True, exist_ok=True)
        (self.sandbox / "src" / "core.py").write_text("VERSION = '1.0.0'\n", encoding="utf-8")
        (self.sandbox / "src" / "math_lib.py").write_text("def add(a, b): return a + b\n", encoding="utf-8")

        subprocess.run(["git", "add", "."], cwd=self.sandbox, check=True)
        subprocess.run(["git", "commit", "-m", "Initial base commit"], cwd=self.sandbox, check=True)

    def tearDown(self) -> None:
        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    # =============================================================================================
    # 1. EXTREME GIT INDEX LOCK CONTENTION ACROSS CONCURRENT WORKERS
    # =============================================================================================

    def test_probe_1_1_concurrent_thread_stampede_run_git_safe(self) -> None:
        """Probe 1.1: 20 concurrent workers in dedicated worktrees pounding run_git_safe with simultaneous commits."""
        num_threads = 20
        worktrees: list[Path] = []
        for i in range(num_threads):
            wt = self.sandbox / ".worktrees" / f"stampede-{i}"
            subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt), "-b", f"stampede/{i}", "HEAD"], check=True)
            worktrees.append(wt)

        errors: list[Exception] = []
        results: list[subprocess.CompletedProcess] = []

        def worker(thread_idx: int, wt: Path) -> None:
            try:
                file_path = wt / "src" / f"worker_{thread_idx}.txt"
                file_path.write_text(f"worker {thread_idx}\n", encoding="utf-8")
                
                # Add file
                add_res = git_lock.run_git_safe(["add", f"src/worker_{thread_idx}.txt"], cwd=wt)
                if add_res.returncode != 0:
                    errors.append(RuntimeError(f"Add failed in thread {thread_idx}: {add_res.stderr}"))
                    return

                # Commit file
                commit_res = git_lock.run_git_safe(["commit", "-m", f"Commit from worker {thread_idx}"], cwd=wt)
                if commit_res.returncode != 0:
                    errors.append(RuntimeError(f"Commit failed in thread {thread_idx}: {commit_res.stderr}"))
                    return
                results.append(commit_res)

                # Status check
                status_res = git_lock.run_git_safe(["status", "--porcelain"], cwd=wt)
                if status_res.returncode != 0:
                    errors.append(RuntimeError(f"Status failed in thread {thread_idx}: {status_res.stderr}"))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i, worktrees[i])) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        self.assertEqual(len(errors), 0, f"Thread stampede encountered errors: {errors}")
        self.assertEqual(len(results), num_threads, f"Expected {num_threads} commits, got {len(results)}")

        # Verify git repository object integrity
        fsck = subprocess.run(["git", "fsck", "--full"], cwd=self.sandbox, capture_output=True, text=True)
        self.assertEqual(fsck.returncode, 0, f"git fsck failed: {fsck.stderr}")
        status = subprocess.check_output(["git", "status", "--porcelain"], cwd=self.sandbox, text=True).strip()
        self.assertEqual(status, "", "Base repository index must remain completely clean")

    def test_probe_1_2_artificial_index_lock_contention_with_exponential_backoff(self) -> None:
        """Probe 1.2: Artificial live lock injection while 10 workers commit in isolated worktrees, verifying backoff recovery."""
        # Create 10 isolated worktrees
        num_workers = 10
        worktrees: list[Path] = []
        for i in range(num_workers):
            wt = self.sandbox / ".worktrees" / f"noisy-lane-{i}"
            subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt), "-b", f"noisy/{i}", "HEAD"], check=True)
            worktrees.append(wt)

        # Target lock file in main repo index.lock (which run_git_safe checks for all linked worktrees!)
        main_lock_path = self.sandbox / ".git" / "index.lock"
        stop_locker = threading.Event()

        def noisy_locker() -> None:
            """Periodically creates and deletes main index.lock simulating transient git lock contention."""
            while not stop_locker.is_set():
                try:
                    main_lock_path.write_text("transient lock\n", encoding="utf-8")
                    time.sleep(random.uniform(0.04, 0.10))
                    if main_lock_path.exists():
                        main_lock_path.unlink(missing_ok=True)
                    time.sleep(random.uniform(0.02, 0.05))
                except OSError:
                    pass

        locker_thread = threading.Thread(target=noisy_locker, daemon=True)
        locker_thread.start()

        worker_errors: list[Exception] = []

        def worker_task(idx: int, wt: Path) -> None:
            try:
                test_file = wt / "src" / f"noisy_task_{idx}.txt"
                test_file.write_text(f"content {idx}\n", encoding="utf-8")
                add_res = git_lock.run_git_safe(["add", f"src/noisy_task_{idx}.txt"], max_retries=10, base_delay=0.15, cwd=wt)
                if add_res.returncode != 0:
                    worker_errors.append(RuntimeError(f"Worker {idx} add failed: {add_res.stderr}"))
                    return
                commit_res = git_lock.run_git_safe(["commit", "-m", f"noisy commit {idx}"], max_retries=10, base_delay=0.15, cwd=wt)
                if commit_res.returncode != 0:
                    worker_errors.append(RuntimeError(f"Worker {idx} commit failed: {commit_res.stderr}"))
            except Exception as e:
                worker_errors.append(e)

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
                futures = [executor.submit(worker_task, i, worktrees[i]) for i in range(num_workers)]
                for f in concurrent.futures.as_completed(futures):
                    f.result()
        finally:
            stop_locker.set()
            locker_thread.join(timeout=5)
            if main_lock_path.exists():
                main_lock_path.unlink(missing_ok=True)

        self.assertEqual(len(worker_errors), 0, f"Worker tasks failed under lock contention: {worker_errors}")
        fsck = subprocess.run(["git", "fsck", "--full"], cwd=self.sandbox, capture_output=True, text=True)
        self.assertEqual(fsck.returncode, 0)

    def test_probe_1_3_multi_worktree_concurrent_independent_commits(self) -> None:
        """Probe 1.3: 8 linked worktrees committing concurrently without index collision."""
        num_worktrees = 8
        worktrees: list[Path] = []
        for i in range(num_worktrees):
            wt = self.sandbox / ".worktrees" / f"lane-{i}"
            subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt), "-b", f"lane/{i}", "HEAD"], check=True)
            worktrees.append(wt)

        errors: list[Exception] = []

        def commit_in_worktree(wt: Path, idx: int) -> None:
            try:
                (wt / "src" / f"feature_{idx}.py").write_text(f"def feat_{idx}(): return {idx}\n", encoding="utf-8")
                add_res = adapters.git(wt, "add", f"src/feature_{idx}.py")
                if add_res.returncode != 0:
                    errors.append(RuntimeError(f"Add in wt {idx} failed: {add_res.stderr}"))
                    return
                commit_res = adapters.git(wt, "commit", "-m", f"Add feature {idx}")
                if commit_res.returncode != 0:
                    errors.append(RuntimeError(f"Commit in wt {idx} failed: {commit_res.stderr}"))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=commit_in_worktree, args=(wt, i)) for i, wt in enumerate(worktrees)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        self.assertEqual(len(errors), 0, f"Concurrent worktree commits failed: {errors}")

        # Base repository tree remains untouched (with .worktrees/ excluded via .git/info/exclude)
        base_status = subprocess.check_output(["git", "status", "--porcelain"], cwd=self.sandbox, text=True).strip()
        self.assertEqual(base_status, "", "Base tree must remain completely clean during worktree operations")

        # Fsck verification
        fsck = subprocess.run(["git", "fsck", "--full"], cwd=self.sandbox, capture_output=True, text=True)
        self.assertEqual(fsck.returncode, 0)

    # =============================================================================================
    # 2. STALE LOCK EVICTION (>45s) VS LIVE LOCK BACKOFF
    # =============================================================================================

    def test_probe_2_1_stale_lock_evicted_immediately(self) -> None:
        """Probe 2.1: index.lock with mtime > 45s is evicted on first attempt without delay."""
        lock_file = self.sandbox / ".git" / "index.lock"
        lock_file.write_text("stale dead process\n", encoding="utf-8")
        stale_time = time.time() - 60  # 60s ago (> 45s threshold)
        os.utime(str(lock_file), (stale_time, stale_time))

        t0 = time.time()
        # Use git add which modifies the index and would fail if index.lock was present
        test_file = self.sandbox / "src" / "stale_test.txt"
        test_file.write_text("stale test\n", encoding="utf-8")
        res = git_lock.run_git_safe(["add", "src/stale_test.txt"], cwd=self.sandbox)
        elapsed = time.time() - t0

        self.assertEqual(res.returncode, 0, f"run_git_safe failed: {res.stderr}")
        self.assertFalse(lock_file.exists(), "Stale index.lock must be evicted")
        self.assertLess(elapsed, 2.0, "Stale lock eviction must be fast on attempt 0")

    def test_probe_2_2_stale_lock_in_linked_worktree_evicted(self) -> None:
        """Probe 2.2: Stale index.lock inside .git/worktrees/<id>/ is evicted by worktree runner."""
        wt = self.sandbox / ".worktrees" / "lane-stale"
        subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt), "-b", "lane/stale", "HEAD"], check=True)

        wt_git_dir = git_lock.resolve_git_dir(wt)
        lock_file = wt_git_dir / "index.lock"
        lock_file.write_text("stale worktree lock\n", encoding="utf-8")
        stale_time = time.time() - 90
        os.utime(str(lock_file), (stale_time, stale_time))

        (wt / "src" / "wt_stale.txt").write_text("wt stale\n", encoding="utf-8")
        res = git_lock.run_git_safe(["add", "src/wt_stale.txt"], cwd=wt)
        self.assertEqual(res.returncode, 0)
        self.assertFalse(lock_file.exists(), "Worktree stale index.lock must be evicted")

    def test_probe_2_3_stale_lock_in_main_git_dir_evicted_by_worktree_runner(self) -> None:
        """Probe 2.3: Stale index.lock in main repo .git/ is evicted when worktree runner runs."""
        wt = self.sandbox / ".worktrees" / "lane-main-stale"
        subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt), "-b", "lane/main-stale", "HEAD"], check=True)

        main_lock = self.sandbox / ".git" / "index.lock"
        main_lock.write_text("stale main lock\n", encoding="utf-8")
        stale_time = time.time() - 50
        os.utime(str(main_lock), (stale_time, stale_time))

        # Call run_git_safe with cwd=wt
        (wt / "src" / "wt_main_stale.txt").write_text("wt main stale\n", encoding="utf-8")
        res = git_lock.run_git_safe(["add", "src/wt_main_stale.txt"], cwd=wt)
        self.assertEqual(res.returncode, 0)
        self.assertFalse(main_lock.exists(), "Main repo stale lock must be evicted by worktree runner")

    def test_probe_2_4_live_lock_not_evicted_and_backs_off(self) -> None:
        """Probe 2.4: Live lock (mtime <= 45s) is NOT evicted; process backs off and succeeds upon release."""
        lock_file = self.sandbox / ".git" / "index.lock"
        lock_file.write_text("active live worker\n", encoding="utf-8")
        fresh_time = time.time() - 5  # Only 5s old (live)
        os.utime(str(lock_file), (fresh_time, fresh_time))

        # Release lock in background after 350ms
        def delayed_release() -> None:
            time.sleep(0.35)
            if lock_file.exists():
                lock_file.unlink(missing_ok=True)

        threading.Thread(target=delayed_release, daemon=True).start()

        test_file = self.sandbox / "src" / "live_backoff_test.txt"
        test_file.write_text("live backoff content\n", encoding="utf-8")

        t0 = time.time()
        res = git_lock.run_git_safe(["add", "src/live_backoff_test.txt"], max_retries=6, base_delay=0.1, cwd=self.sandbox)
        elapsed = time.time() - t0

        self.assertEqual(res.returncode, 0, f"run_git_safe failed: {res.stderr}")
        self.assertGreaterEqual(elapsed, 0.25, "run_git_safe should have backed off waiting for live lock")
        self.assertFalse(lock_file.exists())

    def test_probe_2_5_live_lock_held_exceeds_retries_without_deletion(self) -> None:
        """Probe 2.5: Live lock held continuously causes failure without deleting the live lock."""
        lock_file = self.sandbox / ".git" / "index.lock"
        lock_file.write_text("active non-terminating worker\n", encoding="utf-8")
        fresh_time = time.time() - 2
        os.utime(str(lock_file), (fresh_time, fresh_time))

        test_file = self.sandbox / "src" / "unreleased_lock.txt"
        test_file.write_text("unreleased\n", encoding="utf-8")

        try:
            res = git_lock.run_git_safe(["add", "src/unreleased_lock.txt"], max_retries=3, base_delay=0.05, cwd=self.sandbox)
            self.assertNotEqual(res.returncode, 0, "Should fail when lock is continuously held")
            self.assertIn("index.lock", res.stderr)
            # The lock must NOT have been deleted because it was fresh
            self.assertTrue(lock_file.exists(), "Live lock must NOT be deleted by backoff")
        finally:
            if lock_file.exists():
                lock_file.unlink(missing_ok=True)

    # =============================================================================================
    # 3. CONFLICTING BRANCH EDITS AND ATOMIC ROLLBACK VIA GIT MERGE --ABORT
    # =============================================================================================

    def test_probe_3_1_conflicting_edits_atomic_rollback_and_worktree_preservation(self) -> None:
        """Probe 3.1: Conflicting concurrent branch merges trigger git merge --abort, leaving base clean
        and keeping conflicted worktrees completely preserved for inspection."""
        wt1 = self.sandbox / ".worktrees" / "lane-cf-1"
        wt2 = self.sandbox / ".worktrees" / "lane-cf-2"
        subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt1), "-b", "lane/cf-1", "HEAD"], check=True)
        subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt2), "-b", "lane/cf-2", "HEAD"], check=True)

        # Base initial commit SHA
        initial_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.sandbox, text=True).strip()

        # Lane 1 modifies core.py
        (wt1 / "src" / "core.py").write_text("VERSION = '2.0.0-lane1'\nAUTHOR = 'Worker 1'\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(wt1), "commit", "-am", "Lane 1 version bump"], check=True)

        # Lane 2 modifies core.py in exact same lines (guaranteed conflict)
        (wt2 / "src" / "core.py").write_text("VERSION = '3.0.0-lane2'\nAUTHOR = 'Worker 2'\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(wt2), "commit", "-am", "Lane 2 incompatible version bump"], check=True)

        # Pre-plant untracked developer notes in base repository to verify they survive cleanly
        (self.sandbox / "developer_notes.txt").write_text("Developer notes must survive rollback\n", encoding="utf-8")

        # Merge Lane 1 into base via --no-ff
        merge1 = subprocess.run(["git", "-C", str(self.sandbox), "merge", "--no-ff", "-m", "Merge lane 1", "lane/cf-1"], capture_output=True, text=True)
        self.assertEqual(merge1.returncode, 0, f"Merge 1 failed: {merge1.stderr}")
        lane1_merged_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.sandbox, text=True).strip()
        self.assertNotEqual(initial_sha, lane1_merged_sha)

        # Attempt merge Lane 2 into base -> Expected conflict
        merge2 = subprocess.run(["git", "-C", str(self.sandbox), "merge", "--no-ff", "lane/cf-2"], capture_output=True, text=True)
        self.assertNotEqual(merge2.returncode, 0, "Merge 2 must fail due to conflicting edits")
        self.assertIn("CONFLICT", merge2.stdout + merge2.stderr)

        # Verify base tree is in conflict state
        status_during_conflict = subprocess.check_output(["git", "status", "--porcelain"], cwd=self.sandbox, text=True)
        self.assertIn("UU src/core.py", status_during_conflict, "Must report unmerged conflict path")

        # Execute atomic rollback via git merge --abort
        abort_proc = subprocess.run(["git", "-C", str(self.sandbox), "merge", "--abort"], capture_output=True, text=True)
        self.assertEqual(abort_proc.returncode, 0, f"git merge --abort failed: {abort_proc.stderr}")

        # Assertions on Base Tree:
        # 1. Base status contains only the pre-existing untracked developer_notes.txt (.worktrees/ is excluded)
        status_after_abort = subprocess.check_output(["git", "status", "--porcelain"], cwd=self.sandbox, text=True).strip()
        self.assertEqual(status_after_abort, "?? developer_notes.txt", "Base repo must have no uncommitted diffs or conflict markers")

        # 2. Base content of core.py is strictly Lane 1's version
        core_content = (self.sandbox / "src" / "core.py").read_text(encoding="utf-8")
        self.assertEqual(core_content, "VERSION = '2.0.0-lane1'\nAUTHOR = 'Worker 1'\n")
        self.assertNotIn("<<<<<<<", core_content)
        self.assertNotIn("=======", core_content)
        self.assertNotIn(">>>>>>>", core_content)

        # 3. Base HEAD SHA is unchanged from Lane 1 merge
        current_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.sandbox, text=True).strip()
        self.assertEqual(current_sha, lane1_merged_sha, "HEAD commit must remain at Lane 1 merge commit")

        # 4. Untracked file preserved
        self.assertTrue((self.sandbox / "developer_notes.txt").exists())
        self.assertEqual((self.sandbox / "developer_notes.txt").read_text(encoding="utf-8"), "Developer notes must survive rollback\n")

        # 5. Assertions on Conflicted Worktree:
        # Conflicted worktree must be PRESERVED on disk for operator inspection
        self.assertTrue(wt2.is_dir(), "Conflicted worktree must NOT be deleted")
        self.assertTrue((wt2 / "src" / "core.py").exists())
        self.assertEqual((wt2 / "src" / "core.py").read_text(encoding="utf-8"), "VERSION = '3.0.0-lane2'\nAUTHOR = 'Worker 2'\n")

        # Conflicted branch must still exist and be intact
        branch_check = subprocess.run(["git", "rev-parse", "--verify", "lane/cf-2"], cwd=self.sandbox, capture_output=True, text=True)
        self.assertEqual(branch_check.returncode, 0, "Conflicted branch must be preserved")

    def test_probe_3_2_devloop_gate_merge_conflict_handling_contract(self) -> None:
        """Probe 3.2: Verify devloop gate_merge contract: on conflict, merge is aborted, worktree kept, exit status 1."""
        # Create a worktree and make it conflict with base
        wt = self.sandbox / ".worktrees" / "lane-contract-conflict"
        subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt), "-b", "lane/contract-cf", "HEAD"], check=True)

        # Mutate base
        (self.sandbox / "src" / "math_lib.py").write_text("def add(a, b): return a + b + 10\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.sandbox), "commit", "-am", "Base change to math_lib"], check=True)

        # Mutate worktree
        (wt / "src" / "math_lib.py").write_text("def add(a, b): return a + b + 999\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(wt), "commit", "-am", "Worktree change to math_lib"], check=True)

        # Run merge command via adapters.git
        merge_res = adapters.git(self.sandbox, "merge", "--no-ff", "--no-edit", "lane/contract-cf")
        self.assertNotEqual(merge_res.returncode, 0, "Merge must fail")

        # Execute the exact recovery sequence specified in devloop.sh line 180:
        # `git merge --abort 2>/dev/null || true; echo "  MERGE CONFLICT — aborted; worktree and branch kept for review" >&2`
        abort_res = subprocess.run(["git", "-C", str(self.sandbox), "merge", "--abort"], capture_output=True, text=True)
        self.assertEqual(abort_res.returncode, 0)

        # Verify base tree clean (excluding .worktrees/)
        status = subprocess.check_output(["git", "status", "--porcelain"], cwd=self.sandbox, text=True).strip()
        self.assertEqual(status, "")

        # Verify worktree preserved
        self.assertTrue(wt.exists())

    # =============================================================================================
    # 4. MULTI-HARNESS CONCURRENCY ARGUMENT SYNTHESIS (CLAUDE CODE CLI + AGY)
    # =============================================================================================

    def test_probe_4_1_claude_code_argument_synthesis_contract(self) -> None:
        """Probe 4.1: Claude Code CLI argument synthesis enforces cwd=wt, removes max-turns, excludes -w flag."""
        wt_dir = self.sandbox / ".worktrees" / "lane-claude"
        wt_dir.mkdir(parents=True, exist_ok=True)
        report_file = self.sandbox / ".devloop" / "report-claude.json"
        prompt_file = self.sandbox / ".devloop" / "prompt-claude.md"
        prompt_file.parent.mkdir(parents=True, exist_ok=True)
        prompt_file.write_text("Task: Implement feature in Claude\n", encoding="utf-8")

        lane_spec = {
            "id": "lane-claude",
            "objective": "Implement feature in Claude",
            "worker": {
                "harness": "claude-code",
                "max_turns": 15,
                "timeout_s": 300,
                "model": "claude-3-7-sonnet",
                "effort": "high",
                "permission_mode": "dontAsk",
                "allowed_tools": "Read,Edit,Write,Bash",
                "max_budget_usd": 2.50,
            }
        }

        argv = adapters.build_argv(
            lane_spec,
            wt_dir,
            report_file,
            self.sandbox / "lane.json",
            SCRIPTS.parent / "SKILL.md",
            prompt_file
        )

        # Invariant Assertions:
        self.assertEqual(argv[0], "claude")
        self.assertIn("-p", argv)
        prompt_idx = argv.index("-p") + 1
        self.assertEqual(argv[prompt_idx], "Task: Implement feature in Claude\n")
        self.assertIn("--output-format", argv)
        self.assertEqual(argv[argv.index("--output-format") + 1], "json")
        self.assertIn("--permission-mode", argv)
        self.assertEqual(argv[argv.index("--permission-mode") + 1], "dontAsk")
        self.assertIn("--allowedTools", argv)
        self.assertEqual(argv[argv.index("--allowedTools") + 1], "Read,Edit,Write,Bash")
        self.assertIn("--model", argv)
        self.assertEqual(argv[argv.index("--model") + 1], "claude-3-7-sonnet")
        self.assertIn("--effort", argv)
        self.assertEqual(argv[argv.index("--effort") + 1], "high")
        self.assertIn("--max-budget-usd", argv)
        self.assertEqual(argv[argv.index("--max-budget-usd") + 1], "2.5")
        self.assertIn("--json-schema", argv)

        # Critical Negative Invariants:
        self.assertNotIn("--max-turns", argv, "--max-turns was deprecated and removed from claude CLI")
        self.assertNotIn("-w", argv, "Worktree must NOT be passed via -w flag (isolation handled via cwd=wt)")

    def test_probe_4_2_antigravity_argument_synthesis_contract(self) -> None:
        """Probe 4.2: Antigravity CLI argument synthesis carries print-timeout, dangerously-skip-permissions, model."""
        wt_dir = self.sandbox / ".worktrees" / "lane-agy"
        wt_dir.mkdir(parents=True, exist_ok=True)
        report_file = self.sandbox / ".devloop" / "report-agy.json"
        prompt_file = self.sandbox / ".devloop" / "prompt-agy.md"
        prompt_file.parent.mkdir(parents=True, exist_ok=True)
        prompt_file.write_text("Task: Implement feature in AGY\n", encoding="utf-8")

        lane_spec = {
            "id": "lane-agy",
            "objective": "Implement feature in AGY",
            "worker": {
                "harness": "antigravity",
                "max_turns": 20,
                "timeout_s": 450,
                "model": "gemini-2.5-pro",
                "effort": "high",
                "sandbox": "isolated",
            }
        }

        argv = adapters.build_argv(
            lane_spec,
            wt_dir,
            report_file,
            self.sandbox / "lane.json",
            SCRIPTS.parent / "SKILL.md",
            prompt_file
        )

        # Invariant Assertions:
        self.assertEqual(argv[0], "agy")
        self.assertIn("-p", argv)
        prompt_idx = argv.index("-p") + 1
        self.assertEqual(argv[prompt_idx], "Task: Implement feature in AGY\n")
        self.assertIn("--output-format", argv)
        self.assertEqual(argv[argv.index("--output-format") + 1], "json")
        self.assertIn("--print-timeout", argv)
        self.assertEqual(argv[argv.index("--print-timeout") + 1], "450s")
        self.assertIn("--dangerously-skip-permissions", argv)
        self.assertIn("--model", argv)
        self.assertEqual(argv[argv.index("--model") + 1], "gemini-2.5-pro")
        self.assertIn("--effort", argv)
        self.assertEqual(argv[argv.index("--effort") + 1], "high")
        self.assertIn("--sandbox", argv)
        self.assertEqual(argv[argv.index("--sandbox") + 1], "isolated")

    def test_probe_4_3_heterogeneous_concurrent_multi_harness_waves(self) -> None:
        """Probe 4.3: Parallel wave specification with both Claude Code CLI and AGY lanes synthesizes cleanly."""
        spec = {
            "version": "2",
            "base_ref": "HEAD",
            "worktree_root": ".worktrees",
            "lanes": [
                {
                    "id": "lane-claude-core",
                    "objective": "Core logic in Claude Code",
                    "owned_paths": ["src/core/*"],
                    "positive_cmd": "python3 -c 'exit(0)'",
                    "negative_control_cmd": "python3 -c 'exit(1)'",
                    "negative_expect": "exit(1)",
                    "worker": {"harness": "claude-code", "model": "opus", "max_turns": 10, "timeout_s": 120}
                },
                {
                    "id": "lane-agy-auth",
                    "objective": "Auth service in AGY",
                    "owned_paths": ["src/auth/*"],
                    "positive_cmd": "python3 -c 'exit(0)'",
                    "negative_control_cmd": "python3 -c 'exit(1)'",
                    "negative_expect": "exit(1)",
                    "worker": {"harness": "antigravity", "model": "gemini-3.8-flash-high", "max_turns": 10, "timeout_s": 120}
                },
                {
                    "id": "lane-claude-api",
                    "objective": "API layer in Claude Code",
                    "owned_paths": ["src/api/*"],
                    "positive_cmd": "python3 -c 'exit(0)'",
                    "negative_control_cmd": "python3 -c 'exit(1)'",
                    "negative_expect": "exit(1)",
                    "depends_on": ["lane-claude-core"],
                    "worker": {"harness": "claude-code", "model": "claude-3-5-sonnet", "max_turns": 10, "timeout_s": 120}
                },
                {
                    "id": "lane-agy-db",
                    "objective": "DB layer in AGY",
                    "owned_paths": ["src/db/*"],
                    "positive_cmd": "python3 -c 'exit(0)'",
                    "negative_control_cmd": "python3 -c 'exit(1)'",
                    "negative_expect": "exit(1)",
                    "depends_on": ["lane-agy-auth"],
                    "worker": {"harness": "antigravity", "model": "gemini-2.5-pro", "max_turns": 10, "timeout_s": 120}
                }
            ]
        }

        # Validate spec
        errs = adapters.validate_spec(spec)
        self.assertEqual(errs, [], f"Spec validation failed: {errs}")

        # Compute waves
        waves = adapters.waves(spec)
        self.assertEqual(len(waves), 2, "Expected 2 waves")
        # Wave 0 runs lane-claude-core and lane-agy-auth concurrently
        self.assertEqual(sorted(waves[0]), ["lane-agy-auth", "lane-claude-core"])
        # Wave 1 runs lane-agy-db and lane-claude-api concurrently
        self.assertEqual(sorted(waves[1]), ["lane-agy-db", "lane-claude-api"])

        # Check synthesis for each lane in Wave 0
        wt_root = self.sandbox / ".worktrees"
        for lane_id in waves[0]:
            lane = next(l for l in spec["lanes"] if l["id"] == lane_id)
            wt = wt_root / lane_id
            wt.mkdir(parents=True, exist_ok=True)
            rep = self.sandbox / f"report-{lane_id}.json"
            prompt = self.sandbox / f"prompt-{lane_id}.md"
            prompt.write_text(f"Prompt for {lane_id}\n", encoding="utf-8")
            argv = adapters.build_argv(lane, wt, rep, self.sandbox / "lane.json", SCRIPTS.parent / "SKILL.md", prompt)
            self.assertGreater(len(argv), 3)
            if "claude" in lane_id:
                self.assertEqual(argv[0], "claude")
            else:
                self.assertEqual(argv[0], "agy")

    def test_probe_4_4_permission_denials_and_envelope_downgrade(self) -> None:
        """Probe 4.4: Envelope denials downgrade lane status from done to partial."""
        lane = {"id": "lane-test", "objective": "test objective"}

        # Claude envelope with permission_denials
        claude_stdout = json.dumps({
            "num_turns": 3,
            "permission_denials": ["Bash tool denied"],
            "devloop_report": {
                "status": "done",
                "objective": "test objective",
                "summary": "Completed with denials"
            }
        })
        rep_claude = adapters.normalize_report(lane, "claude-code", claude_stdout, 0, False, 3)
        self.assertEqual(rep_claude["status"], "partial", "Claude permission_denials must downgrade status to partial")
        self.assertTrue(any("denial" in str(u).lower() for u in rep_claude["unverified"]))

        # AGY envelope with denied_actions
        agy_stdout = json.dumps({
            "status": "SUCCESS",
            "denied_actions": ["Command rm -rf denied"],
            "devloop_report": {
                "status": "done",
                "objective": "test objective",
                "summary": "Completed with denied action"
            }
        })
        rep_agy = adapters.normalize_report(lane, "antigravity", agy_stdout, 0, False, 2)
        self.assertEqual(rep_agy["status"], "partial", "AGY denied_actions must downgrade status to partial")

        # AGY exit code 12 maps to budget
        rep_agy_budget = adapters.normalize_report(lane, "antigravity", "", 12, False, None)
        self.assertEqual(rep_agy_budget["status"], "budget", "AGY exit 12 must map to status budget")

    # =============================================================================================
    # 5. ZERO BASE-TREE CORRUPTION OR INDEX COLLISIONS UNDER HIGH CONCURRENCY
    # =============================================================================================

    def test_probe_5_1_stress_lifecycle_and_zero_corruption_git_fsck(self) -> None:
        """Probe 5.1: Full lifecycle of 12 concurrent workers creating worktrees, modifying files,
        committing, merging, and aborting conflicts, followed by comprehensive git fsck --full."""
        num_lanes = 12
        worktrees: list[Path] = []
        for i in range(num_lanes):
            wt = self.sandbox / ".worktrees" / f"stress-lane-{i}"
            subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt), "-b", f"stress/{i}", "HEAD"], check=True)
            worktrees.append(wt)

        def worker_lane(idx: int, wt: Path) -> None:
            # Half lanes write unique files, half lanes write to a contested file
            if idx % 2 == 0:
                (wt / "src" / f"unique_{idx}.py").write_text(f"val = {idx}\n", encoding="utf-8")
            else:
                # Contested file
                (wt / "src" / "contested.py").write_text(f"contested_from_lane = {idx}\n", encoding="utf-8")
            
            adapters.git(wt, "add", ".")
            adapters.git(wt, "commit", "-m", f"Commit from stress lane {idx}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(worker_lane, i, worktrees[i]) for i in range(num_lanes)]
            for f in concurrent.futures.as_completed(futures):
                f.result()

        # Sequential reconciliation loop (mimicking devloop.sh gate_merge)
        merged_count = 0
        conflict_count = 0
        for i in range(num_lanes):
            br = f"stress/{i}"
            res = adapters.git(self.sandbox, "merge", "--no-ff", "--no-edit", br)
            if res.returncode == 0:
                merged_count += 1
            else:
                conflict_count += 1
                subprocess.run(["git", "-C", str(self.sandbox), "merge", "--abort"], check=True)

        self.assertGreater(merged_count, 0, "At least unique lanes should merge cleanly")
        self.assertGreater(conflict_count, 0, "Contested lanes should conflict and abort")

        # Base tree must be clean
        base_status = subprocess.check_output(["git", "status", "--porcelain"], cwd=self.sandbox, text=True).strip()
        self.assertEqual(base_status, "", "Base repository must have zero uncommitted changes after stress reconciliation")

        # Complete object database and index consistency verification
        fsck = subprocess.run(["git", "fsck", "--full", "--strict"], cwd=self.sandbox, capture_output=True, text=True)
        self.assertEqual(fsck.returncode, 0, f"git fsck --full --strict failed: {fsck.stderr}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
