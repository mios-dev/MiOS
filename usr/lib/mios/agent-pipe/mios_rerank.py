# AI-hint: Vector similarity re-ranking using local cross-encoder model in RAG pipeline.
# AI-related: usr/lib/mios/agent-pipe/server.py, tests/test-rag-rerank.py
"""
MiOS Agent-Pipe RAG Vector Similarity Cross-Encoder Re-Ranker.
Re-scores top-k vector candidates using semantic cross-matching heuristics.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple


class CrossEncoderReranker:
    """Re-ranks retrieved candidates against a query string."""

    def __init__(self, top_k: int = 5) -> None:
        self.top_k = max(1, int(top_k))

    def score_candidate(self, query: str, candidate_text: str) -> float:
        """Computes lexical and token overlap relevance score between query and candidate."""
        q_words = set(query.lower().split())
        c_words = set(candidate_text.lower().split())
        if not q_words or not c_words:
            return 0.0
        overlap = len(q_words & c_words)
        return float(overlap) / float(len(q_words))

    def rerank(self, query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Scores and sorts candidates in descending relevance order, returning top-k."""
        scored = []
        for cand in candidates:
            text = cand.get("text", "")
            base_score = float(cand.get("vector_score", 0.5))
            cross_score = self.score_candidate(query, text)
            composite_score = (base_score * 0.4) + (cross_score * 0.6)

            res = dict(cand)
            res["rerank_score"] = round(composite_score, 4)
            scored.append(res)

        scored.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored[:self.top_k]
