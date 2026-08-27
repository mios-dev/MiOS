#!/usr/bin/env python3
# AI-hint: Unit and integration tests for Cosign container signature verification and policy.json auditing.
# AI-related: usr/libexec/mios/sec/cosign_verify.py, usr/share/doc/mios/manual/sec.md
"""Unit and integration test suite for CosignVerifier and CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "sec", "cosign_verify.py")

spec = importlib.util.spec_from_file_location("cosign_verify", _TARGET_PATH)
if spec and spec.loader:
    cosign_verify = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = cosign_verify
    spec.loader.exec_module(cosign_verify)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestCosignVerify(unittest.TestCase):
    """Test suite for Cosign OCI container image signatures, Rekor proofs, and policy.json rules."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="mios-test-cosign-")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_verify_image_signature_valid_image(self):
        verifier = cosign_verify.CosignVerifier(mock=True)
        res = verifier.verify_image_signature("ghcr.io/mios-dev/mios:latest")
        self.assertTrue(res["valid"])
        self.assertEqual(res["image_ref"], "ghcr.io/mios-dev/mios:latest")
        self.assertIn("sha256:", res["digest"])

    def test_verify_image_signature_unsigned_tampered_rejected(self):
        verifier = cosign_verify.CosignVerifier(mock=True)
        res_unsigned = verifier.verify_image_signature("ghcr.io/untrusted/unsigned-image:latest")
        self.assertFalse(res_unsigned["valid"])

        res_tampered = verifier.verify_image_signature("ghcr.io/mios-dev/tampered-payload:v1")
        self.assertFalse(res_tampered["valid"])

    def test_verify_rekor_inclusion_bundle_dict(self):
        verifier = cosign_verify.CosignVerifier(mock=True)
        bundle = {
            "Payload": {
                "logIndex": 987654,
                "integratedTime": 1724670000,
            },
            "rekor_verified": True,
        }
        self.assertTrue(verifier.verify_rekor_inclusion(bundle))

    def test_audit_policy_json_mock_strict(self):
        verifier = cosign_verify.CosignVerifier(mock=True)
        res = verifier.audit_policy_json("/etc/containers/policy.json")
        self.assertTrue(res["policy_strict"])
        self.assertEqual(res["insecure_rules_detected"], 0)

    def test_audit_policy_json_detects_insecure_accept_anything(self):
        insecure_policy = {
            "default": [{"type": "insecureAcceptAnything"}],
            "transports": {
                "docker": {
                    "ghcr.io/untrusted": [{"type": "insecureAcceptAnything"}]
                }
            }
        }
        pol_path = os.path.join(self.temp_dir.name, "insecure_policy.json")
        with open(pol_path, "w", encoding="utf-8") as f:
            json.dump(insecure_policy, f)

        v_real = cosign_verify.CosignVerifier(mock=False)
        res = v_real.audit_policy_json(pol_path)
        self.assertFalse(res["policy_strict"])
        self.assertEqual(res["insecure_rules_detected"], 2)
        self.assertIn("default", res["insecure_scopes"])
        self.assertIn("docker:ghcr.io/untrusted", res["insecure_scopes"])

    def test_evaluate_upgrade_safety_pass_and_fail(self):
        verifier = cosign_verify.CosignVerifier(mock=True)
        res_pass = verifier.evaluate_upgrade_safety("ghcr.io/mios-dev/mios:latest")
        self.assertEqual(res_pass["status"], "pass")
        self.assertTrue(res_pass["signature_valid"])
        self.assertTrue(res_pass["rekor_verified"])

        res_fail = verifier.evaluate_upgrade_safety("ghcr.io/malicious/rootkit:latest")
        self.assertEqual(res_fail["status"], "fail")

    def test_cli_execution_verify_signature(self):
        test_args = [
            "cosign_verify.py",
            "--verify-signature",
            "--image", "ghcr.io/mios-dev/mios:latest",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = cosign_verify.main()
            self.assertEqual(exit_code, 0)

    def test_cli_execution_audit_policy(self):
        test_args = [
            "cosign_verify.py",
            "--audit-policy",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = cosign_verify.main()
            self.assertEqual(exit_code, 0)

    def test_cli_execution_evaluate_upgrade(self):
        test_args = [
            "cosign_verify.py",
            "--evaluate-upgrade",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = cosign_verify.main()
            self.assertEqual(exit_code, 0)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCosignVerify)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
