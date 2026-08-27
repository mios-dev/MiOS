#!/usr/bin/env python3
# AI-hint: Unit test suite for MiOS GPU Slicing and Container Device Interface (CDI) engine (T-586 / AGY-2184).
# AI-related: usr/libexec/mios/hw/gpu_slice.py, usr/share/doc/mios/manual/virt.md
"""Unit and integration tests for GPUSliceManager and CDI generator."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "hw", "gpu_slice.py")

spec = importlib.util.spec_from_file_location("gpu_slice", _TARGET_PATH)
if spec and spec.loader:
    gpu_slice = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = gpu_slice
    spec.loader.exec_module(gpu_slice)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestGPUSliceManager(unittest.TestCase):
    """Test suite for GPU discovery, MIG slice configuration, and CDI spec generation."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="mios-test-gpuslice-")
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_gpu_discovery_mock(self):
        mgr = gpu_slice.GPUSliceManager(mock=True)
        gpus = mgr.discover_gpus()
        self.assertEqual(len(gpus), 2)
        self.assertEqual(gpus[0].vendor, "nvidia")
        self.assertTrue(gpus[0].mig_capable)
        self.assertEqual(gpus[1].vendor, "amd")

    def test_generate_cdi_spec_nvidia_mig(self):
        mgr = gpu_slice.GPUSliceManager(mock=True)
        gpus = mgr.discover_gpus()
        a100 = gpus[0]

        slices = ["1g.5gb", "2g.10gb"]
        out_file = self.root / "cdi" / "nvidia-mig.json"
        cdi = mgr.generate_cdi_spec(a100, slices=slices, output_file=str(out_file))

        self.assertEqual(cdi["cdiVersion"], "0.5.0")
        self.assertEqual(cdi["kind"], "nvidia.com/gpu")
        self.assertEqual(len(cdi["devices"]), 2)
        self.assertEqual(cdi["devices"][0]["name"], "mig-0-0")
        self.assertEqual(cdi["devices"][1]["name"], "mig-0-1")
        self.assertTrue(out_file.exists())

    def test_generate_cdi_spec_amd_rocm(self):
        mgr = gpu_slice.GPUSliceManager(mock=True)
        gpus = mgr.discover_gpus()
        radeon = gpus[1]

        cdi = mgr.generate_cdi_spec(radeon)
        self.assertEqual(cdi["cdiVersion"], "0.5.0")
        self.assertEqual(cdi["kind"], "amd.com/gpu")
        self.assertEqual(len(cdi["devices"]), 1)
        self.assertEqual(cdi["devices"][0]["name"], "gpu-1")
        self.assertIn("/dev/kfd", [d["path"] for d in cdi["devices"][0]["containerEdits"]["deviceNodes"]])

    def test_configure_slices_valid_and_invalid(self):
        mgr = gpu_slice.GPUSliceManager(mock=True)

        ok, msg = mgr.configure_slices(gpu_id=0, slice_profiles=["1g.5gb", "2g.10gb"])
        self.assertTrue(ok)
        self.assertIn("Successfully provisioned", msg)

        bad_ok, bad_msg = mgr.configure_slices(gpu_id=0, slice_profiles=["invalid_slice_999gb"])
        self.assertFalse(bad_ok)
        self.assertIn("Invalid MIG profile", bad_msg)

    def test_cli_execution_scan_mock(self):
        test_args = ["gpu_slice.py", "--scan", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = gpu_slice.main()
            self.assertEqual(exit_code, 0)

    def test_cli_execution_generate_cdi_mock(self):
        out_path = str(self.root / "test_cdi.json")
        test_args = ["gpu_slice.py", "--generate-cdi", "--gpu-id", "0", "--output", out_path, "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = gpu_slice.main()
            self.assertEqual(exit_code, 0)
            self.assertTrue(os.path.exists(out_path))

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGPUSliceManager)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
