#!/usr/bin/env python3
"""
Unit Test Suite for MiOS UID 1000 Enforcement & Systemd User Session Boundary.
Implements T-965 / AGY-2563.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "user")))
try:
    import uid_enforce
except ImportError:
    # fallback direct import
    import importlib.util
    spec = importlib.util.spec_from_file_location("uid_enforce", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "user", "uid_enforce.py")))
    uid_enforce = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(uid_enforce)


class TestUidEnforcement(unittest.TestCase):
    def test_generate_sysusers_remediation(self):
        conf = uid_enforce.generate_sysusers_remediation("mios", 1000)
        self.assertIn("g mios 1000", conf)
        self.assertIn("u mios 1000:mios", conf)
        self.assertIn("m mios wheel", conf)
        self.assertIn("m mios video", conf)

    def test_audit_user_environment_mock_valid(self):
        with patch.object(uid_enforce, "check_user_uid", return_value={
            "exists": True, "username": "mios", "uid": 1000, "gid": 1000,
            "home": "/var/home/mios", "shell": "/bin/bash",
            "is_system_uid": False, "valid_uid": True, "valid_gid": True
        }), patch.object(uid_enforce, "check_subuid_subgid", return_value={
            "subuid_valid": True, "subuid_start": 100000, "subuid_count": 65536,
            "subgid_valid": True, "subgid_start": 100000, "subgid_count": 65536
        }):
            audit = uid_enforce.audit_user_environment("mios")
            self.assertEqual(audit["status"], "PASS")
            self.assertEqual(len(audit["issues"]), 0)

    def test_audit_user_environment_mock_system_uid(self):
        with patch.object(uid_enforce, "check_user_uid", return_value={
            "exists": True, "username": "mios", "uid": 992, "gid": 992,
            "home": "/var/home/mios", "shell": "/bin/bash",
            "is_system_uid": True, "valid_uid": False, "valid_gid": False
        }), patch.object(uid_enforce, "check_subuid_subgid", return_value={
            "subuid_valid": False, "subuid_start": None, "subuid_count": 0,
            "subgid_valid": False, "subgid_start": None, "subgid_count": 0
        }):
            audit = uid_enforce.audit_user_environment("mios")
            self.assertEqual(audit["status"], "FAIL")
            self.assertTrue(any("system UID 992" in issue for issue in audit["issues"]))

    def test_subuid_subgid_parsing(self):
        res = uid_enforce.check_subuid_subgid("nonexistent_user_xyz")
        self.assertFalse(res["subuid_valid"])


if __name__ == "__main__":
    unittest.main()
