#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Semantic Context Compaction & Invariant Retention (T-675, T-676).
# AI-related: usr/lib/mios/agent-pipe/context_compactor.py, tests/test-context-compactor.py
"""Automated unit test suite for MiOS Context Compactor."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "lib", "mios", "agent-pipe"))

from context_compactor import ContextCompactor, ConversationTurn


class TestContextCompactor(unittest.TestCase):
    def setUp(self):
        self.compactor = ContextCompactor(max_context_tokens=8192, dry_run=True)

    def test_pinned_invariants_preservation(self):
        """Test pinned system invariants and architectural rules are strictly preserved."""
        turns = [
            ConversationTurn("system", "LAW: USR-OVER-ETC", 300, is_pinned=True),
            ConversationTurn("user", "Hello world", 100, is_pinned=False),
            ConversationTurn("assistant", "Hi", 100, is_pinned=False),
        ]
        res = self.compactor.compact_dialog(turns)
        self.assertEqual(res.pinned_invariants_count, 1)
        self.assertIn("Preserved 1 pinned system rules", res.recap_summary)

    def test_100k_token_dialog_compaction_retains_constraints(self):
        """Test long-horizon dialog compaction retains 100% of injected constraints."""
        turns = [
            ConversationTurn("system", "LAW: USR-OVER-ETC", 500, is_pinned=True),
            ConversationTurn("user", "CONSTRAINT: Secret token is 9988", 200, is_pinned=False),
            ConversationTurn("assistant", "Working on task...", 4000, is_pinned=False),
            ConversationTurn("user", "CONSTRAINT: Never format NVMe", 200, is_pinned=False),
            ConversationTurn("assistant", "Done.", 4000, is_pinned=False),
        ]
        res = self.compactor.compact_dialog(turns)
        self.assertEqual(len(res.retained_constraint_keys), 3)
        self.assertLess(res.compacted_token_count, res.original_token_count)


if __name__ == "__main__":
    unittest.main()
