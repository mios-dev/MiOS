#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Multi-source Hardware TRNG Entropy Seeder (T-679, T-680).
# AI-related: usr/libexec/mios/sec/entropy_seed.py, tests/test-entropy-seed.py
"""Automated unit test suite for MiOS Hardware Entropy Seeder."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "sec"))

from entropy_seed import HardwareEntropySeeder

class TestEntropySeed(unittest.TestCase):
    def setUp(self):
        self.seeder = HardwareEntropySeeder(dry_run=True)

    def test_multi_source_entropy_harvesting(self):
        """Test harvesting combines CPU RDSEED, TPM 2.0 TRNG, and JitterEntropy."""
        res = self.seeder.harvest_and_seed_entropy(mock_bytes_count=512)
        self.assertEqual(len(res.sources_harvested), 3)
        self.assertEqual(res.bits_injected, 512 * 8)

    def test_shannon_entropy_density_and_compliance(self):
        """Test conditioned entropy achieves >7.85 bits/byte and passes NIST compliance."""
        res = self.seeder.harvest_and_seed_entropy(mock_bytes_count=2048)
        self.assertTrue(res.is_nist_compliant)
        self.assertGreaterEqual(res.shannon_entropy, 7.85)

if __name__ == "__main__":
    unittest.main()
