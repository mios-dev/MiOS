#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-STRG CephFS multi-tenant user provisioning.
# AI-related: usr/libexec/mios/mios-cephfs-provision, usr/share/doc/mios/manual/ch66-v5-authority-inversion-and-cephfs-tiering.md
"""Automated tests for WS-STRG CephFS user subvolume, tenant CephX keyrings, and configuration."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
import importlib.machinery
import importlib.util

sys.path.insert(0, os.path.join(_ROOT, "usr", "lib", "mios"))
sys.path.insert(0, os.path.join(_ROOT, "lib", "mios"))

_PROV_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "mios-cephfs-provision")
loader = importlib.machinery.SourceFileLoader("cephfs_provision", _PROV_PATH)
spec = importlib.util.spec_from_loader("cephfs_provision", loader)
if spec and spec.loader:
    cephfs_provision = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = cephfs_provision
    spec.loader.exec_module(cephfs_provision)
else:
    raise ImportError(f"Could not load mios-cephfs-provision module from {_PROV_PATH}")


class TestCephFSProvision(unittest.TestCase):
    """Validates CephFS configuration defaults, user info parsing, and keyring paths."""

    def test_cephfs_config_defaults(self):
        cfg = cephfs_provision.load_cephfs_config()
        self.assertIn("cluster_name", cfg)
        self.assertIn("fs_name", cfg)
        self.assertIn("tenant_id", cfg)
        self.assertEqual(cfg["subvolume_mode"], "0700")

    def test_user_info_lookup(self):
        username, gid = cephfs_provision.get_user_info("1000")
        self.assertTrue(len(username) > 0)
        self.assertIsInstance(gid, int)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCephFSProvision)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
