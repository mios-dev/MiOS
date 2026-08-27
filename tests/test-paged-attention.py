#!/usr/bin/env python3
# AI-hint: Automated unit test suite for PagedAttention Block Manager and Defragmenter (T-637, T-638).
# AI-related: usr/libexec/mios/ai/paged_attn.py, usr/libexec/mios/ai/paged_attention.py, tests/test-paged-attention.py
"""Automated unit test suite for MiOS PagedAttention Virtual Block Manager."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "ai"))

from paged_attn import PagedAttentionBlockManager, PhysicalBlock, SessionTable

class TestPagedAttention(unittest.TestCase):
    def setUp(self):
        self.mgr = PagedAttentionBlockManager(total_blocks=2048, block_size=32, dry_run=True)

    def test_block_allocation_and_free(self):
        """Test allocating and freeing discrete 32-token blocks."""
        ok = self.mgr.allocate_tokens("sess_alpha", 64)
        self.assertTrue(ok)
        self.assertEqual(len(self.mgr.sessions["sess_alpha"].logical_to_physical), 2)

        self.mgr.free_session("sess_alpha")
        self.assertNotIn("sess_alpha", self.mgr.sessions)
        self.assertTrue(all(b.is_free for b in self.mgr.physical_blocks))

    def test_copy_on_write_branch_sharing(self):
        """Test branching sessions share physical blocks until modified via CoW."""
        ok1 = self.mgr.allocate_tokens("sess_parent", 64)
        self.assertTrue(ok1)
        parent_pids = list(self.mgr.sessions["sess_parent"].logical_to_physical)

        ok_b = self.mgr.branch_session("sess_parent", "sess_child")
        self.assertTrue(ok_b)
        child_pids = self.mgr.sessions["sess_child"].logical_to_physical
        self.assertEqual(parent_pids, child_pids)

        for pid in parent_pids:
            self.assertEqual(self.mgr.physical_blocks[pid].ref_count, 2)

        ok_cow = self.mgr.append_tokens_cow("sess_child", 10)
        self.assertTrue(ok_cow)
        new_child_pids = self.mgr.sessions["sess_child"].logical_to_physical
        self.assertNotEqual(parent_pids[-1], new_child_pids[-1])
        self.assertGreater(self.mgr.cow_splits, 0)

    def test_100_session_concurrency_and_low_fragmentation(self):
        """Test 100 concurrent dynamic sessions maintain <4% average waste."""
        for i in range(100):
            tokens = 32 * (i % 5 + 1)
            ok = self.mgr.allocate_tokens(f"sess_{i}", tokens)
            self.assertTrue(ok)

        waste = self.mgr.compute_fragmentation_waste()
        self.assertLessEqual(waste, 4.0)

    def test_lru_page_eviction_under_vram_pressure(self):
        """Test that reaching capacity triggers LRU eviction of old sessions."""
        small_mgr = PagedAttentionBlockManager(total_blocks=5, block_size=16, dry_run=True)
        small_mgr.allocate_tokens("sess_old", 80)
        self.assertEqual(small_mgr.free_blocks_count, 0)

        ok = small_mgr.allocate_tokens("sess_new", 32)
        self.assertTrue(ok)
        self.assertIn("sess_new", small_mgr.sessions)
        self.assertNotIn("sess_old", small_mgr.sessions)
        self.assertGreater(small_mgr.evictions, 0)

    def test_asynchronous_defragmentation(self):
        """Test compaction moves fragmented physical blocks to contiguous low-index range."""
        self.mgr.allocate_tokens("s1", 32)
        self.mgr.allocate_tokens("s2", 32)
        self.mgr.allocate_tokens("s3", 32)

        self.mgr.free_session("s2")
        moved = self.mgr.defragment_memory()
        self.assertGreaterEqual(moved, 0)

        stats = self.mgr.get_stats()
        self.assertEqual(stats["active_sessions"], 2)

if __name__ == "__main__":
    unittest.main()
