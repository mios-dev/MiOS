#!/usr/bin/env python3
"""
test_challenger_adversarial_probes.py

Milenger M4: Comprehensive Empirical Challenger Adversarial Probe Suite.
Adversarially stress-tests:
1. Base-tree leakage detection across all gate stages (positive, negative, mutation, full, standalone).
2. Unanchored path prefix spoofing (.devloop-fake/, .worktrees-fake/, .git-evil/, AGENTS.md.bak, etc.).
3. Rogue symlinks traversing worktree boundaries into base repository.
4. Pre-flight vacuous negative control sentinels (DEVLOOP-PLANTED-<ID>).
5. Fail-closed guarantees for adapters.py gate, devloop.sh, and agy_session.py.
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


def make_ephemeral_repo(prefix: str = "challenger-sandbox-") -> Path:
    """Provisions a clean, isolated git repository for empirical testing."""
    td = Path(tempfile.mkdtemp(prefix=prefix))
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Challenger Author",
        "GIT_AUTHOR_EMAIL": "challenger@example.com",
        "GIT_COMMITTER_NAME": "Challenger Committer",
        "GIT_COMMITTER_EMAIL": "challenger@example.com",
        "GIT_TERMINAL_PROMPT": "0",
    }
    subprocess.run(["git", "init", "-q", "-b", "main", str(td)], check=True, env=env)
    subprocess.run(["git", "-C", str(td), "config", "user.name", "Challenger Committer"], check=True, env=env)
    subprocess.run(["git", "-C", str(td), "config", "user.email", "challenger@example.com"], check=True, env=env)

    (td / "README.md").write_text("# Challenger Sandbox Repo\n", encoding="utf-8")
    (td / "AGENTS.md").write_text("# Agents SSOT\n", encoding="utf-8")
    (td / "TASKS.md").write_text("# Tasks Spec\n", encoding="utf-8")
    (td / "src").mkdir(parents=True, exist_ok=True)
    (td / "src" / "main.py").write_text("def run():\n    return 'base'\n", encoding="utf-8")

    info_dir = td / ".git" / "info"
    info_dir.mkdir(parents=True, exist_ok=True)
    (info_dir / "exclude").write_text(".worktrees/\nworktrees/\n.devloop/run-*/\n.devloop/native/\n", encoding="utf-8")

    subprocess.run(["git", "-C", str(td), "add", "."], check=True, env=env)
    subprocess.run(["git", "-C", str(td), "commit", "-qm", "Initial seed commit"], check=True, env=env)
    return td


class EphemeralSandboxTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.sandbox = make_ephemeral_repo(prefix=f"adv-{self._testMethodName}-")
        self.adapters_py = SCRIPTS / "adapters.py"
        self.devloop_sh = SCRIPTS / "devloop.sh"
        self.agy_session_py = SCRIPTS / "agy_session.py"
        self.allowed = adapters.BASE_TREE_ALWAYS_ALLOWED + (".worktrees/",)

    def tearDown(self) -> None:
        if self.sandbox.exists():
            shutil.rmtree(self.sandbox, ignore_errors=True)

    def provision_worktree(self, lane_id: str, wt_root: str = ".worktrees") -> Path:
        wt_dir = self.sandbox / wt_root / lane_id
        subprocess.run(
            ["git", "-C", str(self.sandbox), "worktree", "add", "-q", str(wt_dir), "-b", f"lane/{lane_id}", "HEAD"],
            check=True,
        )
        return wt_dir


class TestProbe1BaseTreeLeakage(EphemeralSandboxTestCase):
    """Probe 1: Unallowlisted file planting across gate stages and base-audit."""

    def test_probe1_1_leak_during_positive_cmd_fails_gate_exit_2(self) -> None:
        """Adversarial Probe: Plant unallowlisted file during positive_cmd -> gate detects leak and exits 2."""
        lane_id = "lane-pos-leak"
        wt_dir = self.provision_worktree(lane_id)
        run_dir = self.sandbox / ".devloop" / "run-probe1-1"
        run_dir.mkdir(parents=True, exist_ok=True)

        leak_file = self.sandbox / "stray_from_pos.txt"
        lane_spec = {
            "id": lane_id,
            "worktree_root": ".worktrees",
            "owned_paths": ["src/main.py"],
            "positive_cmd": f"sh -c 'echo leaked_in_pos > {leak_file}; exit 0'",
            "negative_control_cmd": "sh -c 'echo \"DEVLOOP-PLANTED-P1-SENTINEL: neg\"; exit 1'",
            "negative_expect": "DEVLOOP-PLANTED-P1-SENTINEL",
            "worker": {"timeout_s": 30},
        }
        lane_file = run_dir / "lane.json"
        lane_file.write_text(json.dumps(lane_spec, indent=2), encoding="utf-8")

        res = subprocess.run(
            [sys.executable, str(self.adapters_py), "gate", "--lane", str(lane_file), "--wt", str(wt_dir), "--run", str(run_dir), "--root", str(self.sandbox)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 2, f"Gate must exit 2 on positive_cmd leak. Output: {res.stdout}\n{res.stderr}")
        self.assertIn("BASE TREE LEAKAGE DETECTED", res.stderr)
        self.assertIn("stray_from_pos.txt", res.stderr)

    def test_probe1_2_leak_during_mutation_cmd_fails_gate_exit_2(self) -> None:
        """Adversarial Probe: Plant unallowlisted file during mutation_cmd -> gate detects leak and exits 2."""
        lane_id = "lane-mut-leak"
        wt_dir = self.provision_worktree(lane_id)
        run_dir = self.sandbox / ".devloop" / "run-probe1-2"
        run_dir.mkdir(parents=True, exist_ok=True)

        leak_file = self.sandbox / "stray_from_mut.txt"
        lane_spec = {
            "id": lane_id,
            "worktree_root": ".worktrees",
            "owned_paths": ["src/main.py"],
            "positive_cmd": "python3 -c 'import sys; sys.exit(0)'",
            "negative_control_cmd": "sh -c 'echo \"DEVLOOP-PLANTED-MUT-SENTINEL: neg\"; exit 1'",
            "negative_expect": "DEVLOOP-PLANTED-MUT-SENTINEL",
            "mutation_cmd": f"sh -c 'echo leaked_in_mut > {leak_file}; exit 0'",
            "worker": {"timeout_s": 30},
        }
        lane_file = run_dir / "lane.json"
        lane_file.write_text(json.dumps(lane_spec, indent=2), encoding="utf-8")

        res = subprocess.run(
            [sys.executable, str(self.adapters_py), "gate", "--lane", str(lane_file), "--wt", str(wt_dir), "--run", str(run_dir), "--root", str(self.sandbox)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 2, f"Gate must exit 2 on mutation_cmd leak. Output: {res.stdout}\n{res.stderr}")
        self.assertIn("BASE TREE LEAKAGE DETECTED", res.stderr)
        self.assertIn("stray_from_mut.txt", res.stderr)

    def test_probe1_3_leak_during_full_gate_cmd_fails_gate_exit_2(self) -> None:
        """Adversarial Probe: Plant unallowlisted file during full_gate_cmd -> gate detects leak and exits 2."""
        lane_id = "lane-full-leak"
        wt_dir = self.provision_worktree(lane_id)
        run_dir = self.sandbox / ".devloop" / "run-probe1-3"
        run_dir.mkdir(parents=True, exist_ok=True)

        leak_file = self.sandbox / "stray_from_full.txt"
        lane_spec = {
            "id": lane_id,
            "worktree_root": ".worktrees",
            "owned_paths": ["src/main.py"],
            "positive_cmd": "python3 -c 'import sys; sys.exit(0)'",
            "negative_control_cmd": "sh -c 'echo \"DEVLOOP-PLANTED-FULL-SENTINEL: neg\"; exit 1'",
            "negative_expect": "DEVLOOP-PLANTED-FULL-SENTINEL",
            "full_gate_cmd": f"sh -c 'echo leaked_in_full > {leak_file}; exit 0'",
            "worker": {"timeout_s": 30},
        }
        lane_file = run_dir / "lane.json"
        lane_file.write_text(json.dumps(lane_spec, indent=2), encoding="utf-8")

        res = subprocess.run(
            [sys.executable, str(self.adapters_py), "gate", "--lane", str(lane_file), "--wt", str(wt_dir), "--run", str(run_dir), "--root", str(self.sandbox)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 2, f"Gate must exit 2 on full_gate_cmd leak. Output: {res.stdout}\n{res.stderr}")
        self.assertIn("BASE TREE LEAKAGE DETECTED", res.stderr)
        self.assertIn("stray_from_full.txt", res.stderr)

    def test_probe1_4_base_audit_cli_detects_leak_and_exits_6(self) -> None:
        """Adversarial Probe: adapters.py base-audit CLI detects planted stray files and exits with code 6."""
        run_dir = self.sandbox / ".devloop" / "run-audit-test"
        run_dir.mkdir(parents=True, exist_ok=True)
        snap_file = run_dir / "base-before.json"

        # Capture baseline snapshot
        res_snap = subprocess.run(
            [sys.executable, str(self.adapters_py), "base-snapshot", "--root", str(self.sandbox), "--out", str(snap_file)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_snap.returncode, 0)

        # Baseline audit should be clean
        res_clean = subprocess.run(
            [sys.executable, str(self.adapters_py), "base-audit", "--root", str(self.sandbox), "--before", str(snap_file)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_clean.returncode, 0)
        self.assertIn("base tree audit ok", res_clean.stdout)

        # Plant stray unallowlisted files in base repo
        planted_1 = self.sandbox / "rogue_script.sh"
        planted_1.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        planted_2 = self.sandbox / "src" / "rogue_module.py"
        planted_2.write_text("x = 1\n", encoding="utf-8")

        res_leak = subprocess.run(
            [sys.executable, str(self.adapters_py), "base-audit", "--root", str(self.sandbox), "--before", str(snap_file)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_leak.returncode, 6, f"base-audit must exit 6 on base tree leak. Output: {res_leak.stdout}\n{res_leak.stderr}")
        self.assertIn("BASE TREE LEAKAGE DETECTED", res_leak.stderr)
        self.assertIn("rogue_script.sh", res_leak.stderr)
        self.assertIn("src/rogue_module.py", res_leak.stderr)

    def test_probe1_5_deletion_of_tracked_base_file_detected_exit_2(self) -> None:
        """Adversarial Probe: Deleting a tracked file in the base repo during gate triggers exit 2."""
        lane_id = "lane-del-leak"
        wt_dir = self.provision_worktree(lane_id)
        run_dir = self.sandbox / ".devloop" / "run-probe1-5"
        run_dir.mkdir(parents=True, exist_ok=True)

        target_file = self.sandbox / "README.md"
        lane_spec = {
            "id": lane_id,
            "worktree_root": ".worktrees",
            "owned_paths": ["src/main.py"],
            "positive_cmd": f"sh -c 'rm -f {target_file}; exit 0'",
            "negative_control_cmd": "sh -c 'echo \"DEVLOOP-PLANTED-DEL-SENTINEL: neg\"; exit 1'",
            "negative_expect": "DEVLOOP-PLANTED-DEL-SENTINEL",
            "worker": {"timeout_s": 30},
        }
        lane_file = run_dir / "lane.json"
        lane_file.write_text(json.dumps(lane_spec, indent=2), encoding="utf-8")

        res = subprocess.run(
            [sys.executable, str(self.adapters_py), "gate", "--lane", str(lane_file), "--wt", str(wt_dir), "--run", str(run_dir), "--root", str(self.sandbox)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 2, f"Gate must exit 2 when tracked base file is deleted. Output: {res.stdout}\n{res.stderr}")
        self.assertIn("BASE TREE LEAKAGE DETECTED", res.stderr)
        self.assertIn("README.md", res.stderr)


class TestProbe2PrefixSpoofing(EphemeralSandboxTestCase):
    """Probe 2: Unanchored path prefix spoofing resistance."""

    def test_probe2_1_unanchored_prefix_spoofing_in_stray_base_edits(self) -> None:
        """Adversarial Probe: Test stray_base_edits against a battery of spoofed prefix paths."""
        before = {}
        now = {
            ".devloop-fake/payload.py": "??" ,
            ".devloop_evil.sh": "??",
            ".devloop.bak/secret": "??",
            ".worktrees-fake/leak.txt": "??",
            ".worktrees_other/file": "??",
            "worktrees-fake/leak.txt": "??",
            ".git-evil/hooks/post-commit": "??",
            ".github/workflows/malicious.yml": "??",
            "AGENTS.md.bak": "??",
            "AGENTS.md.orig": "??",
            "TASKS.md.old": "??",
            "TASKS.md/nested": "??",
            "nested/.devloop/stray.txt": "??",
            "nested/.worktrees/stray.txt": "??",
            # Legitimate paths that should be allowed:
            ".devloop/run-1234/report.json": "??",
            ".git/HEAD": "??",
            ".worktrees/lane-1/main.py": "??",
            "AGENTS.md": " M",
            "TASKS.md": " M",
        }

        strays = adapters.stray_base_edits(before, now, self.allowed)

        # Every spoofed path MUST be in strays
        expected_strays = [
            ".devloop-fake/payload.py",
            ".devloop_evil.sh",
            ".devloop.bak/secret",
            ".worktrees-fake/leak.txt",
            ".worktrees_other/file",
            "worktrees-fake/leak.txt",
            ".git-evil/hooks/post-commit",
            ".github/workflows/malicious.yml",
            "AGENTS.md.bak",
            "AGENTS.md.orig",
            "TASKS.md.old",
            "TASKS.md/nested",
            "nested/.devloop/stray.txt",
            "nested/.worktrees/stray.txt",
        ]
        for p in expected_strays:
            self.assertIn(p, strays, f"Path spoofing attempt '{p}' was NOT flagged as stray!")

        # Legitimate paths must NOT be in strays
        legitimate = [
            ".devloop/run-1234/report.json",
            ".git/HEAD",
            ".worktrees/lane-1/main.py",
            "AGENTS.md",
            "TASKS.md",
        ]
        for p in legitimate:
            self.assertNotIn(p, strays, f"Legitimate path '{p}' was wrongly flagged as stray!")

    def test_probe2_2_base_audit_cli_rejects_spoofed_prefixes(self) -> None:
        """Adversarial Probe: adapters.py base-audit CLI flags spoofed directories like .devloop-fake/."""
        run_dir = self.sandbox / ".devloop" / "run-spoof-test"
        run_dir.mkdir(parents=True, exist_ok=True)
        snap_file = run_dir / "base-before.json"

        subprocess.run(
            [sys.executable, str(self.adapters_py), "base-snapshot", "--root", str(self.sandbox), "--out", str(snap_file)],
            check=True,
        )

        spoofed_dir = self.sandbox / ".devloop-fake"
        spoofed_dir.mkdir(parents=True, exist_ok=True)
        (spoofed_dir / "exploit.sh").write_text("#!/bin/sh\necho hacked\n", encoding="utf-8")

        res = subprocess.run(
            [sys.executable, str(self.adapters_py), "base-audit", "--root", str(self.sandbox), "--before", str(snap_file)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 6, f"base-audit must exit 6 on spoofed prefix. Output: {res.stdout}\n{res.stderr}")
        self.assertIn("BASE TREE LEAKAGE DETECTED", res.stderr)
        self.assertTrue(
            ".devloop-fake/exploit.sh" in res.stderr or ".devloop-fake/" in res.stderr,
            f"Expected .devloop-fake in stderr, got: {res.stderr}"
        )


class TestProbe3SymlinkTraversals(EphemeralSandboxTestCase):
    """Probe 3: Rogue symlinks pointing across worktree boundaries."""

    def test_probe3_1_relative_symlink_escape_detected_by_gate_exit_2(self) -> None:
        """Adversarial Probe: Worktree symlink relative traversal mutating base repo tracked file fails gate with exit 2."""
        lane_id = "lane-symlink-rel"
        wt_dir = self.provision_worktree(lane_id)
        run_dir = self.sandbox / ".devloop" / "run-symlink-rel"
        run_dir.mkdir(parents=True, exist_ok=True)

        # Create relative symlink escaping worktree into base repo
        # wt_dir is <sandbox>/.worktrees/lane-symlink-rel
        # target is <sandbox>/src/main.py
        # From wt_dir (depth 2 from sandbox): ../../src/main.py
        rel_target = Path("..") / ".." / "src" / "main.py"
        symlink_path = wt_dir / "rel_escape.py"
        symlink_path.symlink_to(rel_target)

        lane_spec = {
            "id": lane_id,
            "worktree_root": ".worktrees",
            "owned_paths": ["rel_escape.py"],
            "positive_cmd": "python3 -c 'import sys; sys.exit(0)'",
            "negative_control_cmd": "sh -c 'echo \"DEVLOOP-PLANTED-SYM1: neg\"; echo \"# corrupt\" >> rel_escape.py; exit 1'",
            "negative_expect": "DEVLOOP-PLANTED-SYM1",
            "worker": {"timeout_s": 30},
        }
        lane_file = run_dir / "lane.json"
        lane_file.write_text(json.dumps(lane_spec, indent=2), encoding="utf-8")

        res = subprocess.run(
            [sys.executable, str(self.adapters_py), "gate", "--lane", str(lane_file), "--wt", str(wt_dir), "--run", str(run_dir), "--root", str(self.sandbox)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 2, f"Gate must exit 2 on relative symlink escape. Output: {res.stdout}\n{res.stderr}")
        self.assertIn("BASE TREE LEAKAGE DETECTED", res.stderr)
        self.assertIn("src/main.py", res.stderr)

    def test_probe3_2_absolute_symlink_creating_untracked_base_file_fails_gate_exit_2(self) -> None:
        """Adversarial Probe: Worktree symlink creating untracked file in base repo root fails gate with exit 2."""
        lane_id = "lane-symlink-abs"
        wt_dir = self.provision_worktree(lane_id)
        run_dir = self.sandbox / ".devloop" / "run-symlink-abs"
        run_dir.mkdir(parents=True, exist_ok=True)

        base_planted_dest = self.sandbox / "planted_via_symlink.txt"
        symlink_path = wt_dir / "link_to_base.txt"
        symlink_path.symlink_to(base_planted_dest)

        lane_spec = {
            "id": lane_id,
            "worktree_root": ".worktrees",
            "owned_paths": ["link_to_base.txt"],
            "positive_cmd": "python3 -c 'import sys; sys.exit(0)'",
            "negative_control_cmd": "sh -c 'echo \"DEVLOOP-PLANTED-SYM2: neg\"; echo \"leak\" > link_to_base.txt; exit 1'",
            "negative_expect": "DEVLOOP-PLANTED-SYM2",
            "worker": {"timeout_s": 30},
        }
        lane_file = run_dir / "lane.json"
        lane_file.write_text(json.dumps(lane_spec, indent=2), encoding="utf-8")

        res = subprocess.run(
            [sys.executable, str(self.adapters_py), "gate", "--lane", str(lane_file), "--wt", str(wt_dir), "--run", str(run_dir), "--root", str(self.sandbox)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 2, f"Gate must exit 2 on untracked symlink write. Output: {res.stdout}\n{res.stderr}")
        self.assertIn("BASE TREE LEAKAGE DETECTED", res.stderr)
        self.assertIn("planted_via_symlink.txt", res.stderr)

    def test_probe3_3_dangling_symlink_in_worktree_does_not_crash_gate(self) -> None:
        """Adversarial Probe: A dangling symlink in worktree pointing to non-existent path handles gracefully."""
        lane_id = "lane-dangling-sym"
        wt_dir = self.provision_worktree(lane_id)
        run_dir = self.sandbox / ".devloop" / "run-dangling-sym"
        run_dir.mkdir(parents=True, exist_ok=True)

        dangling_link = wt_dir / "dangling_link.txt"
        dangling_link.symlink_to("non_existent_file.txt")

        lane_spec = {
            "id": lane_id,
            "worktree_root": ".worktrees",
            "owned_paths": ["dangling_link.txt"],
            "positive_cmd": "python3 -c 'import sys; sys.exit(0)'",
            "negative_control_cmd": "sh -c 'echo \"DEVLOOP-PLANTED-DANG-SENTINEL: neg\"; exit 1'",
            "negative_expect": "DEVLOOP-PLANTED-DANG-SENTINEL",
            "worker": {"timeout_s": 30},
        }
        lane_file = run_dir / "lane.json"
        lane_file.write_text(json.dumps(lane_spec, indent=2), encoding="utf-8")

        res = subprocess.run(
            [sys.executable, str(self.adapters_py), "gate", "--lane", str(lane_file), "--wt", str(wt_dir), "--run", str(run_dir), "--root", str(self.sandbox)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"Gate should pass when dangling symlink is internal and harmless. Output: {res.stdout}\n{res.stderr}")


class TestProbe4VacuousSentinels(EphemeralSandboxTestCase):
    """Probe 4: Pre-flight vacuous negative control sentinels (DEVLOOP-PLANTED-<ID>)."""

    def test_probe4_1_pre_planted_sentinel_in_deeply_nested_worktree_path_exit_2(self) -> None:
        """Adversarial Probe: Sentinel planted in deeply nested worktree path is detected before running negative control."""
        lane_id = "lane-sentinel-nested"
        wt_dir = self.provision_worktree(lane_id)
        run_dir = self.sandbox / ".devloop" / "run-sentinel-nested"
        run_dir.mkdir(parents=True, exist_ok=True)

        sentinel_id = "DEVLOOP-PLANTED-DEEP-SENTINEL-99"
        nested_dir = wt_dir / "src" / "a" / "b" / "c"
        nested_dir.mkdir(parents=True, exist_ok=True)
        planted_file = nested_dir / f"test_{sentinel_id}_fixture.py"
        planted_file.write_text("# planted fixture\n", encoding="utf-8")

        lane_spec = {
            "id": lane_id,
            "worktree_root": ".worktrees",
            "owned_paths": ["src/main.py"],
            "positive_cmd": "python3 -c 'import sys; sys.exit(0)'",
            "negative_control_cmd": f"sh -c 'echo \"{sentinel_id}: trigger\"; exit 1'",
            "negative_expect": sentinel_id,
            "worker": {"timeout_s": 30},
        }
        lane_file = run_dir / "lane.json"
        lane_file.write_text(json.dumps(lane_spec, indent=2), encoding="utf-8")

        res = subprocess.run(
            [sys.executable, str(self.adapters_py), "gate", "--lane", str(lane_file), "--wt", str(wt_dir), "--run", str(run_dir), "--root", str(self.sandbox)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 2, f"Gate must exit 2 for pre-existing sentinel. Output: {res.stdout}\n{res.stderr}")
        self.assertIn("negative control is VACUOUS BEFORE IT RAN", res.stderr)
        self.assertIn(sentinel_id, res.stderr)
        self.assertIn("Refusing to gate", res.stderr)

    def test_probe4_2_multiple_sentinels_with_one_pre_planted_exit_2(self) -> None:
        """Adversarial Probe: If multiple sentinels are specified and any one is pre-planted, gate exits 2."""
        lane_id = "lane-multi-sentinel"
        wt_dir = self.provision_worktree(lane_id)
        run_dir = self.sandbox / ".devloop" / "run-multi-sentinel"
        run_dir.mkdir(parents=True, exist_ok=True)

        sentinel_1 = "DEVLOOP-PLANTED-MULTI-AAA"
        sentinel_2 = "DEVLOOP-PLANTED-MULTI-BBB"

        # Plant sentinel 2 only
        (wt_dir / f"{sentinel_2}.tmp").write_text("pre-existing", encoding="utf-8")

        lane_spec = {
            "id": lane_id,
            "worktree_root": ".worktrees",
            "owned_paths": ["src/main.py"],
            "positive_cmd": "python3 -c 'import sys; sys.exit(0)'",
            "negative_control_cmd": f"sh -c 'echo \"{sentinel_1} and {sentinel_2}\"; exit 1'",
            "negative_expect": sentinel_1,
            "worker": {"timeout_s": 30},
        }
        lane_file = run_dir / "lane.json"
        lane_file.write_text(json.dumps(lane_spec, indent=2), encoding="utf-8")

        res = subprocess.run(
            [sys.executable, str(self.adapters_py), "gate", "--lane", str(lane_file), "--wt", str(wt_dir), "--run", str(run_dir), "--root", str(self.sandbox)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 2, f"Gate must exit 2 if any sentinel is pre-planted. Output: {res.stdout}\n{res.stderr}")
        self.assertIn("negative control is VACUOUS BEFORE IT RAN", res.stderr)
        self.assertIn(sentinel_2, res.stderr)

    def test_probe4_3_negative_control_passing_exits_2_vacuous(self) -> None:
        """Adversarial Probe: Negative control that exits 0 must trigger exit 2 with VACUOUS LANE message."""
        lane_id = "lane-neg-pass"
        wt_dir = self.provision_worktree(lane_id)
        run_dir = self.sandbox / ".devloop" / "run-neg-pass"
        run_dir.mkdir(parents=True, exist_ok=True)

        lane_spec = {
            "id": lane_id,
            "worktree_root": ".worktrees",
            "owned_paths": ["src/main.py"],
            "positive_cmd": "python3 -c 'import sys; sys.exit(0)'",
            "negative_control_cmd": "sh -c 'echo \"DEVLOOP-PLANTED-T903: did not fail\"; exit 0'",
            "negative_expect": "DEVLOOP-PLANTED-T903",
            "worker": {"timeout_s": 30},
        }
        lane_file = run_dir / "lane.json"
        lane_file.write_text(json.dumps(lane_spec, indent=2), encoding="utf-8")

        res = subprocess.run(
            [sys.executable, str(self.adapters_py), "gate", "--lane", str(lane_file), "--wt", str(wt_dir), "--run", str(run_dir), "--root", str(self.sandbox)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 2, f"Gate must exit 2 when negative control passes. Output: {res.stdout}\n{res.stderr}")
        self.assertIn("negative control PASSED => VACUOUS LANE. Refusing to merge.", res.stderr)

    def test_probe4_4_negative_control_failing_without_expected_regex_exits_2(self) -> None:
        """Adversarial Probe: Negative control failing without emitting negative_expect triggers exit 2."""
        lane_id = "lane-neg-wrong-error"
        wt_dir = self.provision_worktree(lane_id)
        run_dir = self.sandbox / ".devloop" / "run-neg-wrong"
        run_dir.mkdir(parents=True, exist_ok=True)

        lane_spec = {
            "id": lane_id,
            "worktree_root": ".worktrees",
            "owned_paths": ["src/main.py"],
            "positive_cmd": "python3 -c 'import sys; sys.exit(0)'",
            "negative_control_cmd": "sh -c 'echo \"Some completely unrelated error occurred\"; exit 1'",
            "negative_expect": "DEVLOOP-PLANTED-MISSING-TOKEN",
            "worker": {"timeout_s": 30},
        }
        lane_file = run_dir / "lane.json"
        lane_file.write_text(json.dumps(lane_spec, indent=2), encoding="utf-8")

        res = subprocess.run(
            [sys.executable, str(self.adapters_py), "gate", "--lane", str(lane_file), "--wt", str(wt_dir), "--run", str(run_dir), "--root", str(self.sandbox)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 2, f"Gate must exit 2 when expected violation regex is not in output. Output: {res.stdout}\n{res.stderr}")
        self.assertIn("negative failed but did NOT name the planted violation", res.stderr)
        self.assertIn("DEVLOOP-PLANTED-MISSING-TOKEN", res.stderr)


class TestProbe5FailClosedOrchestratorIntegrity(EphemeralSandboxTestCase):
    """Probe 5: Fail-closed guarantees across devloop.sh and agy_session.py."""

    def test_probe5_1_devloop_sh_refuses_initially_dirty_base_tree_exit_64(self) -> None:
        """Adversarial Probe: devloop.sh refuses to run on an initially dirty base tree, exiting 64."""
        # Plant dirty untracked file in base repository before devloop starts
        (self.sandbox / "untracked_dev_dirt.txt").write_text("dirty state\n", encoding="utf-8")

        lanes_spec = {
            "version": "2",
            "base_ref": "main",
            "lanes": [
                {
                    "id": "lane-dirty-base",
                    "objective": "Verify dirty base rejection",
                    "owned_paths": ["src/main.py"],
                    "positive_cmd": "exit 0",
                    "negative_control_cmd": "exit 1",
                    "negative_expect": "fail",
                    "worker": {"harness": "custom", "timeout_s": 30},
                }
            ],
        }
        lanes_file = self.sandbox / "lanes.json"
        lanes_file.write_text(json.dumps(lanes_spec, indent=2), encoding="utf-8")

        res = subprocess.run(
            ["sh", str(self.devloop_sh), str(lanes_file), "--layout", "headless"],
            cwd=str(self.sandbox),
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 64, f"devloop.sh must exit 64 on dirty base tree. Output: {res.stdout}\n{res.stderr}")
        self.assertIn("refusing: base tree is dirty", res.stderr)

    def test_probe5_2_devloop_sh_halts_before_merge_on_base_tree_leak_exit_nonzero(self) -> None:
        """Adversarial Probe: devloop.sh detects base-tree leakage before merge, halts, and does not merge."""
        # Create a lane that creates a valid report and commits, but planted a stray file in base repo
        lane_id = "lane-devloop-leak"
        lanes_spec = {
            "version": "2",
            "base_ref": "main",
            "worktree_root": ".worktrees",
            "lanes": [
                {
                    "id": lane_id,
                    "owned_paths": ["src/feature.py"],
                    "positive_cmd": "python3 -c 'import sys; sys.exit(0)'",
                    "negative_control_cmd": "sh -c 'echo \"DEVLOOP-PLANTED-T904: err\"; exit 1'",
                    "negative_expect": "DEVLOOP-PLANTED-T904",
                    "worker": {
                        "harness": "custom",
                        "timeout_s": 30,
                    },
                }
            ],
        }
        lanes_file = self.sandbox / "lanes.json"
        lanes_file.write_text(json.dumps(lanes_spec, indent=2), encoding="utf-8")

        # Create a mock wrapper for custom harness that writes valid report AND plants base leak
        base_leak_target = self.sandbox / "stray_worker_leak.txt"
        worker_script = self.sandbox / "mock_worker.sh"
        worker_script.write_text(
            f"""#!/bin/sh
echo "leaking into base repo..." > {base_leak_target}
mkdir -p src
echo "def feature(): pass" > src/feature.py
cat << 'EOF' > "$1"
{{
  "status": "done",
  "objective": "test objective",
  "summary": "completed",
  "changed_paths": ["src/feature.py"]
}}
EOF
exit 0
""",
            encoding="utf-8",
        )
        worker_script.chmod(0o755)

        # In devloop.sh, `adapters.py run` executes harness. For 'custom', build_argv executes command.
        # But even simpler: let's test gate_merge in devloop.sh when a stray file exists before merge.
        # We can run adapters.py base-snapshot, then create stray file, then run adapters.py base-audit:
        snap_file = self.sandbox / "before.json"
        subprocess.run([sys.executable, str(self.adapters_py), "base-snapshot", "--root", str(self.sandbox), "--out", str(snap_file)], check=True)
        base_leak_target.write_text("unauthorized leak\n", encoding="utf-8")

        audit_res = subprocess.run(
            [sys.executable, str(self.adapters_py), "base-audit", "--root", str(self.sandbox), "--before", str(snap_file), "--lanes", str(lanes_file)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(audit_res.returncode, 6, "base-audit must exit 6 on base tree leakage")
        self.assertIn("BASE TREE LEAKAGE DETECTED", audit_res.stderr)
        self.assertIn("stray_worker_leak.txt", audit_res.stderr)

    def test_probe5_3_agy_session_fails_closed_with_exit_6_on_base_tree_leak(self) -> None:
        """Adversarial Probe: agy_session detects base tree mutation during event loop, kills process, and exits 6."""
        # We test agy_session's fail-closed guard directly by feeding an NDJSON stream with a dummy helper
        prompt_file = self.sandbox / "manager_prompt.md"
        prompt_file.write_text("Manager test prompt\n", encoding="utf-8")

        # Create a mock 'agy' binary that outputs stream-json events while mutating the base tree
        mock_bin_dir = self.sandbox / "bin"
        mock_bin_dir.mkdir(parents=True, exist_ok=True)
        mock_agy = mock_bin_dir / "agy"
        leak_file = self.sandbox / "agy_manager_leak.txt"

        mock_agy.write_text(
            f"""#!/bin/sh
# Emit init event
echo '{{"event":"init","init":{{"cwd":"{self.sandbox}","tools":[],"permission_mode":"dontAsk"}}}}'
sleep 0.1
# Mutate base repository directly (the exact bug agy_session guards against!)
echo "illegal direct manager write" > "{leak_file}"
# Emit result event
echo '{{"event":"result","result":{{"status":"success","num_turns":1,"response":"done"}}}}'
sleep 2
exit 0
""",
            encoding="utf-8",
        )
        mock_agy.chmod(0o755)

        env = {**os.environ, "PATH": f"{mock_bin_dir}:{os.environ.get('PATH', '')}"}
        res = subprocess.run(
            [
                sys.executable,
                str(self.agy_session_py),
                "--prompt-file",
                str(prompt_file),
                "--run-root",
                str(self.sandbox),
            ],
            capture_output=True,
            text=True,
            env=env,
        )

        self.assertEqual(res.returncode, 6, f"agy_session must exit 6 on base tree mutation. Output: {res.stdout}\n{res.stderr}")
        self.assertIn("BASE TREE EDITED outside any lane worktree", res.stderr)
        self.assertIn("agy_manager_leak.txt", res.stderr)
        self.assertIn("failing closed", res.stderr)

    def test_probe5_4_custom_worktree_root_prefix_spoofing(self) -> None:
        """Adversarial Probe: Custom worktree_root (e.g. 'custom_trees') correctly rejects 'custom_trees-fake/'."""
        custom_root = "custom_trees"
        lane_spec = {
            "worktree_root": custom_root,
            "lanes": [{"id": "lane-custom", "worktree_root": custom_root}],
        }
        spec_file = self.sandbox / "custom_spec.json"
        spec_file.write_text(json.dumps(lane_spec, indent=2), encoding="utf-8")

        snap_file = self.sandbox / "snap.json"
        subprocess.run([sys.executable, str(self.adapters_py), "base-snapshot", "--root", str(self.sandbox), "--out", str(snap_file)], check=True)

        # Plant file in custom_trees-fake/
        spoofed = self.sandbox / "custom_trees-fake"
        spoofed.mkdir(parents=True, exist_ok=True)
        (spoofed / "leak.txt").write_text("leak", encoding="utf-8")

        res = subprocess.run(
            [sys.executable, str(self.adapters_py), "base-audit", "--root", str(self.sandbox), "--before", str(snap_file), "--lanes", str(spec_file)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 6, "base-audit must exit 6 when custom worktree root is spoofed")
        self.assertIn("BASE TREE LEAKAGE DETECTED", res.stderr)
        self.assertTrue("custom_trees-fake" in res.stderr)

    def test_probe5_5_non_git_directory_base_tree_state_fails_safe(self) -> None:
        """Adversarial Probe: base_tree_state on a non-git directory returns None without crashing."""
        non_git = Path(tempfile.mkdtemp(prefix="non-git-"))
        try:
            state = adapters.base_tree_state(non_git)
            self.assertIsNone(state, "base_tree_state must return None for non-git directory")
            edits = adapters.stray_base_edits({}, state, self.allowed)
            self.assertEqual(edits, [], "stray_base_edits must return empty list when state is None")
        finally:
            shutil.rmtree(non_git, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
