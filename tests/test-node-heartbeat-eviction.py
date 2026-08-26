#!/usr/bin/env python3
# AI-hint: Automated unit test suite for T-387 / AGY-1985 node heartbeat monitor and dead peer eviction.
# AI-doc: usr/share/doc/mios/manual/ch55-edge-mesh-binary-wire-protocol.md
"""
Unit test suite for WS-NODE: Heartbeat interval (5s), 3-strike dead peer detection (15s threshold),
degraded status transitions, routing table pruning, eviction event dispatching, and re-admission.
"""

from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "usr", "libexec", "mios", "node"))

import discovery


class TestNodeHeartbeatEviction(unittest.TestCase):
    """Validates 5s heartbeat interval, 3-strike dead peer eviction, and routing table lifecycle."""

    def setUp(self):
        self.monitor = discovery.HeartbeatMonitor(
            local_node_id=100,
            heartbeat_interval=5.0,
            degraded_threshold=10.0,
            eviction_threshold=15.0,
        )

    def test_record_heartbeat_and_initial_health(self):
        peer = self.monitor.record_heartbeat(
            node_id=201,
            addr="10.0.0.21",
            port=8650,
            uptime_secs=3600,
            cpu_load_pct=15,
            mem_available_kb=2048000,
            now=1000.0,
        )
        self.assertIsNotNone(peer)
        self.assertEqual(peer.node_id, 201)
        self.assertEqual(peer.status, discovery.PeerHealthStatus.HEALTHY)
        self.assertEqual(peer.missed_strikes, 0)
        self.assertEqual(self.monitor.peer_count, 1)
        self.assertTrue(self.monitor.is_peer_active(201))

    def test_degraded_status_transition_at_two_strikes(self):
        # Peer registered at T=1000
        self.monitor.record_heartbeat(201, "10.0.0.21", 8650, now=1000.0)

        # Sweep at T=1006 (6s elapsed -> 1 strike -> still Healthy)
        healthy, degraded, evicted = self.monitor.sweep(now=1006.0)
        self.assertIn(201, healthy)
        self.assertEqual(len(degraded), 0)
        self.assertEqual(len(evicted), 0)

        # Sweep at T=1011 (11s elapsed -> 2 strikes -> Degraded)
        healthy, degraded, evicted = self.monitor.sweep(now=1011.0)
        self.assertEqual(len(healthy), 0)
        self.assertIn(201, degraded)
        self.assertEqual(len(evicted), 0)
        peer = self.monitor.get_peer(201)
        self.assertEqual(peer.status, discovery.PeerHealthStatus.DEGRADED)
        self.assertEqual(peer.missed_strikes, 2)

    def test_3_strike_dead_peer_eviction_at_15s(self):
        self.monitor.record_heartbeat(202, "10.0.0.22", 8650, now=1000.0)

        # Sweep at T=1016 (16s elapsed -> 3 strikes >= 15s -> Evicted)
        healthy, degraded, evicted = self.monitor.sweep(now=1016.0)
        self.assertEqual(len(healthy), 0)
        self.assertEqual(len(degraded), 0)
        self.assertEqual(len(evicted), 1)

        event = evicted[0]
        self.assertEqual(event.node_id, 202)
        self.assertIn("3-strike timeout", event.reason)
        self.assertEqual(event.missed_strikes, 3)
        self.assertGreaterEqual(event.elapsed_secs, 15.0)

        # Routing table pruned
        self.assertEqual(self.monitor.peer_count, 0)
        self.assertFalse(self.monitor.is_peer_active(202))
        self.assertIsNone(self.monitor.get_peer(202))

    def test_eviction_event_listener_dispatch(self):
        dispatched_events = []

        def on_evict(event: discovery.EvictionEvent):
            dispatched_events.append(event)

        self.monitor.add_eviction_listener(on_evict)
        self.monitor.record_heartbeat(303, "10.0.0.33", 8650, now=500.0)

        # Trigger eviction at T=520 (20s elapsed)
        self.monitor.sweep(now=520.0)

        self.assertEqual(len(dispatched_events), 1)
        self.assertEqual(dispatched_events[0].node_id, 303)
        self.assertEqual(dispatched_events[0].missed_strikes, 4)

    def test_peer_readmission_after_eviction(self):
        # Register and evict peer
        self.monitor.record_heartbeat(404, "10.0.0.44", 8650, now=100.0)
        self.monitor.sweep(now=120.0)
        self.assertEqual(self.monitor.peer_count, 0)

        # Peer comes back online at T=150 with fresh Heartbeat
        re_admitted = self.monitor.record_heartbeat(
            404, "10.0.0.44", 8650, uptime_secs=10, cpu_load_pct=5, now=150.0
        )
        self.assertIsNotNone(re_admitted)
        self.assertEqual(self.monitor.peer_count, 1)
        self.assertEqual(re_admitted.status, discovery.PeerHealthStatus.HEALTHY)
        self.assertEqual(re_admitted.missed_strikes, 0)
        self.assertEqual(re_admitted.uptime_secs, 10)

    def test_manual_peer_eviction(self):
        self.monitor.record_heartbeat(505, "10.0.0.55", 8650, now=200.0)
        self.assertEqual(self.monitor.peer_count, 1)

        event = self.monitor.evict_peer(505, reason="operator_drain_node", now=205.0)
        self.assertIsNotNone(event)
        self.assertEqual(event.node_id, 505)
        self.assertEqual(event.reason, "operator_drain_node")
        self.assertEqual(self.monitor.peer_count, 0)

    def test_multi_peer_sweep_mixed_states(self):
        now = 1000.0
        # Peer A: fresh (last seen at 998 -> 2s elapsed)
        self.monitor.record_heartbeat(10, "10.0.0.10", 8650, now=998.0)
        # Peer B: degraded (last seen at 988 -> 12s elapsed)
        self.monitor.record_heartbeat(20, "10.0.0.20", 8650, now=988.0)
        # Peer C: dead (last seen at 980 -> 20s elapsed)
        self.monitor.record_heartbeat(30, "10.0.0.30", 8650, now=980.0)

        healthy, degraded, evicted = self.monitor.sweep(now=now)
        self.assertEqual(healthy, [10])
        self.assertEqual(degraded, [20])
        self.assertEqual(len(evicted), 1)
        self.assertEqual(evicted[0].node_id, 30)

        # Final active count should be 2 (Node 10 and Node 20)
        self.assertEqual(self.monitor.peer_count, 2)
        active_ids = [p.node_id for p in self.monitor.get_active_peers()]
        self.assertIn(10, active_ids)
        self.assertIn(20, active_ids)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNodeHeartbeatEviction)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
