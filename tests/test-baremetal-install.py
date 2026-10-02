#!/usr/bin/env python3
# AI-hint: Tests for the bare-metal install shim -- argument forwarding to the native mios-install and its failure when absent.
# AI-related: usr/libexec/mios/deploy/baremetal_install.py, tools/native/mios-install/src/main.rs
"""The shim's contract: forward to `mios-install disk`, map --force, fail loudly when missing."""

from __future__ import annotations

import os
import stat
import subprocess
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHIM = os.path.join(_HERE, "..", "usr", "libexec", "mios", "deploy", "baremetal_install.py")


def run_shim(args, fake):
    env = dict(os.environ)
    env["PATH"] = "/usr/bin:/bin"
    if fake:
        env["PATH"] = os.path.dirname(fake) + os.pathsep + env["PATH"]
    return subprocess.run([sys.executable, _SHIM, *args], env=env,
                          capture_output=True, text=True, check=False)


class TestBaremetalInstallShim(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.record = os.path.join(self.dir.name, "argv")
        self.fake = os.path.join(self.dir.name, "mios-install")
        with open(self.fake, "w", encoding="utf-8") as fh:
            fh.write('#!/bin/sh\nprintf "%%s\\n" "$@" > "%s"\n' % self.record)
        os.chmod(self.fake, os.stat(self.fake).st_mode | stat.S_IEXEC)

    def tearDown(self):
        self.dir.cleanup()

    def forwarded(self):
        with open(self.record, encoding="utf-8") as fh:
            return fh.read().split()

    def test_arguments_reach_mios_install_disk_unchanged(self):
        r = run_shim(["--target-disk", "/dev/nvme0n1", "--yes", "--json"], self.fake)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.forwarded(), ["disk", "--target-disk", "/dev/nvme0n1", "--yes", "--json"])

    def test_force_still_confirms_and_now_only_skips_the_uefi_check(self):
        r = run_shim(["--auto-select", "--force"], self.fake)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.forwarded(), ["disk", "--auto-select", "--yes", "--force"])

    def test_a_missing_native_binary_is_a_named_failure(self):
        r = run_shim(["--auto-select"], None)
        self.assertEqual(r.returncode, 127)
        self.assertIn("mios-install is not installed", r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
