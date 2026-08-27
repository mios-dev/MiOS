#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Dynamic VRAM Swapper and LRU KV Pager (T-629, T-630).
# AI-related: usr/libexec/mios/ai/vram_swap.py, tests/test-vram-swap.py
"""Automated unit test suite for MiOS Dynamic VRAM Swapper and LRU KV Pager."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "ai"))

from vram_swap import MAX_SWAP_LATENCY_MS, VRAMSwapManager

class TestVRAMSwap(unittest.TestCase):
    def setUp(self):
        # 8 GB VRAM test budget with fast PCIe 4.0
        self.mgr = VRAMSwapManager(
            total_vram_mb=8192.0,
            total_host_ram_mb=32768.0,
            pcie_bandwidth_gbps=32.0,
            vram_watermark_ratio=0.80,
            dry_run=True,
        )
        self.mgr.register_model("mios-opencode", total_layers=32, layer_size_mb=128.0)
        self.mgr.register_model("mios-chat", total_layers=32, layer_size_mb=128.0)
        self.mgr.register_model("mios-vision", total_layers=32, layer_size_mb=160.0)

    def test_sub_500ms_model_swapping(self):
        """Test multi-model switching occurs in under 500ms."""
        models = ["mios-opencode", "mios-chat", "mios-vision", "mios-opencode"]
        for model in models:
            ok, latency_ms = self.mgr.activate_model(model)
            self.assertTrue(ok)
            self.assertLess(latency_ms, MAX_SWAP_LATENCY_MS)

        status = self.mgr.get_status()
        self.assertTrue(status["sub_500ms_target_met"])

    def test_lru_kv_cache_paging_under_pressure(self):
        """Test that inactive KV cache slots page out to host RAM when VRAM fills up."""
        # Activate model taking 4096 MB
        self.mgr.activate_model("mios-opencode")

        # Create session 1 and unpin it (now idle)
        s1 = self.mgr.allocate_or_update_kv_slot("sess_1", "mios-opencode", token_count=1000, size_mb=1024.0)
        self.mgr.unpin_kv_slot("sess_1")

        # Create session 2 and unpin it
        s2 = self.mgr.allocate_or_update_kv_slot("sess_2", "mios-opencode", token_count=2000, size_mb=1024.0)
        self.mgr.unpin_kv_slot("sess_2")

        # Create session 3 with large KV size (1500 MB) pushing over 80% watermark (8192 * 0.80 = 6553.6 MB)
        s3 = self.mgr.allocate_or_update_kv_slot("sess_3", "mios-opencode", token_count=4000, size_mb=1500.0)

        status = self.mgr.get_status()
        self.assertGreaterEqual(status["kv_in_host"], 1)
        self.assertEqual(s1.location, "host_ram")  # s1 was oldest inactive, should be paged out

    def test_pinned_active_session_protection(self):
        """Test that actively generating session slots are never paged out."""
        self.mgr.activate_model("mios-opencode")
        s_active = self.mgr.allocate_or_update_kv_slot("active_session", "mios-opencode", token_count=100, size_mb=1024.0)
        self.assertTrue(s_active.is_pinned)

        # Trigger page out attempt
        paged = self.mgr._page_out_oldest_inactive_kv()
        self.assertFalse(paged)
        self.assertEqual(s_active.location, "vram")

    def test_session_state_preservation_on_page_in(self):
        """Test 100% token state preservation when paged-out session is recalled."""
        s = self.mgr.allocate_or_update_kv_slot("sess_persist", "mios-chat", token_count=3500, size_mb=512.0)
        self.mgr.unpin_kv_slot("sess_persist")
        s.location = "host_ram"

        ok, lat = self.mgr.page_in_kv_slot("sess_persist")
        self.assertTrue(ok)
        self.assertEqual(s.location, "vram")
        self.assertEqual(s.token_count, 3500)
        self.assertLess(lat, MAX_SWAP_LATENCY_MS)

if __name__ == "__main__":
    unittest.main()
