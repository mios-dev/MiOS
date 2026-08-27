#!/usr/bin/env python3
# AI-hint: Unit test for mios_worktree.py
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from mios_worktree import AgentWorktreeManager


class TestAgentWorktree(unittest.TestCase):
    def test_create_worktree_dry_run(self):
        mgr = AgentWorktreeManager(dry_run=True)
        res = mgr.create_worktree("sub_123")
        self.assertEqual(res["status"], "dry_run")
        self.assertEqual(res["subagent_id"], "sub_123")

    def test_prune_worktree_dry_run(self):
        mgr = AgentWorktreeManager(dry_run=True)
        res = mgr.prune_worktree("sub_123")
        self.assertEqual(res["status"], "dry_run")


if __name__ == "__main__":
    unittest.main()
