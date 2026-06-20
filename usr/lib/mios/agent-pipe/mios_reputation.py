# AI-hint: Pure in-memory per-peer reliability tracker (#54 zero-trust federation):
# AI-related: server.py, mios_a2a_principal, mios_lanes
# AI-functions: PeerReputation.record, PeerReputation.score, PeerReputation.rank, PeerReputation.snapshot
#   records outbound A2A delegation outcomes (ok/bad) and ranks ready peers by a
#   Laplace-smoothed success rate so the orchestrator prefers reliable peers and
#   deprioritises flaky ones. Dependency-free + deterministic -> unit-testable
#   (test_mios_reputation.py). Default-NEUTRAL: a peer with no history scores 0.5
#   and rank() is a STABLE sort, so with no data the caller's existing order
#   (first-ready) is preserved exactly -> zero behaviour change until peers exist.
"""Peer reputation for zero-trust A2A federation (#54).

Tracks how reliably each A2A peer has handled delegations and ranks candidates so
a reliable peer is chosen over a flaky one. In-memory + per-process (like the
_A2A_PEERS registry it complements -- both rebuild on restart); persistence is a
later concern. Pure logic, no I/O, no server import.

Scoring is Laplace-smoothed success rate: (ok + 1) / (ok + bad + 2). No history ->
0.5 (neutral). A recent-failure penalty (consecutive_bad) lets a peer that just
started failing drop quickly without waiting for its long-run average to move.
"""
from __future__ import annotations

from typing import Dict, List

NEUTRAL = 0.5


class PeerReputation:
    def __init__(self, recent_penalty: float = 0.15) -> None:
        # peer_id -> {"ok": int, "bad": int, "streak_bad": int}
        self._stats: Dict[str, dict] = {}
        self._recent_penalty = float(recent_penalty)

    def record(self, peer_id: str, ok: bool) -> None:
        """Record one delegation outcome for a peer."""
        if not peer_id:
            return
        s = self._stats.setdefault(str(peer_id),
                                   {"ok": 0, "bad": 0, "streak_bad": 0})
        if ok:
            s["ok"] += 1
            s["streak_bad"] = 0
        else:
            s["bad"] += 1
            s["streak_bad"] += 1

    def score(self, peer_id: str) -> float:
        """Reliability in [0,1]. Neutral (0.5) with no history. Each consecutive
        recent failure subtracts recent_penalty (floored at 0)."""
        s = self._stats.get(str(peer_id))
        if not s or (s["ok"] + s["bad"]) == 0:
            return NEUTRAL
        base = (s["ok"] + 1.0) / (s["ok"] + s["bad"] + 2.0)
        base -= self._recent_penalty * s["streak_bad"]
        return max(0.0, min(1.0, base))

    def rank(self, peer_ids: List[str]) -> List[str]:
        """Candidates best-first. STABLE: equal scores keep input order, so an
        all-neutral list (no history) is returned unchanged -- the caller's
        existing preference (e.g. first-ready) is preserved."""
        idx = {p: i for i, p in enumerate(peer_ids)}
        return sorted(peer_ids, key=lambda p: (-self.score(p), idx[p]))

    def snapshot(self) -> Dict[str, dict]:
        """Per-peer {ok, bad, streak_bad, score} for inspection/observability."""
        return {
            p: {**s, "score": round(self.score(p), 3)}
            for p, s in self._stats.items()
        }
