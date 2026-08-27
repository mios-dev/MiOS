#!/usr/bin/env python3
# AI-hint: Automated unit test suite for T-564 PCIe Link Width & Speed Degradation Detector.
# AI-related: usr/libexec/mios/hw/inventory_monitor.py, tests/test-hw-degrade.py
"""Automated unit test suite for PCIe Link Width & Speed Degradation Detector (T-564)."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
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


class TestHwDegrade(unittest.TestCase):
    """Validates detection of PCIe link width degradation, bus speed drops, and anomaly alerts."""

    def setUp(self) -> None:
        self.monitor = inventory_monitor.HardwareInventoryMonitor(mock=True)

    def test_healthy_pcie_device(self) -> None:
        """Asserts healthy PCIe link report when width and speed match maximum capability."""
        dev = inventory_monitor.HardwareDevice(
            sys_path="/sys/devices/pci0000:00/0000:00:01.0/0000:01:00.0",
            subsystem="pci",
            vendor_id="10de",
            device_id="2684",
            device_name="NVIDIA GeForce RTX 4090",
            current_link_width=16,
            max_link_width=16,
            current_link_speed="16.0 GT/s",
            max_link_speed="16.0 GT/s",
        )
        is_deg, reasons = dev.is_degraded()
        self.assertFalse(is_deg)
        self.assertEqual(len(reasons), 0)

    def test_degraded_pcie_link_width(self) -> None:
        """Asserts detection when GPU x16 link drops to x1 or x4 due to slot seating/power issues."""
        dev = inventory_monitor.HardwareDevice(
            sys_path="/sys/devices/pci0000:00/0000:00:01.0/0000:01:00.0",
            subsystem="pci",
            vendor_id="10de",
            device_id="2684",
            device_name="NVIDIA GeForce RTX 4090",
            current_link_width=1,
            max_link_width=16,
            current_link_speed="16.0 GT/s",
            max_link_speed="16.0 GT/s",
        )
        is_deg, reasons = dev.is_degraded()
        self.assertTrue(is_deg)
        self.assertEqual(len(reasons), 1)
        self.assertIn("link width degraded", reasons[0])
        self.assertIn("x1", reasons[0])

    def test_degraded_pcie_link_speed(self) -> None:
        """Asserts detection when PCIe Gen4 link drops from 16.0 GT/s to 2.5 GT/s."""
        dev = inventory_monitor.HardwareDevice(
            sys_path="/sys/devices/pci0000:00/0000:00:01.1/0000:02:00.0",
            subsystem="nvme",
            vendor_id="144d",
            device_id="a808",
            device_name="Samsung 980 PRO NVMe SSD",
            current_link_width=4,
            max_link_width=4,
            current_link_speed="2.5 GT/s",
            max_link_speed="16.0 GT/s",
        )
        is_deg, reasons = dev.is_degraded()
        self.assertTrue(is_deg)
        self.assertEqual(len(reasons), 1)
        self.assertIn("link speed degraded", reasons[0])

    def test_detect_degraded_devices_in_inventory(self) -> None:
        """Asserts inventory scan filters degraded devices correctly."""
        # Inject degraded NVMe into mock inventory
        self.monitor._mock_inventory["/sys/devices/pci0000:00/0000:00:01.1/0000:02:00.0"].current_link_width = 1

        degraded = self.monitor.detect_degraded_devices()
        self.assertEqual(len(degraded), 1)
        dev, reasons = degraded[0]
        self.assertEqual(dev.device_id, "a808")
        self.assertTrue(any("link width degraded" in r for r in reasons))

    def test_cli_check_degraded_healthy(self) -> None:
        """Asserts CLI exit code 0 when all devices are healthy."""
        with patch("sys.argv", ["inventory_monitor.py", "--check-degraded", "--mock", "--json"]):
            with patch("builtins.print") as mock_print:
                ret = inventory_monitor.main()
                self.assertEqual(ret, 0)
                mock_print.assert_called()
                parsed = json.loads(mock_print.call_args[0][0])
                self.assertEqual(parsed["status"], "healthy")

    def test_cli_check_degraded_detected(self) -> None:
        """Asserts CLI exit code 2 when degraded devices are detected."""
        # Degrade mock GPU
        self.monitor._mock_inventory["/sys/devices/pci0000:00/0000:00:01.0/0000:01:00.0"].current_link_width = 4

        with patch.object(inventory_monitor, "HardwareInventoryMonitor", return_value=self.monitor):
            with patch("sys.argv", ["inventory_monitor.py", "--check-degraded", "--mock", "--json"]):
                with patch("builtins.print") as mock_print:
                    ret = inventory_monitor.main()
                    self.assertEqual(ret, 2)
                    parsed = json.loads(mock_print.call_args[0][0])
                    self.assertEqual(parsed["status"], "degraded")
                    self.assertEqual(len(parsed["degraded_devices"]), 1)


if __name__ == "__main__":
    unittest.main()
