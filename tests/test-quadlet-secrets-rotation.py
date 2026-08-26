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


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestQuadletSecretsRotation)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
