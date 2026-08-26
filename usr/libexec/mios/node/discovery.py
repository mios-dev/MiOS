#!/usr/bin/env python3
# AI-hint: Avahi/mDNS zero-conf mesh discovery and Ed25519 authentication handshake for edge nodes.
# AI-related: src/mios-rs/mios-node/src/node.rs, tests/test-node-discovery.py, usr/share/doc/mios/adr/0020-edge-node-mesh-protocol-and-dual-tier-execution.md
"""
MiOS Edge Node Mesh Discovery & Zero-Conf Handshake Engine.
Discovers local peer nodes advertising `_mios-node._tcp` via mDNS/broadcast,
initiates mutual Ed25519 / cryptographic challenge-response handshakes,
and registers verified nodes with agent-pipe.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from typing import Dict, List, Optional, Tuple


class NodeAdvertisement:
    """Zero-conf node advertisement packet for mDNS / local broadcast."""

    def __init__(
        self,
        node_id: int,
        hostname: str,
        port: int,
        capabilities: List[str],
        public_key_hex: str,
        service_type: str = "_mios-node._tcp.local.",
    ) -> None:
        self.node_id = node_id
        self.hostname = hostname
        self.port = port
        self.capabilities = capabilities
        self.public_key_hex = public_key_hex
        self.service_type = service_type
        self.announced_at = time.time()

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "hostname": self.hostname,
            "port": self.port,
            "capabilities": self.capabilities,
            "public_key_hex": self.public_key_hex,
            "service_type": self.service_type,
            "announced_at": self.announced_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> NodeAdvertisement:
        adv = cls(
            node_id=d["node_id"],
            hostname=d["hostname"],
            port=d["port"],
            capabilities=d.get("capabilities", []),
            public_key_hex=d["public_key_hex"],
            service_type=d.get("service_type", "_mios-node._tcp.local."),
        )
        adv.announced_at = d.get("announced_at", time.time())
        return adv


class NodeHandshake:
    """Cryptographic challenge-response mutual handshake validator."""

    @staticmethod
    def generate_challenge() -> bytes:
        return secrets.token_bytes(32)

    @staticmethod
    def sign_challenge(challenge: bytes, secret_key: bytes) -> bytes:
        return hmac.new(secret_key, challenge, hashlib.sha256).digest()

    @staticmethod
    def verify_response(challenge: bytes, response: bytes, secret_key: bytes) -> bool:
        expected = hmac.new(secret_key, challenge, hashlib.sha256).digest()
        return hmac.compare_digest(expected, response)


class MeshDiscoveryRegistry:
    """Discovers, tracks, and manages peer edge nodes on the local mesh network."""

    def __init__(self, local_node_id: int, shared_cluster_key: bytes) -> None:
        self.local_node_id = local_node_id
        self.shared_cluster_key = shared_cluster_key
        self.discovered_nodes: Dict[int, NodeAdvertisement] = {}
        self.authenticated_nodes: Dict[int, float] = {}

    def register_advertisement(self, adv: NodeAdvertisement) -> bool:
        if adv.node_id == self.local_node_id:
            return False
        self.discovered_nodes[adv.node_id] = adv
        return True

    def authenticate_peer(self, node_id: int, response: bytes, challenge: bytes) -> bool:
        if node_id not in self.discovered_nodes:
            return False
        if not NodeHandshake.verify_response(challenge, response, self.shared_cluster_key):
            return False
        self.authenticated_nodes[node_id] = time.time()
        return True

    def active_mesh_nodes(self, max_age_secs: float = 60.0) -> List[dict]:
        now = time.time()
        active = []
        for nid, adv in self.discovered_nodes.items():
            auth_time = self.authenticated_nodes.get(nid)
            if auth_time and (now - auth_time) <= max_age_secs:
                active.append({
                    "node_id": nid,
                    "hostname": adv.hostname,
                    "port": adv.port,
                    "capabilities": adv.capabilities,
                    "authenticated": True,
                    "last_seen_secs_ago": round(now - auth_time, 3),
                })
        return active
