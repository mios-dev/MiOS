#!/usr/bin/env python3
# AI-hint: Unit test for mios_worktree.py
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from mios_worktree import AgentWorktreeManager

class TestAgentWorktree(unittest.TestCase):
    def test_create_worktree_dry_run(self):
        mgr = AgentWorktreeManager(dry_run=True)
        res = mgr.create_worktree("sub_123")
        self.assertEqual(res["status"], "dry_run")
        self.assertEqual(res["subagent_id"], "sub_123")

    def test_cleanup_worktree_dry_run(self):
        mgr = AgentWorktreeManager(dry_run=True)
        res = mgr.cleanup_worktree("sub_123")
        self.assertEqual(res["status"], "dry_run")

    def test_subagent_id_validation(self):
        mgr = AgentWorktreeManager(dry_run=False)
        invalid_ids = ["../escaped", "sub/agent", "bad name", "agent;rm", "agent$var", ".."]
        for bad_id in invalid_ids:
            res_c = mgr.create_worktree(bad_id)
            self.assertEqual(res_c["status"], "error", f"Expected error for ID {bad_id}")
            self.assertIn("Invalid subagent_id", res_c["message"])

            res_cl = mgr.cleanup_worktree(bad_id)
            self.assertEqual(res_cl["status"], "error", f"Expected error for ID {bad_id}")
            self.assertIn("Invalid subagent_id", res_cl["message"])

    def test_merge_tree_success_and_cleanup(self):
        with tempfile.TemporaryDirectory() as td:
            repo_dir = os.path.join(td, "repo")
            wt_dir = os.path.join(td, "worktrees")
            scratch_dir = os.path.join(td, "scratch")
            os.makedirs(repo_dir)

            subprocess.run(["git", "init", repo_dir], check=True, capture_output=True)
            subprocess.run(["git", "-C", repo_dir, "config", "user.name", "Tester"], check=True)
            subprocess.run(["git", "-C", repo_dir, "config", "user.email", "tester@test.local"], check=True)

            f1 = os.path.join(repo_dir, "file1.txt")
            with open(f1, "w") as fh:
                fh.write("init\n")
            subprocess.run(["git", "-C", repo_dir, "add", "file1.txt"], check=True)
            subprocess.run(["git", "-C", repo_dir, "commit", "-m", "init"], check=True)

            mgr = AgentWorktreeManager(
                repo_root=repo_dir,
                base_worktree_dir=wt_dir,
                base_scratch_dir=scratch_dir,
                dry_run=False,
            )

            # Create worktree
            sub_id = "agent-unit-01"
            res_c = mgr.create_worktree(sub_id, base_branch="HEAD")
            self.assertEqual(res_c["status"], "success")
            self.assertTrue(os.path.isdir(res_c["worktree_path"]))

            # Make a commit in the worktree
            f2 = os.path.join(res_c["worktree_path"], "file2.txt")
            with open(f2, "w") as fh:
                fh.write("worktree data\n")
            subprocess.run(["git", "-C", res_c["worktree_path"], "add", "file2.txt"], check=True)
            subprocess.run(["git", "-C", res_c["worktree_path"], "commit", "-m", "add file2"], check=True)

            # Clean up with merge
            head_branch = subprocess.run(["git", "-C", repo_dir, "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True).stdout.strip()
            res_cl = mgr.cleanup_worktree(sub_id, merge=True, target_branch=head_branch)
            self.assertEqual(res_cl["status"], "success")
            self.assertTrue(res_cl["merged"])
            self.assertTrue(res_cl["worktree_removed"])
            self.assertTrue(res_cl["branch_deleted"])

            # Verify file2 is now on target_branch
            log = subprocess.run(["git", "-C", repo_dir, "log", "--oneline"], capture_output=True, text=True, check=True).stdout
            self.assertIn(f"Merge agent/{sub_id} into {head_branch}", log)
            self.assertTrue(os.path.isfile(os.path.join(repo_dir, "file2.txt")))

    def test_merge_tree_conflict_surfacing(self):
        with tempfile.TemporaryDirectory() as td:
            repo_dir = os.path.join(td, "repo")
            wt_dir = os.path.join(td, "worktrees")
            scratch_dir = os.path.join(td, "scratch")
            os.makedirs(repo_dir)

            subprocess.run(["git", "init", repo_dir], check=True, capture_output=True)
            subprocess.run(["git", "-C", repo_dir, "config", "user.name", "Tester"], check=True)
            subprocess.run(["git", "-C", repo_dir, "config", "user.email", "tester@test.local"], check=True)

            f1 = os.path.join(repo_dir, "conflict.txt")
            with open(f1, "w") as fh:
                fh.write("base line\n")
            subprocess.run(["git", "-C", repo_dir, "add", "conflict.txt"], check=True)
            subprocess.run(["git", "-C", repo_dir, "commit", "-m", "init"], check=True)

            mgr = AgentWorktreeManager(
                repo_root=repo_dir,
                base_worktree_dir=wt_dir,
                base_scratch_dir=scratch_dir,
                dry_run=False,
            )

            sub_id = "agent-unit-conf"
            res_c = mgr.create_worktree(sub_id, base_branch="HEAD")
            self.assertEqual(res_c["status"], "success")

            # Commit A in worktree
            with open(os.path.join(res_c["worktree_path"], "conflict.txt"), "w") as fh:
                fh.write("worktree conflict change\n")
            subprocess.run(["git", "-C", res_c["worktree_path"], "commit", "-am", "worktree change"], check=True)

            # Commit B in main
            with open(f1, "w") as fh:
                fh.write("main conflict change\n")
            subprocess.run(["git", "-C", repo_dir, "commit", "-am", "main change"], check=True)

            head_branch = subprocess.run(["git", "-C", repo_dir, "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True).stdout.strip()
            res_cl = mgr.cleanup_worktree(sub_id, merge=True, target_branch=head_branch)
            self.assertEqual(res_cl["status"], "error")
            self.assertFalse(res_cl["merged"])
            self.assertIn("errors", res_cl)
            self.assertTrue(any("Merge error" in e for e in res_cl["errors"]))
            self.assertTrue(res_cl["worktree_removed"])

if __name__ == "__main__":
    unittest.main()
