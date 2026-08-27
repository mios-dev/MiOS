#!/usr/bin/env python3
# AI-hint: Unit and integration tests for storage health, 4K block alignment, and fake flash detection.
# AI-related: usr/libexec/mios/deploy/storage_verify.py, usr/share/mios/mios.toml, usr/libexec/mios/deploy/usb_format.py
"""Unit and integration test suite for StorageVerifierEngine and CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "deploy", "storage_verify.py")

spec = importlib.util.spec_from_file_location("storage_verify", _TARGET_PATH)
if spec and spec.loader:
    storage_verify = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = storage_verify
    spec.loader.exec_module(storage_verify)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestStorageVerify(unittest.TestCase):
    """Test suite for partition 4K/1MB alignment math, block SHA-256 digest comparison, fake capacity probe, and CLI."""

    def test_verify_partition_alignment_mock(self):
        engine = storage_verify.StorageVerifierEngine(device="/dev/sdb", mock=True)
        report = engine.verify_partition_alignment()

        self.assertEqual(report.total_partitions, 2)
        self.assertTrue(report.all_4k_aligned)
        self.assertTrue(report.all_1mb_aligned)
        self.assertEqual(report.partitions[0].start_sector, 2048)
        self.assertEqual(report.partitions[1].start_sector, 4194304)

    def test_verify_block_digest_mock(self):
        engine = storage_verify.StorageVerifierEngine(
            device="/dev/sdb",
            source_image="dummy_source.iso",
            mock=True,
        )
        digest_res = engine.verify_block_digest()
        self.assertEqual(digest_res["status"], "match")
        self.assertTrue(digest_res["verified"])
        self.assertEqual(digest_res["source_sha256"], digest_res["target_sha256"])

    def test_detect_fake_capacity_mock(self):
        engine = storage_verify.StorageVerifierEngine(
            device="/dev/sdb",
            check_fake_flash=True,
            destructive=True,
            mock=True,
        )
        fc_report = engine.detect_fake_capacity()
        self.assertFalse(fc_report.is_counterfeit)
        self.assertEqual(fc_report.reported_capacity_gb, 32.0)
        self.assertEqual(fc_report.verified_capacity_gb, 32.0)
        self.assertEqual(len(fc_report.failed_offsets_gb), 0)

    def test_run_mock_complete(self):
        engine = storage_verify.StorageVerifierEngine(
            device="/dev/sdb",
            source_image="source.iso",
            verify_alignment=True,
            check_fake_flash=True,
            mock=True,
        )
        res = engine.run()
        self.assertEqual(res["status"], "success")
        self.assertIn("alignment", res)
        self.assertIn("digest", res)
        self.assertIn("fake_capacity", res)

    def test_cli_execution_mock_json(self):
        test_args = [
            "storage_verify.py",
            "--device", "/dev/sdb",
            "--source-image", "test.iso",
            "--check-fake-flash",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = storage_verify.main()
            self.assertEqual(exit_code, 0)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestStorageVerify)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
