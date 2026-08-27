#!/usr/bin/env python3
# AI-hint: Unit and integration tests for SLSA Level 3 build provenance generator and DSSE envelope signer.
# AI-related: usr/libexec/mios/sec/slsa_provenance.py, usr/share/doc/mios/manual/sec.md
"""Unit and integration test suite for SlsaProvenanceEngine and CLI."""

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
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "sec", "slsa_provenance.py")

spec = importlib.util.spec_from_file_location("slsa_provenance", _TARGET_PATH)
if spec and spec.loader:
    slsa_provenance = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = slsa_provenance
    spec.loader.exec_module(slsa_provenance)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestSlsaProvenance(unittest.TestCase):
    """Test suite for SLSA v1 provenance statements, artifact hashing, and DSSE envelope verification."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="mios-test-slsa-")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_compute_artifact_hash_real_file(self):
        test_file = os.path.join(self.temp_dir.name, "sample_build.raw")
        with open(test_file, "wb") as f:
            f.write(b"SAMPLE-BUILD-ARTIFACT-DATA-12345")

        engine = slsa_provenance.SlsaProvenanceEngine(mock=False)
        digest = engine.compute_artifact_hash(test_file)
        self.assertEqual(len(digest), 64)

    def test_generate_statement_schema_compliance(self):
        engine = slsa_provenance.SlsaProvenanceEngine(mock=True)
        stmt = engine.generate_statement(
            artifact_path="build/mios-bootc.raw",
            builder_id="https://github.com/mios-dev/mios/.github/workflows/build-bootc.yml@refs/heads/main",
            source_repo="https://github.com/mios-dev/mios",
            commit_sha="a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
        )

        self.assertEqual(stmt["_type"], "https://in-toto.io/Statement/v1")
        self.assertEqual(stmt["predicateType"], "https://slsa.dev/provenance/v1")
        self.assertEqual(len(stmt["subject"]), 1)
        self.assertEqual(stmt["subject"][0]["name"], "mios-bootc.raw")
        self.assertIn("sha256", stmt["subject"][0]["digest"])

        pred = stmt["predicate"]
        self.assertEqual(pred["buildDefinition"]["buildType"], "https://mios.dev/builds/bootc-bib/v1")
        self.assertEqual(pred["runDetails"]["builder"]["id"], "https://github.com/mios-dev/mios/.github/workflows/build-bootc.yml@refs/heads/main")

    def test_verify_statement_matching_and_mismatching_artifacts(self):
        test_file = os.path.join(self.temp_dir.name, "target_image.img")
        with open(test_file, "wb") as f:
            f.write(b"IMAGE-CONTENT-AAA")

        engine = slsa_provenance.SlsaProvenanceEngine(mock=False)
        stmt = engine.generate_statement(
            artifact_path=test_file,
            builder_id="https://github.com/mios-dev/mios/builder",
            source_repo="https://github.com/mios-dev/mios",
            commit_sha="1111222233334444555566667777888899990000",
        )

        # 1. Match verification
        ver_ok = engine.verify_statement(
            statement=stmt,
            artifact_path=test_file,
            expected_builder="https://github.com/mios-dev/mios/builder",
            expected_source="https://github.com/mios-dev/mios",
        )
        self.assertTrue(ver_ok["valid"])
        self.assertTrue(ver_ok["digest_matched"])

        # 2. Tampered file mismatch
        tampered_file = os.path.join(self.temp_dir.name, "tampered.img")
        with open(tampered_file, "wb") as f:
            f.write(b"TAMPERED-CONTENT-BBB")

        ver_tampered = engine.verify_statement(
            statement=stmt,
            artifact_path=tampered_file,
        )
        self.assertFalse(ver_tampered["valid"])
        self.assertIn("mismatch", ver_tampered["error"])

    def test_sign_and_verify_dsse_envelope(self):
        engine = slsa_provenance.SlsaProvenanceEngine(mock=True)
        stmt = engine.generate_statement("build/mios.raw")
        envelope = engine.sign_envelope(stmt)

        self.assertEqual(envelope["payloadType"], "application/vnd.in-toto+json")
        self.assertIn("payload", envelope)
        self.assertEqual(len(envelope["signatures"]), 1)

        # Verify envelope
        self.assertTrue(engine.verify_envelope(envelope))

    def test_cli_execution_generate(self):
        test_args = [
            "slsa_provenance.py",
            "--generate",
            "--artifact", "build/mios-bootc.raw",
            "--sign",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = slsa_provenance.main()
            self.assertEqual(exit_code, 0)

    def test_cli_execution_verify(self):
        test_args = [
            "slsa_provenance.py",
            "--verify",
            "--artifact", "build/mios-bootc.raw",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = slsa_provenance.main()
            self.assertEqual(exit_code, 0)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSlsaProvenance)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
