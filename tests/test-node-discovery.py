#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-NODE mDNS zero-conf mesh discovery and handshake.
# AI-related: usr/libexec/mios/node/discovery.py, src/mios-rs/mios-node/src/discovery.rs
"""Automated tests for WS-NODE mDNS zero-conf discovery, packet validation, and challenge handshake."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_DISC_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "node", "discovery.py")

spec = importlib.util.spec_from_file_location("discovery", _DISC_PATH)
if spec and spec.loader:
    discovery = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = discovery
    spec.loader.exec_module(discovery)
else:
    raise ImportError(f"Could not load discovery module from {_DISC_PATH}")


class TestNodeDiscovery(unittest.TestCase):
    """Validates mDNS advertisement parsing, challenge-response authentication, and active registry."""

    def test_node_advertisement_serialization(self):
        adv = discovery.NodeAdvertisement(
            node_id=202,
            hostname="mios-edge-blade01",
            port=8640,
            capabilities=["tier1_wasm", "tier2_native", "fp16_inference"],
            public_key_hex="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        )
        d = adv.to_dict()
        self.assertEqual(d["node_id"], 202)
        self.assertEqual(d["hostname"], "mios-edge-blade01")
        self.assertIn("tier1_wasm", d["capabilities"])

        restored = discovery.NodeAdvertisement.from_dict(d)
        self.assertEqual(restored.node_id, 202)
        self.assertEqual(restored.public_key_hex, adv.public_key_hex)

    def test_cryptographic_challenge_handshake_success(self):
        cluster_secret = b"mios-mesh-cluster-secret-key-32b"
        challenge = discovery.NodeHandshake.generate_challenge()
        self.assertEqual(len(challenge), 32)

        response = discovery.NodeHandshake.sign_challenge(challenge, cluster_secret)
        self.assertTrue(discovery.NodeHandshake.verify_response(challenge, response, cluster_secret))

    def test_challenge_handshake_tamper_rejection(self):
        cluster_secret = b"mios-mesh-cluster-secret-key-32b"
        wrong_secret = b"attacker-invalid-cluster-secret-"
        challenge = discovery.NodeHandshake.generate_challenge()

        bad_response = discovery.NodeHandshake.sign_challenge(challenge, wrong_secret)
        self.assertFalse(discovery.NodeHandshake.verify_response(challenge, bad_response, cluster_secret))

    def test_registry_discovery_and_authentication_lifecycle(self):
        cluster_secret = b"mios-mesh-cluster-secret-key-32b"
        registry = discovery.MeshDiscoveryRegistry(local_node_id=100, shared_cluster_key=cluster_secret)

        peer_adv = discovery.NodeAdvertisement(
            node_id=205,
            hostname="mios-blade-worker",
            port=9090,
            capabilities=["cuda_tensor_cores", "crdt_sync"],
            public_key_hex="abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
        )

        # Register peer
        self.assertTrue(registry.register_advertisement(peer_adv))
        self.assertEqual(len(registry.active_mesh_nodes()), 0)  # Not authenticated yet

        # Authenticate peer
        challenge = discovery.NodeHandshake.generate_challenge()
        response = discovery.NodeHandshake.sign_challenge(challenge, cluster_secret)
        self.assertTrue(registry.authenticate_peer(205, response, challenge))

        # Check active nodes
        active = registry.active_mesh_nodes()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["node_id"], 205)
        self.assertTrue(active[0]["authenticated"])


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNodeDiscovery)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
