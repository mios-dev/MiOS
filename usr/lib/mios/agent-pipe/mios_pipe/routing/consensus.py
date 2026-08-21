# AI-hint: Pure consensus math for multi-judge Definition-of-Done verdicts. weighted_vote folds 2-3 independent judge lanes' yes/no/abstain verdicts into one reliability-weighted decision; reciprocal_rank_fusion merges the lanes' ranked candidate lists (standard RRF, score = sum w/(k+rank)); resolve_weights turns a reliability mapping into per-lane weights and degrades to uniform when no reliability signal exists. No I/O, no config import, no server import -- the caller supplies lanes, verdicts and weights, so every branch is isolation-testable.
# AI-related: ./reflect.py, ../../test_mios_consensus.py, usr/share/mios/mios.toml [consensus]
# AI-functions: resolve_weights, weighted_vote, reciprocal_rank_fusion, quorum_reached
"""Weighted multi-judge consensus (CONS-01). Rationale + the degrade-open
contract: usr/share/doc/mios/manual/ch52-multi-judge-consensus-and-drift.md"""

from __future__ import annotations

from typing import Iterable, Mapping, Optional, Sequence

__all__ = [
    "resolve_weights",
    "weighted_vote",
    "reciprocal_rank_fusion",
    "quorum_reached",
]


def resolve_weights(
    lanes: Sequence[str],
    reliability: Optional[Mapping[str, float]] = None,
    *,
    floor: float = 0.1,
    default: float = 1.0,
) -> dict:
    """Per-lane weights from a reliability mapping, degrading to uniform.
    Unscored lanes get `default`; every weight is clamped up to `floor`."""
    weights = {}
    rel = reliability or {}
    for lane in lanes:
        raw = rel.get(lane, default)
        try:
            w = float(raw)
        except (TypeError, ValueError):
            w = default
        if w != w or w in (float("inf"), float("-inf")):  # NaN / inf
            w = default
        weights[lane] = max(float(floor), w)
    return weights


def quorum_reached(verdicts: Mapping[str, Optional[bool]], min_lanes: int = 2) -> bool:
    """True when at least ``min_lanes`` lanes returned a real (non-abstain) vote."""
    live = sum(1 for v in verdicts.values() if v is not None)
    return live >= max(1, int(min_lanes))


def weighted_vote(
    verdicts: Mapping[str, Optional[bool]],
    weights: Optional[Mapping[str, float]] = None,
    *,
    threshold: float = 0.5,
    min_lanes: int = 2,
) -> dict:
    """Fold per-lane True/False/None(abstain) verdicts into one weighted
    decision: {decision, score, quorum, live, agreement, weights}. See ch52."""
    w = dict(weights or {})
    live = {k: v for k, v in verdicts.items() if v is not None}
    total = 0.0
    yes = 0.0
    for lane, vote in live.items():
        lane_w = float(w.get(lane, 1.0))
        if lane_w <= 0.0:
            continue
        total += lane_w
        if vote:
            yes += lane_w
    quorum = quorum_reached(verdicts, min_lanes)
    if total <= 0.0:
        return {"decision": None, "score": 0.0, "quorum": False, "live": 0,
                "agreement": 0.0, "weights": w}
    score = yes / total
    decision = score >= float(threshold)
    agreement = score if decision else 1.0 - score
    return {
        "decision": decision if quorum else None,
        "score": score,
        "quorum": quorum,
        "live": len(live),
        "agreement": agreement,
        "weights": w,
    }


def reciprocal_rank_fusion(
    rankings: Mapping[str, Sequence],
    weights: Optional[Mapping[str, float]] = None,
    *,
    k: int = 60,
) -> list:
    """Fuse each lane's ranked list into one ordering (standard RRF, score =
    sum weight/(k+rank)). Returns [(candidate, score)], best first. See ch52."""
    w = dict(weights or {})
    scores: dict = {}
    order: dict = {}
    seq = 0
    for lane, ranked in rankings.items():
        lane_w = float(w.get(lane, 1.0))
        if lane_w <= 0.0:
            continue
        for idx, cand in enumerate(ranked, start=1):
            key = cand
            if key not in order:
                order[key] = seq
                seq += 1
            scores[key] = scores.get(key, 0.0) + lane_w / (float(k) + idx)
    return sorted(scores.items(), key=lambda kv: (-kv[1], order[kv[0]]))
