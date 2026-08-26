#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-SEC / SEC-06 interactive human-in-the-loop permission escalation.
# AI-related: usr/libexec/mios/sec/approval.py, usr/share/mios/mios.toml
"""
Automated unit tests for MiOS HITL Permission Escalation and Approval Engine (SEC-06).

Validates high-risk command interception, safe command passthrough, approval token cryptography,
rejection handling, TTL expiration, persistence, and CLI operations.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "usr", "libexec", "mios", "sec"))

try:
    import approval
except ImportError:
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        "approval",
        os.path.join(_ROOT, "usr", "libexec", "mios", "sec", "approval.py")
    )
    approval = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(approval)


class TestHitlApproval(unittest.TestCase):
    """Unit test suite for ApprovalEngine and ApprovalRequest lifecycle."""

    def setUp(self) -> None:
        self.engine = approval.ApprovalEngine()

    def test_dangerous_command_detection(self) -> None:
        """Verify that known destructive and system-modifying commands trigger approval requirement."""
        dangerous_commands = [
            "rm -rf /var/lib/data",
            "rm -rf /",
            "rm -r /home/user/docs",
            "rm --recursive --force /tmp/cache",
            "mkfs.ext4 /dev/nvme0n1",
            "mkfs.xfs /dev/sda1",
            "fdisk /dev/sda",
            "gdisk /dev/nvme0n1",
            "parted /dev/sda mklabel gpt",
            "sfdisk /dev/sdb",
            "wipefs -a /dev/sda1",
            "dd if=/dev/zero of=/dev/sda bs=1M",
            "dd if=/dev/urandom of=/dev/nvme0n1",
            "bootc switch quay.io/ublue-os/ucore-hci:latest",
            "bootc rollback",
            "bootc edit",
            "cryptsetup luksFormat /dev/sda2",
            "cryptsetup luksKillSlot /dev/sda2 1",
            "cryptsetup luksErase /dev/sda2",
            "iptables -F",
            "iptables --flush",
            "ip6tables -F",
            "iptables -X",
            "nft flush ruleset",
            "nft delete table inet filter",
            "lvremove -f /dev/vg0/lv_root",
            "vgremove vg0",
            "pvremove /dev/sdb",
            "btrfs subvolume delete /mnt/data/@snapshots",
            "zpool destroy tank",
            "zfs destroy tank/data",
            "reboot",
            "shutdown -h now",
            "poweroff",
            "init 0",
            "init 6",
        ]
        for cmd in dangerous_commands:
            with self.subTest(command=cmd):
                self.assertTrue(
                    self.engine.requires_approval(cmd),
                    f"Expected command to require approval: {cmd}"
                )

    def test_safe_command_passthrough(self) -> None:
        """Verify that benign diagnostic, inspection, and development commands pass without escalation."""
        safe_commands = [
            "ls -la /usr/share",
            "cat /etc/os-release",
            "echo 'hello world'",
            "git status",
            "git log -n 5",
            "python tests/test-suite.py",
            "grep -rn 'pattern' /usr/share/mios",
            "find /var/log -name '*.log'",
            "df -h",
            "uptime",
            "ps aux",
            "systemctl status mios-llm-light",
            "",
            "   ",
        ]
        for cmd in safe_commands:
            with self.subTest(command=cmd):
                self.assertFalse(
                    self.engine.requires_approval(cmd),
                    f"Expected benign command to pass without approval: {cmd}"
                )

    def test_custom_pattern_configuration(self) -> None:
        """Verify custom pattern lists and dynamic pattern addition."""
        custom_engine = approval.ApprovalEngine(patterns=[r"^dangerous-custom-tool\b.*"])
        self.assertTrue(custom_engine.requires_approval("dangerous-custom-tool --wipe"))
        self.assertFalse(custom_engine.requires_approval("rm -rf /tmp"))

        custom_engine.add_pattern(r"^rm\s+-rf.*")
        self.assertTrue(custom_engine.requires_approval("rm -rf /tmp"))

    def test_request_creation_and_fields(self) -> None:
        """Verify request lifecycle creation, initial status, and field assignment."""
        req = self.engine.create_request(
            tool_name="bash_exec",
            command="rm -rf /tmp/scratch",
            reason="Cleanup temporary build artifacts",
            ttl_seconds=300,
        )
        self.assertTrue(req.request_id.startswith("req-"))
        self.assertEqual(req.tool_name, "bash_exec")
        self.assertEqual(req.command, "rm -rf /tmp/scratch")
        self.assertEqual(req.reason, "Cleanup temporary build artifacts")
        self.assertEqual(req.status, approval.Status.PENDING)
        self.assertEqual(req.status.value, "PENDING")
        self.assertEqual(req.ttl_seconds, 300)
        self.assertGreater(req.expires_at, req.created_at)

        fetched = self.engine.get_request(req.request_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.request_id, req.request_id)

    def test_approval_token_issuance_and_validation(self) -> None:
        """Verify approval workflow, token generation, and authorization check."""
        req = self.engine.create_request(
            tool_name="bash_exec",
            command="wipefs -a /dev/sdb1",
        )
        self.assertFalse(self.engine.is_executable(req.request_id))

        token = self.engine.approve(req.request_id, operator="sec_operator")
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 32)

        self.assertEqual(req.status, approval.Status.APPROVED)
        self.assertEqual(req.operator, "sec_operator")
        self.assertIsNotNone(req.approved_at)
        self.assertEqual(req.token, token)

        # Validate token and execution check
        self.assertTrue(self.engine.validate_token(req.request_id, token))
        self.assertTrue(self.engine.is_executable(req.request_id))

    def test_token_cryptographic_verification_and_tampering(self) -> None:
        """Verify cryptographic rejection of forged, tampered, or mismatched tokens."""
        req1 = self.engine.create_request(tool_name="bash_exec", command="mkfs.ext4 /dev/sdb")
        token1 = self.engine.approve(req1.request_id, operator="admin")

        req2 = self.engine.create_request(tool_name="bash_exec", command="mkfs.ext4 /dev/sdc")
        token2 = self.engine.approve(req2.request_id, operator="admin")

        # Mismatched token between requests
        self.assertFalse(self.engine.validate_token(req1.request_id, token2))
        self.assertFalse(self.engine.validate_token(req2.request_id, token1))

        # Tampered token string
        tampered_token = token1[:-4] + "AAAA"
        self.assertFalse(self.engine.validate_token(req1.request_id, tampered_token))

        # Foreign secret key verification rejection
        foreign_engine = approval.ApprovalEngine()
        self.assertFalse(foreign_engine.validate_token(req1.request_id, token1))

        # Null / Empty values
        self.assertFalse(self.engine.validate_token("", token1))
        self.assertFalse(self.engine.validate_token(req1.request_id, ""))
        self.assertFalse(self.engine.validate_token("req-nonexistent", token1))

    def test_rejection_behavior(self) -> None:
        """Verify request rejection, reason tracking, and execution blocking."""
        req = self.engine.create_request(
            tool_name="bash_exec",
            command="dd if=/dev/zero of=/dev/sda",
        )
        ok = self.engine.reject(req.request_id, reason="Prohibited raw disk wipe")
        self.assertTrue(ok)
        self.assertEqual(req.status, approval.Status.REJECTED)
        self.assertEqual(req.rejection_reason, "Prohibited raw disk wipe")
        self.assertIsNotNone(req.rejected_at)

        self.assertFalse(self.engine.is_executable(req.request_id))

        # Attempting to approve a rejected request must fail
        with self.assertRaises(ValueError):
            self.engine.approve(req.request_id, operator="admin")

        # Second rejection should return False
        self.assertFalse(self.engine.reject(req.request_id))

    def test_ttl_expiration_behavior(self) -> None:
        """Verify that requests expire after TTL and cannot be approved or executed."""
        req = self.engine.create_request(
            tool_name="bash_exec",
            command="bootc rollback",
            ttl_seconds=0,
        )
        # Immediate expiration check
        self.assertTrue(req.is_expired())
        self.assertEqual(req.status, approval.Status.EXPIRED)

        # Cannot approve expired request
        with self.assertRaises(ValueError):
            self.engine.approve(req.request_id, operator="admin")

        self.assertFalse(self.engine.is_executable(req.request_id))

    def test_expired_approved_token_invalidation(self) -> None:
        """Verify that an approved token becomes invalid once the request expires."""
        req = self.engine.create_request(
            tool_name="bash_exec",
            command="systemctl stop firewalld",
            ttl_seconds=1,
        )
        token = self.engine.approve(req.request_id, operator="admin")
        self.assertTrue(self.engine.validate_token(req.request_id, token))

        # Force expiration
        req.expires_at = time.time() - 5
        self.assertTrue(req.is_expired())
        self.assertFalse(self.engine.validate_token(req.request_id, token))
        self.assertFalse(self.engine.is_executable(req.request_id))

    def test_list_and_purge_requests(self) -> None:
        """Verify filtering and purging of approval requests."""
        engine = approval.ApprovalEngine()
        r1 = engine.create_request("bash", "cmd1", ttl_seconds=100)
        r2 = engine.create_request("bash", "cmd2", ttl_seconds=100)
        r3 = engine.create_request("bash", "cmd3", ttl_seconds=0)

        engine.approve(r1.request_id, "admin")
        engine.reject(r2.request_id, "test reject")

        all_reqs = engine.list_requests()
        self.assertEqual(len(all_reqs), 3)

        approved_reqs = engine.list_requests(status=approval.Status.APPROVED)
        self.assertEqual(len(approved_reqs), 1)
        self.assertEqual(approved_reqs[0].request_id, r1.request_id)

        rejected_reqs = engine.list_requests(status="REJECTED")
        self.assertEqual(len(rejected_reqs), 1)
        self.assertEqual(rejected_reqs[0].request_id, r2.request_id)

        expired_reqs = engine.list_requests(status=approval.Status.EXPIRED)
        self.assertEqual(len(expired_reqs), 1)
        self.assertEqual(expired_reqs[0].request_id, r3.request_id)

        purged_count = engine.purge_expired()
        self.assertEqual(purged_count, 1)
        self.assertEqual(len(engine.list_requests()), 2)

    def test_state_persistence_and_reload(self) -> None:
        """Verify JSON state persistence across engine instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "approval_state.json")
            eng1 = approval.ApprovalEngine(state_file=state_file)
            req = eng1.create_request("bash", "fdisk /dev/nvme0n1", ttl_seconds=300)
            token = eng1.approve(req.request_id, operator="admin_user")

            eng2 = approval.ApprovalEngine(state_file=state_file)
            req_loaded = eng2.get_request(req.request_id)
            self.assertIsNotNone(req_loaded)
            self.assertEqual(req_loaded.status, approval.Status.APPROVED)
            self.assertEqual(req_loaded.operator, "admin_user")
            self.assertTrue(eng2.validate_token(req.request_id, token))
            self.assertTrue(eng2.is_executable(req.request_id))

    def test_cli_operations(self) -> None:
        """Verify CLI subcommands and JSON output format."""
        script_path = os.path.join(_ROOT, "usr", "libexec", "mios", "sec", "approval.py")

        # Test --check
        res_risky = subprocess.run(
            [sys.executable, script_path, "--check", "rm -rf /var", "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(res_risky.returncode, 0)
        data_risky = json.loads(res_risky.stdout)
        self.assertTrue(data_risky["requires_approval"])

        res_safe = subprocess.run(
            [sys.executable, script_path, "--check", "ls -l /tmp", "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(res_safe.returncode, 1)
        data_safe = json.loads(res_safe.stdout)
        self.assertFalse(data_safe["requires_approval"])

        # Test full CLI lifecycle with state-file
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "cli_state.json")

            # 1. Create request
            res_req = subprocess.run(
                [
                    sys.executable, script_path,
                    "--request",
                    "--command", "wipefs -a /dev/sda",
                    "--tool", "bash_exec",
                    "--reason", "CLI test wipe",
                    "--ttl", "300",
                    "--state-file", state_file,
                    "--json",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            req_data = json.loads(res_req.stdout)
            req_id = req_data["request_id"]
            self.assertEqual(req_data["status"], "PENDING")

            # 2. Query status
            res_status = subprocess.run(
                [sys.executable, script_path, "--status", req_id, "--state-file", state_file, "--json"],
                capture_output=True,
                text=True,
                check=True,
            )
            status_data = json.loads(res_status.stdout)
            self.assertEqual(status_data["request_id"], req_id)
            self.assertEqual(status_data["status"], "PENDING")

            # 3. Approve request
            res_app = subprocess.run(
                [
                    sys.executable, script_path,
                    "--approve", req_id,
                    "--operator", "cli_admin",
                    "--state-file", state_file,
                    "--json",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            app_data = json.loads(res_app.stdout)
            self.assertEqual(app_data["status"], "APPROVED")
            token = app_data["token"]

            # 4. Validate token
            res_val = subprocess.run(
                [
                    sys.executable, script_path,
                    "--validate",
                    "--request-id", req_id,
                    "--token", token,
                    "--state-file", state_file,
                    "--json",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            val_data = json.loads(res_val.stdout)
            self.assertTrue(val_data["valid"])

            # 5. List requests
            res_list = subprocess.run(
                [sys.executable, script_path, "--list", "--state-file", state_file, "--json"],
                capture_output=True,
                text=True,
                check=True,
            )
            list_data = json.loads(res_list.stdout)
            self.assertEqual(len(list_data), 1)
            self.assertEqual(list_data[0]["request_id"], req_id)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestHitlApproval)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
