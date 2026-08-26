#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-SEC Quadlet secret 0600 permissions and rotation.
# AI-related: usr/libexec/mios/sec/rotate-quadlet-secrets.py, usr/share/doc/mios/manual/ch02-architecture.md
"""Automated tests for WS-SEC Quadlet secret file permissions audit and token rotation."""

from __future__ import annotations

import importlib.util
import os
import stat
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_ROT_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "sec", "rotate-quadlet-secrets.py")

spec = importlib.util.spec_from_file_location("rotate_quadlet_secrets", _ROT_PATH)
if spec and spec.loader:
    rotate_quadlet_secrets = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = rotate_quadlet_secrets
    spec.loader.exec_module(rotate_quadlet_secrets)
else:
    raise ImportError(f"Could not load rotate-quadlet-secrets module from {_ROT_PATH}")


class TestQuadletSecretsRotation(unittest.TestCase):
    """Validates 0600 permission hardening on env files and secure token rotation generation."""

    def test_permission_hardening(self):
        with tempfile.TemporaryDirectory(prefix="mios-sec-test-") as tmpdir:
            test_env = os.path.join(tmpdir, "test.env")
            with open(test_env, "w", encoding="utf-8") as f:
                f.write("API_KEY=12345\n")
            os.chmod(test_env, 0o644)

            hardener = rotate_quadlet_secrets.QuadletSecretsHardener(secrets_dir=tmpdir)
            fixed = hardener.audit_and_harden_permissions(tmpdir)
            self.assertEqual(len(fixed), 1)
            if os.name != "nt":
                st = os.stat(test_env)
                self.assertEqual(stat.S_IMODE(st.st_mode), 0o600)

    def test_token_rotation_generation(self):
        hardener = rotate_quadlet_secrets.QuadletSecretsHardener()
        token, line = hardener.generate_rotated_secret("AGENT_AUTH_TOKEN", length_bytes=32)
        self.assertEqual(len(token), 64)
        self.assertTrue(line.startswith("AGENT_AUTH_TOKEN="))

    def test_init_secrets_env_non_destructive(self):
        with tempfile.TemporaryDirectory(prefix="mios-sec-init-") as tmpdir:
            sec_file = os.path.join(tmpdir, "secrets.env")
            with open(sec_file, "w", encoding="utf-8") as f:
                f.write("POSTGRES_PASSWORD=my_existing_db_password_123\n")

            hardener = rotate_quadlet_secrets.QuadletSecretsHardener(secrets_dir=tmpdir)
            secrets_map = hardener.init_secrets_env(secrets_file=sec_file)

            # Assert pre-existing password is NOT disrupted
            self.assertEqual(secrets_map["POSTGRES_PASSWORD"], "my_existing_db_password_123")
            # Assert missing default keys were generated
            self.assertIn("MIOS_DEFAULT_PASSWORD", secrets_map)
            self.assertIn("K3S_TOKEN", secrets_map)
            self.assertIn("WEBUI_SECRET_KEY", secrets_map)
            self.assertEqual(len(secrets_map["K3S_TOKEN"]), 64)

            # Re-read file from disk
            with open(sec_file, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("POSTGRES_PASSWORD=my_existing_db_password_123", content)
            self.assertIn("K3S_TOKEN=", content)

    def test_service_unit_file(self):
        svc_path = os.path.join(_ROOT, "usr", "lib", "systemd", "system", "mios-secret-init.service")
        self.assertTrue(os.path.exists(svc_path), f"Service file missing at {svc_path}")
        with open(svc_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("rotate-quadlet-secrets.py --init", content)
        self.assertIn("[Install]", content)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestQuadletSecretsRotation)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
