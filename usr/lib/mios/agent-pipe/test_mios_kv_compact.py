#!/usr/bin/env python3
# AI-hint: Unit test for mios_kv_compact.py
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from mios_kv_compact import KVCompactEngine, estimate_tokens

class TestKVCompact(unittest.TestCase):
    def test_estimate_tokens(self):
        self.assertGreater(estimate_tokens("hello world"), 0)
        self.assertGreater(estimate_tokens([{"role": "user", "content": "hi"}]), 0)

    def test_compact_engine(self):
        engine = KVCompactEngine(max_tokens=100)
        msgs = [{"role": "user", "content": "test " * 50}]
        res = engine.compact_messages(msgs)
        self.assertIn("messages", res)

if __name__ == "__main__":
    unittest.main()
