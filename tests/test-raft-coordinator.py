#!/usr/bin/env python3
# AI-hint: Unit tests for MiOS embedded Raft consensus coordinator and Patroni failover.
# AI-doc: usr/share/doc/mios/manual/cluster.md
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "cluster"))
from raft_coordinator import RaftClusterCoordinator


class TestRaftClusterCoordinator(unittest.TestCase):
    def setUp(self):
        self.coordinator = RaftClusterCoordinator(node_id="mios-node-01", dry_run=True)

    def test_check_quorum_status_mock(self):
        status = self.coordinator.check_quorum_status()
        self.assertEqual(status["status"], "healthy")
        self.assertEqual(status["leader_id"], "mios-node-01")
        self.assertTrue(status["is_leader"])
        self.assertEqual(status["quorum_needed"], 2)
        self.assertEqual(status["patroni_role"], "primary")

    def test_trigger_failover_mock(self):
        res = self.coordinator.trigger_failover("mios-node-02")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["new_leader"], "mios-node-02")
        self.assertTrue(res["patroni_switchover_executed"])


if __name__ == "__main__":
    unittest.main()
