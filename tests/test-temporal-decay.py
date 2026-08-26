#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-RAG temporal decay ranking.
# AI-related: usr/lib/mios/agent-pipe/mios_temporal_decay.py
"""Automated tests for WS-RAG exponential temporal decay on memory similarity rankings."""

from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "usr", "lib", "mios", "agent-pipe"))

from mios_temporal_decay import TemporalDecayScorer


class TestTemporalDecay(unittest.TestCase):
    """Validates temporal decay factor computation and ranking adjustments."""

    def test_recency_prioritization(self):
        scorer = TemporalDecayScorer(decay_lambda=0.001)
        now = 1000000.0

        records = [
            # High similarity but very old (10,000s ago)
            {"id": "old_record", "cosine_similarity": 0.95, "updated_at": now - 10000.0},
            # Slightly lower similarity but very recent (10s ago)
            {"id": "recent_record", "cosine_similarity": 0.90, "updated_at": now - 10.0},
        ]

        ranked = scorer.rank_records(records, current_ts=now)
        # Recent record should outrank decayed old record despite lower raw similarity
        self.assertEqual(ranked[0]["id"], "recent_record")


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTemporalDecay)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
