#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-RAG cross-encoder re-ranking.
# AI-related: usr/lib/mios/agent-pipe/mios_rerank.py
"""Automated tests for WS-RAG cross-encoder candidate scoring and top-k ordering."""

from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "usr", "lib", "mios", "agent-pipe"))

from mios_rerank import CrossEncoderReranker

class TestRagRerank(unittest.TestCase):
    """Validates candidate scoring and top-k truncation."""

    def test_rerank_scoring(self):
        reranker = CrossEncoderReranker(top_k=2)
        candidates = [
            {"id": "doc_unrelated", "text": "Cooking recipes and baking cakes", "vector_score": 0.8},
            {"id": "doc_perfect", "text": "Fedora Linux bootc immutable ostree filesystem", "vector_score": 0.7},
            {"id": "doc_partial", "text": "Linux kernel compilation on Fedora", "vector_score": 0.6},
        ]
        query = "Fedora bootc immutable ostree"
        results = reranker.rerank(query, candidates)
        self.assertEqual(len(results), 2)
        # doc_perfect has highest keyword overlap with query
        self.assertEqual(results[0]["id"], "doc_perfect")

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRagRerank)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
