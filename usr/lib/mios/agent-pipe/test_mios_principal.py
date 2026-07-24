# AI-hint: Unit test suite for mios_pipe.identity.principal module (signed A2A delegation principal).
# AI-related: mios_pipe/identity/principal.py
"""Unit tests for mios_pipe.identity.principal."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from mios_pipe.identity.principal import text_digest, build_claims, build_metadata, verify, TABLE, METADATA_KEY


class TestPrincipal(unittest.TestCase):
    """Test signed A2A delegation principal claims and digests."""

    def test_text_digest_sha256(self):
        digest = text_digest("run diagnostic task")
        self.assertIsInstance(digest, str)
        self.assertEqual(len(digest), 64)
        empty_digest = text_digest("")
        self.assertEqual(len(empty_digest), 64)

    def test_build_claims(self):
        claims = build_claims(
            agent="opencode",
            principal="operator",
            peer_id="node_42",
            context_id="ctx_101",
            text="execute command"
        )
        self.assertEqual(claims["agent"], "opencode")
        self.assertEqual(claims["principal"], "operator")
        self.assertEqual(claims["peer"], "node_42")
        self.assertEqual(claims["context"], "ctx_101")
        self.assertEqual(claims["text_sha256"], text_digest("execute command"))

    def test_build_metadata_unsigned(self):
        mock_sign = lambda table, claims: None
        meta = build_metadata(
            agent="opencode",
            principal="operator",
            peer_id="node_42",
            context_id="ctx_101",
            text="execute command",
            sign_fn=mock_sign,
        )
        self.assertEqual(meta["claims"]["agent"], "opencode")
        self.assertIsNone(meta["passport"])

    def test_verify_absent_metadata(self):
        verdict, reason, claims = verify(None, "text", verify_fn=lambda p, c: (True, "ok"))
        self.assertIsNone(verdict)
        self.assertEqual(reason, "absent")


if __name__ == "__main__":
    unittest.main()
