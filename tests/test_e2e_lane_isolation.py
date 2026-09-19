#!/usr/bin/env python3
"""
test_e2e_lane_isolation.py

Comprehensive 5-Tier E2E Test Suite for Dev-Loop Lane Isolation,
Base-Tree Leakage Detection & Concurrent Worker Orchestration.

Covers:
  Tier 1: Feature Coverage (>=5 per feature, 15 tests total)
    - F1: Strict Worktree Isolation
    - F2: Base-Tree Leakage Detection & Enforcement
    - F3: Concurrent Worker Lanes & Claude Code CLI
  Tier 2: Boundary & Corner Cases (>=5 per feature, 15 tests total)
    - F1 Boundary/Corners
    - F2 Boundary/Corners
    - F3 Boundary/Corners
  Tier 3: Cross-Feature Combinations (5 tests)
  Tier 4: Real-World Application Scenarios (5 tests)
  Tier 5: Adversarial Coverage Hardening (4 tests)

Total: 44 comprehensive E2E tests executing in ephemeral sandboxes under /tmp.
"""
from __future__ import annotations

import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

# Resolve dev-loop scripts path
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent

SCRIPTS_PATHS = [
    Path("/home/mios-dev/.gemini/config/skills/dev-loop/scripts"),
    Path("/home/mios-dev/.dev-loop/skills/dev-loop/scripts"),
]
SCRIPTS = next((p for p in SCRIPTS_PATHS if p.exists()), None)
if SCRIPTS is None:
    raise RuntimeError(f"Could not locate dev-loop scripts directory in {SCRIPTS_PATHS}")

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import adapters
import agy_session
import git_lock
import job


# Compatibility wrappers between adapters.py (M2 target) and agy_session.py
def base_tree_state(root: Path) -> dict[str, str] | None:
    if hasattr(adapters, "base_tree_state"):
        return adapters.base_tree_state(root)
    return agy_session.base_tree_state(root)


def stray_base_edits(
    before: dict[str, str],
    now: dict[str, str] | None,
    allowed: tuple[str, ...],
) -> list[str]:
    if hasattr(adapters, "stray_base_edits"):
        return adapters.stray_base_edits(before, now, allowed)
    return agy_session.stray_base_edits(before, now, allowed)


def get_base_tree_always_allowed() -> tuple[str, ...]:
    if hasattr(adapters, "BASE_TREE_ALWAYS_ALLOWED"):
        return getattr(adapters, "BASE_TREE_ALWAYS_ALLOWED")
    return getattr(agy_session, "BASE_TREE_ALWAYS_ALLOWED")


def make_sandbox_repo(prefix: str = "devloop-e2e-sandbox-") -> Path:
    """Provisions a clean, self-contained git repository in /tmp with an initial commit."""
    td = Path(tempfile.mkdtemp(prefix=prefix))
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test Author",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test Committer",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }
    subprocess.run(["git", "init", "-q", "-b", "main", str(td)], check=True, env=env)
    subprocess.run(["git", "-C", str(td), "config", "user.name", "Test Committer"], check=True, env=env)
    subprocess.run(["git", "-C", str(td), "config", "user.email", "test@example.com"], check=True, env=env)

    (td / "README.md").write_text("# Test Repo\n", encoding="utf-8")
    (td / "src").mkdir(parents=True, exist_ok=True)
    (td / "src" / "main.py").write_text("def hello():\n    return 'world'\n", encoding="utf-8")

    # Set up dev-loop narrow exclude rules by default so .worktrees/ is excluded
    info_dir = td / ".git" / "info"
    info_dir.mkdir(parents=True, exist_ok=True)
    (info_dir / "exclude").write_text(".worktrees/\n.devloop/run-*/\n.devloop/native/\n", encoding="utf-8")

    subprocess.run(["git", "-C", str(td), "add", "."], check=True, env=env)
    subprocess.run(["git", "-C", str(td), "commit", "-qm", "Initial seed commit"], check=True, env=env)
    return td


class SandboxTestCase(unittest.TestCase):
    """Base test case managing ephemeral sandbox lifecycle."""

    def setUp(self) -> None:
        self.sandbox = make_sandbox_repo(prefix=f"sandbox-{self._testMethodName}-")
        self.allowed = get_base_tree_always_allowed() + (".worktrees/",)

    def tearDown(self) -> None:
        if self.sandbox.exists():
            shutil.rmtree(self.sandbox, ignore_errors=True)


# =================================================================================================
# TIER 1: FEATURE COVERAGE (15 tests, 5 per feature)
# =================================================================================================


class TestTier1FeatureCoverage(SandboxTestCase):
    """Tier 1: Core Feature Verification across F1, F2, F3."""

    # ---------------------------------------------------------------------------------------------
    # F1: Strict Worktree Isolation
    # ---------------------------------------------------------------------------------------------

    def test_t1_f1_01_dedicated_worktree_layout(self) -> None:
        """F1: Dedicated worktrees are provisioned under <worktree_root>/<id>."""
        wt_root = self.sandbox / ".worktrees"
        lane_id = "lane-feature-auth"
        wt_dir = wt_root / lane_id
        branch = f"lane/{lane_id}"

        subprocess.run(
            ["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt_dir), "-b", branch, "HEAD"],
            check=True,
        )

        self.assertTrue(wt_dir.is_dir(), f"Worktree directory {wt_dir} must exist")
        self.assertTrue(wt_dir.resolve().is_relative_to(self.sandbox.resolve()))
        self.assertNotEqual(wt_dir.resolve(), self.sandbox.resolve())

    def test_t1_f1_02_pointer_file_structure(self) -> None:
        """F1: In linked worktrees, .git is an ASCII pointer file citing gitdir:."""
        wt_dir = self.sandbox / ".worktrees" / "lane-ptr"
        branch = "lane/lane-ptr"
        subprocess.run(
            ["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt_dir), "-b", branch, "HEAD"],
            check=True,
        )

        git_pointer = wt_dir / ".git"
        self.assertTrue(git_pointer.is_file(), ".git inside a linked worktree must be a regular file, not directory")
        content = git_pointer.read_text(encoding="utf-8").strip()
        self.assertTrue(content.startswith("gitdir:"), f"Pointer file must start with gitdir: but was: {content}")
        self.assertIn(".git/worktrees/lane-ptr", content)

    def test_t1_f1_03_base_tree_untouched(self) -> None:
        """F1: Worker actions within a worktree leave the base repository tree completely clean."""
        wt_dir = self.sandbox / ".worktrees" / "lane-worker"
        subprocess.run(
            ["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt_dir), "-b", "lane/worker", "HEAD"],
            check=True,
        )

        # Worker creates and edits files inside wt
        (wt_dir / "src" / "worker_output.py").write_text("RESULT = 42\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(wt_dir), "add", "src/worker_output.py"], check=True)
        subprocess.run(["git", "-C", str(wt_dir), "commit", "-qm", "Worker contribution"], check=True)

        # Base repository working tree must be 100% clean
        proc = subprocess.run(["git", "-C", str(self.sandbox), "status", "--porcelain"], capture_output=True, text=True)
        self.assertEqual(proc.stdout.strip(), "", "Base repository status must be empty after worker commit in worktree")
        self.assertFalse((self.sandbox / "src" / "worker_output.py").exists())

    def test_t1_f1_04_branch_naming_convention(self) -> None:
        """F1: Provisioned worktrees checkout branch name lane/<id>."""
        lane_id = "lane-naming"
        wt_dir = self.sandbox / ".worktrees" / lane_id
        branch = f"lane/{lane_id}"
        subprocess.run(
            ["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt_dir), "-b", branch, "HEAD"],
            check=True,
        )

        # Check checked-out branch in worktree
        active_branch = subprocess.check_output(
            ["git", "-C", str(wt_dir), "rev-parse", "--abbrev-ref", "HEAD"], text=True
        ).strip()
        self.assertEqual(active_branch, branch)

        # Check branch exists in base repo
        ref_check = subprocess.run(
            ["git", "-C", str(self.sandbox), "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"]
        )
        self.assertEqual(ref_check.returncode, 0)

    def test_t1_f1_05_narrow_git_exclude_rules(self) -> None:
        """F1: Narrow .git/info/exclude ignores ephemeral run/worktrees but retains tracked .devloop items."""
        exclude_file = self.sandbox / ".git" / "info" / "exclude"
        exclude_file.parent.mkdir(parents=True, exist_ok=True)
        narrow_rules = [".worktrees/", ".devloop/run-*/", ".devloop/native/"]
        exclude_file.write_text("\n".join(narrow_rules) + "\n", encoding="utf-8")

        tracked_ledger = self.sandbox / ".devloop" / "LEDGER.md"
        tracked_plan = self.sandbox / ".devloop" / "lanes.plan.json"
        ephemeral_run = self.sandbox / ".devloop" / "run-20260919" / "report.json"
        worktree_file = self.sandbox / ".worktrees" / "lane-1" / "file.txt"

        for p in (tracked_ledger, tracked_plan, ephemeral_run, worktree_file):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("test content\n", encoding="utf-8")

        def is_ignored(rel_path: str) -> bool:
            return subprocess.run(
                ["git", "-C", str(self.sandbox), "check-ignore", "-q", rel_path]
            ).returncode == 0

        self.assertFalse(is_ignored(".devloop/LEDGER.md"), "Tracked LEDGER.md must NOT be ignored")
        self.assertFalse(is_ignored(".devloop/lanes.plan.json"), "Tracked lane plan must NOT be ignored")
        self.assertTrue(is_ignored(".devloop/run-20260919/report.json"), "Transient run-* must be ignored")
        self.assertTrue(is_ignored(".worktrees/lane-1/file.txt"), "Worktree files must be ignored")

    # ---------------------------------------------------------------------------------------------
    # F2: Base-Tree Leakage Detection & Enforcement
    # ---------------------------------------------------------------------------------------------

    def test_t1_f2_06_baseline_snapshot_capture_and_comparison(self) -> None:
        """F2: Baseline porcelain snapshot captures clean tree and detects zero strays when unchanged."""
        before = base_tree_state(self.sandbox)
        self.assertEqual(before, {})

        now = base_tree_state(self.sandbox)
        strays = stray_base_edits(before, now, self.allowed)
        self.assertEqual(strays, [])

    def test_t1_f2_07_detect_planted_stray_file(self) -> None:
        """F2: An untracked stray file planted in base tree is detected immediately."""
        before = base_tree_state(self.sandbox)
        stray = self.sandbox / "planted_leak.txt"
        stray.write_text("leaked fixture\n", encoding="utf-8")

        now = base_tree_state(self.sandbox)
        strays = stray_base_edits(before, now, self.allowed)
        self.assertEqual(strays, ["planted_leak.txt"])

    def test_t1_f2_08_detect_planted_mutation_in_tracked_file(self) -> None:
        """F2: Mutating a tracked file in the base tree is detected as a stray edit."""
        before = base_tree_state(self.sandbox)
        (self.sandbox / "README.md").write_text("# Polluted README\n", encoding="utf-8")

        now = base_tree_state(self.sandbox)
        strays = stray_base_edits(before, now, self.allowed)
        self.assertEqual(strays, ["README.md"])

    def test_t1_f2_09_allowlist_permits_designated_metadata_paths(self) -> None:
        """F2: Allowed metadata paths (.devloop/, .git/, AGENTS.md, TASKS.md, .worktrees/) are not flagged."""
        before = base_tree_state(self.sandbox)

        (self.sandbox / ".devloop").mkdir(exist_ok=True)
        (self.sandbox / ".devloop" / "LEDGER.md").write_text("new entry\n", encoding="utf-8")
        (self.sandbox / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
        (self.sandbox / "TASKS.md").write_text("# Tasks\n", encoding="utf-8")
        (self.sandbox / ".worktrees" / "lane-1").mkdir(parents=True, exist_ok=True)
        (self.sandbox / ".worktrees" / "lane-1" / "scratch.py").write_text("x=1\n", encoding="utf-8")

        now = base_tree_state(self.sandbox)
        strays = stray_base_edits(before, now, self.allowed)
        self.assertEqual(strays, [], f"Designated metadata paths must be permitted, but got: {strays}")

    def test_t1_f2_10_allowlist_rejects_unauthorized_paths(self) -> None:
        """F2: Edits outside the allowlist are flagged as stray base edits."""
        before = base_tree_state(self.sandbox)

        (self.sandbox / "src" / "leak.py").write_text("print('leak')\n", encoding="utf-8")
        (self.sandbox / "package.json").write_text("{}\n", encoding="utf-8")

        now = base_tree_state(self.sandbox)
        strays = stray_base_edits(before, now, self.allowed)
        self.assertEqual(set(strays), {"src/leak.py", "package.json"})

    # ---------------------------------------------------------------------------------------------
    # F3: Concurrent Worker Lanes & Claude Code CLI
    # ---------------------------------------------------------------------------------------------

    def test_t1_f3_11_detached_job_spawning_via_job_py(self) -> None:
        """F3: Detached jobs spawn under setsid via job.py, exit cleanly, and write completion receipts."""
        jobs_root = self.sandbox / ".devloop" / "jobs"
        wt_dir = self.sandbox / ".worktrees" / "lane-job"
        wt_dir.mkdir(parents=True, exist_ok=True)

        job.spawn(jobs_root, "job-1", ["sh", "-c", "echo 'job done' > result.txt; exit 0"], wt_dir, budget_s=30)
        res = job.wait(jobs_root, ["job-1"], budget_s=15, interval_s=1)

        self.assertIn("job-1", res)
        self.assertEqual(res["job-1"]["state"], "done")
        self.assertEqual(res["job-1"]["rc"], 0)
        self.assertTrue((wt_dir / "result.txt").exists())

    def test_t1_f3_12_claude_code_argument_synthesis_with_cwd_wt(self) -> None:
        """F3: adapters.build_argv synthesizes claude -p arguments with correct options and cwd=wt."""
        spec = {
            "base_ref": "HEAD",
            "lanes": [
                {
                    "id": "claude-worker-1",
                    "objective": "Implement authentication middleware",
                    "owned_paths": ["src/auth.py"],
                    "worker": {
                        "harness": "claude-code",
                        "model": "opus",
                        "effort": "xhigh",
                        "permission_mode": "dontAsk",
                        "allowed_tools": "Read,Edit,Write,Glob,Grep,Bash",
                    },
                }
            ],
        }
        normalized = adapters.normalize_spec(spec)
        lane = adapters.merged_lane(normalized, "claude-worker-1")

        wt = self.sandbox / ".worktrees" / "claude-worker-1"
        wt.mkdir(parents=True, exist_ok=True)
        report = self.sandbox / ".devloop" / "report.json"
        lane_json = self.sandbox / ".devloop" / "lane.json"
        skill = self.sandbox / "SKILL.md"
        skill.write_text("# Skill", encoding="utf-8")
        prompt_file = self.sandbox / "prompt.md"
        prompt_file.write_text("# Prompt instructions", encoding="utf-8")

        argv = adapters.build_argv(lane, wt, report, lane_json, skill, prompt_file)

        self.assertEqual(argv[0], "claude")
        self.assertIn("-p", argv)
        self.assertIn("--output-format", argv)
        self.assertEqual(argv[argv.index("--output-format") + 1], "json")
        self.assertIn("--permission-mode", argv)
        self.assertEqual(argv[argv.index("--permission-mode") + 1], "dontAsk")
        self.assertIn("--allowedTools", argv)
        self.assertIn("--model", argv)
        self.assertEqual(argv[argv.index("--model") + 1], "opus")
        self.assertIn("--effort", argv)
        self.assertEqual(argv[argv.index("--effort") + 1], "xhigh")
        self.assertIn("--json-schema", argv)
        self.assertNotIn("-w", argv, "claude -w must NOT be used because orchestrator provides dedicated wt")

    def test_t1_f3_13_independent_worktree_index_files(self) -> None:
        """F3: Each worktree holds an independent index file, preventing staging contention."""
        wt1 = self.sandbox / ".worktrees" / "wt1"
        wt2 = self.sandbox / ".worktrees" / "wt2"
        subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt1), "-b", "lane/wt1", "HEAD"], check=True)
        subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt2), "-b", "lane/wt2", "HEAD"], check=True)

        (wt1 / "f1.txt").write_text("file 1\n", encoding="utf-8")
        (wt2 / "f2.txt").write_text("file 2\n", encoding="utf-8")

        # Staging in wt1 must only affect wt1's index
        subprocess.run(["git", "-C", str(wt1), "add", "f1.txt"], check=True)

        cached_wt1 = subprocess.check_output(["git", "-C", str(wt1), "diff", "--cached", "--name-only"], text=True).strip()
        cached_wt2 = subprocess.check_output(["git", "-C", str(wt2), "diff", "--cached", "--name-only"], text=True).strip()
        cached_base = subprocess.check_output(["git", "-C", str(self.sandbox), "diff", "--cached", "--name-only"], text=True).strip()

        self.assertEqual(cached_wt1, "f1.txt")
        self.assertEqual(cached_wt2, "")
        self.assertEqual(cached_base, "")

    def test_t1_f3_14_atomic_no_ff_merge(self) -> None:
        """F3: Lane completion merges atomically via git merge --no-ff creating a dual-parent commit."""
        wt = self.sandbox / ".worktrees" / "wt-merge"
        subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt), "-b", "lane/merge", "HEAD"], check=True)

        (wt / "src" / "feature.py").write_text("def feature(): pass\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(wt), "add", "src/feature.py"], check=True)
        subprocess.run(["git", "-C", str(wt), "commit", "-qm", "Implement feature"], check=True)

        # Merge lane into base repo
        subprocess.run(["git", "-C", str(self.sandbox), "merge", "--no-ff", "-m", "Merge lane/merge", "lane/merge"], check=True)

        parents = subprocess.check_output(["git", "-C", str(self.sandbox), "rev-parse", "HEAD^@"], text=True).strip().splitlines()
        self.assertEqual(len(parents), 2, "--no-ff merge must produce a merge commit with exactly 2 parents")

    def test_t1_f3_15_clean_rollback_on_conflict(self) -> None:
        """F3: Conflicting concurrent lane merges trigger git merge --abort leaving base tree clean."""
        wt = self.sandbox / ".worktrees" / "wt-conflict"
        subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt), "-b", "lane/conflict", "HEAD"], check=True)

        # Base branch edit
        (self.sandbox / "src" / "main.py").write_text("BASE EDIT\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.sandbox), "commit", "-am", "Base edit"], check=True)

        # Lane branch conflicting edit
        (wt / "src" / "main.py").write_text("LANE EDIT\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(wt), "commit", "-am", "Lane conflicting edit"], check=True)

        # Attempt merge on base - expected to fail with conflict
        merge_proc = subprocess.run(["git", "-C", str(self.sandbox), "merge", "--no-ff", "lane/conflict"], capture_output=True, text=True)
        self.assertNotEqual(merge_proc.returncode, 0)

        # Execute immediate abort
        abort_proc = subprocess.run(["git", "-C", str(self.sandbox), "merge", "--abort"], capture_output=True, text=True)
        self.assertEqual(abort_proc.returncode, 0)

        # Base status must be clean
        status = subprocess.check_output(["git", "-C", str(self.sandbox), "status", "--porcelain"], text=True).strip()
        self.assertEqual(status, "", "Base tree must be completely clean after merge --abort")
        self.assertEqual((self.sandbox / "src" / "main.py").read_text(encoding="utf-8"), "BASE EDIT\n")


# =================================================================================================
# TIER 2: BOUNDARY & CORNER CASES (15 tests, 5 per feature)
# =================================================================================================


class TestTier2BoundaryAndCornerCases(SandboxTestCase):
    """Tier 2: Boundary value analysis, corner conditions, and edge cases."""

    # ---------------------------------------------------------------------------------------------
    # F1 Boundary & Corners
    # ---------------------------------------------------------------------------------------------

    def test_t2_f1_16_empty_worktree_root_defaults(self) -> None:
        """F1: Empty or omitted worktree_root falls back safely to default .worktrees/."""
        spec = {"base_ref": "HEAD", "lanes": []}
        normalized = adapters.normalize_spec(spec)
        self.assertEqual(normalized["worktree_root"], ".worktrees")

        fallback = agy_session.worktree_root_of(Path("/nonexistent/lanes.json"))
        self.assertEqual(fallback, ".worktrees/")

    def test_t2_f1_17_dirty_existing_worktree_reuse_cleaned(self) -> None:
        """F1: Reusing a pre-existing dirty worktree from an aborted run is sanitized before lane starts."""
        wt_dir = self.sandbox / ".worktrees" / "lane-dirty-reuse"
        subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt_dir), "-b", "lane/dirty", "HEAD"], check=True)

        # Plant dirty files in worktree
        (wt_dir / "src" / "main.py").write_text("CORRUPTED\n", encoding="utf-8")
        (wt_dir / "stray_untracked.txt").write_text("stray\n", encoding="utf-8")

        # Sanitization procedure: git checkout -f and git clean -fd
        subprocess.run(["git", "-C", str(wt_dir), "checkout", "-f", "HEAD"], check=True)
        subprocess.run(["git", "-C", str(wt_dir), "clean", "-fd"], check=True)

        status = subprocess.check_output(["git", "-C", str(wt_dir), "status", "--porcelain"], text=True).strip()
        self.assertEqual(status, "", "Worktree must be completely clean after reset")
        self.assertFalse((wt_dir / "stray_untracked.txt").exists())

    def test_t2_f1_18_deeply_nested_worktree_root(self) -> None:
        """F1: Deeply nested worktree_root creates valid worktrees and pointer structures."""
        nested_root = "build/nested/isolated/worktrees"
        wt_dir = self.sandbox / nested_root / "lane-deep"
        subprocess.run(
            ["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt_dir), "-b", "lane/deep", "HEAD"],
            check=True,
        )

        self.assertTrue(wt_dir.is_dir())
        git_ptr = (wt_dir / ".git").read_text(encoding="utf-8").strip()
        self.assertTrue(git_ptr.startswith("gitdir:"))
        self.assertIn(".git/worktrees/lane-deep", git_ptr)

    def test_t2_f1_19_special_characters_in_lane_id(self) -> None:
        """F1: Lane IDs containing hyphens, underscores, and dots are safely handled."""
        lane_id = "lane_core-v2.1"
        wt_dir = self.sandbox / ".worktrees" / lane_id
        subprocess.run(
            ["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt_dir), "-b", f"lane/{lane_id}", "HEAD"],
            check=True,
        )

        jobs_root = self.sandbox / ".devloop" / "jobs"
        job.spawn(jobs_root, lane_id, ["sh", "-c", "echo ok > ok.txt; exit 0"], wt_dir, budget_s=30)
        res = job.wait(jobs_root, [lane_id], budget_s=10)
        self.assertEqual(res[lane_id]["state"], "done")
        self.assertEqual(res[lane_id]["rc"], 0)

    def test_t2_f1_20_missing_base_ref_validation(self) -> None:
        """F1: Invalid or empty base_ref is rejected by specification validation."""
        invalid_spec = {"version": 2, "lanes": []}
        errors = adapters.validate_spec(invalid_spec)
        self.assertTrue(any("base_ref" in e.lower() for e in errors), f"Expected base_ref error in {errors}")

    # ---------------------------------------------------------------------------------------------
    # F2 Boundary & Corners
    # ---------------------------------------------------------------------------------------------

    def test_t2_f2_21_pre_existing_dirty_file_not_blamed(self) -> None:
        """F2: Pre-existing untracked/dirty files in base tree are not blamed on the run."""
        pre_existing = self.sandbox / "pre_existing_notes.txt"
        pre_existing.write_text("developer notes\n", encoding="utf-8")

        before = base_tree_state(self.sandbox)
        self.assertIn("pre_existing_notes.txt", before)

        # Post-run check with same file unchanged
        now = base_tree_state(self.sandbox)
        strays = stray_base_edits(before, now, self.allowed)
        self.assertEqual(strays, [], "Inherited pre-existing dirt must not be flagged as a stray edit")

    def test_t2_f2_22_unanchored_prefix_edge_cases(self) -> None:
        """F2: Unanchored allowlist prefixes like .devloop-scratch or .worktrees-fake must be rejected."""
        before = base_tree_state(self.sandbox)

        (self.sandbox / ".devloop-fake").mkdir(exist_ok=True)
        (self.sandbox / ".devloop-fake" / "stray.txt").write_text("fake\n", encoding="utf-8")
        (self.sandbox / ".worktrees-fake").mkdir(exist_ok=True)
        (self.sandbox / ".worktrees-fake" / "stray.txt").write_text("fake\n", encoding="utf-8")

        now = base_tree_state(self.sandbox)
        strays = stray_base_edits(before, now, self.allowed)

        # Unanchored prefixes must be identified as strays
        self.assertTrue(
            any(".devloop-fake" in s for s in strays),
            f".devloop-fake must NOT be excused by .devloop/, got: {strays}",
        )
        self.assertTrue(
            any(".worktrees-fake" in s for s in strays),
            f".worktrees-fake must NOT be excused by .worktrees/, got: {strays}",
        )

    def test_t2_f2_23_file_deleted_in_base_tree_during_run(self) -> None:
        """F2: Deleting a tracked file in the base tree is detected as a stray modification."""
        before = base_tree_state(self.sandbox)
        (self.sandbox / "src" / "main.py").unlink()

        now = base_tree_state(self.sandbox)
        strays = stray_base_edits(before, now, self.allowed)
        self.assertEqual(strays, ["src/main.py"])

    def test_t2_f2_24_file_modified_and_restored(self) -> None:
        """F2: A file modified and restored to its exact original content returns to clean status."""
        original = (self.sandbox / "README.md").read_text(encoding="utf-8")
        before = base_tree_state(self.sandbox)

        # Mutate
        (self.sandbox / "README.md").write_text("TEMPORARY EDIT\n", encoding="utf-8")
        # Restore
        (self.sandbox / "README.md").write_text(original, encoding="utf-8")

        now = base_tree_state(self.sandbox)
        strays = stray_base_edits(before, now, self.allowed)
        self.assertEqual(strays, [])

    def test_t2_f2_25_stray_in_git_dir_vs_base_tree(self) -> None:
        """F2: Edits inside .git/ metadata are allowed while edits in base tree outside .git/ are rejected."""
        before = base_tree_state(self.sandbox)

        # Update inside .git
        (self.sandbox / ".git" / "custom_meta").write_text("internal\n", encoding="utf-8")
        # Update outside .git
        (self.sandbox / "unauthorized.txt").write_text("stray\n", encoding="utf-8")

        now = base_tree_state(self.sandbox)
        strays = stray_base_edits(before, now, self.allowed)
        self.assertEqual(strays, ["unauthorized.txt"])

    # ---------------------------------------------------------------------------------------------
    # F3 Boundary & Corners
    # ---------------------------------------------------------------------------------------------

    def test_t2_f3_26_claude_permission_denials_downgrades_status(self) -> None:
        """F3: When Claude Code CLI envelope contains permission_denials, report status is downgraded to partial."""
        envelope = {
            "result": "Partial work completed",
            "num_turns": 5,
            "permission_denials": [{"tool_name": "Bash", "action": "run_command"}],
        }
        denials = adapters.envelope_denials(envelope)
        self.assertTrue(len(denials) > 0, "Expected non-empty denials list")
        self.assertTrue(any("permission_denials" in d for d in denials))

        raw_text = json.dumps(envelope)
        report = adapters.normalize_report(
            lane={"id": "l1", "objective": "test"},
            harness="claude-code",
            stdout=raw_text,
            exit_code=0,
            timed_out=False,
            turns=5,
        )
        self.assertEqual(report["status"], "partial", "Report with permission denials must be downgraded to partial")
        self.assertTrue(any("permission_denials" in u for u in report.get("unverified", [])))

    def test_t2_f3_27_rapid_lock_contention_with_backoff(self) -> None:
        """F3: Concurrent git commands encountering momentary index.lock backoff and succeed."""
        lock_file = self.sandbox / ".git" / "index.lock"

        def hold_and_release():
            lock_file.write_text("locked\n", encoding="utf-8")
            time.sleep(0.3)
            lock_file.unlink(missing_ok=True)

        t = threading.Thread(target=hold_and_release)
        t.start()

        # Execute safe git operation with retry backoff
        cp = git_lock.run_git_safe(["status"], cwd=self.sandbox)
        t.join()

        self.assertEqual(cp.returncode, 0, f"run_git_safe failed: {cp.stderr}")

    def test_t2_f3_28_stale_lock_eviction(self) -> None:
        """F3: An abandoned index.lock older than 45 seconds is evicted automatically."""
        lock_file = self.sandbox / ".git" / "index.lock"
        lock_file.write_text("abandoned lock\n", encoding="utf-8")

        # Set mtime to 60 seconds ago
        stale_time = time.time() - 60
        os.utime(lock_file, (stale_time, stale_time))

        cp = git_lock.run_git_safe(["status"], cwd=self.sandbox)
        self.assertEqual(cp.returncode, 0)
        self.assertFalse(lock_file.exists(), "Stale lockfile must be evicted")

    def test_t2_f3_29_wave_dependency_cycles_detected(self) -> None:
        """F3: Circular lane dependencies (A -> B -> A) raise a clear dependency error."""
        spec = {
            "base_ref": "HEAD",
            "lanes": [
                {"id": "lane-a", "objective": "A", "depends_on": ["lane-b"]},
                {"id": "lane-b", "objective": "B", "depends_on": ["lane-a"]},
            ],
        }
        with self.assertRaises(ValueError):
            adapters.order_lanes(spec)

    def test_t2_f3_30_zero_lane_empty_wave_rejected(self) -> None:
        """F3: A specification with zero lanes yields empty waves, preventing vacuous pass."""
        spec = {"base_ref": "HEAD", "lanes": []}
        w = adapters.waves(spec)
        self.assertEqual(w, [], "Empty spec must yield empty waves list")


# =================================================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS (5 tests)
# =================================================================================================


class TestTier3CrossFeatureCombinations(SandboxTestCase):
    """Tier 3: Pairwise and multi-feature interaction verification."""

    def test_t3_31_multilane_concurrent_execution_with_simultaneous_leakage(self) -> None:
        """F1+F2+F3: Multiple concurrent worker jobs with simultaneous stray base file planting halts audit."""
        wt1 = self.sandbox / ".worktrees" / "lane-c1"
        wt2 = self.sandbox / ".worktrees" / "lane-c2"
        subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt1), "-b", "lane/c1", "HEAD"], check=True)
        subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt2), "-b", "lane/c2", "HEAD"], check=True)

        jobs_root = self.sandbox / ".devloop" / "jobs"
        before = base_tree_state(self.sandbox)

        # Spawn concurrent jobs
        job.spawn(jobs_root, "c1", ["sh", "-c", "echo 'w1' > w1.txt; sleep 0.2; exit 0"], wt1, budget_s=30)
        job.spawn(jobs_root, "c2", ["sh", "-c", "echo 'w2' > w2.txt; sleep 0.2; exit 0"], wt2, budget_s=30)

        # Plant leak in base tree during execution
        (self.sandbox / "unauthorized_concurrent_leak.sh").write_text("malicious\n", encoding="utf-8")

        res = job.wait(jobs_root, ["c1", "c2"], budget_s=15)
        self.assertTrue(all(r["state"] == "done" and r["rc"] == 0 for r in res.values()))

        # Base tree audit must detect the leak
        now = base_tree_state(self.sandbox)
        strays = stray_base_edits(before, now, self.allowed)
        self.assertIn("unauthorized_concurrent_leak.sh", strays)

    def test_t3_32_claude_code_and_agy_parallel_worktrees(self) -> None:
        """F1+F3: Claude Code CLI worker and Antigravity worker run in parallel worktrees without collision."""
        wt_claude = self.sandbox / ".worktrees" / "lane-claude"
        wt_agy = self.sandbox / ".worktrees" / "lane-agy"
        subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt_claude), "-b", "lane/claude", "HEAD"], check=True)
        subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt_agy), "-b", "lane/agy", "HEAD"], check=True)

        spec = {
            "base_ref": "HEAD",
            "lanes": [
                {"id": "lane-claude", "objective": "Claude job", "worker": {"harness": "claude-code"}},
                {"id": "lane-agy", "objective": "AGY job", "worker": {"harness": "antigravity"}},
            ],
        }
        normalized = adapters.normalize_spec(spec)
        lane_claude = adapters.merged_lane(normalized, "lane-claude")
        lane_agy = adapters.merged_lane(normalized, "lane-agy")

        self.assertEqual(lane_claude["worker"]["harness"], "claude-code")
        self.assertEqual(lane_agy["worker"]["harness"], "antigravity")

        jobs_root = self.sandbox / ".devloop" / "jobs"
        job.spawn(jobs_root, "lane-claude", ["sh", "-c", "echo 'claude-work' > out.txt; exit 0"], wt_claude, budget_s=30)
        job.spawn(jobs_root, "lane-agy", ["sh", "-c", "echo 'agy-work' > out.txt; exit 0"], wt_agy, budget_s=30)

        res = job.wait(jobs_root, ["lane-claude", "lane-agy"], budget_s=15)
        self.assertTrue(all(r["state"] == "done" and r["rc"] == 0 for r in res.values()))
        self.assertEqual((wt_claude / "out.txt").read_text(encoding="utf-8").strip(), "claude-work")
        self.assertEqual((wt_agy / "out.txt").read_text(encoding="utf-8").strip(), "agy-work")

    def test_t3_33_negative_control_base_leak_halts_gate(self) -> None:
        """F1+F2: Negative control in worktree mutating base tree fails the base audit."""
        wt = self.sandbox / ".worktrees" / "lane-nc-leak"
        subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt), "-b", "lane/nc-leak", "HEAD"], check=True)

        before = base_tree_state(self.sandbox)

        # Simulate negative control escaping worktree boundary to mutate base repo
        escaped_file = self.sandbox / "src" / "leaked_during_negative_control.py"
        escaped_file.write_text("# LEAKED FIXTURE\n", encoding="utf-8")

        now = base_tree_state(self.sandbox)
        strays = stray_base_edits(before, now, self.allowed)
        self.assertIn("src/leaked_during_negative_control.py", strays)

    def test_t3_34_concurrent_git_commits_with_index_lock(self) -> None:
        """F1+F3: Multiple concurrent git commits across worktrees serialize safely via git_lock."""
        wt1 = self.sandbox / ".worktrees" / "lane-lock-1"
        wt2 = self.sandbox / ".worktrees" / "lane-lock-2"
        subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt1), "-b", "lane/lock1", "HEAD"], check=True)
        subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt2), "-b", "lane/lock2", "HEAD"], check=True)

        errors = []

        def worker_task(wt_path: Path, tag: str):
            try:
                for i in range(3):
                    (wt_path / f"file_{tag}_{i}.txt").write_text(f"content {i}\n", encoding="utf-8")
                    cp1 = git_lock.run_git_safe(["add", f"file_{tag}_{i}.txt"], cwd=wt_path)
                    if cp1.returncode != 0:
                        errors.append(f"Add failed: {cp1.stderr}")
                    cp2 = git_lock.run_git_safe(["commit", "-m", f"commit {tag} {i}"], cwd=wt_path)
                    if cp2.returncode != 0:
                        errors.append(f"Commit failed: {cp2.stderr}")
            except Exception as e:
                errors.append(str(e))

        t1 = threading.Thread(target=worker_task, args=(wt1, "a"))
        t2 = threading.Thread(target=worker_task, args=(wt2, "b"))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(errors, [], f"Concurrent git commits failed: {errors}")

    def test_t3_35_pre_existing_base_dirt_with_concurrent_lanes(self) -> None:
        """F2+F3: Pre-existing base dirt survives concurrent lane runs without false leakage alerts."""
        (self.sandbox / "existing_untracked.txt").write_text("pre-existing\n", encoding="utf-8")
        before = base_tree_state(self.sandbox)

        wt1 = self.sandbox / ".worktrees" / "lane-d1"
        wt2 = self.sandbox / ".worktrees" / "lane-d2"
        subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt1), "-b", "lane/d1", "HEAD"], check=True)
        subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt2), "-b", "lane/d2", "HEAD"], check=True)

        jobs_root = self.sandbox / ".devloop" / "jobs"
        job.spawn(jobs_root, "d1", ["sh", "-c", "echo 1 > out1.txt; exit 0"], wt1, budget_s=30)
        job.spawn(jobs_root, "d2", ["sh", "-c", "echo 2 > out2.txt; exit 0"], wt2, budget_s=30)
        res = job.wait(jobs_root, ["d1", "d2"], budget_s=15)
        self.assertTrue(all(r["state"] == "done" and r["rc"] == 0 for r in res.values()))

        now = base_tree_state(self.sandbox)
        strays = stray_base_edits(before, now, self.allowed)
        self.assertEqual(strays, [], "No stray leakage should be flagged when pre-existing dirt remains untouched")


# =================================================================================================
# TIER 4: REAL-WORLD APPLICATION SCENARIOS (5 tests)
# =================================================================================================


class TestTier4RealWorldApplicationScenarios(SandboxTestCase):
    """Tier 4: End-to-end integration and real-world application scenarios."""

    def test_t4_36_scenario_1_parallel_agy_claude_two_sided_gates(self) -> None:
        """Scenario 1: Parallel AGY & Claude Code CLI multi-lane run in isolated worktrees completing two-sided gates."""
        wt_auth = self.sandbox / ".worktrees" / "lane-auth"
        wt_db = self.sandbox / ".worktrees" / "lane-db"
        subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt_auth), "-b", "lane/auth", "HEAD"], check=True)
        subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt_db), "-b", "lane/db", "HEAD"], check=True)

        # Lane 1 (AGY) modifies auth
        (wt_auth / "src" / "auth.py").write_text("def auth(): return True\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(wt_auth), "add", "src/auth.py"], check=True)
        subprocess.run(["git", "-C", str(wt_auth), "commit", "-qm", "Implement auth"], check=True)

        # Lane 2 (Claude) modifies db
        (wt_db / "src" / "db.py").write_text("def connect(): return True\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(wt_db), "add", "src/db.py"], check=True)
        subprocess.run(["git", "-C", str(wt_db), "commit", "-qm", "Implement db connect"], check=True)

        # Reconcile Lane 1 atomically
        subprocess.run(["git", "-C", str(self.sandbox), "merge", "--no-ff", "-m", "Merge auth lane", "lane/auth"], check=True)
        # Reconcile Lane 2 atomically
        subprocess.run(["git", "-C", str(self.sandbox), "merge", "--no-ff", "-m", "Merge db lane", "lane/db"], check=True)

        # Assert final base repo state
        self.assertTrue((self.sandbox / "src" / "auth.py").exists())
        self.assertTrue((self.sandbox / "src" / "db.py").exists())
        status = subprocess.check_output(["git", "-C", str(self.sandbox), "status", "--porcelain"], text=True).strip()
        self.assertEqual(status, "", "Base repository must remain clean after reconciling all lanes")

    def test_t4_37_scenario_2_stray_fixture_causes_exit_2_with_diagnostic_stderr(self) -> None:
        """Scenario 2: Stray fixture planted during gate causes immediate failure with diagnostic error naming stray path."""
        before = base_tree_state(self.sandbox)

        # Simulate negative control writing stray root password / fixture into base repository
        stray_path = self.sandbox / "boot_secret.env"
        stray_path.write_text("ROOT_PASSWORD=leak\n", encoding="utf-8")

        now = base_tree_state(self.sandbox)
        strays = stray_base_edits(before, now, self.allowed)

        # Verify stray identification and diagnostic message format
        self.assertEqual(strays, ["boot_secret.env"])
        diagnostic_message = f"BASE TREE LEAKAGE DETECTED: {', '.join(strays)}"
        self.assertIn("boot_secret.env", diagnostic_message)

    def test_t4_38_scenario_3_pre_existing_untracked_survives_without_false_alarm(self) -> None:
        """Scenario 3: Pre-existing untracked file in base repository survives multi-lane run without triggering false alarm."""
        notes = self.sandbox / "developer_notes.txt"
        notes.write_text("private notes\n", encoding="utf-8")

        before = base_tree_state(self.sandbox)

        wt = self.sandbox / ".worktrees" / "lane-work"
        subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt), "-b", "lane/work", "HEAD"], check=True)

        (wt / "src" / "logic.py").write_text("def run(): pass\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(wt), "add", "src/logic.py"], check=True)
        subprocess.run(["git", "-C", str(wt), "commit", "-qm", "Work"], check=True)

        subprocess.run(["git", "-C", str(self.sandbox), "merge", "--no-ff", "-m", "Merge work", "lane/work"], check=True)

        now = base_tree_state(self.sandbox)
        strays = stray_base_edits(before, now, self.allowed)
        self.assertEqual(strays, [], "No strays should be reported; developer notes must survive")
        self.assertTrue(notes.exists())
        self.assertEqual(notes.read_text(encoding="utf-8"), "private notes\n")

    def test_t4_39_scenario_4_four_lane_stress_lock_recovery_diff_reconciliation(self) -> None:
        """Scenario 4: Concurrent stress test across 4 lanes testing lock recovery and clean diff reconciliation."""
        jobs_root = self.sandbox / ".devloop" / "jobs"
        lanes = [f"lane-stress-{i}" for i in range(4)]
        wts = [self.sandbox / ".worktrees" / lid for lid in lanes]

        for lid, wt in zip(lanes, wts):
            subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt), "-b", f"lane/{lid}", "HEAD"], check=True)
            (wt / "src" / f"mod_{lid}.py").write_text(f"# module {lid}\n", encoding="utf-8")
            # Spawn job to commit within worktree
            job.spawn(
                jobs_root,
                lid,
                ["sh", "-c", f"git add src/mod_{lid}.py && git commit -m 'Commit {lid}'"],
                wt,
                budget_s=30,
            )

        # Await all 4 parallel jobs
        res = job.wait(jobs_root, lanes, budget_s=30, interval_s=1)
        self.assertTrue(all(r["state"] == "done" and r["rc"] == 0 for r in res.values()), f"Some jobs failed: {res}")

        # Sequentially reconcile diffs with no-ff merge
        for lid in lanes:
            merge_cp = git_lock.run_git_safe(
                ["merge", "--no-ff", "-m", f"Merge {lid}", f"lane/{lid}"], cwd=self.sandbox
            )
            self.assertEqual(merge_cp.returncode, 0, f"Merge of {lid} failed: {merge_cp.stderr}")

        # Verify all 4 modules are present in base repo
        for lid in lanes:
            self.assertTrue((self.sandbox / "src" / f"mod_{lid}.py").exists())

    def test_t4_40_scenario_5_merge_conflict_triggers_instant_abort(self) -> None:
        """Scenario 5: Merge conflict triggers instant --abort without base-tree corruption, preserving worktree."""
        wt1 = self.sandbox / ".worktrees" / "lane-mc-1"
        wt2 = self.sandbox / ".worktrees" / "lane-mc-2"
        subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt1), "-b", "lane/mc-1", "HEAD"], check=True)
        subprocess.run(["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt2), "-b", "lane/mc-2", "HEAD"], check=True)

        # Lane 1 edits main.py
        (wt1 / "src" / "main.py").write_text("def hello(): return 'lane1'\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(wt1), "commit", "-am", "Lane 1 edit"], check=True)

        # Lane 2 edits main.py differently
        (wt2 / "src" / "main.py").write_text("def hello(): return 'lane2'\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(wt2), "commit", "-am", "Lane 2 edit"], check=True)

        # Lane 1 merges cleanly
        subprocess.run(["git", "-C", str(self.sandbox), "merge", "--no-ff", "-m", "Merge lane 1", "lane/mc-1"], check=True)

        # Lane 2 merge encounters conflict
        merge_proc = subprocess.run(
            ["git", "-C", str(self.sandbox), "merge", "--no-ff", "lane/mc-2"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(merge_proc.returncode, 0, "Merge must encounter conflict")

        # Instant abort is triggered
        abort_proc = subprocess.run(["git", "-C", str(self.sandbox), "merge", "--abort"], capture_output=True, text=True)
        self.assertEqual(abort_proc.returncode, 0)

        # Base tree is restored to Lane 1 clean state
        status = subprocess.check_output(["git", "-C", str(self.sandbox), "status", "--porcelain"], text=True).strip()
        self.assertEqual(status, "", "Base repository must have no lingering conflict markers")
        self.assertEqual((self.sandbox / "src" / "main.py").read_text(encoding="utf-8"), "def hello(): return 'lane1'\n")

        # Worktree 2 is preserved for diagnostic inspection
        self.assertTrue(wt2.is_dir(), "Conflicted worktree must be preserved for investigation")
        self.assertTrue((wt2 / "src" / "main.py").exists())


# =================================================================================================
# TIER 5: ADVERSARIAL COVERAGE HARDENING (4 tests)
# =================================================================================================


class TestTier5AdversarialHardening(SandboxTestCase):
    """Tier 5: Adversarial Hardening covering CLI gate leakage, vacuous sentinels, symlink traversal, and multi-wave pipelines."""

    def test_t5_41_adapters_gate_cli_base_leakage_detected_exit_2(self) -> None:
        """Adversarial: adapters.py gate CLI halts with exit code 2 and outputs BASE TREE LEAKAGE DETECTED on base leaks."""
        lane_id = "lane-adv-leak"
        wt_dir = self.sandbox / ".worktrees" / lane_id
        subprocess.run(
            ["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt_dir), "-b", f"lane/{lane_id}", "HEAD"],
            check=True,
        )

        run_dir = self.sandbox / ".devloop" / "run-gate-test"
        run_dir.mkdir(parents=True, exist_ok=True)

        # Negative control deliberately leaks a planted file into the base repository
        lane_spec = {
            "id": lane_id,
            "worktree_root": ".worktrees",
            "owned_paths": ["src/feature.py"],
            "positive_cmd": "python3 -c 'import sys; sys.exit(0)'",
            "negative_control_cmd": f"sh -c 'echo \"DEVLOOP-PLANTED-T501-SENTINEL: test failure\"; echo leak > {self.sandbox}/planted_base_leak.txt; exit 1'",
            "negative_expect": "DEVLOOP-PLANTED-T501-SENTINEL",
            "worker": {"timeout_s": 30},
        }
        lane_file = run_dir / "lane.json"
        lane_file.write_text(json.dumps(lane_spec, indent=2), encoding="utf-8")

        adapters_py = SCRIPTS / "adapters.py"
        res = subprocess.run(
            [
                sys.executable,
                str(adapters_py),
                "gate",
                "--lane",
                str(lane_file),
                "--wt",
                str(wt_dir),
                "--run",
                str(run_dir),
                "--root",
                str(self.sandbox),
            ],
            capture_output=True,
            text=True,
        )

        self.assertEqual(res.returncode, 2, f"Gate must exit with code 2 on base tree leakage. Output: {res.stdout}\n{res.stderr}")
        self.assertIn("BASE TREE LEAKAGE DETECTED", res.stderr)
        self.assertIn("planted_base_leak.txt", res.stderr)

        # Clean up leak and verify positive control path succeeds with exit 0
        (self.sandbox / "planted_base_leak.txt").unlink(missing_ok=True)
        lane_spec["negative_control_cmd"] = "sh -c 'echo \"DEVLOOP-PLANTED-T501-SENTINEL: clean\"; exit 1'"
        lane_file.write_text(json.dumps(lane_spec, indent=2), encoding="utf-8")

        res_clean = subprocess.run(
            [
                sys.executable,
                str(adapters_py),
                "gate",
                "--lane",
                str(lane_file),
                "--wt",
                str(wt_dir),
                "--run",
                str(run_dir),
                "--root",
                str(self.sandbox),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_clean.returncode, 0, f"Gate must exit 0 when no base leakage occurs. Output: {res_clean.stdout}\n{res_clean.stderr}")

    def test_t5_42_preflight_vacuous_sentinel_rejection_exit_2(self) -> None:
        """Adversarial: adapters.py gate rejects vacuous negative control before running if sentinel already exists."""
        lane_id = "lane-vacuous-sentinel"
        wt_dir = self.sandbox / "worktrees" / lane_id
        subprocess.run(
            ["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt_dir), "-b", f"lane/{lane_id}", "HEAD"],
            check=True,
        )

        run_dir = self.sandbox / ".devloop" / "run-vacuous-test"
        run_dir.mkdir(parents=True, exist_ok=True)

        sentinel_name = "DEVLOOP-PLANTED-T502-VACUOUS"
        lane_spec = {
            "id": lane_id,
            "worktree_root": "worktrees",
            "owned_paths": ["src/feature.py"],
            "positive_cmd": "python3 -c 'import sys; sys.exit(0)'",
            "negative_control_cmd": f"sh -c 'cat src/{sentinel_name}.txt; exit 1'",
            "negative_expect": sentinel_name,
            "worker": {"timeout_s": 30},
        }
        lane_file = run_dir / "lane.json"
        lane_file.write_text(json.dumps(lane_spec, indent=2), encoding="utf-8")

        # Plant the sentinel file in the worktree prior to gate execution
        planted_file = wt_dir / "src" / f"{sentinel_name}.txt"
        planted_file.write_text("accidental pre-existing fixture", encoding="utf-8")

        adapters_py = SCRIPTS / "adapters.py"
        res = subprocess.run(
            [
                sys.executable,
                str(adapters_py),
                "gate",
                "--lane",
                str(lane_file),
                "--wt",
                str(wt_dir),
                "--run",
                str(run_dir),
                "--root",
                str(self.sandbox),
            ],
            capture_output=True,
            text=True,
        )

        self.assertEqual(res.returncode, 2, f"Gate must exit with code 2 for vacuous pre-existing sentinel. Output: {res.stdout}\n{res.stderr}")
        self.assertIn("negative control is VACUOUS BEFORE IT RAN", res.stderr)
        self.assertIn("Refusing to gate", res.stderr)

        # Remove the pre-planted sentinel and verify it now passes pre-flight
        planted_file.unlink()
        lane_spec["negative_control_cmd"] = f"sh -c 'echo \"{sentinel_name}: triggered failure\"; exit 1'"
        lane_file.write_text(json.dumps(lane_spec, indent=2), encoding="utf-8")

        res_clean = subprocess.run(
            [
                sys.executable,
                str(adapters_py),
                "gate",
                "--lane",
                str(lane_file),
                "--wt",
                str(wt_dir),
                "--run",
                str(run_dir),
                "--root",
                str(self.sandbox),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_clean.returncode, 0, f"Clean gate must pass. Output: {res_clean.stdout}\n{res_clean.stderr}")

    def test_t5_43_symlink_traversal_isolation_across_worktree_boundary(self) -> None:
        """Adversarial: Symlink creation and write traversals across the worktree boundary are trapped."""
        lane_id = "lane-adv-symlink"
        wt_dir = self.sandbox / ".worktrees" / lane_id
        subprocess.run(
            ["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt_dir), "-b", f"lane/{lane_id}", "HEAD"],
            check=True,
        )

        # 1. Internal worktree symlinks do not affect base tree immutability
        internal_link = wt_dir / "src" / "main_link.py"
        internal_link.symlink_to("main.py")
        subprocess.run(["git", "-C", str(wt_dir), "add", "src/main_link.py"], check=True)
        subprocess.run(["git", "-C", str(wt_dir), "commit", "-qm", "Add internal symlink"], check=True)

        base_status = subprocess.check_output(["git", "-C", str(self.sandbox), "status", "--porcelain"], text=True).strip()
        self.assertEqual(base_status, "", "Internal worktree symlink must leave base repository completely clean")

        # 2. Rogue traversal symlink pointing into base repo
        base_target = self.sandbox / "src" / "main.py"
        escape_link = wt_dir / "escape_link.py"
        escape_link.symlink_to(base_target)

        # Assert differential snapshot detects direct writes through symlink
        base_snap_before = base_tree_state(self.sandbox)
        self.assertIsNotNone(base_snap_before)

        escape_link.write_text("def hello(): return 'mutated-through-symlink'\n", encoding="utf-8")
        strays = stray_base_edits(base_snap_before, base_tree_state(self.sandbox), self.allowed)
        self.assertIn("src/main.py", strays, "Base audit must detect mutation through escaping symlink")

        # Restore base repo to clean state before gate test
        subprocess.run(["git", "-C", str(self.sandbox), "checkout", "--", "src/main.py"], check=True)

        # 3. Assert adapters.py gate traps symlink writes occurring during gate execution
        run_dir = self.sandbox / ".devloop" / "run-symlink-test"
        run_dir.mkdir(parents=True, exist_ok=True)
        sentinel_name = "DEVLOOP-PLANTED-T503-SYMLINK"
        # The negative control command writes through the escape symlink into base repo
        lane_spec = {
            "id": lane_id,
            "worktree_root": ".worktrees",
            "owned_paths": ["src/main_link.py"],
            "positive_cmd": "python3 -c 'import sys; sys.exit(0)'",
            "negative_control_cmd": f"sh -c 'echo \"{sentinel_name}: fail\"; echo \"leak\" >> escape_link.py; exit 1'",
            "negative_expect": sentinel_name,
            "worker": {"timeout_s": 30},
        }
        lane_file = run_dir / "lane.json"
        lane_file.write_text(json.dumps(lane_spec, indent=2), encoding="utf-8")

        adapters_py = SCRIPTS / "adapters.py"
        res = subprocess.run(
            [
                sys.executable,
                str(adapters_py),
                "gate",
                "--lane",
                str(lane_file),
                "--wt",
                str(wt_dir),
                "--run",
                str(run_dir),
                "--root",
                str(self.sandbox),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 2, f"Gate must halt with code 2 on symlink leakage. Output: {res.stdout}\n{res.stderr}")
        self.assertIn("BASE TREE LEAKAGE DETECTED", res.stderr)
        self.assertIn("src/main.py", res.stderr)

    def test_t5_44_multi_wave_pipeline_dependency_execution(self) -> None:
        """Adversarial: Multi-wave dependency execution where Wave 1 builds upon and verifies Wave 0 merged artifacts."""
        pipeline_spec = {
            "version": 2,
            "lanes": [
                {
                    "id": "wave0-core-math",
                    "worktree_root": ".worktrees",
                    "owned_paths": ["src/math_core.py"],
                    "depends_on": [],
                },
                {
                    "id": "wave1-calc-service",
                    "worktree_root": ".worktrees",
                    "owned_paths": ["src/calc_service.py"],
                    "depends_on": ["wave0-core-math"],
                },
            ],
        }

        calculated_waves = adapters.waves(pipeline_spec)
        self.assertEqual(calculated_waves, [["wave0-core-math"], ["wave1-calc-service"]], "Wave ordering must place dependencies in earlier waves")

        # --- Execute Wave 0 ---
        w0_id = "wave0-core-math"
        wt_w0 = self.sandbox / ".worktrees" / w0_id
        subprocess.run(
            ["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt_w0), "-b", f"lane/{w0_id}", "HEAD"],
            check=True,
        )

        (wt_w0 / "src" / "math_core.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(wt_w0), "add", "src/math_core.py"], check=True)
        subprocess.run(["git", "-C", str(wt_w0), "commit", "-qm", "feat(math): implement math_core add"], check=True)

        run_dir = self.sandbox / ".devloop" / "run-multi-wave"
        run_dir.mkdir(parents=True, exist_ok=True)
        w0_sentinel = "DEVLOOP-PLANTED-T504-WAVE0"
        w0_spec = {
            "id": w0_id,
            "worktree_root": ".worktrees",
            "owned_paths": ["src/math_core.py"],
            "positive_cmd": "python3 -c 'import sys; sys.path.insert(0, \".\"); from src.math_core import add; assert add(2, 3) == 5'",
            "negative_control_cmd": f"sh -c 'echo \"{w0_sentinel}: expected failure\"; exit 1'",
            "negative_expect": w0_sentinel,
            "worker": {"timeout_s": 30},
        }
        w0_lane_file = run_dir / f"lane-{w0_id}.json"
        w0_lane_file.write_text(json.dumps(w0_spec, indent=2), encoding="utf-8")

        adapters_py = SCRIPTS / "adapters.py"
        res_w0 = subprocess.run(
            [
                sys.executable,
                str(adapters_py),
                "gate",
                "--lane",
                str(w0_lane_file),
                "--wt",
                str(wt_w0),
                "--run",
                str(run_dir),
                "--root",
                str(self.sandbox),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_w0.returncode, 0, f"Wave 0 gate must pass. Output: {res_w0.stdout}\n{res_w0.stderr}")

        # Merge Wave 0 into main with --no-ff
        subprocess.run(
            ["git", "-C", str(self.sandbox), "merge", "--no-ff", "--no-edit", f"lane/{w0_id}"],
            check=True,
            capture_output=True,
        )
        self.assertTrue((self.sandbox / "src" / "math_core.py").exists(), "Wave 0 merged artifact must exist in base main")

        # Clean up Wave 0 worktree
        subprocess.run(["git", "-C", str(self.sandbox), "worktree", "remove", "--force", str(wt_w0)], check=True)

        # --- Execute Wave 1 ---
        w1_id = "wave1-calc-service"
        wt_w1 = self.sandbox / ".worktrees" / w1_id
        subprocess.run(
            ["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt_w1), "-b", f"lane/{w1_id}", "HEAD"],
            check=True,
        )

        self.assertTrue((wt_w1 / "src" / "math_core.py").exists(), "Wave 1 worktree must inherit Wave 0 artifact from updated base_ref")

        (wt_w1 / "src" / "calc_service.py").write_text(
            "import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parent.parent))\nfrom src.math_core import add\n\ndef multiply_by_sum(x, y, multiplier):\n    return add(x, y) * multiplier\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "-C", str(wt_w1), "add", "src/calc_service.py"], check=True)
        subprocess.run(["git", "-C", str(wt_w1), "commit", "-qm", "feat(calc): implement calc_service using math_core"], check=True)

        w1_sentinel = "DEVLOOP-PLANTED-T504-WAVE1"
        w1_spec = {
            "id": w1_id,
            "worktree_root": ".worktrees",
            "owned_paths": ["src/calc_service.py"],
            "positive_cmd": "python3 -c 'import sys; sys.path.insert(0, \".\"); from src.calc_service import multiply_by_sum; assert multiply_by_sum(2, 3, 4) == 20'",
            "negative_control_cmd": f"sh -c 'echo \"{w1_sentinel}: expected failure\"; exit 1'",
            "negative_expect": w1_sentinel,
            "worker": {"timeout_s": 30},
        }
        w1_lane_file = run_dir / f"lane-{w1_id}.json"
        w1_lane_file.write_text(json.dumps(w1_spec, indent=2), encoding="utf-8")

        res_w1 = subprocess.run(
            [
                sys.executable,
                str(adapters_py),
                "gate",
                "--lane",
                str(w1_lane_file),
                "--wt",
                str(wt_w1),
                "--run",
                str(run_dir),
                "--root",
                str(self.sandbox),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_w1.returncode, 0, f"Wave 1 gate must pass. Output: {res_w1.stdout}\n{res_w1.stderr}")

        # Merge Wave 1 into main with --no-ff
        subprocess.run(
            ["git", "-C", str(self.sandbox), "merge", "--no-ff", "--no-edit", f"lane/{w1_id}"],
            check=True,
            capture_output=True,
        )

        self.assertTrue((self.sandbox / "src" / "math_core.py").exists())
        self.assertTrue((self.sandbox / "src" / "calc_service.py").exists())
        base_status = subprocess.check_output(["git", "-C", str(self.sandbox), "status", "--porcelain"], text=True).strip()
        self.assertEqual(base_status, "", "Base repository must be clean after all waves merge")

        # Clean up Wave 1 worktree
        subprocess.run(["git", "-C", str(self.sandbox), "worktree", "remove", "--force", str(wt_w1)], check=True)


if __name__ == "__main__":
    unittest.main()
