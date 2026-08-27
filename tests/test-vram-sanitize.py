#!/usr/bin/env python3
# AI-hint: Unit and integration tests for GPU VRAM memory sanitization and Quadlet config audit.
# AI-related: usr/libexec/mios/sec/vram_sanitize.py, usr/share/doc/mios/manual/sec.md
"""Unit and integration test suite for VramSanitizer and CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "sec", "vram_sanitize.py")

spec = importlib.util.spec_from_file_location("vram_sanitize", _TARGET_PATH)
if spec and spec.loader:
    vram_sanitize = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = vram_sanitize
    spec.loader.exec_module(vram_sanitize)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")


class TestVramSanitize(unittest.TestCase):
    """Test suite for multi-vendor GPU discovery, VRAM scrubbing, and Quadlet config audits."""

    def test_discover_gpus_mock(self):
        sanitizer = vram_sanitize.VramSanitizer(mock=True)
        gpus = sanitizer.discover_gpus()
        self.assertGreaterEqual(len(gpus), 2)
        vendors = [g["vendor"] for g in gpus]
        self.assertIn("NVIDIA", vendors)
        self.assertIn("AMD", vendors)

    def test_scrub_gpu_memory_mock(self):
        sanitizer = vram_sanitize.VramSanitizer(mock=True)
        res = sanitizer.scrub_gpu_memory(device_id=0, pattern=b"\x00")
        self.assertTrue(res["success"])
        self.assertEqual(res["device_id"], 0)
        self.assertEqual(res["pattern_used"], "0x00")

    def test_verify_memory_zeroed_mock(self):
        sanitizer = vram_sanitize.VramSanitizer(mock=True)
        self.assertTrue(sanitizer.verify_memory_zeroed(device_id=0))

    def test_audit_quadlet_configs_mock(self):
        sanitizer = vram_sanitize.VramSanitizer(mock=True)
        audit_res = sanitizer.audit_quadlet_configs()
        self.assertTrue(audit_res["audit_passed"])
        self.assertEqual(len(audit_res["findings"]), 0)

    def test_cli_execution_scrub(self):
        test_args = [
            "vram_sanitize.py",
            "--scrub",
            "--pattern", "zero",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = vram_sanitize.main()
            self.assertEqual(exit_code, 0)

    def test_cli_execution_verify(self):
        test_args = [
            "vram_sanitize.py",
            "--verify",
            "--device-id", "0",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = vram_sanitize.main()
            self.assertEqual(exit_code, 0)

    def test_cli_execution_audit_configs(self):
        test_args = [
            "vram_sanitize.py",
            "--audit-configs",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = vram_sanitize.main()
            self.assertEqual(exit_code, 0)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestVramSanitize)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
