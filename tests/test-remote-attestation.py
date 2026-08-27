#!/usr/bin/env python3
# AI-hint: Unit and integration tests for TPM2 remote attestation quote generator and report verifier.
# AI-related: usr/libexec/mios/sec/remote_attestation.py, usr/share/doc/mios/manual/sec.md
"""Unit and integration test suite for RemoteAttestationEngine and CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "sec", "remote_attestation.py")

spec = importlib.util.spec_from_file_location("remote_attestation", _TARGET_PATH)
if spec and spec.loader:
    remote_attestation = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = remote_attestation
    spec.loader.exec_module(remote_attestation)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestRemoteAttestation(unittest.TestCase):
    """Test suite for TPM2 quotes, nonces, report generation, and peer measurement verification."""

    def test_generate_tpm2_quote_mock(self):
        engine = remote_attestation.RemoteAttestationEngine(mock=True)
        quote = engine.generate_tpm2_quote(pcr_list=[0, 7, 11, 14], nonce="aabbccddeeff0011")
        self.assertEqual(quote["pcr_list"], [0, 7, 11, 14])
        self.assertEqual(quote["nonce"], "aabbccddeeff0011")
        self.assertEqual(len(quote["pcrs"]), 4)
        self.assertIn("pcr_digest", quote)
        self.assertIn("quote_signature", quote)

    def test_build_report_schema(self):
        engine = remote_attestation.RemoteAttestationEngine(mock=True)
        rep = engine.build_report(node_id="test-node-01", pcr_list=[0, 7, 11, 14], nonce="1234567890abcdef")
        self.assertEqual(rep["version"], "1.0")
        self.assertEqual(rep["node_id"], "test-node-01")
        self.assertIn("quote", rep)
        self.assertIn("kernel_release", rep)
        self.assertIn("uki_hash", rep)

    def test_verify_report_matching_golden_pcrs(self):
        engine = remote_attestation.RemoteAttestationEngine(mock=True)
        rep = engine.build_report(node_id="node-a", pcr_list=[0, 7, 11, 14], nonce="nonce-123")

        golden = rep["quote"]["pcrs"]
        res = engine.verify_report(report=rep, golden_pcrs=golden, expected_nonce="nonce-123")
        self.assertTrue(res["valid"])
        self.assertEqual(res["status"], "verified")
        self.assertTrue(res["nonce_valid"])
        self.assertTrue(res["pcr_measurements_valid"])

    def test_verify_report_nonce_mismatch_rejected(self):
        engine = remote_attestation.RemoteAttestationEngine(mock=True)
        rep = engine.build_report(node_id="node-a", nonce="nonce-AAA")

        res = engine.verify_report(report=rep, expected_nonce="nonce-BBB")
        self.assertFalse(res["valid"])
        self.assertEqual(res["status"], "rejected")
        self.assertIn("Nonce challenge mismatch", res["error"])

    def test_verify_report_pcr_mismatch_rejected(self):
        engine = remote_attestation.RemoteAttestationEngine(mock=True)
        rep = engine.build_report(node_id="node-a", nonce="nonce-123")

        # Golden expectation differing from quote
        golden = dict(rep["quote"]["pcrs"])
        golden["7"] = "0000000000000000000000000000000000000000000000000000000000000000"

        res = engine.verify_report(report=rep, golden_pcrs=golden, expected_nonce="nonce-123")
        self.assertFalse(res["valid"])
        self.assertEqual(res["status"], "rejected")
        self.assertIn("PCR baseline mismatch", res["error"])

    def test_cli_execution_generate_quote(self):
        test_args = [
            "remote_attestation.py",
            "--generate-quote",
            "--pcr-list", "0,7,11,14",
            "--nonce", "deadbeef12345678",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = remote_attestation.main()
            self.assertEqual(exit_code, 0)

    def test_cli_execution_verify_quote(self):
        test_args = [
            "remote_attestation.py",
            "--verify-quote",
            "--node-id", "test-node-99",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = remote_attestation.main()
            self.assertEqual(exit_code, 0)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRemoteAttestation)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
