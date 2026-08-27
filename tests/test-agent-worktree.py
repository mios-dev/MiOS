#!/usr/bin/env python3
# AI-hint: Unit tests for MiOS subagent git worktree lifecycle manager.
# AI-doc: usr/share/doc/mios/manual/agent-pipe.md
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "lib", "mios", "agent-pipe"))
from mios_worktree import AgentWorktreeManager


class TestAgentWorktreeManager(unittest.TestCase):
    def setUp(self):
        self.mgr = AgentWorktreeManager(
            repo_root="/mnt/c/MiOS",
            base_worktree_dir="/tmp/test-workspaces",
            base_scratch_dir="/tmp/test-scratch",
            dry_run=True,
        )

    def test_create_worktree_dry_run(self):
        res = self.mgr.create_worktree("subagent-42")
        self.assertEqual(res["status"], "dry_run")
        self.assertEqual(res["action"], "create")
        self.assertEqual(res["branch"], "agent/subagent-42")
        self.assertIn("worktree add", res["command"])

    def test_cleanup_worktree_dry_run(self):
        res = self.mgr.cleanup_worktree("subagent-42", merge=True)
        self.assertEqual(res["status"], "dry_run")
        self.assertEqual(res["action"], "cleanup")
        self.assertTrue(res["merged"])
        self.assertTrue(res["cleaned"])


if __name__ == "__main__":
    unittest.main()
