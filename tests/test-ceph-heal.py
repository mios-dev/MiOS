#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Ceph Self-Healing & Client Latency Throttling (T-729, T-730).
# AI-related: usr/libexec/mios/storage/ceph_heal.py, tests/test-ceph-heal.py
"""Automated unit test suite for MiOS Ceph Self-Healing Orchestrator."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "storage"))

from ceph_heal import MAX_CLIENT_LATENCY_DEGRADATION_PCT, CephSelfHealingOrchestrator


class TestCephHeal(unittest.TestCase):
    def setUp(self):
        self.orch = CephSelfHealingOrchestrator(max_backfills=1, dry_run=True)

    def test_osd_failure_heals_to_health_ok(self):
        """Test failed OSD rebalances PGs to HEALTH_OK with <10% client latency degradation."""
        rep = self.orch.trigger_osd_failover_and_heal("osd.1", degraded_pg_count=48)
        self.assertEqual(rep.cluster_health_state, "HEALTH_OK")
        self.assertTrue(rep.recovery_completed)
        self.assertLess(rep.client_latency_degradation_pct, MAX_CLIENT_LATENCY_DEGRADATION_PCT)


if __name__ == "__main__":
    unittest.main()
