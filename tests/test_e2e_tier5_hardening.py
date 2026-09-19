#!/usr/bin/env python3
"""
test_e2e_tier5_hardening.py

Milestone M4: Tier 5 Adversarial Coverage Hardening Test Suite for Dev-Loop.
Covers:
  - Test 1: Direct CLI execution test for adapters.py gate verifying base-tree leakage
            emits BASE TREE LEAKAGE DETECTED to stderr and exits with code 2.
  - Test 2: Pre-flight vacuous sentinel check verifying adapters.py gate refuses to
            gate with exit code 2 if sentinel already exists in worktree.
  - Test 3: Symlink traversal isolation test across worktree boundary.
  - Test 4: Multi-wave pipeline dependency execution.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

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


def make_sandbox_repo(prefix: str = "devloop-tier5-sandbox-") -> Path:
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

    info_dir = td / ".git" / "info"
    info_dir.mkdir(parents=True, exist_ok=True)
    (info_dir / "exclude").write_text(".worktrees/\nworktrees/\n.devloop/run-*/\n.devloop/native/\n", encoding="utf-8")

    subprocess.run(["git", "-C", str(td), "add", "."], check=True, env=env)
    subprocess.run(["git", "-C", str(td), "commit", "-qm", "Initial seed commit"], check=True, env=env)
    return td


class SandboxTestCase(unittest.TestCase):
    """Base test case managing ephemeral sandbox lifecycle."""

    def setUp(self) -> None:
        self.sandbox = make_sandbox_repo(prefix=f"sandbox-{self._testMethodName}-")
        self.allowed = get_base_tree_always_allowed() + (".worktrees/", "worktrees/")

    def tearDown(self) -> None:
        if self.sandbox.exists():
            shutil.rmtree(self.sandbox, ignore_errors=True)


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
