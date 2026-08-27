#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Hierarchical Accelerator Router (T-693, T-694).
# AI-related: usr/libexec/mios/ai/accelerator_router.py, tests/test-accelerator-router.py
"""Automated unit test suite for MiOS Hierarchical Accelerator Router."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "ai"))

from accelerator_router import HierarchicalAcceleratorRouter


class TestAcceleratorRouter(unittest.TestCase):
    def setUp(self):
        self.router_npu = HierarchicalAcceleratorRouter(has_npu=True, dry_run=True)
        self.router_cpu = HierarchicalAcceleratorRouter(has_npu=False, dry_run=True)

    def test_npu_priority_for_embeddings_keeps_dgpu_asleep(self):
        """Test embeddings route to NPU with dGPU power-gated in D3cold."""
        res = self.router_npu.route_inference_task("embedding")
        self.assertEqual(res.assigned_target, "NPU")
        self.assertEqual(res.dgpu_power_state, "D3cold_Sleep")
        self.assertTrue(res.is_power_gated)
        self.assertLess(res.estimated_wattage, 2.0)

    def test_cpu_vector_fallback_when_no_npu_present(self):
        """Test systems without NPU fall back to optimized CPU vector threads."""
        res = self.router_cpu.route_inference_task("wake_word")
        self.assertEqual(res.assigned_target, "CPU_Vector")
        self.assertEqual(res.dgpu_power_state, "D3cold_Sleep")

    def test_heavy_llm_routes_to_dgpu(self):
        """Test heavy 32B coding model wakes dGPU to D0 active."""
        res = self.router_npu.route_inference_task("reasoning_32b")
        self.assertEqual(res.assigned_target, "dGPU_Heavy")
        self.assertEqual(res.dgpu_power_state, "D0_Active")
        self.assertFalse(res.is_power_gated)


if __name__ == "__main__":
    unittest.main()
