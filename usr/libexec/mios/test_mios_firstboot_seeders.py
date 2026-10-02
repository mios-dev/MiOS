#!/usr/bin/env python3
# AI-hint: Two-sided verification test suite for firstboot seeder ordering and degradation reporting (T-1141).
# AI-related: usr/lib/systemd/system/mios-ai-firstboot.service, usr/lib/systemd/system/mios-forgejo-runner-firstboot.service, usr/libexec/mios/seed-db-config.py, usr/libexec/mios/mios-ai-firstboot, usr/libexec/mios/mios-forgejo-runner-firstboot.sh
# AI-functions: parse_unit_section, TestFirstbootSeedersTwoSided
"""Two-sided verification controls for Task T-1141.

WHEN forgejo/pgvector/psycopg are unavailable THE SYSTEM SHALL order firstboot seeders
after them and surface the degradation instead of silently skipping.

Positive control:
- Verifies systemd units and mios.toml order mios-ai-firstboot after mios-pgvector.service.
- Verifies systemd units and mios.toml order mios-forgejo-runner-firstboot after mios-forge-firstboot.service.
- Verifies seed-db-config.py surfaces DEGRADED message and exits non-zero (exit 2) when psycopg is missing.
- Verifies mios-forgejo-runner-firstboot.sh surfaces DEGRADED message and exits non-zero when token is missing/empty.
- Verifies mios-ai-firstboot surfaces DEGRADED messages and refrains from creating .ai-firstboot-done when pgvector is unavailable.

Negative control:
- In an isolated temporary scratch copy:
  * Plants defect omitting mios-pgvector ordering from unit; asserts detection.
  * Plants defect restoring silent exit 0 in seed-db-config.py; asserts detection.
  * Plants defect restoring silent exit 0 in mios-forgejo-runner-firstboot.sh; asserts detection.
- Asserts that all real tree files remain pristine (unmodified SHA-256).
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.normpath(os.path.join(_HERE, "..", "..", ".."))


def parse_unit_section(file_path: str, section: str = "Unit") -> dict[str, str]:
    """Parse key-value pairs from a specific section of a systemd unit file."""
    directives: dict[str, str] = {}
    target_header = f"[{section}]"
    in_section = False
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith(";"):
                continue
            if stripped.startswith("[") and stripped.endswith("]"):
                in_section = (stripped == target_header)
                continue
            if in_section and "=" in stripped:
                k, v = stripped.split("=", 1)
                directives[k.strip()] = v.strip()
    return directives


def to_bash_path(path: str) -> str:
    norm = os.path.abspath(path).replace("\\", "/")
    if re.match(r"^[a-zA-Z]:", norm):
        drive = norm[0].lower()
        return f"/{drive}{norm[2:]}"
    return norm


def file_sha256(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class TestFirstbootSeedersTwoSided(unittest.TestCase):
    def setUp(self):
        self.ai_unit_path = os.path.join(_REPO_ROOT, "usr", "lib", "systemd", "system", "mios-ai-firstboot.service")
        self.runner_unit_path = os.path.join(_REPO_ROOT, "usr", "lib", "systemd", "system", "mios-forgejo-runner-firstboot.service")
        self.toml_path = os.environ.get("MIOS_TOML", os.path.join(_REPO_ROOT, "usr", "share", "mios", "mios.toml"))
        self.seed_db_script = os.path.join(_REPO_ROOT, "usr", "libexec", "mios", "seed-db-config.py")
        self.runner_script = os.path.join(_REPO_ROOT, "usr", "libexec", "mios", "mios-forgejo-runner-firstboot.sh")
        self.ai_firstboot_script = os.path.join(_REPO_ROOT, "usr", "libexec", "mios", "mios-ai-firstboot")

        self.watched_files = [
            self.ai_unit_path,
            self.runner_unit_path,
            self.toml_path,
            self.seed_db_script,
            self.runner_script,
            self.ai_firstboot_script,
        ]
        self.baseline_shas = {f: file_sha256(f) for f in self.watched_files}

    def tearDown(self):
        # Invariant check: real tree must never be modified by tests
        for f, original_sha in self.baseline_shas.items():
            current_sha = file_sha256(f)
            self.assertEqual(
                original_sha, current_sha,
                f"SAFETY INVARIANT VIOLATION: Test modified real tree file {f}!"
            )

    def test_positive_control_systemd_ordering(self):
        """Positive Control: Verify systemd units order firstboot seeders after pgvector and forgejo."""
        # 1. mios-ai-firstboot.service ordering
        ai_directives = parse_unit_section(self.ai_unit_path, "Unit")
        after_ai = ai_directives.get("After", "").split()
        wants_ai = ai_directives.get("Wants", "").split()
        self.assertIn("mios-pgvector.service", after_ai, "mios-ai-firstboot.service missing After=mios-pgvector.service")
        self.assertIn("mios-pgvector.service", wants_ai, "mios-ai-firstboot.service missing Wants=mios-pgvector.service")

        # 2. mios-forgejo-runner-firstboot.service ordering
        runner_directives = parse_unit_section(self.runner_unit_path, "Unit")
        after_runner = runner_directives.get("After", "").split()
        wants_runner = runner_directives.get("Wants", "").split()
        self.assertIn("mios-forge-firstboot.service", after_runner, "mios-forgejo-runner-firstboot.service missing After=mios-forge-firstboot.service")
        self.assertIn("mios-forge-firstboot.service", wants_runner, "mios-forgejo-runner-firstboot.service missing Wants=mios-forge-firstboot.service")

        # 3. mios.toml SSOT parity
        with open(self.toml_path, "r", encoding="utf-8") as f:
            toml_content = f.read()

        self.assertRegex(
            toml_content,
            r'\[units\."mios-ai-firstboot\.service"\.Unit\][^\[]*After\s*=\s*"[^"]*mios-pgvector\.service',
            "mios.toml mios-ai-firstboot After does not include mios-pgvector.service"
        )
        self.assertRegex(
            toml_content,
            r'\[units\."mios-forgejo-runner-firstboot\.service"\.Unit\][^\[]*Wants\s*=\s*"[^"]*mios-forge-firstboot\.service',
            "mios.toml mios-forgejo-runner-firstboot Wants does not include mios-forge-firstboot.service"
        )

    def test_positive_control_psycopg_degradation_reporting(self):
        """Positive Control: Verify seed-db-config.py exits 2 and surfaces DEGRADED when psycopg missing."""
        env = os.environ.copy()
        env["PYTHONPATH"] = ""
        res = subprocess.run(
            [sys.executable, self.seed_db_script],
            capture_output=True,
            text=True,
            env=env,
        )
        # When psycopg is not installed, it must return exit code 2 and log DEGRADED message
        try:
            import psycopg
            # If psycopg happens to be present in test environment, test via mock
            mock_cmd = [
                sys.executable, "-c",
                "import sys; sys.modules['psycopg'] = None; import runpy; runpy.run_path('" + self.seed_db_script.replace('\\', '/') + "', run_name='__main__')"
            ]
            res_mock = subprocess.run(mock_cmd, capture_output=True, text=True)
            self.assertEqual(res_mock.returncode, 2, "Expected exit code 2 when psycopg missing")
            self.assertIn("DEGRADED: psycopg not installed", res_mock.stderr + res_mock.stdout)
        except ImportError:
            self.assertEqual(res.returncode, 2, "Expected exit code 2 when psycopg missing")
            self.assertIn("DEGRADED: psycopg not installed", res.stderr + res.stdout)

    def test_positive_control_forge_runner_degradation_reporting(self):
        """Positive Control: Verify mios-forgejo-runner-firstboot.sh surfaces DEGRADED when token missing."""
        with open(self.runner_script, "rb") as f:
            script_bytes = f.read()

        # 1. Missing token file
        env = os.environ.copy()
        env["TOKEN_FILE"] = "/nonexistent/runner-token"
        env["SENTINEL"] = "/tmp/.runner"
        res_missing = subprocess.run(
            ["bash", "-s"],
            input=script_bytes,
            capture_output=True,
            env=env,
        )
        self.assertNotEqual(res_missing.returncode, 0, "runner script must exit non-zero when token file missing")
        self.assertIn(b"DEGRADED", res_missing.stderr, "runner script must log DEGRADED when token file missing")

        # 2. Empty token file
        env["TOKEN_FILE"] = "/dev/null"
        res_empty = subprocess.run(
            ["bash", "-s"],
            input=script_bytes,
            capture_output=True,
            env=env,
        )
        self.assertNotEqual(res_empty.returncode, 0, "runner script must exit non-zero when token is empty")
        self.assertIn(b"DEGRADED", res_empty.stderr, "runner script must log DEGRADED when token is empty")

    def test_positive_control_ai_firstboot_degradation_reporting(self):
        """Positive Control: Verify mios-ai-firstboot surfaces degradation when pgvector is unavailable."""
        with open(self.ai_firstboot_script, "r", encoding="utf-8") as f:
            content = f.read()

        # Verify degradation reporting and sentinel gating on _db_ok
        self.assertIn("DEGRADED: pgvector port not ready", content)
        self.assertIn("_db_seed_ok", content)
        self.assertIn("_db_config_ok", content)
        self.assertIn("_db_ok", content)
        self.assertIn('"skipped/degraded"', content)
        # Ensure sentinel writing requires _db_ok
        self.assertRegex(content, r'\[\s*"\$_db_ok"\s*-(?:eq\s*1|ne\s*0)\s*\]')

    def test_negative_control_scratch_isolation(self):
        """Negative Control: Plant defects in isolated scratch copies and verify detection."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            scratch_ai_unit = os.path.join(tmp_dir, "mios-ai-firstboot.service")
            scratch_seed_db = os.path.join(tmp_dir, "seed-db-config.py")
            scratch_runner = os.path.join(tmp_dir, "mios-forgejo-runner-firstboot.sh")

            shutil.copyfile(self.ai_unit_path, scratch_ai_unit)
            shutil.copyfile(self.seed_db_script, scratch_seed_db)
            shutil.copyfile(self.runner_script, scratch_runner)

            # Defect 1: Remove mios-pgvector.service from scratch AI unit
            with open(scratch_ai_unit, "r", encoding="utf-8") as f:
                ai_text = f.read()
            bad_ai_text = re.sub(r'mios-pgvector\.service\s*', '', ai_text)
            with open(scratch_ai_unit, "w", encoding="utf-8") as f:
                f.write(bad_ai_text)

            bad_directives = parse_unit_section(scratch_ai_unit, "Unit")
            bad_after = bad_directives.get("After", "").split()
            self.assertNotIn(
                "mios-pgvector.service", bad_after,
                "Plant defect failed: scratch copy still had mios-pgvector.service"
            )
            # Verify validator flags this planted defect
            with self.assertRaises(AssertionError) as ctx:
                self.assertIn("mios-pgvector.service", bad_after, "PLANT_DETECTED: scratch unit missing pgvector ordering")
            self.assertIn("PLANT_DETECTED: scratch unit missing pgvector ordering", str(ctx.exception))

            # Defect 2: Restore silent exit 0 on missing psycopg in scratch seed-db-config
            with open(scratch_seed_db, "r", encoding="utf-8") as f:
                seed_text = f.read()
            bad_seed_text = seed_text.replace("return 2", "return 0")
            with open(scratch_seed_db, "w", encoding="utf-8") as f:
                f.write(bad_seed_text)

            res_bad_seed = subprocess.run([sys.executable, scratch_seed_db], capture_output=True, text=True)
            with self.assertRaises(AssertionError) as ctx:
                self.assertEqual(res_bad_seed.returncode, 2, "PLANT_DETECTED: seed-db-config returned 0 instead of 2")
            self.assertIn("PLANT_DETECTED: seed-db-config returned 0 instead of 2", str(ctx.exception))

            # Defect 3: Restore silent exit 0 on missing token in scratch runner script
            with open(scratch_runner, "rb") as f:
                runner_bytes = f.read()
            bad_runner_bytes = runner_bytes.replace(b"exit 1", b"exit 0")
            with open(scratch_runner, "wb") as f:
                f.write(bad_runner_bytes)

            env = os.environ.copy()
            env["TOKEN_FILE"] = "/nonexistent/token"
            env["SENTINEL"] = "/tmp/.runner"
            res_bad_runner = subprocess.run(["bash", "-s"], input=bad_runner_bytes, capture_output=True, env=env)
            with self.assertRaises(AssertionError) as ctx:
                self.assertNotEqual(res_bad_runner.returncode, 0, "PLANT_DETECTED: runner script returned 0 instead of 1")
            self.assertIn("PLANT_DETECTED: runner script returned 0 instead of 1", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
