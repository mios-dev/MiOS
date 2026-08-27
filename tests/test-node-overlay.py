#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-NODE multi-transport routing and WAN overlay failover.
# AI-related: usr/libexec/mios/node/overlay.py, src/mios-rs/mios-node/src/overlay.rs
"""Automated tests for WS-NODE MultiTransportRouter, 3-strike LAN partition failover, and anti-flap recovery."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_OVERLAY_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "node", "overlay.py")

spec = importlib.util.spec_from_file_location("overlay", _OVERLAY_PATH)
if spec and spec.loader:
    overlay = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = overlay
    spec.loader.exec_module(overlay)
else:
    raise ImportError(f"Could not load overlay module from {_OVERLAY_PATH}")

class TestNodeOverlay(unittest.TestCase):
    """Validates multi-transport routing, 3-strike partition detection, and asymmetric anti-flap dwell."""

    def test_transport_types_and_defaults(self):
        self.assertEqual(overlay.TransportType.LAN_BROADCAST, 1)
        self.assertEqual(overlay.TransportType.WIREGUARD, 2)
        self.assertEqual(overlay.TransportType.TAILSCALE, 3)
        self.assertEqual(overlay.TransportType.DIRECT_TCP, 4)

    def test_lan_partition_failover_to_wireguard(self):
        config = overlay.HysteresisConfig(
            fail_strikes_threshold=3,
            recovery_dwell_ms=10_000,
            recovery_strikes_threshold=3,
        )
        router = overlay.MultiTransportRouter(config)

        endpoints = {
            overlay.TransportType.LAN_BROADCAST: "192.168.1.50:8650",
            overlay.TransportType.WIREGUARD: "10.0.0.50:8650",
            overlay.TransportType.TAILSCALE: "100.64.0.50:8650",
        }
        router.register_peer(node_id=201, endpoints=endpoints)

        # 1. Initial primary transport is LAN
        transport, endpoint = router.select_route(node_id=201)
        self.assertEqual(transport, overlay.TransportType.LAN_BROADCAST)
        self.assertEqual(endpoint, "192.168.1.50:8650")
        self.assertFalse(router.is_peer_partitioned(node_id=201))

        # 2. 2 missed heartbeats on LAN: should still remain LAN
        router.record_missed_heartbeat(node_id=201, transport=overlay.TransportType.LAN_BROADCAST, now_ms=1000)
        router.record_missed_heartbeat(node_id=201, transport=overlay.TransportType.LAN_BROADCAST, now_ms=2000)
        self.assertFalse(router.is_peer_partitioned(node_id=201))
        self.assertEqual(router.select_route(node_id=201)[0], overlay.TransportType.LAN_BROADCAST)

        # 3. 3rd missed heartbeat: triggers failover to WireGuard
        router.record_missed_heartbeat(node_id=201, transport=overlay.TransportType.LAN_BROADCAST, now_ms=3000)
        self.assertTrue(router.is_peer_partitioned(node_id=201))
        transport2, endpoint2 = router.select_route(node_id=201)
        self.assertEqual(transport2, overlay.TransportType.WIREGUARD)
        self.assertEqual(endpoint2, "10.0.0.50:8650")

    def test_failover_hierarchy_to_tailscale(self):
        router = overlay.MultiTransportRouter()

        endpoints = {
            overlay.TransportType.LAN_BROADCAST: "192.168.1.75:8650",
            overlay.TransportType.TAILSCALE: "100.64.0.75:8650",
        }
        router.register_peer(node_id=202, endpoints=endpoints)

        # Failover without WireGuard endpoint -> falls back to Tailscale
        for i in range(3):
            router.record_missed_heartbeat(node_id=202, transport=overlay.TransportType.LAN_BROADCAST, now_ms=1000 * (i + 1))

        self.assertTrue(router.is_peer_partitioned(node_id=202))
        transport, endpoint = router.select_route(node_id=202)
        self.assertEqual(transport, overlay.TransportType.TAILSCALE)
        self.assertEqual(endpoint, "100.64.0.75:8650")

    def test_asymmetric_anti_flap_recovery_hysteresis(self):
        config = overlay.HysteresisConfig(
            fail_strikes_threshold=3,
            recovery_dwell_ms=5000,  # 5s dwell for test
            recovery_strikes_threshold=3,
        )
        router = overlay.MultiTransportRouter(config)

        endpoints = {
            overlay.TransportType.LAN_BROADCAST: "192.168.1.99:8650",
            overlay.TransportType.TAILSCALE: "100.64.0.99:8650",
        }
        router.register_peer(node_id=203, endpoints=endpoints)

        # Trigger failover
        for i in range(3):
            router.record_missed_heartbeat(node_id=203, transport=overlay.TransportType.LAN_BROADCAST, now_ms=1000 * (i + 1))
        self.assertEqual(router.select_route(node_id=203)[0], overlay.TransportType.TAILSCALE)

        # LAN probes resume at t=4000
        router.record_heartbeat(node_id=203, transport=overlay.TransportType.LAN_BROADCAST, latency_ms=1, now_ms=4000)
        router.record_heartbeat(node_id=203, transport=overlay.TransportType.LAN_BROADCAST, latency_ms=1, now_ms=5000)
        router.record_heartbeat(node_id=203, transport=overlay.TransportType.LAN_BROADCAST, latency_ms=1, now_ms=6000)

        # 3 strikes achieved, but dwell elapsed is only 2000ms (< 5000ms) -> Still Tailscale!
        self.assertEqual(router.select_route(node_id=203)[0], overlay.TransportType.TAILSCALE)
        self.assertTrue(router.is_peer_partitioned(node_id=203))

        # Probe at t=9500 (dwell elapsed = 5500ms >= 5000ms) -> Restores LAN!
        router.record_heartbeat(node_id=203, transport=overlay.TransportType.LAN_BROADCAST, latency_ms=1, now_ms=9500)
        self.assertEqual(router.select_route(node_id=203)[0], overlay.TransportType.LAN_BROADCAST)
        self.assertFalse(router.is_peer_partitioned(node_id=203))

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNodeOverlay)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
