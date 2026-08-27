#!/usr/bin/env python3
# AI-hint: Automated unit test suite for system notification daemon and HITL alert bridge.
# AI-related: usr/libexec/mios/ux/notification_daemon.py, usr/share/mios/mios.toml
"""Unit and integration test suite for NotificationDaemonEngine and notification_daemon CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "ux", "notification_daemon.py")

spec = importlib.util.spec_from_file_location("notification_daemon", _TARGET_PATH)
if spec and spec.loader:
    notification_daemon = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = notification_daemon
    spec.loader.exec_module(notification_daemon)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestNotificationDaemon(unittest.TestCase):
    """Test suite for desktop notifications, rate limiting, and HITL alert dispatching."""

    def test_notification_message_dataclass(self):
        msg = notification_daemon.NotificationMessage(
            title="Bake Staged",
            body="3 changes approved",
            severity="critical",
            actions=["Approve", "Reject"],
        )
        self.assertEqual(msg.title, "Bake Staged")
        self.assertEqual(msg.severity, "critical")
        self.assertEqual(len(msg.actions), 2)

    def test_engine_send_mock(self):
        engine = notification_daemon.NotificationDaemonEngine(mock=True)
        msg = notification_daemon.NotificationMessage(title="Test Alert", body="Details")
        res = engine.send(msg)
        self.assertTrue(res["sent"])
        self.assertEqual(res["backend"], "mock_toast")
        self.assertIn("notification_id", res)
        self.assertEqual(len(engine.history), 1)

    def test_rate_limiter_enforcement(self):
        engine = notification_daemon.NotificationDaemonEngine(rate_limit_per_min=2, mock=True)
        msg = notification_daemon.NotificationMessage(title="Spam Test")
        res1 = engine.send(msg)
        self.assertTrue(res1["sent"])
        res2 = engine.send(msg)
        self.assertTrue(res2["sent"])
        res3 = engine.send(msg)
        self.assertFalse(res3["sent"])
        self.assertEqual(res3["reason"], "rate_limited")

    def test_run_daemon_loop_mock(self):
        engine = notification_daemon.NotificationDaemonEngine(mock=True)
        events = engine.run_daemon_loop(max_ticks=1)
        self.assertEqual(len(events), 1)
        self.assertTrue(events[0]["sent"])
        self.assertEqual(events[0]["message"]["severity"], "critical")

    def test_cli_send_mock(self):
        test_args = ["notification_daemon.py", "--title", "CLI Alert", "--body", "Action required", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = notification_daemon.main()
            self.assertEqual(exit_code, 0)

    def test_cli_listen_mock(self):
        test_args = ["notification_daemon.py", "--listen", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = notification_daemon.main()
            self.assertEqual(exit_code, 0)

    def test_cli_post_alias_mock(self):
        test_args = ["notification_daemon.py", "--post", "Quick message", "--level", "warn", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = notification_daemon.main()
            self.assertEqual(exit_code, 0)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNotificationDaemon)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
