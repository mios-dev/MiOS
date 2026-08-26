#!/usr/bin/env python3
# AI-hint: Automated unit test suite for CephFS tenant dynamic quota enforcement.
# AI-related: usr/libexec/mios/storage/mios-cephfs-quota, usr/lib/systemd/system/mios-cephfs-quota.service, usr/lib/systemd/system/mios-cephfs-quota.timer
"""Automated tests for CephFS dynamic quota parsing, extended attribute quotas, resizing, and monitoring."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))

sys.path.insert(0, os.path.join(_ROOT, "usr", "lib", "mios"))
sys.path.insert(0, os.path.join(_ROOT, "lib", "mios"))

_QUOTA_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "storage", "mios-cephfs-quota")
loader = importlib.machinery.SourceFileLoader("cephfs_quota", _QUOTA_PATH)
spec = importlib.util.spec_from_loader("cephfs_quota", loader)
if spec and spec.loader:
    cephfs_quota = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = cephfs_quota
    spec.loader.exec_module(cephfs_quota)
else:
    raise ImportError(f"Could not load mios-cephfs-quota module from {_QUOTA_PATH}")


class TestCephFSQuota(unittest.TestCase):
    """Tests byte size parsing, quota management, subvolume resize command generation, and directory monitoring."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="mios_quota_test_")
        self.tenant_a = os.path.join(self.test_dir, "tenant_a")
        self.tenant_b = os.path.join(self.test_dir, "tenant_b")
        os.makedirs(self.tenant_a, exist_ok=True)
        os.makedirs(self.tenant_b, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_parse_size_bytes_units(self):
        self.assertEqual(cephfs_quota.parse_size_bytes("0"), 0)
        self.assertEqual(cephfs_quota.parse_size_bytes("unlimited"), 0)
        self.assertEqual(cephfs_quota.parse_size_bytes("500"), 500)
        self.assertEqual(cephfs_quota.parse_size_bytes("1k"), 1000)
        self.assertEqual(cephfs_quota.parse_size_bytes("1kib"), 1024)
        self.assertEqual(cephfs_quota.parse_size_bytes("100MB"), 100 * 1000 * 1000)
        self.assertEqual(cephfs_quota.parse_size_bytes("100MiB"), 100 * 1024 * 1024)
        self.assertEqual(cephfs_quota.parse_size_bytes("50GiB"), 50 * (1024**3))
        self.assertEqual(cephfs_quota.parse_size_bytes("1TiB"), 1024**4)
        self.assertEqual(cephfs_quota.parse_size_bytes(1073741824), 1073741824)

    def test_parse_size_bytes_invalid(self):
        with self.assertRaises(ValueError):
            cephfs_quota.parse_size_bytes("50invalid")

    def test_format_size_bytes(self):
        self.assertEqual(cephfs_quota.format_size_bytes(0), "0 B")
        self.assertEqual(cephfs_quota.format_size_bytes(1024), "1.00 KiB")
        self.assertEqual(cephfs_quota.format_size_bytes(1048576), "1.00 MiB")
        self.assertEqual(cephfs_quota.format_size_bytes(53687091200), "50.00 GiB")

    def test_parse_count(self):
        self.assertEqual(cephfs_quota.parse_count("0"), 0)
        self.assertEqual(cephfs_quota.parse_count("100"), 100)
        self.assertEqual(cephfs_quota.parse_count("10k"), 10000)
        self.assertEqual(cephfs_quota.parse_count("1M"), 1000000)

    def test_set_and_get_quota(self):
        mgr = cephfs_quota.CephFSQuotaManager()
        quota_bytes = 10 * 1024 * 1024  # 10 MiB
        quota_files = 500

        res = mgr.set_quota(self.tenant_a, max_bytes=quota_bytes, max_files=quota_files)
        self.assertEqual(res["ceph.quota.max_bytes"], quota_bytes)
        self.assertEqual(res["ceph.quota.max_files"], quota_files)

        info = mgr.get_quota(self.tenant_a)
        self.assertEqual(info["max_bytes"], quota_bytes)
        self.assertEqual(info["max_files"], quota_files)
        self.assertEqual(info["status"], "OK")

    def test_quota_usage_calculation_and_status(self):
        mgr = cephfs_quota.CephFSQuotaManager()
        quota_bytes = 10000  # 10 KB
        mgr.set_quota(self.tenant_a, max_bytes=quota_bytes, max_files=10)

        # Write 9.5 KB file (95% usage -> CRITICAL)
        test_file = os.path.join(self.tenant_a, "data.bin")
        with open(test_file, "wb") as f:
            f.write(b"x" * 9500)

        info = mgr.get_quota(self.tenant_a)
        self.assertEqual(info["used_bytes"], 9500)
        self.assertEqual(info["used_files"], 1)
        self.assertGreaterEqual(info["bytes_percent"], 90.0)
        self.assertEqual(info["status"], "CRITICAL")

        # Write additional file to exceed quota -> EXCEEDED
        test_file2 = os.path.join(self.tenant_a, "data2.bin")
        with open(test_file2, "wb") as f:
            f.write(b"x" * 1000)

        info2 = mgr.get_quota(self.tenant_a)
        self.assertEqual(info2["status"], "EXCEEDED")

    def test_subvolume_resize_command(self):
        mgr = cephfs_quota.CephFSQuotaManager()
        new_size = 200 * (1024**3)  # 200 GiB
        res = mgr.resize_subvolume(
            fs_name="cephfs",
            subvolume="user_subvol_1000",
            group_name="tenants",
            new_size_bytes=new_size,
            dry_run=True,
        )
        self.assertEqual(res["status"], "simulated")
        self.assertIn("ceph fs subvolume resize cephfs user_subvol_1000", res["command"])
        self.assertIn("--group_name tenants", res["command"])

    def test_service_and_timer_files_exist(self):
        svc_path = os.path.join(_ROOT, "usr", "lib", "systemd", "system", "mios-cephfs-quota.service")
        timer_path = os.path.join(_ROOT, "usr", "lib", "systemd", "system", "mios-cephfs-quota.timer")

        self.assertTrue(os.path.exists(svc_path), f"Service unit missing at {svc_path}")
        self.assertTrue(os.path.exists(timer_path), f"Timer unit missing at {timer_path}")

        with open(svc_path, "r", encoding="utf-8") as f:
            s_content = f.read()
        self.assertIn("mios-cephfs-quota", s_content)

        with open(timer_path, "r", encoding="utf-8") as f:
            t_content = f.read()
        self.assertIn("OnCalendar=", t_content)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCephFSQuota)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
