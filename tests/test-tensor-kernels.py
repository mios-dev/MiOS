#!/usr/bin/env python3
# AI-hint: Automated unit test suite for GPU Compute Capability & Tensor Kernel Dispatcher (T-649, T-650).
# AI-related: usr/libexec/mios/ai/tensor_kernels.py, tests/test-tensor-kernels.py
"""Automated unit test suite for MiOS GPU Tensor Kernel Dispatcher."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "ai"))

from tensor_kernels import TensorKernelDispatcher


class TestTensorKernels(unittest.TestCase):
    def setUp(self):
        self.dispatcher = TensorKernelDispatcher(dry_run=True)

    def test_rtx4090_probe_and_env_bindings(self):
        """Test RTX 4090 probe selects SM_89 and FlashAttention-3."""
        arch = self.dispatcher.probe_gpu_capability("NVIDIA GeForce RTX 4090")
        self.assertEqual(arch.sm_version, "sm_89")
        self.assertTrue(arch.flash_attn_supported)

        env = self.dispatcher.get_env_bindings()
        self.assertEqual(env["FLASH_ATTN_VERSION"], "3")
        self.assertEqual(env["CUTLASS_SM_ARCH"], "89")

    def test_tensor_throughput_benchmark_target(self):
        """Test kernel dispatch achieves >90% theoretical peak efficiency."""
        self.dispatcher.probe_gpu_capability("NVIDIA GeForce RTX 4090")
        res = self.dispatcher.benchmark_throughput(batch_size=16)
        self.assertTrue(res["meets_target"])
        self.assertGreaterEqual(res["efficiency_pct"], 90.0)


if __name__ == "__main__":
    unittest.main()
