#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Medusa Tree-Attention Speculative Decoding (T-695, T-696).
# AI-related: usr/lib/mios/ai/medusa_tree.py, tests/test-medusa-tree.py
"""Automated unit test suite for MiOS Medusa Tree Engine."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "lib", "mios", "ai"))

from medusa_tree import MIN_MEDUSA_SPEEDUP, MedusaTreeEngine


class TestMedusaTree(unittest.TestCase):
    def setUp(self):
        self.engine = MedusaTreeEngine(num_heads=4, dry_run=True)

    def test_medusa_speedup_exceeds_2_5x_target(self):
        """Test Medusa tree attention achieves >=2.5x generation speedup."""
        res = self.engine.generate_with_tree_attention("def quicksort(arr):", target_tokens=100)
        self.assertGreaterEqual(res.speedup_ratio, MIN_MEDUSA_SPEEDUP)
        self.assertTrue(res.exact_parity_verified)

    def test_mathematical_token_parity_verified(self):
        """Test generated tokens strictly match baseline autoregressive output."""
        res = self.engine.generate_with_tree_attention("import numpy as np", target_tokens=40)
        self.assertTrue(res.exact_parity_verified)
        self.assertEqual(res.tokens_generated, 40)


if __name__ == "__main__":
    unittest.main()
