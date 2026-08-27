#!/usr/bin/env python3
# AI-hint: Unit and integration tests for streaming OCI layer extractor and whiteout processor.
# AI-related: usr/libexec/mios/deploy/oci_extractor.py, usr/share/mios/mios.toml, usr/libexec/mios/deploy/baremetal_install.py
"""Unit and integration test suite for OciExtractorEngine and WhiteoutHandler."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "deploy", "oci_extractor.py")

spec = importlib.util.spec_from_file_location("oci_extractor", _TARGET_PATH)
if spec and spec.loader:
    oci_extractor = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = oci_extractor
    spec.loader.exec_module(oci_extractor)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestOciExtractor(unittest.TestCase):
    """Test suite for OCI layer streaming, whiteout handling (.wh.<name> and .wh..wh..opq), and CLI."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="mios-test-oci-")
        self.dest_rootfs = os.path.join(self.temp_dir.name, "rootfs")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_whiteout_handler_detection(self):
        handler = oci_extractor.WhiteoutHandler
        self.assertTrue(handler.is_whiteout("etc/.wh.deleted_file"))
        self.assertTrue(handler.is_whiteout("var/lib/.wh..wh..opq"))
        self.assertFalse(handler.is_whiteout("usr/bin/bash"))

        self.assertTrue(handler.is_opaque("var/lib/.wh..wh..opq"))
        self.assertFalse(handler.is_opaque("etc/.wh.deleted_file"))

        self.assertEqual(os.path.normpath(handler.get_target_filename("etc/.wh.deleted_file")), os.path.normpath("etc/deleted_file"))

    def test_whiteout_application_file_and_opaque(self):
        handler = oci_extractor.WhiteoutHandler
        test_root = self.dest_rootfs
        os.makedirs(os.path.join(test_root, "etc"), exist_ok=True)
        os.makedirs(os.path.join(test_root, "var", "cache"), exist_ok=True)

        # File whiteout test
        target_file = os.path.join(test_root, "etc", "old_config.conf")
        with open(target_file, "w") as f:
            f.write("old data")
        self.assertTrue(os.path.exists(target_file))

        deleted = handler.apply_file_whiteout(test_root, "etc/old_config.conf")
        self.assertTrue(deleted)
        self.assertFalse(os.path.exists(target_file))

        # Opaque whiteout test
        file1 = os.path.join(test_root, "var", "cache", "f1.dat")
        file2 = os.path.join(test_root, "var", "cache", "f2.dat")
        with open(file1, "w") as f:
            f.write("1")
        with open(file2, "w") as f:
            f.write("2")

        count = handler.apply_opaque_whiteout(test_root, "var/cache")
        self.assertEqual(count, 2)
        self.assertTrue(os.path.exists(os.path.join(test_root, "var", "cache")))
        self.assertEqual(len(os.listdir(os.path.join(test_root, "var", "cache"))), 0)

    def test_run_mock_multi_layer_whiteout_verification(self):
        engine = oci_extractor.OciExtractorEngine(dest_rootfs=self.dest_rootfs, mock=True)
        summary = engine.run()

        self.assertEqual(summary.layers_processed, 2)
        self.assertGreaterEqual(summary.total_files, 2)
        self.assertEqual(summary.total_whiteouts, 1)

        # Confirm Layer 1 file /etc/os-release exists
        os_release = os.path.join(self.dest_rootfs, "etc", "os-release")
        self.assertTrue(os.path.exists(os_release))

        # Confirm Layer 2 file /etc/mios/profile.toml exists
        profile_toml = os.path.join(self.dest_rootfs, "etc", "mios", "profile.toml")
        self.assertTrue(os.path.exists(profile_toml))

        # Confirm Layer 1 file /tmp/obsolete.txt was whited out by Layer 2
        obsolete = os.path.join(self.dest_rootfs, "tmp", "obsolete.txt")
        self.assertFalse(os.path.exists(obsolete))

    def test_cli_execution_mock_json(self):
        test_args = [
            "oci_extractor.py",
            "--dest-rootfs", self.dest_rootfs,
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = oci_extractor.main()
            self.assertEqual(exit_code, 0)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestOciExtractor)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
