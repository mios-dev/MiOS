#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Static CUDA Graph Capture & Replay Speedup (T-709, T-710).
# AI-related: usr/lib/mios/ai/cuda_graphs.py, tests/test-cuda-graphs.py
"""Automated unit test suite for MiOS CUDA Graph Manager."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "lib", "mios", "ai"))

from cuda_graphs import MIN_CUDA_GRAPH_SPEEDUP, CUDAGraphManager


class TestCUDAGraphs(unittest.TestCase):
    def setUp(self):
        self.mgr = CUDAGraphManager(dry_run=True)

    def test_cuda_graph_capture_under_1ms(self):
        """Test capturing CUDA Graph completes in <1.0ms."""
        cap_time = self.mgr.capture_graph_for_batch(1)
        self.assertLess(cap_time, 1.0)
        self.assertTrue(self.mgr.captured_graphs[1])

    def test_replay_achieves_greater_than_1_5x_speedup_with_exact_parity(self):
        """Test replay decoding achieves >1.5x speedup with bit parity verified."""
        for b in [1, 4, 16]:
            res = self.mgr.replay_graph_decoding(batch_size=b, num_tokens=30)
            self.assertGreaterEqual(res.replay_speedup, MIN_CUDA_GRAPH_SPEEDUP)
            self.assertTrue(res.bit_parity_verified)


if __name__ == "__main__":
    unittest.main()
