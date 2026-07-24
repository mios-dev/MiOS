# AI-hint: Unit test suite for mios_pipe.federation.agentcard_sign module.
# AI-related: mios_pipe/federation/agentcard_sign.py
"""Unit tests for mios_pipe.federation.agentcard_sign."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from mios_pipe.federation.agentcard_sign import (
    _b64u,
    _b64u_decode,
    _jcs_canonicalize,
    _agent_card_signing_input,
    _agent_card_signature,
    _verify_agent_card_signature,
)


class TestAgentCardSign(unittest.TestCase):
    """Test JCS canonicalization and JWS agentcard signature generation/verification."""

    def test_b64u_roundtrip(self):
        data = b"hello world 123 !@#"
        encoded = _b64u(data)
        self.assertNotIn("=", encoded)
        decoded = _b64u_decode(encoded)
        self.assertEqual(decoded, data)

    def test_jcs_canonicalize(self):
        card = {"name": "MiOS Agent", "version": "1.0", "active": True, "count": 5}
        canonical = _jcs_canonicalize(card)
        self.assertIsInstance(canonical, bytes)
        self.assertIn(b'"active":true', canonical)
        self.assertIn(b'"name":"MiOS Agent"', canonical)

    def test_card_sign_and_verify_roundtrip(self):
        try:
            from cryptography.hazmat.primitives.asymmetric import ed25519
            priv = ed25519.Ed25519PrivateKey.generate()
            pub = priv.public_key()
        except ImportError:
            self.skipTest("cryptography library not installed")

        card = {
            "name": "TestAgent",
            "url": "http://localhost:8640",
            "skills": [{"id": "code", "description": "coding assistant"}],
        }

        mock_load_priv = lambda: priv
        mock_kid = lambda: "test_kid_01"

        sig_dict = _agent_card_signature(card, load_priv_fn=mock_load_priv, kid_fn=mock_kid)
        self.assertIsInstance(sig_dict, dict)
        self.assertIn("protected", sig_dict)
        self.assertIn("signature", sig_dict)

        # Attach signature to card
        signed_card = dict(card)
        signed_card["signatures"] = [sig_dict]

        # Verify signed card (True, "ok")
        verdict, reason = _verify_agent_card_signature(signed_card, public_key=pub)
        self.assertTrue(verdict)
        self.assertEqual(reason, "ok")

        # Tamper card payload -> Verify FAILS (False, "invalid_signature")
        tampered_card = dict(signed_card)
        tampered_card["name"] = "TamperedAgent"
        tampered_verdict, tampered_reason = _verify_agent_card_signature(tampered_card, public_key=pub)
        self.assertFalse(tampered_verdict)
        self.assertEqual(tampered_reason, "invalid_signature")

    def test_verify_unsigned_card(self):
        card = {"name": "UnsignedAgent"}
        verdict, reason = _verify_agent_card_signature(card)
        self.assertIsNone(verdict)
        self.assertEqual(reason, "unsigned")


if __name__ == "__main__":
    unittest.main()
