#!/usr/bin/env python3
# AI-hint: Automated unit test suite for A/B UKI staging and systemd-ukify compilation pipeline (T-507).
# AI-doc: usr/share/doc/mios/manual/ch08-bootloader-and-unified-kernel-images-uki.md
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_UKIFY_STAGE_BIN = os.path.join(_ROOT, "usr", "libexec", "mios", "mios-ukify-stage")
_UKIFY_STAGE_CMD = [sys.executable, _UKIFY_STAGE_BIN] if sys.platform == "win32" else [_UKIFY_STAGE_BIN]


class TestUkifyStage(unittest.TestCase):
    """Validates A/B UKI staging and systemd-boot entry generation."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_binary_exists(self):
        self.assertTrue(os.path.isfile(_UKIFY_STAGE_BIN), f"Missing {_UKIFY_STAGE_BIN}")
        self.assertTrue(os.access(_UKIFY_STAGE_BIN, os.X_OK) or sys.platform == "win32", f"Not executable: {_UKIFY_STAGE_BIN}")

    def test_dry_run_json(self):
        res = subprocess.run(
            [*_UKIFY_STAGE_CMD, "--dry-run", "--json", "--root", _ROOT],  # the repo tree, not the host
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(res.stdout)
        self.assertEqual(data.get("status"), "success")
        self.assertTrue(data.get("dry_run"))
        self.assertIn("baked_kargs", data)
        with open(os.path.join(_ROOT, "usr", "lib", "kernel", "cmdline"), encoding="utf-8") as fh:
            self.assertEqual(data["baked_kargs"], fh.read().strip())
        self.assertIn("console=tty0", data["baked_kargs"])

    def test_stage_execution(self):
        out_efi = os.path.join(self.tmpdir.name, "boot", "EFI", "Linux", "mios-next.efi")
        mock_kernel = os.path.join(self.tmpdir.name, "vmlinuz-test")
        mock_initrd = os.path.join(self.tmpdir.name, "initrd-test.img")

        with open(mock_kernel, "w") as f:
            f.write("mock-vmlinuz\n")
        with open(mock_initrd, "w") as f:
            f.write("mock-initrd\n")

        fake_ukify = os.path.join(self.tmpdir.name, "fake_ukify.py")
        with open(fake_ukify, "w", encoding="utf-8") as f:
            f.write(
                "import sys\n"
                "for arg in sys.argv[1:]:\n"
                "    if arg.startswith('--output='):\n"
                "        with open(arg.split('=', 1)[1], 'w', encoding='utf-8') as fh:\n"
                "            fh.write('MZ-FAKE-UKIFY\\n')\n"
                "sys.exit(0)\n"
            )
        env = os.environ.copy()
        env["MIOS_UKIFY_BIN"] = fake_ukify

        entry = os.path.join(self.tmpdir.name, "loader", "entries", "mios-next.conf")
        host_entry = "/boot/loader/entries/mios-next.conf"
        host_before = os.stat(host_entry).st_mtime_ns if os.path.exists(host_entry) else None
        res = subprocess.run(
            [
                *_UKIFY_STAGE_CMD,
                "--root", _ROOT,
                "--loader-entry", entry,
                "--output", out_efi,
                "--kernel", mock_kernel,
                "--initrd", mock_initrd,
                "--cmdline", "console=tty0 root=UUID=123 rw",
                "--json",
            ],
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
        data = json.loads(res.stdout)
        self.assertEqual(data.get("status"), "success")
        self.assertTrue(data.get("ukify_executed"))
        self.assertTrue(os.path.isfile(out_efi), f"Missing staged EFI at {out_efi}")
        self.assertTrue(os.path.isfile(entry), f"Missing loader entry at {entry}")
        host_after = os.stat(host_entry).st_mtime_ns if os.path.exists(host_entry) else None
        self.assertEqual(host_before, host_after, "the stage test wrote the HOST loader entry")

        with open(out_efi, "rb") as f:
            hdr = f.read(32)
        self.assertIn(b"MZ-FAKE-UKIFY", hdr)

    def test_stage_execution_simulated_fallback(self):
        out_efi = os.path.join(self.tmpdir.name, "boot", "EFI", "Linux", "mios-sim.efi")
        mock_kernel = os.path.join(self.tmpdir.name, "vmlinuz-sim")
        mock_initrd = os.path.join(self.tmpdir.name, "initrd-sim.img")

        with open(mock_kernel, "w") as f:
            f.write("mock-vmlinuz\n")
        with open(mock_initrd, "w") as f:
            f.write("mock-initrd\n")

        entry = os.path.join(self.tmpdir.name, "loader", "entries", "mios-sim.conf")
        env = os.environ.copy()
        env["MIOS_UKIFY_BIN"] = ""
        res = subprocess.run(
            [
                *_UKIFY_STAGE_CMD,
                "--root", _ROOT,
                "--loader-entry", entry,
                "--output", out_efi,
                "--kernel", mock_kernel,
                "--initrd", mock_initrd,
                "--cmdline", "console=tty0 rw",
                "--json",
            ],
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
        data = json.loads(res.stdout)
        self.assertEqual(data.get("status"), "success")
        self.assertFalse(data.get("ukify_executed"))
        with open(out_efi, "rb") as f:
            hdr = f.read(32)
        self.assertIn(b"MZ-SIMULATED-UKI", hdr)

    def test_real_ukify_validation_on_suitable_inputs(self):
        real_ukify = shutil.which("ukify")
        if not real_ukify:
            self.skipTest("ukify not installed on host")
        res = subprocess.run([real_ukify, "--help"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("ukify", res.stdout.lower() + res.stderr.lower())


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUkifyStage)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
