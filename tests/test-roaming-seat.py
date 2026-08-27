#!/usr/bin/env python3
# AI-hint: Automated unit test suite for roaming multi-seat session orchestrator and GPU assignment manager.
# AI-related: usr/libexec/mios/user/roaming_seat.py, usr/share/mios/mios.toml
"""Unit test suite for RoamingSeatOrchestrator and roaming_seat CLI."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "user", "roaming_seat.py")

spec = importlib.util.spec_from_file_location("roaming_seat", _TARGET_PATH)
if spec and spec.loader:
    roaming_seat = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = roaming_seat
    spec.loader.exec_module(roaming_seat)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestRoamingSeatOrchestrator(unittest.TestCase):
    """Test suite for roaming multi-seat orchestration, GPU balancing, and user session assignment."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(prefix="mios-seat-test-")
        self.orchestrator = roaming_seat.RoamingSeatOrchestrator(
            mock=True,
            cephfs_root=self.tmpdir.name,
        )

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_user_authentication(self) -> None:
        # Correct credentials
        user_info = self.orchestrator.user_registry.authenticate("mios", "mios")
        self.assertIsNotNone(user_info)
        self.assertEqual(user_info["username"], "mios")
        self.assertEqual(user_info["uid"], 1000)

        # Incorrect credentials
        bad_auth = self.orchestrator.user_registry.authenticate("mios", "wrong_password")
        self.assertIsNone(bad_auth)

        # Unknown user
        unknown_auth = self.orchestrator.user_registry.authenticate("nonexistent", "pass")
        self.assertIsNone(unknown_auth)

    def test_gpu_discovery_and_allocation(self) -> None:
        gpus = self.orchestrator.gpu_manager.list_gpus()
        self.assertGreaterEqual(len(gpus), 3)

        # Allocate best dedicated GPU (RTX 4090 with 24GB VRAM)
        best_gpu = self.orchestrator.gpu_manager.allocate_best_gpu(prefer_dedicated=True)
        self.assertIsNotNone(best_gpu)
        self.assertEqual(best_gpu.gpu_id, "gpu0")
        self.assertFalse(best_gpu.is_virtual)

    def test_seat_assignment_and_gpu_binding(self) -> None:
        # Assign user 'operator' to seat0
        ok, msg = self.orchestrator.assign_seat(
            seat_id="seat0",
            username="operator",
            gpu_id="gpu0",
            display_head="DP-1",
        )
        self.assertTrue(ok)
        self.assertIn("successfully assigned", msg)

        seat = self.orchestrator.get_seat("seat0")
        self.assertIsNotNone(seat)
        self.assertEqual(seat.status, "active")
        self.assertEqual(seat.assigned_user, "operator")
        self.assertEqual(seat.gpu_id, "gpu0")

        # Check GPU status
        gpu0 = self.orchestrator.gpu_manager.get_gpu("gpu0")
        self.assertEqual(gpu0.assigned_seat, "seat0")
        self.assertEqual(gpu0.load_score, 1.0)

    def test_seat_conflict_and_gpu_conflict(self) -> None:
        # Assign seat0 to mios
        ok, _ = self.orchestrator.assign_seat(seat_id="seat0", username="mios", gpu_id="gpu0")
        self.assertTrue(ok)

        # Attempt to assign already occupied seat0 to operator
        ok_conflict, err_msg = self.orchestrator.assign_seat(seat_id="seat0", username="operator")
        self.assertFalse(ok_conflict)
        self.assertIn("already occupied", err_msg)

        # Attempt to assign seat1 with already claimed gpu0
        ok_gpu_conflict, err_gpu_msg = self.orchestrator.assign_seat(
            seat_id="seat1",
            username="operator",
            gpu_id="gpu0",
        )
        self.assertFalse(ok_gpu_conflict)
        self.assertIn("already assigned to seat", err_gpu_msg)

    def test_seat_release_and_cleanup(self) -> None:
        # Assign then release
        self.orchestrator.assign_seat(seat_id="seat1", username="guest")
        seat = self.orchestrator.get_seat("seat1")
        self.assertEqual(seat.status, "active")
        assigned_gpu_id = seat.gpu_id

        ok, msg = self.orchestrator.release_seat("seat1")
        self.assertTrue(ok)
        self.assertIn("successfully released", msg)

        # Verify seat reset
        seat = self.orchestrator.get_seat("seat1")
        self.assertEqual(seat.status, "idle")
        self.assertIsNone(seat.assigned_user)
        self.assertIsNone(seat.gpu_id)

        # Verify GPU unassigned
        if assigned_gpu_id:
            gpu = self.orchestrator.gpu_manager.get_gpu(assigned_gpu_id)
            self.assertIsNone(gpu.assigned_seat)

    def test_logind_device_attachment(self) -> None:
        mgr = roaming_seat.LogindSeatManager(mock=True)
        self.assertTrue(mgr.attach_device_to_seat("seat1", "/sys/devices/pci0000:00/0000:00:14.0/usb1/1-1"))
        self.assertIn("seat1", mgr.list_logind_seats())
        self.assertTrue(mgr.detach_device_from_seat("seat1", "/sys/devices/pci0000:00/0000:00:14.0/usb1/1-1"))

    def test_cli_execution(self) -> None:
        # Test --status --json
        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            ret = roaming_seat.main(["--status", "--json", "--mock"])
            self.assertEqual(ret, 0)
            data = json.loads(stdout_buf.getvalue())
            self.assertEqual(data["status"], "online")
            self.assertIn("seats", data)

        # Test --authenticate --json
        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            ret = roaming_seat.main(["--authenticate", "--user", "mios", "--password", "mios", "--json", "--mock"])
            self.assertEqual(ret, 0)
            data = json.loads(stdout_buf.getvalue())
            self.assertTrue(data["success"])

        # Test --assign-seat and --release-seat
        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            ret = roaming_seat.main([
                "--assign-seat", "seat0",
                "--user", "mios",
                "--json",
                "--mock",
            ])
            self.assertEqual(ret, 0)
            data = json.loads(stdout_buf.getvalue())
            self.assertTrue(data["success"])

        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            ret = roaming_seat.main([
                "--release-seat", "seat0",
                "--json",
                "--mock",
            ])
            self.assertEqual(ret, 0)
            data = json.loads(stdout_buf.getvalue())
            self.assertTrue(data["success"])

if __name__ == "__main__":
    unittest.main()
