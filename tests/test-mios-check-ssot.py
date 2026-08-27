#!/usr/bin/env python3
# AI-hint: Test suite for T-398: Rust SSOT mios.toml validator (mios check / miosd check).
# AI-related: usr/share/mios/mios.toml, src/mios-rs/mios-config/src/validator.rs

import pathlib
import subprocess
import tempfile
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent

class TestMiosCheckSSOT(unittest.TestCase):
    def test_real_ssot_toml_validity(self):
        """Verify that live SSOT usr/share/mios/mios.toml passes validation cleanly."""
        ssot_file = ROOT / "usr/share/mios/mios.toml"
        self.assertTrue(ssot_file.is_file(), f"SSOT file missing at {ssot_file}")

        cmd = [
            "wsl", "-u", "root", "-d", "podman-MiOS-DEV", "--",
            "bash", "-c", "cd /mnt/c/MiOS/src/mios-rs && cargo test -p mios-config --lib -- validator"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(
            res.returncode, 0,
            f"Cargo test for mios-config validator failed:\nstdout: {res.stdout}\nstderr: {res.stderr}"
        )
        self.assertIn("test validator::tests::test_valid_ssot_toml ... ok", res.stdout)
        self.assertIn("test validator::tests::test_port_collision_detection ... ok", res.stdout)
        self.assertIn("test validator::tests::test_law7_empty_string_rejection ... ok", res.stdout)
        self.assertIn("test validator::tests::test_ratchet_violation ... ok", res.stdout)

    def test_negative_port_collision_detection(self):
        """Verify that duplicate port assignments in [ports] are detected and reported."""
        sample_toml = """
[meta]
mios_version = "0.3.0"
fedora_version = "44"

[identity]
username = "mios"
fullname = "MiOS Operator"
hostname = "mios"
shell = "/bin/bash"

[ports]
service_alpha = 9090
service_beta = 9090
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(sample_toml)
            temp_path = f.name

        try:
            # Run miosd check on the invalid temp file
            wsl_path = f"/mnt/c/{temp_path.replace('C:\\', '').replace('\\', '/')}"
            cmd = [
                "wsl", "-u", "root", "-d", "podman-MiOS-DEV", "--",
                "bash", "-c", f"cd /mnt/c/MiOS/src/mios-rs && cargo run -p miosd -- check {wsl_path}"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(res.returncode, 0, "Validator should fail on port collision")
            self.assertIn("Port Collision", res.stdout + res.stderr)
        finally:
            pathlib.Path(temp_path).unlink(missing_ok=True)

    def test_negative_law7_empty_string_rejection(self):
        """Verify that empty string literals in critical configuration sections are rejected under Law 7."""
        sample_toml = """
[meta]
mios_version = ""
fedora_version = "44"

[identity]
username = "   "
fullname = "MiOS Operator"
hostname = "mios"
shell = "/bin/bash"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(sample_toml)
            temp_path = f.name

        try:
            wsl_path = f"/mnt/c/{temp_path.replace('C:\\', '').replace('\\', '/')}"
            cmd = [
                "wsl", "-u", "root", "-d", "podman-MiOS-DEV", "--",
                "bash", "-c", f"cd /mnt/c/MiOS/src/mios-rs && cargo run -p miosd -- check {wsl_path}"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(res.returncode, 0, "Validator should fail on empty string literal")
            self.assertIn("Law 7 Violation", res.stdout + res.stderr)
        finally:
            pathlib.Path(temp_path).unlink(missing_ok=True)

if __name__ == "__main__":
    unittest.main()
