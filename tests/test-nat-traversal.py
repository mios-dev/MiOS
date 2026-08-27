#!/usr/bin/env python3
# AI-hint: Unit tests for MiOS Tiered NAT Traversal Engine (UPnP, STUN, DERP relay).
# AI-doc: usr/share/doc/mios/manual/networking.md
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "net"))
from nat_traversal import NATTraversalEngine

class TestNATTraversalEngine(unittest.TestCase):
    def test_mock_upnp_mapping_success(self):
        engine = NATTraversalEngine(local_port=51820, mock_mode=True)
        res = engine.establish_traversal_channel()
        self.assertEqual(res["status"], "established")
        self.assertEqual(res["method"], "upnp_port_mapping")
        self.assertTrue(res["direct"])
        self.assertIn("198.51.100.25:51820", res["endpoint"])

    def test_stun_hole_punch_fallback(self):
        engine = NATTraversalEngine(local_port=51820, mock_mode=False)
        # Mock probe_upnp_nat_pmp returning unsupported
        engine.probe_upnp_nat_pmp = lambda: {"supported": False, "status": "disabled"}
        engine.probe_stun_endpoints = lambda: {
            "tier": "tier2_stun_hole_punch",
            "direct_p2p_viable": True,
            "external_ip": "203.0.113.10",
            "external_port": 51820,
        }

        res = engine.establish_traversal_channel()
        self.assertEqual(res["status"], "established")
        self.assertEqual(res["method"], "stun_udp_hole_punch")
        self.assertTrue(res["direct"])
        self.assertEqual(res["endpoint"], "203.0.113.10:51820")

    def test_derp_relay_fallback_selection(self):
        engine = NATTraversalEngine(local_port=51820, mock_mode=False)
        engine.probe_upnp_nat_pmp = lambda: {"supported": False}
        engine.probe_stun_endpoints = lambda: {"direct_p2p_viable": False}

        res = engine.establish_traversal_channel()
        self.assertEqual(res["status"], "established")
        self.assertEqual(res["method"], "derp_relay_fallback")
        self.assertFalse(res["direct"])
        self.assertEqual(res["endpoint"], "derp1.mios.mesh:8443")
        self.assertLess(res["tier_details"]["expected_latency_ms"], 50.0)

if __name__ == "__main__":
    unittest.main()
