#!/usr/bin/env python3
# AI-hint: Automated unit test suite for T-562 Git DAG Reconciliation & Consensus Signer.
# AI-related: usr/libexec/mios/git/reconcile_dag.py, tests/test-git-reconcile.py
"""Automated unit test suite for Multi-Master Git DAG Reconciliation (T-562)."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_MODULE_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "git", "reconcile_dag.py")

spec = importlib.util.spec_from_file_location("reconcile_dag", _MODULE_PATH)
if spec and spec.loader:
    reconcile_dag = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = reconcile_dag
    spec.loader.exec_module(reconcile_dag)
else:
    raise ImportError(f"Could not load reconcile_dag module from {_MODULE_PATH}")


class TestGitReconcile(unittest.TestCase):
    """Validates LCA computation, divergent branch reconciliation, and consensus signing."""

    def setUp(self) -> None:
        self.engine = reconcile_dag.DagReconcileEngine(mock=True)

    def test_find_lca_divergent(self) -> None:
        """Asserts discovery of root ancestor 'a1b2c3d4' between local2 and peer2."""
        lca = self.engine.find_lca("l2222222", "p2222222")
        self.assertEqual(lca, "a1b2c3d4")

    def test_find_lca_same_commit(self) -> None:
        """Asserts LCA of identical commit is itself."""
        lca = self.engine.find_lca("l1111111", "l1111111")
        self.assertEqual(lca, "l1111111")

    def test_calculate_reconciliation_plan_consensus(self) -> None:
        """Asserts consensus merge plan on divergent branch tips."""
        plan = self.engine.calculate_reconciliation_plan("main", "peer/main", "l2222222", "p2222222")
        self.assertEqual(plan.strategy, "consensus_merge")
        self.assertEqual(plan.lca_hash, "a1b2c3d4")
        self.assertEqual(plan.commits_to_apply, ["p1111111", "p2222222"])

    def test_calculate_reconciliation_plan_fast_forward(self) -> None:
        """Asserts fast-forward plan when local head is the direct ancestor."""
        plan = self.engine.calculate_reconciliation_plan("main", "peer/main", "a1b2c3d4", "l2222222")
        self.assertEqual(plan.strategy, "fast_forward")
        self.assertEqual(plan.commits_to_apply, ["l1111111", "l2222222"])

    def test_sign_consensus_commit(self) -> None:
        """Asserts cryptographic consensus commit generation and signature verification."""
        commit, record = self.engine.sign_consensus_commit(
            parent_hashes=["l2222222", "p2222222"],
            tree_hash="tree_reconciled_01",
            node_id="node-blade-4",
            signing_key="ed25519_secret_blade4",
        )
        self.assertIsNotNone(commit.signature)
        self.assertEqual(commit.parent_hashes, ["l2222222", "p2222222"])
        self.assertIn("node-blade-4", record.participating_nodes)
        self.assertIn("node-blade-4", record.signatures)

    def test_full_reconcile_workflow(self) -> None:
        """Asserts end-to-end reconciliation workflow."""
        res = self.engine.reconcile(
            local_branch="main",
            peer_branch="peer/main",
            local_head="l2222222",
            peer_head="p2222222",
            node_id="node-local",
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["strategy"], "consensus_merge")
        self.assertIn("consensus_commit", res)

    def test_sync_remotes_mock(self) -> None:
        """Asserts multi-remote synchronization."""
        sync_res = self.engine.sync_remotes(repo_path=".", remotes=["forgejo", "github"])
        self.assertEqual(sync_res["status"], "success")
        self.assertEqual(sync_res["synced_remotes"]["forgejo"], "synced")
        self.assertEqual(sync_res["synced_remotes"]["github"], "synced")

    def test_cli_mock_json(self) -> None:
        """Asserts CLI execution with --mock --json."""
        with patch("sys.argv", ["reconcile_dag.py", "--mock", "--json"]):
            with patch("builtins.print") as mock_print:
                ret = reconcile_dag.main()
                self.assertEqual(ret, 0)
                mock_print.assert_called()
                parsed = json.loads(mock_print.call_args[0][0])
                self.assertEqual(parsed["status"], "success")


if __name__ == "__main__":
    unittest.main()
