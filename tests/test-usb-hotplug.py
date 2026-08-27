#!/usr/bin/env python3
# AI-hint: Automated unit test suite for T-422 USB controller and DAC hotplug manager.
# AI-related: usr/libexec/mios/hw/usb_hotplug.py, usr/lib/udev/rules.d/90-mios-usb-passthrough.rules
"""Automated tests for MiOS USB Controller & DAC Hotplug Passthrough Manager (T-422)."""

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
_MODULE_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "hw", "usb_hotplug.py")

spec = importlib.util.spec_from_file_location("usb_hotplug", _MODULE_PATH)
if spec and spec.loader:
    usb_hotplug = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = usb_hotplug
    spec.loader.exec_module(usb_hotplug)
else:
    raise ImportError(f"Could not load usb_hotplug module from {_MODULE_PATH}")

class TestUSBHotplug(unittest.TestCase):
    """Validates USB topology scanning, device classification, host peripheral exclusion, and XML generation."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp(prefix="mios_test_usb_")
        self.sysfs_root = self.tmp_dir
        self.usb_dir = os.path.join(self.sysfs_root, "sys", "bus", "usb", "devices")
        os.makedirs(self.usb_dir, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _create_usb_device(
        self,
        dev_name: str,
        vid: str,
        pid: str,
        product: str = "Device",
        manufacturer: str = "Vendor",
        dev_class: str = "00",
        interfaces: list[tuple[str, str, str]] | None = None,
    ) -> str:
        dpath = os.path.join(self.usb_dir, dev_name)
        os.makedirs(dpath, exist_ok=True)
        with open(os.path.join(dpath, "idVendor"), "w") as f:
            f.write(f"{vid}\n")
        with open(os.path.join(dpath, "idProduct"), "w") as f:
            f.write(f"{pid}\n")
        with open(os.path.join(dpath, "product"), "w") as f:
            f.write(f"{product}\n")
        with open(os.path.join(dpath, "manufacturer"), "w") as f:
            f.write(f"{manufacturer}\n")
        with open(os.path.join(dpath, "bDeviceClass"), "w") as f:
            f.write(f"{dev_class}\n")
        with open(os.path.join(dpath, "busnum"), "w") as f:
            f.write("1\n")
        with open(os.path.join(dpath, "devnum"), "w") as f:
            f.write("2\n")

        if interfaces:
            for idx, (iclass, isub, iproto) in enumerate(interfaces):
                ipath = os.path.join(dpath, f"iface_{idx}.0")
                os.makedirs(ipath, exist_ok=True)
                with open(os.path.join(ipath, "bInterfaceClass"), "w") as f:
                    f.write(f"{iclass}\n")
                with open(os.path.join(ipath, "bInterfaceSubClass"), "w") as f:
                    f.write(f"{isub}\n")
                with open(os.path.join(ipath, "bInterfaceProtocol"), "w") as f:
                    f.write(f"{iproto}\n")
        return dpath

    def test_scan_and_classify_controllers(self) -> None:
        # Xbox Controller
        self._create_usb_device("1-1", "045e", "028e", product="Xbox 360 Controller", manufacturer="Microsoft")
        # DualSense Controller
        self._create_usb_device("1-2", "054c", "0ce6", product="Wireless Controller", manufacturer="Sony")
        # Switch Pro Controller
        self._create_usb_device("1-3", "057e", "2009", product="Pro Controller", manufacturer="Nintendo")

        mgr = usb_hotplug.USBHotplugManager(sysfs_root=self.sysfs_root)
        devices = mgr.scan_usb_devices()
        self.assertEqual(len(devices), 3)

        for dev in devices:
            classification = mgr.classify_device(dev)
            self.assertEqual(classification["category"], "gamepad")
            self.assertTrue(classification["eligible_for_passthrough"])

    def test_scan_and_classify_audio_dac(self) -> None:
        # Focusrite Scarlett DAC
        self._create_usb_device("1-4", "1235", "8210", product="Scarlett 2i2 USB", manufacturer="Focusrite")
        # Generic USB Audio Class device
        self._create_usb_device(
            "1-5",
            "9999",
            "8888",
            product="Custom HiFi DAC",
            manufacturer="Audiophile",
            interfaces=[("01", "01", "00"), ("01", "02", "00")],
        )

        mgr = usb_hotplug.USBHotplugManager(sysfs_root=self.sysfs_root)
        devices = mgr.scan_usb_devices()
        self.assertEqual(len(devices), 2)

        for dev in devices:
            classification = mgr.classify_device(dev)
            self.assertEqual(classification["category"], "audio_dac")
            self.assertTrue(classification["eligible_for_passthrough"])

    def test_host_keyboard_and_mouse_exclusion_invariant(self) -> None:
        """Enforces: Do NOT hotplug host keyboards or mice that would lock the operator out of the host OS."""
        # Host Keyboard (HID class 03, subclass 01, proto 01)
        self._create_usb_device(
            "1-6",
            "046d",
            "c31c",
            product="USB Mechanical Keyboard",
            manufacturer="Logitech",
            interfaces=[("03", "01", "01")],
        )
        # Host Mouse (HID class 03, subclass 01, proto 02)
        self._create_usb_device(
            "1-7",
            "1532",
            "0084",
            product="DeathAdder Mouse",
            manufacturer="Razer",
            interfaces=[("03", "01", "02")],
        )

        mgr = usb_hotplug.USBHotplugManager(sysfs_root=self.sysfs_root)
        devices = mgr.scan_usb_devices()
        self.assertEqual(len(devices), 2)

        for dev in devices:
            self.assertTrue(mgr.is_host_keyboard_or_mouse(dev))
            classification = mgr.classify_device(dev)
            self.assertEqual(classification["category"], "host_input")
            self.assertFalse(classification["eligible_for_passthrough"])

        # Test attach rejection
        attach_res = mgr.attach_device("win11", "046d", "c31c")
        self.assertEqual(attach_res["status"], "rejected")
        self.assertIn("Cannot attach host keyboard or mouse", attach_res["reason"])

    def test_hostdev_xml_generation(self) -> None:
        mgr = usb_hotplug.USBHotplugManager(sysfs_root=self.sysfs_root)
        xml = mgr.generate_hostdev_xml("045e", "028e", bus=1, device=4)
        self.assertIn("<vendor id='0x045e'/>", xml)
        self.assertIn("<product id='0x028e'/>", xml)
        self.assertIn("<address bus='1' device='4'/>", xml)

    def test_udev_rules_generation(self) -> None:
        mgr = usb_hotplug.USBHotplugManager(sysfs_root=self.sysfs_root)
        rules = mgr.generate_udev_rules(domain="gaming-vm")
        self.assertIn('ATTR{idVendor}=="045e"', rules)
        self.assertIn('ATTR{idVendor}=="054c"', rules)
        self.assertIn('ATTR{idVendor}=="1235"', rules)
        self.assertIn('--domain=gaming-vm', rules)

    def test_8bitdo_and_logitech_gamepads(self) -> None:
        # 8BitDo Ultimate Controller (2dc8:3106)
        self._create_usb_device("1-8", "2dc8", "3106", product="8BitDo Ultimate", manufacturer="8BitDo")
        # Logitech F310 Gamepad (046d:c216)
        self._create_usb_device("1-9", "046d", "c216", product="Logitech Gamepad F310", manufacturer="Logitech")

        mgr = usb_hotplug.USBHotplugManager(sysfs_root=self.sysfs_root)
        devices = mgr.scan_usb_devices()
        self.assertEqual(len(devices), 2)

        for dev in devices:
            cl = mgr.classify_device(dev)
            self.assertEqual(cl["category"], "gamepad")
            self.assertTrue(cl["eligible_for_passthrough"])

    def test_dry_run_attach_and_detach(self) -> None:
        mgr = usb_hotplug.USBHotplugManager(sysfs_root=self.sysfs_root, dry_run=True)
        res_attach = mgr.attach_device("win11", "045e", "028e", bus=2, device=5)
        self.assertEqual(res_attach["status"], "simulated")
        self.assertIn("<vendor id='0x045e'/>", res_attach["xml"])
        self.assertIn("<address bus='2' device='5'/>", res_attach["xml"])

        res_detach = mgr.detach_device("win11", "045e", "028e", bus=2, device=5)
        self.assertEqual(res_detach["status"], "simulated")
        self.assertIn("<vendor id='0x045e'/>", res_detach["xml"])

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUSBHotplug)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
