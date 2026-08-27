#!/usr/bin/env python3
# AI-hint: Unit and integration tests for Composefs image descriptor and fs-verity integrity verification.
# AI-related: usr/libexec/mios/sec/composefs_verify.py, usr/share/doc/mios/manual/sec.md
"""Unit and integration test suite for ComposefsVerifier and CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "sec", "composefs_verify.py")

spec = importlib.util.spec_from_file_location("composefs_verify", _TARGET_PATH)
if spec and spec.loader:
    composefs_verify = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = composefs_verify
    spec.loader.exec_module(composefs_verify)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestComposefsVerify(unittest.TestCase):
    """Test suite for Composefs headers, fs-verity Merkle trees, and prepare-root configuration."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="mios-test-cfs-")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_parse_header_valid_magic_bytes(self):
        verifier = composefs_verify.ComposefsVerifier(mock=True)
        # Valid header with LE magic
        valid_hdr = struct.pack("<IHHQQ", composefs_verify.COMPOSEFS_MAGIC_LE, 1, 0, 4096, 1048576) + (b"\x00" * 36)
        res = verifier.parse_header(valid_hdr)
        self.assertTrue(res["valid"])
        self.assertEqual(res["version"], 1)

    def test_parse_header_alt_magic_bytes(self):
        verifier = composefs_verify.ComposefsVerifier(mock=True)
        alt_hdr = b"cfs\x00" + struct.pack("<HHQQ", 1, 0, 4096, 1048576) + (b"\x00" * 36)
        res = verifier.parse_header(alt_hdr)
        self.assertTrue(res["valid"])

    def test_parse_header_invalid_magic_returns_invalid(self):
        verifier = composefs_verify.ComposefsVerifier(mock=True)
        bad_hdr = b"BADMAGIC12345678" + (b"\x00" * 48)
        res = verifier.parse_header(bad_hdr)
        self.assertFalse(res["valid"])
        self.assertIn("Invalid magic", res["error"])

    def test_parse_header_too_short_returns_invalid(self):
        verifier = composefs_verify.ComposefsVerifier(mock=True)
        short_hdr = b"SHORT"
        res = verifier.parse_header(short_hdr)
        self.assertFalse(res["valid"])
        self.assertIn("Header too short", res["error"])

    def test_compute_fsverity_digest_mock_and_real_file(self):
        verifier = composefs_verify.ComposefsVerifier(mock=True)
        # Mock path
        digest = verifier.compute_fsverity_digest("/ostree/deploy/mock.img")
        self.assertEqual(len(digest), 64)

        # Real file
        real_img = os.path.join(self.temp_dir.name, "test.img")
        with open(real_img, "wb") as f:
            f.write(b"\x00" * 8192)

        v_real = composefs_verify.ComposefsVerifier(mock=False)
        real_digest = v_real.compute_fsverity_digest(real_img)
        self.assertEqual(len(real_digest), 64)

    def test_check_prepare_root_config_mock(self):
        verifier = composefs_verify.ComposefsVerifier(mock=True)
        res = verifier.check_prepare_root_config("/usr/lib/ostree/prepare-root.conf")
        self.assertTrue(res["composefs_enabled"])
        self.assertEqual(res["composefs_mode"], "verity")
        self.assertTrue(res["strict_integrity"])

    def test_check_prepare_root_config_real_file(self):
        conf_path = os.path.join(self.temp_dir.name, "prepare-root.conf")
        with open(conf_path, "w", encoding="utf-8") as f:
            f.write("[composefs]\nenabled = verity\n")

        v_real = composefs_verify.ComposefsVerifier(mock=False)
        res = v_real.check_prepare_root_config(conf_path)
        self.assertTrue(res["composefs_enabled"])
        self.assertEqual(res["composefs_mode"], "verity")

    def test_verify_rootfs_integrity_mock(self):
        verifier = composefs_verify.ComposefsVerifier(mock=True)
        res = verifier.verify_rootfs_integrity(image_path="/ostree/mock.img")
        self.assertEqual(res["status"], "pass")
        self.assertTrue(res["header_valid"])
        self.assertTrue(res["signature_valid"])
        self.assertEqual(res["composefs_mode"], "verity")

    def test_cli_execution_header_check(self):
        test_args = [
            "composefs_verify.py",
            "--header-check",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = composefs_verify.main()
            self.assertEqual(exit_code, 0)

    def test_cli_execution_compute_digest(self):
        test_args = [
            "composefs_verify.py",
            "--compute-digest",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = composefs_verify.main()
            self.assertEqual(exit_code, 0)

    def test_cli_execution_check_config(self):
        test_args = [
            "composefs_verify.py",
            "--check-config",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = composefs_verify.main()
            self.assertEqual(exit_code, 0)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestComposefsVerify)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
