#!/usr/bin/env python3
# AI-hint: Automated test suite for MiOS Dynamic Runtime VFIO Device Unbind and Rebind Utility (T-414).
# AI-related: usr/libexec/mios/virt/vfio_bind.py, usr/share/doc/mios/manual/ch21-looking-glass-b7-and-kvmfr.md
"""
Automated unit tests for VFIO dynamic runtime unbind/rebind, primary display guard,
slot-sibling coordination, and driver_override management.
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
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "virt", "vfio_bind.py")

spec = importlib.util.spec_from_file_location("vfio_bind", _TARGET_PATH)
if spec and spec.loader:
    vfio_bind = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = vfio_bind
    spec.loader.exec_module(vfio_bind)
else:
    raise ImportError(f"Could not load vfio_bind module from {_TARGET_PATH}")

class TestVFIOBind(unittest.TestCase):
    """Tests VFIO dynamic binding, primary display protection, and sysfs state transitions."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="mios-test-vfio-")

    def tearDown(self) -> None:
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _setup_synthetic_gpu(
        self,
        sysfs_root: str,
        bdf_vga: str = "0000:01:00.0",
        bdf_audio: str = "0000:01:00.1",
        primary_vga: bool = False,
        initial_driver: str = "nvidia",
    ) -> None:
        # Create driver dirs
        for drv in ["nvidia", "snd_hda_intel", "vfio-pci", "amdgpu", "i915"]:
            os.makedirs(os.path.join(sysfs_root, "bus", "pci", "drivers", drv), exist_ok=True)
            with open(os.path.join(sysfs_root, "bus", "pci", "drivers", drv, "bind"), "w", encoding="utf-8") as f:
                f.write("")
            with open(os.path.join(sysfs_root, "bus", "pci", "drivers", drv, "unbind"), "w", encoding="utf-8") as f:
                f.write("")

        # Create device dirs
        for bdf, dev_id, class_code, drv, is_boot in [
            (bdf_vga, "0x2484", "0x030000", initial_driver, primary_vga),
            (bdf_audio, "0x228b", "0x040300", "snd_hda_intel", False),
        ]:
            fs_bdf = vfio_bind.sanitize_bdf_for_fs(bdf)
            dev_dir = os.path.join(sysfs_root, "bus", "pci", "devices", fs_bdf)
            os.makedirs(dev_dir, exist_ok=True)
            with open(os.path.join(dev_dir, "vendor"), "w", encoding="utf-8") as f:
                f.write("0x10de\n")
            with open(os.path.join(dev_dir, "device"), "w", encoding="utf-8") as f:
                f.write(f"{dev_id}\n")
            with open(os.path.join(dev_dir, "class"), "w", encoding="utf-8") as f:
                f.write(f"{class_code}\n")
            with open(os.path.join(dev_dir, "boot_vga"), "w", encoding="utf-8") as f:
                f.write(f"{'1' if is_boot else '0'}\n")
            with open(os.path.join(dev_dir, "driver_override"), "w", encoding="utf-8") as f:
                f.write("(null)\n")
            with open(os.path.join(dev_dir, "current_driver"), "w", encoding="utf-8") as f:
                f.write(f"{drv}\n")

    def test_bdf_normalization(self) -> None:
        self.assertEqual(vfio_bind.normalize_bdf("0000:01:00.0"), "0000:01:00.0")
        self.assertEqual(vfio_bind.normalize_bdf("01:00.1"), "0000:01:00.1")
        self.assertEqual(vfio_bind.normalize_bdf("0000_02_00.0"), "0000:02:00.0")
        with self.assertRaises(ValueError):
            vfio_bind.normalize_bdf("invalid-format")

    def test_mock_bind_and_rebind(self) -> None:
        binder = vfio_bind.VFIOBinder(mock=True)
        res_vfio = binder.bind_to_vfio("0000:01:00.0")
        self.assertEqual(res_vfio["status"], "success")
        self.assertTrue(res_vfio["bound"])
        self.assertEqual(res_vfio["target_driver"], "vfio-pci")

        res_host = binder.rebind_to_host("0000:01:00.0", host_driver="nvidia")
        self.assertEqual(res_host["status"], "success")
        self.assertTrue(res_host["bound"])

    def test_primary_gpu_unbind_refused_without_force(self) -> None:
        self._setup_synthetic_gpu(self.temp_dir, primary_vga=True)
        binder = vfio_bind.VFIOBinder(sysfs_root=self.temp_dir, mock=False)

        res = binder.bind_to_vfio("0000:01:00.0", force=False)
        self.assertEqual(res["status"], "refused")
        self.assertFalse(res["bound"])
        self.assertIn("primary host display", res["error"])
        self.assertIn("Wayland", res["error"])

    def test_primary_gpu_unbind_succeeds_with_force(self) -> None:
        self._setup_synthetic_gpu(self.temp_dir, primary_vga=True)
        binder = vfio_bind.VFIOBinder(sysfs_root=self.temp_dir, mock=False)

        res = binder.bind_to_vfio("0000:01:00.0", force=True)
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["bound"])

    def test_synthetic_full_bind_unbind_cycle(self) -> None:
        # Set up secondary GPU (VGA + Audio companion)
        self._setup_synthetic_gpu(self.temp_dir, primary_vga=False, initial_driver="nvidia")
        binder = vfio_bind.VFIOBinder(sysfs_root=self.temp_dir, mock=False)

        # Check initial status
        st = binder.get_status("0000:01:00.0")
        self.assertFalse(st["is_primary_gpu"])
        self.assertEqual(len(st["slot_devices"]), 2)

        # 1. Bind to VFIO
        res_vfio = binder.bind_to_vfio("0000:01:00.0")
        self.assertEqual(res_vfio["status"], "success")
        self.assertEqual(len(res_vfio["siblings"]), 2)

        # Verify driver_override file on disk
        vga_fs = vfio_bind.sanitize_bdf_for_fs("0000:01:00.0")
        override_file = os.path.join(self.temp_dir, "bus", "pci", "devices", vga_fs, "driver_override")
        with open(override_file, "r", encoding="utf-8") as f:
            self.assertEqual(f.read().strip(), "vfio-pci")

        # 2. Rebind back to host drivers
        res_host = binder.rebind_to_host("0000:01:00.0", host_driver="nvidia")
        self.assertEqual(res_host["status"], "success")
        self.assertEqual(len(res_host["siblings"]), 2)

        # Verify driver_override cleared on disk
        with open(override_file, "r", encoding="utf-8") as f:
            self.assertEqual(f.read().strip(), "")

    def test_status_json_structure(self) -> None:
        binder = vfio_bind.VFIOBinder(mock=True)
        st = binder.get_status("0000:01:00.0")
        self.assertIn("target_bdf", st)
        self.assertIn("is_primary_gpu", st)
        self.assertIn("slot_devices", st)
        self.assertIsInstance(st["slot_devices"], list)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestVFIOBind)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
