#!/usr/bin/env python3
# AI-hint: Automated unit test suite for T-563 Hardware Netlink Inventory Monitor.
# AI-related: usr/libexec/mios/hw/inventory_monitor.py, tests/test-inventory-monitor.py
"""Automated unit test suite for Hardware Netlink Inventory Monitor (T-563)."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_MODULE_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "hw", "inventory_monitor.py")

spec = importlib.util.spec_from_file_location("inventory_monitor", _MODULE_PATH)
if spec and spec.loader:
    inventory_monitor = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = inventory_monitor
    spec.loader.exec_module(inventory_monitor)
else:
    raise ImportError(f"Could not load inventory_monitor module from {_MODULE_PATH}")

class TestInventoryMonitor(unittest.TestCase):
    """Validates sysfs inventory enumeration, netlink packet decoding, and uevent processing."""

    def setUp(self) -> None:
        self.monitor = inventory_monitor.HardwareInventoryMonitor(mock=True)
        self.tmp_dir = tempfile.mkdtemp(prefix="mios_test_hw_")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_scan_mock_inventory(self) -> None:
        """Asserts discovery of mock GPU and NVMe hardware devices."""
        devices = self.monitor.scan_sysfs_inventory()
        self.assertEqual(len(devices), 2)

        gpu = next(d for d in devices if d.vendor_id == "10de")
        self.assertEqual(gpu.device_id, "2684")
        self.assertEqual(gpu.current_link_width, 16)
        self.assertFalse(gpu.is_degraded()[0])

    def test_parse_raw_netlink_packet(self) -> None:
        """Asserts decoding of raw null-delimited netlink uevent packet."""
        raw_packet = b"add@/devices/pci0000:00/0000:00:01.0\x00ACTION=add\x00DEVPATH=/devices/pci0000:00/0000:00:01.0\x00SUBSYSTEM=pci\x00PCI_ID=10de:2684\x00"
        parsed = self.monitor.parse_raw_netlink_packet(raw_packet)
        self.assertEqual(parsed["ACTION"], "add")
        self.assertEqual(parsed["SUBSYSTEM"], "pci")
        self.assertEqual(parsed["PCI_ID"], "10de:2684")

    def test_process_uevent_lifecycle(self) -> None:
        """Asserts state transition upon receiving add and remove uevents."""
        # Process remove
        rem_event = self.monitor.process_uevent_dict({
            "ACTION": "remove",
            "SUBSYSTEM": "pci",
            "DEVPATH": "/devices/pci0000:00/0000:00:01.0/0000:01:00.0",
        })
        self.assertEqual(rem_event.action, "remove")
        dev = self.monitor._mock_inventory["/sys/devices/pci0000:00/0000:00:01.0/0000:01:00.0"]
        self.assertEqual(dev.status, "removed")

    def test_listen_netlink_mock(self) -> None:
        """Asserts netlink generator in mock mode."""
        events = list(self.monitor.listen_netlink())
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].subsystem, "pci")

    def test_cli_scan_json(self) -> None:
        """Asserts CLI execution with --scan --mock --json."""
        with patch("sys.argv", ["inventory_monitor.py", "--scan", "--mock", "--json"]):
            with patch("builtins.print") as mock_print:
                ret = inventory_monitor.main()
                self.assertEqual(ret, 0)
                mock_print.assert_called()
                parsed = json.loads(mock_print.call_args[0][0])
                self.assertEqual(parsed["status"], "ok")
                self.assertIn("inventory", parsed)

if __name__ == "__main__":
    unittest.main()
