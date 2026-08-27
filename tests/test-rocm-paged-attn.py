#!/usr/bin/env python3
# AI-hint: Automated unit test suite for AMD ROCm PagedAttention Capacity & Concurrency (T-731, T-732).
# AI-related: usr/lib/mios/ai/rocm_paged_attn.py, tests/test-rocm-paged-attn.py
"""Automated unit test suite for MiOS ROCm PagedAttention Manager."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "lib", "mios", "ai"))

from rocm_paged_attn import MIN_VRAM_UTILIZATION_PCT, ROCmPagedAttentionManager


class TestROCMPagedAttn(unittest.TestCase):
    def setUp(self):
        self.mgr = ROCmPagedAttentionManager(block_size=16, dry_run=True)

    def test_50_concurrent_streams_reach_over_92_percent_vram_efficiency(self):
        """Test sustaining 50 concurrent streams achieves >92% VRAM utilization with 0 OOMs."""
        res = self.mgr.allocate_and_benchmark_streams(50)
        self.assertEqual(res.concurrent_streams, 50)
        self.assertEqual(res.oom_errors_count, 0)
        self.assertGreaterEqual(res.vram_utilization_pct, MIN_VRAM_UTILIZATION_PCT)
        self.assertTrue(res.output_parity_verified)


if __name__ == "__main__":
    unittest.main()
