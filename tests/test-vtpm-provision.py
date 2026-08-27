#!/usr/bin/env python3
# AI-hint: Automated test suite for MiOS Virtual TPM2 (swtpm) Provisioning and Domain XML Generator (T-417).
# AI-related: usr/libexec/mios/virt/vtpm_provision.py, usr/share/doc/mios/manual/ch21-looking-glass-b7-and-kvmfr.md
"""
Automated unit tests for vTPM2 swtpm provisioning, per-VM state isolation,
ephemeral UNIX socket path management, and libvirt CRB domain XML generation.
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
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "virt", "vtpm_provision.py")

spec = importlib.util.spec_from_file_location("vtpm_provision", _TARGET_PATH)
if spec and spec.loader:
    vtpm_provision = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = vtpm_provision
    spec.loader.exec_module(vtpm_provision)
else:
    raise ImportError(f"Could not load vtpm_provision module from {_TARGET_PATH}")

class TestVTPMProvision(unittest.TestCase):
    """Tests vTPM swtpm isolation, socket lifecycle, and domain XML generation."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="mios-test-vtpm-")
        self.state_root = os.path.join(self.temp_dir, "libvirt", "swtpm")
        self.sock_root = os.path.join(self.temp_dir, "run", "swtpm")

    def tearDown(self) -> None:
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_vm_id_validation(self) -> None:
        self.assertEqual(vtpm_provision.validate_vm_id("win11"), "win11")
        self.assertEqual(vtpm_provision.validate_vm_id("gaming-vm_01"), "gaming-vm_01")
        with self.assertRaises(ValueError):
            vtpm_provision.validate_vm_id("bad vm id with spaces")
        with self.assertRaises(ValueError):
            vtpm_provision.validate_vm_id("../escape")
        with self.assertRaises(ValueError):
            vtpm_provision.validate_vm_id("")

    def test_per_vm_state_directory_isolation(self) -> None:
        prov = vtpm_provision.VTPMProvisioner(
            state_root=self.state_root,
            sock_root=self.sock_root,
        )
        state_vm1 = prov.get_state_dir("vm-win11")
        state_vm2 = prov.get_state_dir("vm-linux-dev")

        # Invariant 1 check: Never share state directories between VMs
        self.assertNotEqual(state_vm1, state_vm2)
        self.assertTrue(state_vm1.endswith("vm-win11"))
        self.assertTrue(state_vm2.endswith("vm-linux-dev"))

    def test_domain_xml_generation(self) -> None:
        prov = vtpm_provision.VTPMProvisioner(
            state_root="/var/lib/libvirt/swtpm",
            sock_root="/run/libvirt/swtpm",
        )
        xml = prov.generate_domain_xml("win11-prod")
        self.assertIn('<tpm model="tpm-crb">', xml)
        self.assertIn('<backend type="emulator" version="2.0">', xml)
        self.assertIn('/run/libvirt/swtpm/win11-prod-swtpm.sock', xml)

    def test_build_setup_and_daemon_cmds(self) -> None:
        prov = vtpm_provision.VTPMProvisioner(
            state_root="/var/lib/libvirt/swtpm",
            sock_root="/run/libvirt/swtpm",
        )
        setup_cmd = prov.build_setup_cmd("win11")
        self.assertEqual(setup_cmd[0], "swtpm_setup")
        self.assertIn("--tpm2", setup_cmd)
        self.assertIn("--createek", setup_cmd)

        daemon_cmd = prov.build_daemon_cmd("win11")
        self.assertEqual(daemon_cmd[0], "swtpm")
        self.assertEqual(daemon_cmd[1], "socket")
        self.assertIn("--tpm2", daemon_cmd)
        self.assertIn("type=unixio,path=/run/libvirt/swtpm/win11-swtpm.sock", daemon_cmd)

    def test_provision_and_status_lifecycle(self) -> None:
        prov = vtpm_provision.VTPMProvisioner(
            state_root=self.state_root,
            sock_root=self.sock_root,
        )
        # Initial status: not provisioned
        st_before = prov.get_status("win11-test")
        self.assertFalse(st_before["provisioned"])

        # Provision
        res = prov.provision("win11-test")
        self.assertEqual(res["status"], "provisioned")
        self.assertTrue(os.path.isdir(res["state_dir"]))
        self.assertTrue(os.path.isfile(os.path.join(res["state_dir"], "tpm2-00.permall")))

        # Check status after
        st_after = prov.get_status("win11-test")
        self.assertTrue(st_after["provisioned"])
        self.assertTrue(st_after["has_nvram"])

    def test_cleanup_sockets_and_purge_state(self) -> None:
        prov = vtpm_provision.VTPMProvisioner(
            state_root=self.state_root,
            sock_root=self.sock_root,
        )
        prov.provision("win11-cleanup")
        sock_path = prov.get_socket_path("win11-cleanup")
        os.makedirs(os.path.dirname(sock_path), exist_ok=True)
        with open(sock_path, "w") as f:
            f.write("mock-sock")

        # Cleanup without purge
        res1 = prov.cleanup("win11-cleanup", purge_state=False)
        self.assertFalse(os.path.exists(sock_path))
        self.assertTrue(os.path.isdir(res1["state_dir"]))

        # Cleanup with purge
        res2 = prov.cleanup("win11-cleanup", purge_state=True)
        self.assertTrue(res2["state_purged"])
        self.assertFalse(os.path.exists(res2["state_dir"]))

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestVTPMProvision)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
