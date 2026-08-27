# AI-hint: Temporal decay scoring on memory retrieval vectors to prioritize recent state changes.
# AI-related: usr/lib/mios/agent-pipe/server.py, tests/test-temporal-decay.py
"""
MiOS Memory Retrieval Temporal Decay Scoring Engine.
Computes composite ranking: score = cosine_similarity * exp(-lambda * delta_time).
"""

from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional


class TemporalDecayScorer:
    """Applies exponential temporal decay to vector similarity rankings."""

    def __init__(self, decay_lambda: float = 0.0001) -> None:
        self.decay_lambda = decay_lambda

    def compute_composite_score(
        self,
        cosine_similarity: float,
        updated_at_ts: float,
        current_ts: Optional[float] = None
    ) -> float:
        """Calculates time-weighted similarity score."""
        now = current_ts if current_ts is not None else time.time()
        delta_s = max(0.0, now - float(updated_at_ts))
        decay_factor = math.exp(-self.decay_lambda * delta_s)
        return float(cosine_similarity) * decay_factor

    def rank_records(self, records: List[Dict[str, Any]], current_ts: Optional[float] = None) -> List[Dict[str, Any]]:
        """Ranks list of memory records using temporal decay scores."""
        now = current_ts if current_ts is not None else time.time()
        ranked = []
        for rec in records:
            sim = float(rec.get("cosine_similarity", 0.5))
            ts = float(rec.get("updated_at", now))
            c_score = self.compute_composite_score(sim, ts, now)

            r = dict(rec)
            r["composite_score"] = round(c_score, 4)
            ranked.append(r)

        ranked.sort(key=lambda x: x["composite_score"], reverse=True)
        return ranked
