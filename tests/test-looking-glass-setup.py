#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-VFIO Looking Glass B6 IVSHMEM and VFIO setup.
# AI-related: usr/libexec/mios/vfio/setup-looking-glass.py, usr/share/doc/mios/manual/ch21-looking-glass-b7-and-kvmfr.md
"""Automated tests for WS-VFIO Looking Glass IVSHMEM XML generation and shared memory validation."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_VFIO_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "vfio", "setup-looking-glass.py")

spec = importlib.util.spec_from_file_location("setup_looking_glass", _VFIO_PATH)
if spec and spec.loader:
    setup_looking_glass = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = setup_looking_glass
    spec.loader.exec_module(setup_looking_glass)
else:
    raise ImportError(f"Could not load setup-looking-glass module from {_VFIO_PATH}")


class TestLookingGlassSetup(unittest.TestCase):
    """Validates Looking Glass IVSHMEM XML generation and memory allocation checks."""

    def test_ivshmem_xml_generation(self):
        lg = setup_looking_glass.LookingGlassManager(size_mb=128)
        xml = lg.generate_ivshmem_xml()
        self.assertIn('<shmem name="looking-glass">', xml)
        self.assertIn('<model type="ivshmem-plain"/>', xml)
        self.assertIn('<size unit="M">128</size>', xml)

    def test_mock_shm_validation(self):
        lg = setup_looking_glass.LookingGlassManager()
        self.assertTrue(lg.validate_shm_allocation(mock=True))

    def test_mock_kvmfr_validation(self):
        lg = setup_looking_glass.LookingGlassManager()
        self.assertTrue(lg.validate_kvmfr_device(mock=True))

    def test_verify_all_mock(self):
        lg = setup_looking_glass.LookingGlassManager(size_mb=64)
        res = lg.verify_all(mock=True)
        self.assertEqual(res["status"], "pass")
        self.assertEqual(res["checks"]["shm_allocation"], "pass")
        self.assertEqual(res["checks"]["kvmfr_device"], "pass")

    def test_service_unit_file(self):
        svc_path = os.path.join(_ROOT, "usr", "lib", "systemd", "system", "mios-vfio-setup.service")
        self.assertTrue(os.path.exists(svc_path), f"Service file missing at {svc_path}")
        with open(svc_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("setup-looking-glass.py --verify", content)
        self.assertIn("[Install]", content)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestLookingGlassSetup)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
