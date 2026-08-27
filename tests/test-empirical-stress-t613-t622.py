#!/usr/bin/env python3
# AI-hint: Multi-perspective empirical adversarial stress tests for batch T-613 through T-622.
# Tests boundary conditions across WirePlumber audio, git merge fuzzing, IOMMU isolation, config drift, and Raft consensus.
# AI-doc: usr/share/doc/mios/manual/testing.md
import unittest
import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "audio"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "git"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "hw"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "cfg"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "cluster"))

from wireplumber_manager import WirePlumberManager
from merge_fuzzer import MergeFuzzHarness
from iommu_validator import IOMMUValidator
from drift_reconciler import ConfigDriftReconciler
from raft_coordinator import RaftClusterCoordinator

class TestEmpiricalStressT613T622(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="mios-stress-t613-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # --- 1. WirePlumber Stress Tests ---
    def test_wireplumber_loopback_unique_node_names(self):
        """Stress: Virtual Mic and Virtual Speaker must have distinct capture/playback node names."""
        mgr = WirePlumberManager(dry_run=True)
        conf = mgr.render_virtual_loopbacks_config()
        self.assertIn('node.name = "Virtual-Agent-Mic"', conf)
        self.assertIn('node.name = "Virtual-Agent-Speaker"', conf)

    # --- 2. AST Merge Fuzzer Stress Tests ---
    def test_merge_fuzzer_invalid_syntax_error_resilience(self):
        """Stress: Corrupted code with invalid syntax must be caught and logged cleanly."""
        harness = MergeFuzzHarness(dry_run=True)
        corrupted = "def incomplete_fn(:"
        res = harness.simulate_3way_ast_merge(corrupted, corrupted, corrupted)
        self.assertEqual(res["status"], "syntax_error")
        self.assertFalse(res["valid"])

    # --- 3. IOMMU Validator Stress Tests ---
    def test_iommu_nonexistent_bdf_handling(self):
        """Stress: Validating isolation on non-existent BDF must return not_found status."""
        validator = IOMMUValidator(dry_run=True)
        res = validator.validate_device_isolation("0000:99:99.9")
        self.assertEqual(res["status"], "not_found")

    # --- 4. Config Drift Reconciler Stress Tests ---
    def test_drift_reconciler_consistent_state(self):
        """Stress: Reconciler must detect 0 conflicts on synced baseline."""
        reconciler = ConfigDriftReconciler(dry_run=True)
        res = reconciler.reconcile_state()
        self.assertEqual(res["status"], "reconciled")
        self.assertEqual(res["state"], "consistent")

    # --- 5. Raft Consensus Stress Tests ---
    def test_raft_odd_quorum_calculation(self):
        """Stress: 5-node cluster must require 3 nodes for quorum."""
        coord = RaftClusterCoordinator(
            peer_nodes=["node1", "node2", "node3", "node4", "node5"],
            dry_run=True,
        )
        status = coord.check_quorum_status()
        self.assertEqual(status["quorum_needed"], 3)

if __name__ == "__main__":
    unittest.main()
