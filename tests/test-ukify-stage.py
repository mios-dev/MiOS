#!/usr/bin/env python3
# AI-hint: Automated unit test suite for A/B UKI staging and systemd-ukify compilation pipeline (T-507).
# AI-doc: usr/share/doc/mios/manual/ch02-boot-and-lifecycle.md
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_UKIFY_STAGE_BIN = os.path.join(_ROOT, "usr", "libexec", "mios", "mios-ukify-stage")


class TestUkifyStage(unittest.TestCase):
    """Validates A/B UKI staging and systemd-boot entry generation."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_binary_exists(self):
        self.assertTrue(os.path.isfile(_UKIFY_STAGE_BIN), f"Missing {_UKIFY_STAGE_BIN}")
        self.assertTrue(os.access(_UKIFY_STAGE_BIN, os.X_OK), f"Not executable: {_UKIFY_STAGE_BIN}")

    def test_dry_run_json(self):
        res = subprocess.run(
            [_UKIFY_STAGE_BIN, "--dry-run", "--json", "--root", _ROOT],  # the repo tree, not the host
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(res.stdout)
        self.assertEqual(data.get("status"), "success")
        self.assertTrue(data.get("dry_run"))
        self.assertIn("baked_kargs", data)
        self.assertIn("console=tty0", data["baked_kargs"])

    def test_stage_execution(self):
        out_efi = os.path.join(self.tmpdir.name, "boot", "EFI", "Linux", "mios-next.efi")
        mock_kernel = os.path.join(self.tmpdir.name, "vmlinuz-test")
        mock_initrd = os.path.join(self.tmpdir.name, "initrd-test.img")

        with open(mock_kernel, "w") as f:
            f.write("mock-vmlinuz\n")
        with open(mock_initrd, "w") as f:
            f.write("mock-initrd\n")

        res = subprocess.run(
            [
                _UKIFY_STAGE_BIN,
                "--output", out_efi,
                "--kernel", mock_kernel,
                "--initrd", mock_initrd,
                "--cmdline", "console=tty0 root=UUID=123 rw",
                "--json",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(res.stdout)
        self.assertEqual(data.get("status"), "success")
        self.assertTrue(os.path.isfile(out_efi), f"Missing staged EFI at {out_efi}")

        # Verify EFI content carries simulated header or ukify binary
        with open(out_efi, "rb") as f:
            hdr = f.read(32)
        self.assertTrue(len(hdr) > 0)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUkifyStage)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
