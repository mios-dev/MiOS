#!/usr/bin/env python3
# AI-hint: Standalone unit test for mios_temporal_decay sibling module.
# AI-doc: usr/share/doc/mios/manual/agent-pipe.md
"""Unit tests for mios_temporal_decay."""

import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from mios_temporal_decay import TemporalDecayScorer

_fails = 0

def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))

def main():
    scorer = TemporalDecayScorer(decay_lambda=0.001)
    now = 10000.0
    recent_score = scorer.compute_composite_score(0.9, 9990.0, current_ts=now)
    old_score = scorer.compute_composite_score(0.9, 1000.0, current_ts=now)

    check("recent score > old score", recent_score > old_score)

    records = [
        {"id": "old", "cosine_similarity": 0.95, "updated_at": 1000.0},
        {"id": "recent", "cosine_similarity": 0.90, "updated_at": 9990.0}
    ]
    ranked = scorer.rank_records(records, current_ts=now)
    check("ranked list non-empty", len(ranked) == 2)
    check("recent record ranked higher", ranked[0]["id"] == "recent")

    if _fails > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
