#!/usr/bin/env python3
# AI-hint: Automated unit test suite for CycloneDX/SPDX SBOM Generation & Cosign Attestation (T-711, T-712).
# AI-related: usr/libexec/mios/sec/sbom_gen.py, tests/test-sbom-gen.py
"""Automated unit test suite for MiOS SBOM Generator."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "sec"))

from sbom_gen import SBOMGenerator


class TestSBOMGen(unittest.TestCase):
    def setUp(self):
        self.gen = SBOMGenerator(dry_run=True)

    def test_sbom_generation_with_100_percent_package_inventory(self):
        """Test SBOM includes all scanned packages and generates valid Cosign signature."""
        pkgs = [f"rpm_pkg_{i}" for i in range(50)] + [f"wheel_{i}" for i in range(20)]
        res = self.gen.generate_image_sbom(pkgs)
        self.assertEqual(res.total_packages_scanned, 70)
        self.assertTrue(res.is_signature_valid)
        self.assertTrue(res.cosign_attestation_signature.startswith("cosign_sig_"))


if __name__ == "__main__":
    unittest.main()
