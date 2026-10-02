#!/usr/bin/env python3
# AI-hint: Automated unit test suite for A/B UKI staging and systemd-ukify compilation pipeline (T-507).
# AI-doc: usr/share/doc/mios/manual/ch08-bootloader-and-unified-kernel-images-uki.md
"""Unit fixtures use an EXPLICIT fake compiler (MIOS_UKIFY_BIN) or --simulate;
nothing here depends on whether the host has ukify. The real compiler is
validated separately, on a real kernel, and that one case is a registered
skip (exit 77, [ci.tool_skips]) when ukify, its EFI stub or a kernel is absent
-- never a pass."""
from __future__ import annotations

import glob
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
_HOST_ENTRY = "/boot/loader/entries/mios-next.conf"
_EXIT_SKIP = 77


def _env(**extra: str) -> dict[str, str]:
    """The host's MIOS_* (MIOS_UKIFY_BIN above all) never reaches the stager."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("MIOS_")}
    env.update(extra)
    return env


def _real_uki_inputs() -> tuple[str, str, str] | None:
    """(ukify, stub, kernel) when this host can build a real UKI, else None."""
    ukify = shutil.which("ukify")
    stubs = glob.glob("/usr/lib/systemd/boot/efi/linux*.efi.stub")
    kernels = sorted(glob.glob("/usr/lib/modules/*/vmlinuz") + glob.glob("/boot/vmlinuz-*"))
    if ukify and stubs and kernels:
        return ukify, stubs[0], kernels[-1]
    return None


class TestUkifyStage(unittest.TestCase):
    """Validates A/B UKI staging and systemd-boot entry generation."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.kernel = os.path.join(self.tmpdir.name, "vmlinuz-test")
        self.initrd = os.path.join(self.tmpdir.name, "initrd-test.img")
        with open(self.kernel, "w") as f:
            f.write("mock-vmlinuz\n")
        with open(self.initrd, "w") as f:
            f.write("mock-initrd\n")
        self.out_efi = os.path.join(self.tmpdir.name, "boot", "EFI", "Linux", "mios-next.efi")
        self.entry = os.path.join(self.tmpdir.name, "loader", "entries", "mios-next.conf")
        self.host_before = os.stat(_HOST_ENTRY).st_mtime_ns if os.path.exists(_HOST_ENTRY) else None

    def tearDown(self):
        host_after = os.stat(_HOST_ENTRY).st_mtime_ns if os.path.exists(_HOST_ENTRY) else None
        self.tmpdir.cleanup()
        self.assertEqual(self.host_before, host_after, "a stage test wrote the HOST loader entry")

    def _stage(self, *extra: str, env: dict[str, str], kernel: str | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [*_UKIFY_STAGE_CMD, "--root", _ROOT, "--loader-entry", self.entry, "--output", self.out_efi,
             "--kernel", kernel or self.kernel, "--initrd", self.initrd,
             "--cmdline", "console=tty0 root=UUID=123 rw", "--json", *extra],
            capture_output=True, text=True, env=env, timeout=120)

    def _no_ukify_path(self) -> str:
        """A PATH holding only the interpreter -- no ukify, whatever the host has."""
        bindir = os.path.join(self.tmpdir.name, "bin")
        os.makedirs(bindir, exist_ok=True)
        py = os.path.join(bindir, "python3")
        if not os.path.exists(py):
            os.symlink(sys.executable, py)
        return bindir

    def test_binary_exists(self):
        self.assertTrue(os.path.isfile(_UKIFY_STAGE_BIN), f"Missing {_UKIFY_STAGE_BIN}")
        self.assertTrue(os.access(_UKIFY_STAGE_BIN, os.X_OK) or sys.platform == "win32", f"Not executable: {_UKIFY_STAGE_BIN}")

    def test_dry_run_json(self):
        res = subprocess.run(
            [*_UKIFY_STAGE_CMD, "--dry-run", "--json", "--root", _ROOT],  # the repo tree, not the host
            capture_output=True, text=True, check=True, env=_env())
        data = json.loads(res.stdout)
        self.assertEqual(data.get("status"), "success")
        self.assertTrue(data.get("dry_run"))
        with open(os.path.join(_ROOT, "usr", "lib", "kernel", "cmdline"), encoding="utf-8") as fh:
            self.assertEqual(data["baked_kargs"], fh.read().strip())
        self.assertIn("console=tty0", data["baked_kargs"])

    def test_stage_execution_with_explicit_fake_compiler(self):
        fake_ukify = os.path.join(self.tmpdir.name, "fake_ukify.py")
        with open(fake_ukify, "w", encoding="utf-8") as f:
            f.write(
                "import sys\n"
                "args = sys.argv[1:]\n"
                "assert args[0] == 'build', args\n"
                "for arg in args:\n"
                "    if arg.startswith('--output='):\n"
                "        with open(arg.split('=', 1)[1], 'w', encoding='utf-8') as fh:\n"
                "            fh.write('MZ-FAKE-UKIFY\\n' + '\\n'.join(args) + '\\n')\n"
            )
        res = self._stage(env=_env(MIOS_UKIFY_BIN=fake_ukify))
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        data = json.loads(res.stdout)
        self.assertEqual(data.get("status"), "success")
        self.assertTrue(data.get("ukify_executed"))
        self.assertTrue(os.path.isfile(self.entry), f"Missing loader entry at {self.entry}")
        with open(self.out_efi, "r", encoding="utf-8") as f:
            built = f.read()
        self.assertTrue(built.startswith("MZ-FAKE-UKIFY"))
        self.assertIn(f"--linux={self.kernel}", built)
        self.assertIn("--cmdline=console=tty0 root=UUID=123 rw", built)

    def test_stage_execution_simulate_is_explicit(self):
        res = self._stage("--simulate", env=_env(PATH=self._no_ukify_path()))
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        data = json.loads(res.stdout)
        self.assertTrue(data.get("simulated"))
        self.assertFalse(data.get("ukify_executed"))
        with open(self.out_efi, "rb") as f:
            self.assertIn(b"MZ-SIMULATED-UKI", f.read(32))

    def test_negative_missing_compiler_is_an_error(self):
        """Pre-fix, no ukify meant a SIMULATED UKI reported as success with a loader entry."""
        res = self._stage(env=_env(PATH=self._no_ukify_path()))
        self.assertEqual(res.returncode, 1, res.stdout)
        data = json.loads(res.stdout)
        self.assertEqual(data.get("status"), "error")
        self.assertIn("ukify not found", data.get("error", ""))
        self.assertFalse(os.path.exists(self.out_efi), "a placeholder EFI was staged")
        self.assertFalse(os.path.exists(self.entry), "a loader entry points at no real UKI")

    def test_negative_missing_kernel_is_an_error(self):
        res = self._stage(env=_env(MIOS_UKIFY_BIN=sys.executable),
                          kernel=os.path.join(self.tmpdir.name, "no-such-vmlinuz"))
        self.assertEqual(res.returncode, 1, res.stdout)
        self.assertIn("kernel/initrd not found", json.loads(res.stdout).get("error", ""))
        self.assertFalse(os.path.exists(self.entry))

    def test_negative_unrunnable_compiler_is_an_error(self):
        res = self._stage(env=_env(MIOS_UKIFY_BIN=os.path.join(self.tmpdir.name, "no-such-ukify")))
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("ukify could not run", json.loads(res.stdout).get("error", ""))
        self.assertFalse(os.path.exists(self.entry))

    @unittest.skipUnless(_real_uki_inputs(), "real UKI build needs ukify, a systemd-boot EFI stub and a kernel")
    def test_real_ukify_builds_a_pe_uki(self):
        ukify, stub, kernel = _real_uki_inputs()
        res = self._stage(env=_env(MIOS_UKIFY_BIN=ukify), kernel=kernel)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        with open(self.out_efi, "rb") as f:
            pe = f.read()
        self.assertEqual(pe[:2], b"MZ", "not a PE image")
        for section in (b".linux", b".initrd", b".cmdline"):
            self.assertIn(section, pe, f"UKI lacks {section.decode()}")
        self.assertIn(b"console=tty0 root=UUID=123 rw", pe)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUkifyStage)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        return 1
    if result.skipped:
        print("[test-ukify-stage] SKIP real-compiler tier: " + "; ".join(r for _, r in result.skipped))
        return _EXIT_SKIP
    return 0


if __name__ == "__main__":
    sys.exit(main())
