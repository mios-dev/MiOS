#!/usr/bin/env python3
# AI-hint: Automated test suite for MiOS VirtIO-FS Shared Directory Mount Daemon & XML Generator (T-419).
# AI-related: usr/libexec/mios/virt/virtiofs_mount.py, usr/share/doc/mios/manual/ch21-looking-glass-b7-and-kvmfr.md
"""
Automated unit tests for VirtIO-FS daemon command construction, POSIX ACL / xattr configuration,
persistent /var/home/mios/Shared verification, and libvirt domain XML generation.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "virt", "virtiofs_mount.py")

spec = importlib.util.spec_from_file_location("virtiofs_mount", _TARGET_PATH)
if spec and spec.loader:
    virtiofs_mount = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = virtiofs_mount
    spec.loader.exec_module(virtiofs_mount)
else:
    raise ImportError(f"Could not load virtiofs_mount module from {_TARGET_PATH}")


class TestVirtioFSMount(unittest.TestCase):
    """Tests VirtIO-FS mount configuration, daemon commands, and libvirt XML."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="mios-test-virtiofs-")
        self.run_root = os.path.join(self.temp_dir, "run")
        self.share_root = os.path.join(self.temp_dir, "var", "home", "mios", "Shared")

    def tearDown(self) -> None:
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_tag_validation(self) -> None:
        self.assertEqual(virtiofs_mount.validate_tag("shared"), "shared")
        self.assertEqual(virtiofs_mount.validate_tag("host_share_01"), "host_share_01")
        with self.assertRaises(ValueError):
            virtiofs_mount.validate_tag("invalid tag spaces")
        with self.assertRaises(ValueError):
            virtiofs_mount.validate_tag("../escape")

    def test_socket_path_generation(self) -> None:
        vfs = virtiofs_mount.VirtioFSManager(run_root="/run/libvirt")
        sock = vfs.get_socket_path("win11", "shared")
        self.assertEqual(sock, "/run/libvirt/virtiofsd-win11-shared.sock")

    def test_daemon_command_building(self) -> None:
        vfs = virtiofs_mount.VirtioFSManager(run_root="/run/libvirt")
        cmd = vfs.build_daemon_cmd(
            "win11",
            source_dir="/var/home/mios/Shared",
            mount_tag="shared",
            dax_size_mb=2048,
            posix_acl=True,
            xattr=True,
        )
        self.assertEqual(cmd[0], "virtiofsd")
        self.assertIn("--socket-path=/run/libvirt/virtiofsd-win11-shared.sock", cmd)
        self.assertIn("--shared-dir=/var/home/mios/Shared", cmd)
        self.assertIn("--posix-acl", cmd)
        self.assertIn("--xattr", cmd)
        self.assertIn("--dax-size=2048M", cmd)

    def test_domain_xml_generation(self) -> None:
        vfs = virtiofs_mount.VirtioFSManager()
        xml = vfs.generate_domain_xml(
            source_dir="/var/home/mios/Shared",
            mount_tag="shared",
            dax_size_mb=1024,
        )
        self.assertIn('<filesystem type="mount" accessmode="passthrough">', xml)
        self.assertIn('<driver type="virtiofs" queue="1024"/>', xml)
        self.assertIn('<source dir="/var/home/mios/Shared"/>', xml)
        self.assertIn('<target dir="shared"/>', xml)
        self.assertIn('<dax unit="KiB">1048576</dax>', xml)
        self.assertIn('<memoryBacking>', xml)
        self.assertIn('<access mode="shared"/>', xml)

    def test_guest_mount_commands(self) -> None:
        vfs = virtiofs_mount.VirtioFSManager()
        cmds = vfs.generate_guest_mount_command(mount_tag="shared", guest_mount_point="/mnt/shared")
        self.assertEqual(cmds["mount_tag"], "shared")
        self.assertEqual(cmds["shell_command"], "sudo mount -t virtiofs shared /mnt/shared")
        self.assertIn("virtiofs", cmds["fstab_entry"])

    def test_source_directory_verification_and_creation(self) -> None:
        vfs = virtiofs_mount.VirtioFSManager(default_shared_dir=self.share_root, mock=False)
        res = vfs.verify_source_directory(create=True)
        self.assertTrue(res["exists"])
        self.assertTrue(os.path.isdir(self.share_root))

    def test_status_report(self) -> None:
        vfs = virtiofs_mount.VirtioFSManager(
            run_root=self.run_root,
            default_shared_dir=self.share_root,
            mock=False,
        )
        os.makedirs(self.run_root, exist_ok=True)
        sock_path = vfs.get_socket_path("win11", "shared")
        with open(sock_path, "w") as f:
            f.write("mock-sock")

        st = vfs.get_status("win11", "shared")
        self.assertEqual(st["vm_id"], "win11")
        self.assertTrue(st["socket_active"])
        self.assertEqual(st["protocol"], "virtiofs")
        self.assertTrue(st["legacy_9p_avoided"])


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestVirtioFSMount)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
