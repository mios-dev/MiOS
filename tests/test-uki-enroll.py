#!/usr/bin/env python3
# AI-hint: Unit and integration tests for UKI Secure Boot signing and TPM2 policy sealing.
# AI-related: usr/libexec/mios/sec/uki_enroll.py, usr/share/doc/mios/manual/sec.md
"""Unit and integration test suite for UkiEnrollEngine and CLI."""

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
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "sec", "uki_enroll.py")

spec = importlib.util.spec_from_file_location("uki_enroll", _TARGET_PATH)
if spec and spec.loader:
    uki_enroll = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = uki_enroll
    spec.loader.exec_module(uki_enroll)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")


class TestUkiEnroll(unittest.TestCase):
    """Test suite for UKI signing key generation, UEFI db enrollment, and TPM2 PCR sealing."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="mios-test-uki-")
        self.key_dir = self.temp_dir.name

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_generate_signing_keys_mock(self):
        engine = uki_enroll.UkiEnrollEngine(mock=True)
        res = engine.generate_signing_keys(key_dir=self.key_dir, key_type="rsa4096")
        self.assertIn("key_path", res)
        self.assertIn("crt_path", res)
        self.assertEqual(res["key_type"], "rsa4096")
        self.assertTrue(os.path.exists(res["key_path"]))
        self.assertTrue(os.path.exists(res["crt_path"]))

        with open(res["key_path"], "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("BEGIN PRIVATE KEY", content)

    def test_generate_signing_keys_ed25519_mock(self):
        engine = uki_enroll.UkiEnrollEngine(mock=True)
        res = engine.generate_signing_keys(key_dir=self.key_dir, key_type="ed25519")
        self.assertEqual(res["key_type"], "ed25519")
        self.assertTrue(os.path.exists(res["key_path"]))

    def test_generate_signing_keys_invalid_type_raises(self):
        engine = uki_enroll.UkiEnrollEngine(mock=False)
        with self.assertRaises(ValueError):
            engine.generate_signing_keys(key_dir=self.key_dir, key_type="unsupported_cipher")

    def test_enroll_uefi_db_mock(self):
        engine = uki_enroll.UkiEnrollEngine(mock=True)
        crt_file = os.path.join(self.key_dir, "uki-signing.crt")
        self.assertTrue(engine.enroll_uefi_db(crt_file))

    def test_enroll_uefi_db_missing_file_raises(self):
        engine = uki_enroll.UkiEnrollEngine(mock=False)
        non_existent = os.path.join(self.key_dir, "non_existent.crt")
        with self.assertRaises(FileNotFoundError):
            engine.enroll_uefi_db(non_existent)

    def test_seal_and_unseal_secret_matching_pcrs(self):
        engine = uki_enroll.UkiEnrollEngine(mock=True)
        secret = b"my-super-secret-luks-passphrase"
        nv_idx = 0x1500018

        # Seal
        seal_info = engine.seal_secret_to_pcr(secret=secret, pcr_list=[7, 14], nv_index=nv_idx)
        self.assertEqual(seal_info["nv_index"], hex(nv_idx))
        self.assertEqual(seal_info["pcr_list"], [7, 14])
        self.assertIn("policy_digest", seal_info)
        self.assertIn("sealed_blob", seal_info)

        # Unseal with matching measurements
        unsealed = engine.unseal_secret_from_pcr(nv_index=nv_idx, current_pcrs=seal_info["pcr_hashes"])
        self.assertEqual(unsealed, secret)

    def test_unseal_secret_mismatched_pcrs_raises(self):
        engine = uki_enroll.UkiEnrollEngine(mock=True)
        secret = b"confidential-kernel-key"
        nv_idx = 0x1500019

        seal_info = engine.seal_secret_to_pcr(secret=secret, pcr_list=[7, 14], nv_index=nv_idx)

        # Tamper with PCR 7 measurement
        tampered_pcrs = dict(seal_info["pcr_hashes"])
        tampered_pcrs[7] = "0000000000000000000000000000000000000000000000000000000000000000"

        with self.assertRaises(PermissionError):
            engine.unseal_secret_from_pcr(nv_index=nv_idx, current_pcrs=tampered_pcrs)

    def test_unseal_missing_nv_index_raises(self):
        engine = uki_enroll.UkiEnrollEngine(mock=True)
        with self.assertRaises(RuntimeError):
            engine.unseal_secret_from_pcr(nv_index=0x9999999)

    def test_check_enrollment_status(self):
        engine = uki_enroll.UkiEnrollEngine(mock=True)
        status = engine.check_enrollment_status(key_dir=self.key_dir, nv_index=0x1500018)
        self.assertEqual(status["status"], "ok")
        self.assertTrue(status["uefi_enrolled"])
        self.assertTrue(status["tpm2_sealed"])

    def test_cli_execution_mock_json(self):
        test_args = [
            "uki_enroll.py",
            "--generate-keys",
            "--key-dir", self.key_dir,
            "--key-type", "rsa4096",
            "--enroll-uefi",
            "--seal",
            "--secret", "cli-test-secret",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = uki_enroll.main()
            self.assertEqual(exit_code, 0)

    def test_cli_execution_check_only(self):
        test_args = [
            "uki_enroll.py",
            "--check",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = uki_enroll.main()
            self.assertEqual(exit_code, 0)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUkiEnroll)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
