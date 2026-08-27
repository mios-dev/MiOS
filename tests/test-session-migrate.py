#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Wayland session checkpoint and migration protocol.
# AI-related: usr/libexec/mios/user/session_migrate.py, usr/share/mios/mios.toml
"""Unit test suite for SessionMigrateEngine and session_migrate CLI."""

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
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "user", "session_migrate.py")

spec = importlib.util.spec_from_file_location("session_migrate", _TARGET_PATH)
if spec and spec.loader:
    session_migrate = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = session_migrate
    spec.loader.exec_module(session_migrate)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")


class TestSessionMigrate(unittest.TestCase):
    """Test suite for Wayland desktop session checkpointing, checksumming, and migration."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(prefix="mios-sess-test-")
        self.engine = session_migrate.SessionMigrateEngine(
            mock=True,
            sessions_dir=self.tmpdir.name,
            node_name="blade-01",
        )

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_window_descriptor_and_checkpoint_checksum(self) -> None:
        win = session_migrate.WindowDescriptor(
            window_id="w-1",
            app_id="firefox",
            title="MiOS Web",
            x=0,
            y=0,
            width=1920,
            height=1080,
            workspace=1,
            is_fullscreen=True,
            is_maximized=False,
            pid=5555,
        )
        self.assertEqual(win.app_id, "firefox")

        chk = session_migrate.SessionCheckpoint(
            session_id="sess-01",
            username="mios",
            uid=1000,
            source_node="blade-01",
            source_seat="seat0",
            compositor_type="hyprland",
            wayland_display="wayland-0",
            env_vars={"WAYLAND_DISPLAY": "wayland-0"},
            windows=[win],
            cephfs_mount="/var/home/mios",
        )
        csum1 = chk.calculate_checksum()
        self.assertTrue(len(csum1) == 64)

        # Modifying a window should change checksum
        win.title = "Modified Title"
        csum2 = chk.calculate_checksum()
        self.assertNotEqual(csum1, csum2)

    def test_checkpoint_save_and_load(self) -> None:
        ok, msg, chk = self.engine.checkpoint_session(
            session_id="sess-alpha",
            username="operator",
            source_seat="seat0",
        )
        self.assertTrue(ok)
        self.assertIn("checkpointed successfully", msg)
        self.assertIsNotNone(chk)

        # Load back
        loaded = self.engine.store.load_checkpoint("sess-alpha")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.session_id, "sess-alpha")
        self.assertEqual(loaded.username, "operator")
        self.assertGreaterEqual(len(loaded.windows), 1)

    def test_corrupt_checkpoint_tamper_detection(self) -> None:
        ok, _, chk = self.engine.checkpoint_session(session_id="sess-tamper")
        self.assertTrue(ok)

        chk_path = os.path.join(self.tmpdir.name, "sess-tamper", "checkpoint.json")
        with open(chk_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Tamper with username while keeping old checksum
        data["username"] = "attacker"
        with open(chk_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        # Loading tampered checkpoint should fail checksum validation
        loaded = self.engine.store.load_checkpoint("sess-tamper")
        self.assertIsNone(loaded)

    def test_restore_session(self) -> None:
        self.engine.checkpoint_session(session_id="sess-restore-test")
        ok, msg = self.engine.restore_session(session_id="sess-restore-test", target_seat="seat1")
        self.assertTrue(ok)
        self.assertIn("restored on seat 'seat1'", msg)

        # Non-existent session
        ok_bad, msg_bad = self.engine.restore_session(session_id="sess-nonexistent")
        self.assertFalse(ok_bad)
        self.assertIn("No valid checkpoint found", msg_bad)

    def test_migrate_session(self) -> None:
        ok, msg = self.engine.migrate_session(
            session_id="sess-mig-01",
            target_node="blade-02",
            target_seat="seat0",
            username="mios",
        )
        self.assertTrue(ok)
        self.assertIn("migrated from blade-01 to blade-02", msg)

    def test_cli_execution(self) -> None:
        # CLI --checkpoint
        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            ret = session_migrate.main([
                "--checkpoint",
                "--session-id", "cli-sess-01",
                "--user", "mios",
                "--sessions-dir", self.tmpdir.name,
                "--json",
                "--mock",
            ])
            self.assertEqual(ret, 0)
            data = json.loads(stdout_buf.getvalue())
            self.assertTrue(data["success"])

        # CLI --list-sessions
        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            ret = session_migrate.main([
                "--list-sessions",
                "--sessions-dir", self.tmpdir.name,
                "--json",
                "--mock",
            ])
            self.assertEqual(ret, 0)
            data = json.loads(stdout_buf.getvalue())
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["session_id"], "cli-sess-01")

        # CLI --restore
        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            ret = session_migrate.main([
                "--restore",
                "--session-id", "cli-sess-01",
                "--seat", "seat0",
                "--sessions-dir", self.tmpdir.name,
                "--json",
                "--mock",
            ])
            self.assertEqual(ret, 0)
            data = json.loads(stdout_buf.getvalue())
            self.assertTrue(data["success"])


if __name__ == "__main__":
    unittest.main()
