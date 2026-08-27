#!/usr/bin/env python3
# AI-hint: Unit and integration tests for SELinux Type Enforcement policy generator and AVC denial parser.
# AI-related: usr/libexec/mios/sec/selinux_policy.py, usr/share/doc/mios/manual/sec.md
"""Unit and integration test suite for SelinuxPolicyManager and CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "sec", "selinux_policy.py")

spec = importlib.util.spec_from_file_location("selinux_policy", _TARGET_PATH)
if spec and spec.loader:
    selinux_policy = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = selinux_policy
    spec.loader.exec_module(selinux_policy)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")


class TestSelinuxPolicy(unittest.TestCase):
    """Test suite for SELinux Type Enforcement (.te) generation, mock compilation, and AVC denial parsing."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="mios-test-selinux-")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_generate_te_source_syntax(self):
        manager = selinux_policy.SelinuxPolicyManager(mock=True)
        te_src = manager.generate_te_source(
            module_name="mios_sidecar",
            allowed_ports=[5432, 8642, 11450],
            allowed_dirs=["/var/lib/mios"],
        )
        self.assertIn("module mios_sidecar 1.0;", te_src)
        self.assertIn("type mios_sidecar_t;", te_src)
        self.assertIn("typeattribute mios_sidecar_t container_domain;", te_src)
        self.assertIn("5432, 8642, 11450", te_src)

    def test_compile_module_mock(self):
        manager = selinux_policy.SelinuxPolicyManager(mock=True)
        te_path = os.path.join(self.temp_dir.name, "mios_sidecar.te")
        with open(te_path, "w", encoding="utf-8") as f:
            f.write("module mios_sidecar 1.0;\n")

        res = manager.compile_module(te_path)
        self.assertTrue(os.path.exists(res["mod_file"]))
        self.assertTrue(os.path.exists(res["pp_file"]))

    def test_install_module_mock(self):
        manager = selinux_policy.SelinuxPolicyManager(mock=True)
        pp_path = os.path.join(self.temp_dir.name, "mios_sidecar.pp")
        self.assertTrue(manager.install_module(pp_path))

    def test_parse_avc_denials_matching_domain(self):
        manager = selinux_policy.SelinuxPolicyManager(mock=True)
        sample_log = (
            'type=AVC msg=audit(1724670000.123:456): avc:  denied  { read } for  '
            'pid=1234 comm="hermes" name="unauthorized.txt" dev="dm-0" ino=5678 '
            'scontext=system_u:system_r:mios_sidecar_t:s0:c123,c456 '
            'tcontext=system_u:object_r:admin_home_t:s0 tclass=file permissive=0\n'
            'type=AVC msg=audit(1724670005.123:457): avc:  denied  { write } for  '
            'pid=5678 comm="unrelated" name="file.txt" '
            'scontext=system_u:system_r:unconfined_t:s0 '
            'tcontext=system_u:object_r:etc_t:s0 tclass=file permissive=0\n'
        )

        denials = manager.parse_avc_denials(sample_log, target_domain="mios_sidecar_t")
        self.assertEqual(len(denials), 1)
        self.assertEqual(denials[0]["audit_id"], "456")
        self.assertIn("read", denials[0]["permissions"])
        self.assertIn("mios_sidecar_t", denials[0]["scontext"])

    def test_audit_sidecar_confinement_mock(self):
        manager = selinux_policy.SelinuxPolicyManager(mock=True)
        audit_res = manager.audit_sidecar_confinement()
        self.assertTrue(audit_res["enforcing"])
        self.assertTrue(audit_res["compliant"])
        self.assertEqual(len(audit_res["unconfined_containers"]), 0)

    def test_cli_execution_generate_te(self):
        te_file = os.path.join(self.temp_dir.name, "custom.te")
        test_args = [
            "selinux_policy.py",
            "--generate-te",
            "--module-name", "custom_test",
            "--te-file", te_file,
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = selinux_policy.main()
            self.assertEqual(exit_code, 0)
            self.assertTrue(os.path.exists(te_file))

    def test_cli_execution_status(self):
        test_args = [
            "selinux_policy.py",
            "--status",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = selinux_policy.main()
            self.assertEqual(exit_code, 0)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSelinuxPolicy)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
