#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Radix Tree Prefix Hash Cache Manager (T-635, T-636).
# AI-related: usr/libexec/mios/ai/prompt_cache.py, tests/test-prompt-cache.py
"""Automated unit test suite for MiOS Radix Tree Prefix Hash Cache Manager."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "ai"))

from prompt_cache import RadixPromptCacheManager, TTFT_TARGET_MS, MATCH_LATENCY_MAX_MS

class TestPromptCache(unittest.TestCase):
    def setUp(self):
        self.cache = RadixPromptCacheManager(max_cache_mb=1024.0, dry_run=True)

    def test_prefix_insertion_and_cache_hit(self):
        """Test storing and hitting cached system prompt token prefixes with sub-10ms match latency."""
        system_prompt_tokens = [1, 256, 89, 4421, 981, 102, 55, 912, 1004, 302, 11, 44, 99, 120, 881, 402]
        h = self.cache.insert_prefix(system_prompt_tokens)
        self.assertIsNotNone(h)
        self.assertNotEqual(h, "")

        hit, node, match_latency = self.cache.match_prefix(system_prompt_tokens, min_prefix_len=16)
        self.assertTrue(hit)
        self.assertIsNotNone(node)
        self.assertEqual(node.tokens, system_prompt_tokens)
        self.assertLess(match_latency, MATCH_LATENCY_MAX_MS)

    def test_zero_token_loss_on_prefix_match(self):
        """Test that returned prefix node maintains bit-for-bit exact token sequences."""
        tokens = list(range(500, 564))
        self.cache.insert_prefix(tokens)
        hit, node, _ = self.cache.match_prefix(tokens + [9999], min_prefix_len=16)
        self.assertTrue(hit)
        self.assertEqual(node.tokens, tokens)

    def test_high_concurrency_hit_rate(self):
        """Test 50 consecutive queries sharing common system prompt achieve >95% hit rate."""
        sys_tokens = list(range(50, 100))
        self.cache.insert_prefix(sys_tokens)

        for i in range(50):
            query_tokens = sys_tokens + [1000 + i, 2000 + i]
            hit, node, match_latency = self.cache.match_prefix(query_tokens, min_prefix_len=16)
            self.assertTrue(hit)
            self.assertLess(match_latency, MATCH_LATENCY_MAX_MS)

        stats = self.cache.get_stats()
        self.assertGreaterEqual(stats["hit_rate_pct"], 95.0)
        self.assertTrue(stats["sub_20ms_target_met"])
        self.assertGreater(stats["tokens_saved"], 0)

    def test_lru_memory_eviction(self):
        """Test LRU eviction reclaims memory when max_cache_mb is reached."""
        small_cache = RadixPromptCacheManager(max_cache_mb=1.0, dry_run=True)
        for i in range(20):
            prefix = [i + 1] + list(range(100, 130))
            small_cache.insert_prefix(prefix, kv_state_bytes=65536)

        self.assertLessEqual(small_cache.total_memory_bytes, 1048576)

    def test_openai_chat_messages_slot_reuse(self):
        """Test parsing OpenAI chat messages and coordinating slot reuse."""
        messages = [
            {"role": "system", "content": "You are MiOS agent assistant with full local MCP tool capabilities."},
            {"role": "user", "content": "Query energy telemetry status."},
        ]
        tokens = self.cache.parse_openai_chat_messages(messages)
        self.assertGreater(len(tokens), 10)

        # Cold request
        res1 = self.cache.coordinate_slot_reuse("sess_1", tokens)
        self.assertIn("session_id", res1)

        # Warm request
        res2 = self.cache.coordinate_slot_reuse("sess_2", tokens)
        self.assertTrue(res2["prefix_cache_hit"])
        self.assertLess(res2["match_latency_ms"], MATCH_LATENCY_MAX_MS)
        self.assertLess(res2["estimated_ttft_ms"], TTFT_TARGET_MS)

if __name__ == "__main__":
    unittest.main()
