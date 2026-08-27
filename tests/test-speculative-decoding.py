#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Speculative Decoding Draft Pairing & Adaptation (T-655, T-656).
# AI-related: usr/libexec/mios/ai/speculative.py, tests/test-speculative-decoding.py
"""Automated unit test suite for MiOS Speculative Decoding Manager."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "ai"))

from speculative import SpeculativeDraftManager

class TestSpeculativeDecoding(unittest.TestCase):
    def setUp(self):
        self.mgr = SpeculativeDraftManager(dry_run=True)

    def test_paired_draft_model_lookup(self):
        """Test Qwen-32B pairs with lightweight Qwen-0.5B draft model."""
        draft = self.mgr.get_draft_model("qwen2.5-32b-instruct.Q4_K_M.gguf")
        self.assertEqual(draft, "qwen2.5-0.5b-instruct.Q4_K_M.gguf")

    def test_adaptive_draft_length_scaling(self):
        """Test high acceptance rate expands draft length from 5 to 6."""
        model = "qwen2.5-32b-instruct.Q4_K_M.gguf"
        # Simulate high acceptance (5 of 5 accepted for 3 steps)
        for _ in range(3):
            new_len = self.mgr.update_acceptance_rate(model, accepted_tokens=5, drafted_tokens=5)
        self.assertGreaterEqual(new_len, 6)

    def test_speedup_benchmark_target(self):
        """Test speculative decoding model achieves >=2.5x generation acceleration."""
        res = self.mgr.benchmark_speedup("qwen2.5-32b-instruct.Q4_K_M.gguf")
        self.assertGreaterEqual(res["speedup_ratio"], 2.5)
        self.assertTrue(res["meets_target"])

if __name__ == "__main__":
    unittest.main()
