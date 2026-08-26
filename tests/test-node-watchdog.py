#!/usr/bin/env python3
# AI-hint: Automated unit test suite for T-400 hardware watchdog timer integration with safe 'V' close.
# AI-related: usr/libexec/mios/node/watchdog.py, src/mios-rs/mios-node/src/watchdog.rs
"""Automated tests for WS-NODE hardware watchdog supervisor, keepalive pinging, and magic close ('V')."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_WATCHDOG_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "node", "watchdog.py")

spec = importlib.util.spec_from_file_location("watchdog", _WATCHDOG_PATH)
if spec and spec.loader:
    watchdog = importlib.util.module_from_spec(spec)
    sys.modules["watchdog"] = watchdog
    sys.modules["usr.libexec.mios.node.watchdog"] = watchdog
    spec.loader.exec_module(watchdog)
else:
    raise ImportError(f"Could not load watchdog module from {_WATCHDOG_PATH}")


class TestNodeWatchdog(unittest.TestCase):
    """Validates watchdog supervisor, keepalive pings, and safe 'V' magic close."""

    def test_mock_watchdog_lifecycle(self):
        config = watchdog.WatchdogConfig(enabled=True, timeout_secs=30)
        mock_driver = watchdog.MockWatchdogDriver(simulated_present=True, timeout_secs=30)
        supervisor = watchdog.WatchdogSupervisor(config=config, driver=mock_driver)

        self.assertTrue(supervisor.is_present())
        self.assertFalse(supervisor.is_armed())

        # Arm
        self.assertTrue(supervisor.arm())
        self.assertTrue(supervisor.is_armed())

        # Ping 3 times
        self.assertTrue(supervisor.ping())
        self.assertTrue(supervisor.ping())
        self.assertTrue(supervisor.ping())
        self.assertEqual(mock_driver.ping_count, 3)
        self.assertFalse(mock_driver.disarmed_safely)

        # Disarm safely with 'V'
        self.assertTrue(supervisor.disarm())
        self.assertFalse(supervisor.is_armed())
        self.assertTrue(mock_driver.disarmed_safely)

        # Ping after disarm fails
        self.assertFalse(supervisor.ping())

    def test_linux_watchdog_absence_graceful_detection(self):
        driver = watchdog.LinuxHardwareWatchdog(device_path="/tmp/nonexistent_watchdog_dev", timeout_secs=30)
        self.assertFalse(driver.is_hardware_present())
        self.assertFalse(driver.is_armed())
        with self.assertRaises(FileNotFoundError):
            driver.arm()


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNodeWatchdog)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
