#!/usr/bin/env python3
# AI-hint: Automated unit test suite for GPU Interconnect Profiler & P2P Heatmap (T-663, T-664).
# AI-related: usr/libexec/mios/hw/gpu_heatd.py, tests/test-gpu-interconnect.py
"""Automated unit test suite for MiOS GPU Interconnect Profiler."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "hw"))

from gpu_heatd import GPUInterconnectProfiler

class TestGPUInterconnect(unittest.TestCase):
    def setUp(self):
        self.profiler = GPUInterconnectProfiler(dry_run=True)

    def test_sample_nvlink_matrix_normal_bandwidth(self):
        """Test sampling 4x GPU NVLink-4 matrix captures 450 GB/s with 0 bottlenecks."""
        mat = self.profiler.sample_interconnect_matrix(gpu_count=4, mock_bandwidth_gbps=450.0)
        self.assertEqual(mat.gpu_count, 4)
        self.assertEqual(mat.interconnect_type, "NVLink-4")
        self.assertEqual(len(mat.bottlenecks_detected), 0)
        self.assertEqual(mat.bandwidth_gbps_matrix[0][1], 450.0)

    def test_degraded_link_bottleneck_detection(self):
        """Test low bandwidth (<100 GB/s) generates actionable bottleneck alerts."""
        mat = self.profiler.sample_interconnect_matrix(gpu_count=2, mock_bandwidth_gbps=32.0)
        self.assertEqual(mat.interconnect_type, "PCIe-Gen5")
        self.assertGreater(len(mat.bottlenecks_detected), 0)
        self.assertIn("Degraded link", mat.bottlenecks_detected[0])

if __name__ == "__main__":
    unittest.main()
