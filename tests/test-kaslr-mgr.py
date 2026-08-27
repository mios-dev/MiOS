#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Early EFI KASLR Entropy & Address Space Variance (T-701, T-702).
# AI-related: usr/libexec/mios/sec/kaslr_mgr.py, tests/test-kaslr-mgr.py
"""Automated unit test suite for MiOS KASLR Randomizer Manager."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "sec"))

from kaslr_mgr import MIN_KASLR_ENTROPY_BITS, KASLRRandomizerManager

class TestKASLRMgr(unittest.TestCase):
    def setUp(self):
        self.mgr = KASLRRandomizerManager(dry_run=True)

    def test_kaslr_boot_address_randomization(self):
        """Test sampling kernel base address generates 2MB-aligned random offset."""
        sample = self.mgr.sample_boot_kernel_base(1)
        self.assertTrue(sample.text_base_address_hex.startswith("0xffffffff"))
        self.assertEqual(sample.offset_bytes % (2 * 1024 * 1024), 0)

    def test_15_reboots_yield_zero_duplicate_addresses_and_high_entropy(self):
        """Test 15 consecutive boot cycles yield zero duplicate base addresses and >28 bits entropy."""
        samples = [self.mgr.sample_boot_kernel_base(i) for i in range(15)]
        addresses = [s.text_base_address_hex for s in samples]
        self.assertEqual(len(set(addresses)), 15)  # 0 duplicates
        entropy = self.mgr.compute_address_variance_entropy(samples)
        self.assertGreaterEqual(entropy, MIN_KASLR_ENTROPY_BITS)

if __name__ == "__main__":
    unittest.main()
