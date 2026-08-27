#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Multi-GPU NCCL Tuning & AllReduce Latency (T-713, T-714).
# AI-related: usr/libexec/mios/hw/nccl_tune.py, tests/test-nccl-tune.py
"""Automated unit test suite for MiOS NCCL Topology Tuner."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "hw"))

from nccl_tune import MAX_ALLREDUCE_LATENCY_US, MIN_TP2_SPEEDUP_RATIO, NCCLTopologyTuner


class TestNCCLTune(unittest.TestCase):
    def setUp(self):
        self.tuner = NCCLTopologyTuner(dry_run=True)

    def test_nvlink_topology_allreduce_latency_under_50us(self):
        """Test NVLink discovery yields <50us AllReduce latency and >1.8x TP=2 scaling."""
        cfg = self.tuner.discover_and_optimize(gpu_count=2, has_nvlink=True)
        self.assertEqual(cfg.interconnect_type, "NVLink_P2P")
        self.assertLess(cfg.allreduce_latency_us, MAX_ALLREDUCE_LATENCY_US)
        self.assertGreaterEqual(cfg.tp2_throughput_scaling, MIN_TP2_SPEEDUP_RATIO)

    def test_nccl_env_export_structure(self):
        """Test generated NCCL environment variables match SSOT specification."""
        cfg = self.tuner.discover_and_optimize(gpu_count=4, has_nvlink=True)
        env = self.tuner.export_nccl_env(cfg)
        self.assertIn("NCCL_BUFFSIZE=8M", env)
        self.assertIn("NCCL_P2P_LEVEL=NVL", env)
        self.assertIn("NCCL_NET_GDR_LEVEL=5", env)


if __name__ == "__main__":
    unittest.main()
