#!/usr/bin/env python3
# AI-hint: Test suite for T-399: Compiled binary CLI dispatcher (/usr/bin/mios).
# AI-related: usr/bin/mios, src/mios-rs/miosd/src/cli/

import pathlib
import subprocess
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent

class TestMiosCliDispatcher(unittest.TestCase):
    def test_cli_help_and_verbs_coverage(self):
        """Verify that CLI prints help and includes all expected verbs."""
        cmd = [
            "wsl", "-u", "root", "-d", "podman-MiOS-DEV", "--",
            "bash", "-c", "cd /mnt/c/MiOS/src/mios-rs && cargo run -p miosd -- cli --help"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Help failed: {res.stdout}\n{res.stderr}")

        output = res.stdout + res.stderr
        expected_verbs = [
            "build", "dash", "mini", "mon", "config", "code", "ai",
            "xbox", "virt", "vfio", "tune", "summary", "profile",
            "assess", "theme", "dotfiles", "new", "iommu", "env",
            "sync-env", "blade", "flatpaks", "user", "flight", "models",
            "update", "check", "status", "logs", "backup"
        ]
        for v in expected_verbs:
            self.assertIn(v, output, f"Verb '{v}' missing from CLI dispatcher help output")

    def test_completion_generation(self):
        """Verify that shell completions are correctly generated for bash, zsh, fish, pwsh."""
        for shell in ["bash", "zsh", "fish", "pwsh"]:
            cmd = [
                "wsl", "-u", "root", "-d", "podman-MiOS-DEV", "--",
                "bash", "-c", f"cd /mnt/c/MiOS/src/mios-rs && cargo run -p miosd -- cli --generate-completion {shell}"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Completion generation failed for {shell}")
            out = res.stdout
            self.assertTrue(len(out) > 50, f"Completion output too short for {shell}")
            self.assertIn("build", out)
            self.assertIn("dash", out)

    def test_rust_unit_tests_pass(self):
        """Execute Rust unit tests for CLI dispatcher module via cargo test in WSL."""
        cmd = [
            "wsl", "-u", "root", "-d", "podman-MiOS-DEV", "--",
            "bash", "-c", "cd /mnt/c/MiOS/src/mios-rs && cargo test -p miosd --lib -- cli"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(
            res.returncode, 0,
            f"Cargo test for miosd cli failed:\nstdout: {res.stdout}\nstderr: {res.stderr}"
        )
        self.assertIn("test cli::dispatcher::tests::test_known_verbs_table_count ... ok", res.stdout)
        self.assertIn("test cli::completions::tests::test_completion_generation ... ok", res.stdout)
        self.assertIn("test cli::tests::test_dispatch_help ... ok", res.stdout)

if __name__ == "__main__":
    unittest.main()
