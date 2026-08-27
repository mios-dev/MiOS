#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-FED / A2A-01 agent capability exchange and cryptographic attestation.
# AI-related: usr/libexec/mios/a2a/attestation.py, usr/lib/mios/agent-pipe/server.py
"""Automated unit test suite for A2A mutual capability attestation and Ed25519 signing."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout

from cryptography.hazmat.primitives import serialization

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_ATTESTATION_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "a2a", "attestation.py")

spec = importlib.util.spec_from_file_location("attestation", _ATTESTATION_PATH)
if spec and spec.loader:
    attestation = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = attestation
    spec.loader.exec_module(attestation)
else:
    raise ImportError(f"Could not load attestation module from {_ATTESTATION_PATH}")

class TestA2AAttestation(unittest.TestCase):
    """Validates Ed25519 key management, AgentCard signing, tampering rejection, clock skew, and negotiation."""

    def setUp(self):
        self.auth = attestation.A2AAuthenticator.generate_keypair(node_id=101)
        self.peer_auth = attestation.A2AAuthenticator.generate_keypair(node_id=102)

    def test_keypair_generation_and_export(self):
        self.assertEqual(self.auth.node_id, 101)
        self.assertIsNotNone(self.auth.private_key)
        self.assertIsNotNone(self.auth.public_key)
        self.assertEqual(len(self.auth.public_key_bytes), 32)
        self.assertEqual(len(self.auth.public_key_hex), 64)
        self.assertEqual(len(self.auth.private_key_bytes), 32)
        self.assertEqual(len(self.auth.private_key_hex), 64)

        # Restore from hex
        restored_priv = attestation.A2AAuthenticator.from_private_key(self.auth.private_key_hex, node_id=101)
        self.assertEqual(restored_priv.public_key_hex, self.auth.public_key_hex)
        self.assertEqual(restored_priv.private_key_hex, self.auth.private_key_hex)

        # Restore verify-only from public key hex
        restored_pub = attestation.A2AAuthenticator.from_public_key(self.auth.public_key_hex, node_id=101)
        self.assertIsNone(restored_pub.private_key)
        self.assertEqual(restored_pub.public_key_hex, self.auth.public_key_hex)

        # Restore from PEM bytes
        pem_priv = self.auth.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        auth_from_pem = attestation.A2AAuthenticator.from_private_key(pem_priv, node_id=101)
        self.assertEqual(auth_from_pem.public_key_hex, self.auth.public_key_hex)

        pem_pub = self.auth.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        auth_from_pem_pub = attestation.A2AAuthenticator.from_public_key(pem_pub, node_id=101)
        self.assertEqual(auth_from_pem_pub.public_key_hex, self.auth.public_key_hex)

        # Attempting create_card without private key should raise ValueError
        with self.assertRaises(ValueError):
            restored_pub.create_card(agent_name="verify_only", capabilities=["test"])

    def test_invalid_key_formats_raise(self):
        with self.assertRaises(ValueError):
            attestation._load_pub_key("invalid_short_hex")
        with self.assertRaises(ValueError):
            attestation._load_priv_key("invalid_short_hex")

    def test_agent_card_creation_and_fields(self):
        card = self.auth.create_card(
            agent_name="executor_node",
            capabilities=["sql_query", "code_exec", "file_io"],
            endpoints={"rpc": "http://127.0.0.1:8640/a2a", "ws": "ws://127.0.0.1:8640/a2a/ws"},
            ttl_seconds=1800,
            node_id=101,
        )
        self.assertEqual(card["agent_name"], "executor_node")
        self.assertEqual(card["node_id"], 101)
        # Capabilities should be sorted
        self.assertEqual(card["capabilities"], ["code_exec", "file_io", "sql_query"])
        self.assertEqual(card["endpoints"]["rpc"], "http://127.0.0.1:8640/a2a")
        self.assertEqual(card["public_key"], self.auth.public_key_hex)
        self.assertIn("nonce", card)
        self.assertIn("sig", card)
        self.assertEqual(len(card["sig"]), 128)  # 64 bytes in hex
        self.assertGreater(card["expires_at"], card["issued_at"])
        self.assertEqual(card["expires_at"] - card["issued_at"], 1800)

    def test_signature_verification_success(self):
        card = self.auth.create_card(
            agent_name="executor_node",
            capabilities=["code_exec", "sql_query"],
            ttl_seconds=3600,
        )
        # Verify via static method with trusted key object
        self.assertTrue(attestation.A2AAuthenticator.verify_card(card, self.auth.public_key))
        # Verify via static method with trusted key hex string
        self.assertTrue(attestation.A2AAuthenticator.verify_card(card, self.auth.public_key_hex))
        # Verify via static method with trusted key bytes
        self.assertTrue(attestation.A2AAuthenticator.verify_card(card, self.auth.public_key_bytes))
        # Verify via module-level convenience function
        self.assertTrue(attestation.verify_card(card, self.auth.public_key_hex))
        # Verify with self-embedded public key when trusted_key is omitted
        self.assertTrue(attestation.A2AAuthenticator.verify_card(card))

    def test_wrong_trusted_key_rejected(self):
        card = self.auth.create_card(
            agent_name="executor_node",
            capabilities=["code_exec"],
            ttl_seconds=3600,
        )
        # Verifying with peer's public key must fail
        self.assertFalse(attestation.A2AAuthenticator.verify_card(card, self.peer_auth.public_key))
        self.assertFalse(attestation.A2AAuthenticator.verify_card(card, self.peer_auth.public_key_hex))

    def test_tampered_payload_rejected(self):
        card = self.auth.create_card(
            agent_name="executor_node",
            capabilities=["code_exec"],
            ttl_seconds=3600,
        )
        # Tamper capabilities
        t_caps = dict(card)
        t_caps["capabilities"] = ["code_exec", "admin_escalation"]
        self.assertFalse(attestation.A2AAuthenticator.verify_card(t_caps, self.auth.public_key))

        # Tamper agent_name
        t_name = dict(card)
        t_name["agent_name"] = "imposter_node"
        self.assertFalse(attestation.A2AAuthenticator.verify_card(t_name, self.auth.public_key))

        # Tamper nonce
        t_nonce = dict(card)
        t_nonce["nonce"] = "00000000000000000000000000000000"
        self.assertFalse(attestation.A2AAuthenticator.verify_card(t_nonce, self.auth.public_key))

        # Tamper timestamps
        t_time = dict(card)
        t_time["issued_at"] = card["issued_at"] - 100
        self.assertFalse(attestation.A2AAuthenticator.verify_card(t_time, self.auth.public_key))

        # Tamper public_key in payload
        t_pub = dict(card)
        t_pub["public_key"] = self.peer_auth.public_key_hex
        self.assertFalse(attestation.A2AAuthenticator.verify_card(t_pub, self.auth.public_key))

        # Tamper signature bytes
        t_sig = dict(card)
        t_sig["sig"] = "00" * 64
        self.assertFalse(attestation.A2AAuthenticator.verify_card(t_sig, self.auth.public_key))

    def test_clock_skew_and_expiration(self):
        now = time.time()

        # Expired card (expired 120 seconds ago, max clock skew 60s)
        expired_card = self.auth.create_card(
            agent_name="node",
            capabilities=["ping"],
            issued_at=int(now - 1000),
            ttl_seconds=800,  # expired 200s ago
        )
        self.assertFalse(attestation.A2AAuthenticator.verify_card(expired_card, self.auth.public_key, max_clock_skew=60))

        # Card slightly expired within clock skew window
        borderline_expired = self.auth.create_card(
            agent_name="node",
            capabilities=["ping"],
            issued_at=int(now - 300),
            ttl_seconds=280,  # expired 20s ago
        )
        # Should be valid when max_clock_skew is 60s
        self.assertTrue(attestation.A2AAuthenticator.verify_card(borderline_expired, self.auth.public_key, max_clock_skew=60))
        # Should fail if clock skew is strictly 0
        self.assertFalse(attestation.A2AAuthenticator.verify_card(borderline_expired, self.auth.public_key, max_clock_skew=0))

        # Future timestamp beyond clock skew
        future_card = self.auth.create_card(
            agent_name="node",
            capabilities=["ping"],
            issued_at=int(now + 200),
            ttl_seconds=3600,
        )
        self.assertFalse(attestation.A2AAuthenticator.verify_card(future_card, self.auth.public_key, max_clock_skew=60))

        # Future timestamp within clock skew window
        borderline_future = self.auth.create_card(
            agent_name="node",
            capabilities=["ping"],
            issued_at=int(now + 30),
            ttl_seconds=3600,
        )
        self.assertTrue(attestation.A2AAuthenticator.verify_card(borderline_future, self.auth.public_key, max_clock_skew=60))

        # Invalid TTL (expires_at <= issued_at)
        invalid_ttl_card = self.auth.create_card(
            agent_name="node",
            capabilities=["ping"],
            issued_at=int(now),
            ttl_seconds=0,
        )
        self.assertFalse(attestation.A2AAuthenticator.verify_card(invalid_ttl_card, self.auth.public_key))

    def test_malformed_card_inputs(self):
        # Non-dict input
        self.assertFalse(attestation.A2AAuthenticator.verify_card("not a dict", self.auth.public_key))
        self.assertFalse(attestation.A2AAuthenticator.verify_card(None, self.auth.public_key))

        # Missing signature
        self.assertFalse(attestation.A2AAuthenticator.verify_card({"agent_name": "test"}, self.auth.public_key))

        # Invalid signature hex length
        self.assertFalse(attestation.A2AAuthenticator.verify_card({
            "agent_name": "test",
            "issued_at": int(time.time()),
            "expires_at": int(time.time() + 3600),
            "sig": "abcdef",
        }, self.auth.public_key))

        # Missing timestamps
        self.assertFalse(attestation.A2AAuthenticator.verify_card({
            "agent_name": "test",
            "sig": "00" * 64,
        }, self.auth.public_key))

    def test_capability_negotiation(self):
        card = self.auth.create_card(
            agent_name="worker_mesh",
            capabilities=["code_exec", "file_io", "sql_query", "wasm_eval"],
            ttl_seconds=3600,
        )

        # Full match
        ok, granted = attestation.A2AAuthenticator.negotiate_capabilities(
            card,
            required_capabilities=["code_exec", "sql_query"],
            trusted_key=self.auth.public_key,
        )
        self.assertTrue(ok)
        self.assertEqual(granted, ["code_exec", "sql_query"])

        # Empty required capabilities -> full pass
        ok, granted = attestation.A2AAuthenticator.negotiate_capabilities(
            card,
            required_capabilities=[],
            trusted_key=self.auth.public_key,
        )
        self.assertTrue(ok)
        self.assertEqual(granted, [])

        # Partial match / missing capability
        ok, missing = attestation.A2AAuthenticator.negotiate_capabilities(
            card,
            required_capabilities=["code_exec", "root_shell_exec"],
            trusted_key=self.auth.public_key,
        )
        self.assertFalse(ok)
        self.assertEqual(missing, ["root_shell_exec"])

        # Tampered card during negotiation
        tampered = dict(card)
        tampered["capabilities"] = ["code_exec", "root_shell_exec"]
        ok, caps = attestation.A2AAuthenticator.negotiate_capabilities(
            tampered,
            required_capabilities=["code_exec"],
            trusted_key=self.auth.public_key,
        )
        self.assertFalse(ok)
        self.assertEqual(caps, [])

        # Module-level convenience function
        ok, granted = attestation.negotiate_capabilities(
            card,
            required_capabilities=["file_io"],
            trusted_key=self.auth.public_key,
        )
        self.assertTrue(ok)
        self.assertEqual(granted, ["file_io"])

    def test_cli_interface(self):
        with tempfile.TemporaryDirectory(prefix="mios-a2a-cli-test-") as tmpdir:
            priv_file = os.path.join(tmpdir, "node.priv")
            pub_file = os.path.join(tmpdir, "node.pub")
            card_file = os.path.join(tmpdir, "card.json")

            # 0. Test CLI with no action prints help
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = attestation.main([])
            self.assertEqual(code, 1)

            # 1. Test CLI keygen
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = attestation.main(["keygen", "--node-id", "201", "--out-priv", priv_file, "--out-pub", pub_file])
            self.assertEqual(code, 0)
            self.assertTrue(os.path.isfile(priv_file))
            self.assertTrue(os.path.isfile(pub_file))

            with open(pub_file, "r", encoding="utf-8") as f:
                pub_hex = f.read().strip()

            # 2. Test CLI sign-card
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = attestation.main([
                    "sign-card",
                    "--agent", "cli_agent",
                    "--capabilities", "code_exec,sql_query",
                    "--key", priv_file,
                    "--node-id", "201",
                    "--ttl", "1800",
                    "--out", card_file,
                ])
            self.assertEqual(code, 0)
            self.assertTrue(os.path.isfile(card_file))

            with open(card_file, "r", encoding="utf-8") as f:
                card_data = json.load(f)
            self.assertEqual(card_data["agent_name"], "cli_agent")

            # 3. Test CLI verify-card (Valid)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = attestation.main(["verify-card", "--card", card_file, "--key", pub_file])
            self.assertEqual(code, 0)
            self.assertIn('"valid": true', stdout.getvalue())

            # Test CLI verify-card with invalid JSON
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = attestation.main(["verify-card", "--card", "not_valid_json"])
            self.assertEqual(code, 1)
            self.assertIn('"valid": false', stdout.getvalue())

            # 4. Test CLI negotiate (Success)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = attestation.main([
                    "negotiate",
                    "--card", card_file,
                    "--required", "code_exec",
                    "--key", pub_file,
                ])
            self.assertEqual(code, 0)
            self.assertIn('"authenticated": true', stdout.getvalue())

            # 5. Test CLI negotiate (Missing capability)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = attestation.main([
                    "negotiate",
                    "--card", card_file,
                    "--required", "root_admin",
                    "--key", pub_file,
                ])
            self.assertEqual(code, 1)
            self.assertIn('"authenticated": false', stdout.getvalue())

            # Test CLI negotiate with invalid JSON
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = attestation.main([
                    "negotiate",
                    "--card", "bad_json",
                    "--required", "code_exec",
                ])
            self.assertEqual(code, 1)
            self.assertIn('"authenticated": false', stdout.getvalue())

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestA2AAttestation)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
