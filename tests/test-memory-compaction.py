#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-RAG episodic memory compaction into semantic trees.
# AI-related: usr/libexec/mios/rag/memory-compact.py
"""Automated tests for WS-RAG fact extraction and hierarchical tree construction."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_COMPACT_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "rag", "memory-compact.py")

spec = importlib.util.spec_from_file_location("memory_compact", _COMPACT_PATH)
if spec and spec.loader:
    memory_compact = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = memory_compact
    spec.loader.exec_module(memory_compact)
else:
    raise ImportError(f"Could not load memory-compact module from {_COMPACT_PATH}")

class TestMemoryCompaction(unittest.TestCase):
    """Validates conversation fact parsing and semantic tree creation."""

    def test_fact_extraction_and_tree_building(self):
        compactor = memory_compact.MemoryCompactor()
        sample_turns = [
            {"role": "user", "content": "Preference: Always use dark mode in web UI."},
            {"role": "system", "content": "Constraint: All Quadlets must run rootless."},
            {"role": "user", "content": "Hello there, how are you?"},
        ]

        facts = compactor.extract_facts_from_turns(sample_turns)
        self.assertEqual(len(facts), 2)

        tree = compactor.build_hierarchical_tree(facts)
        self.assertIn("user_preference", tree)
        self.assertIn("system_constraint", tree)
        self.assertEqual(len(tree["user_preference"]), 1)
        self.assertEqual(len(tree["system_constraint"]), 1)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMemoryCompaction)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
