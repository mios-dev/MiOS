# AI-hint: Stdlib offline unit tests for mios_pipe.routing.consensus -- the weighted multi-judge Definition-of-Done fold (CONS-01). No network / no DB / no...
# AI-doc: usr/share/doc/mios/manual/agent-pipe.md
"""Stdlib offline unit tests for the weighted multi-judge consensus fold (CONS-01)."""

import sys

from mios_pipe.routing import consensus as M

_fails = 0


def check(name, cond):
    global _fails
    if cond:
        print(f"ok   - {name}")
    else:
        _fails += 1
        print(f"FAIL - {name}")


def t_resolve_weights():
    w = M.resolve_weights(["a", "b", "c"])
    check("weights: no reliability -> uniform", w == {"a": 1.0, "b": 1.0, "c": 1.0})

    w = M.resolve_weights(["a", "b"], {"a": 0.8, "b": 0.3})
    check("weights: reliability passed through", w == {"a": 0.8, "b": 0.3})

    w = M.resolve_weights(["a", "b"], {"a": 0.0}, floor=0.25)
    check("weights: zero score clamps to the floor", w["a"] == 0.25)
    check("weights: unscored lane keeps the default", w["b"] == 1.0)

    w = M.resolve_weights(["a", "b"], {"a": "junk", "b": float("nan")})
    check("weights: non-numeric score -> default", w["a"] == 1.0)
    check("weights: NaN score -> default", w["b"] == 1.0)


def t_weighted_vote_basic():
    r = M.weighted_vote({"a": True, "b": True})
    check("vote: unanimous yes -> True", r["decision"] is True)
    check("vote: unanimous yes -> agreement 1.0", r["agreement"] == 1.0)

    r = M.weighted_vote({"a": False, "b": False})
    check("vote: unanimous no -> False", r["decision"] is False)
    check("vote: unanimous no -> agreement 1.0", r["agreement"] == 1.0)

    r = M.weighted_vote({"a": True, "b": False})
    check("vote: even split at threshold 0.5 -> True", r["decision"] is True)
    check("vote: even split -> score 0.5", abs(r["score"] - 0.5) < 1e-9)

    r = M.weighted_vote({"a": True, "b": False}, threshold=0.51)
    check("vote: even split under a raised threshold -> False", r["decision"] is False)


def t_weighted_vote_resolves_conflict_by_weight():
    # Done-When: conflicting judges are resolved by WEIGHT, not by head-count.
    verdicts = {"trusted": True, "flaky_a": False, "flaky_b": False}
    weights = {"trusted": 3.0, "flaky_a": 0.5, "flaky_b": 0.5}
    r = M.weighted_vote(verdicts, weights)
    check("vote: one heavy lane outvotes two light ones", r["decision"] is True)
    check("vote: weighted score is 3/4", abs(r["score"] - 0.75) < 1e-9)

    r_unweighted = M.weighted_vote(verdicts)
    check("vote: same verdicts unweighted flip to the majority",
          r_unweighted["decision"] is False)

    r = M.weighted_vote(verdicts, {"trusted": 3.0, "flaky_a": 0.0, "flaky_b": 0.5})
    check("vote: a zero-weight lane is excluded from the fold",
          abs(r["score"] - (3.0 / 3.5)) < 1e-9)


def t_abstain_is_not_a_no():
    r = M.weighted_vote({"a": True, "b": None, "c": True})
    check("abstain: dropped from the denominator", r["score"] == 1.0)
    check("abstain: live count excludes it", r["live"] == 2)
    check("abstain: quorum still formed", r["quorum"] is True)

    # The whole panel erroring must not read as a rejection.
    r = M.weighted_vote({"a": None, "b": None})
    check("abstain: all lanes out -> no decision", r["decision"] is None)
    check("abstain: all lanes out -> no quorum", r["quorum"] is False)


def t_quorum_gate():
    check("quorum: two live votes reach the default min",
          M.quorum_reached({"a": True, "b": False}) is True)
    check("quorum: one live vote does not",
          M.quorum_reached({"a": True, "b": None}) is False)

    r = M.weighted_vote({"a": True, "b": None})
    check("quorum: sub-quorum panel returns decision=None", r["decision"] is None)
    check("quorum: sub-quorum still reports the raw score", r["score"] == 1.0)

    r = M.weighted_vote({"a": True, "b": None}, min_lanes=1)
    check("quorum: min_lanes=1 admits the single survivor", r["decision"] is True)

    r = M.weighted_vote({"a": True, "b": True}, min_lanes=3)
    check("quorum: min_lanes above the panel size withholds a decision",
          r["decision"] is None)


def t_rrf():
    # 'y' is 2nd for one lane and 1st for the other; 'x' is the mirror image --
    # a tie. 'z' is ranked by one lane only and must land below both.
    fused = M.reciprocal_rank_fusion({"a": ["x", "y", "z"], "b": ["y", "x"]})
    names = [c for c, _ in fused]
    check("rrf: both agreed candidates outrank the single-lane one",
          names.index("z") == 2)
    check("rrf: scores descend", all(
        fused[i][1] >= fused[i + 1][1] for i in range(len(fused) - 1)))

    # A candidate two lanes both rank first beats one lane's first place.
    fused = M.reciprocal_rank_fusion({"a": ["p", "q"], "b": ["p", "r"], "c": ["q"]})
    check("rrf: consensus first-place wins", fused[0][0] == "p")

    fused = M.reciprocal_rank_fusion({"a": ["x", "y"]}, {"a": 0.0})
    check("rrf: a zero-weight lane contributes nothing", fused == [])

    heavy = M.reciprocal_rank_fusion(
        {"a": ["x", "y"], "b": ["y", "x"]}, {"a": 5.0, "b": 1.0})
    check("rrf: weights break the tie toward the heavy lane",
          heavy[0][0] == "x")

    check("rrf: empty input -> empty output",
          M.reciprocal_rank_fusion({}) == [])

    # k damps the head of each list: a larger k narrows the gap between ranks.
    tight = M.reciprocal_rank_fusion({"a": ["x", "y"]}, k=1000)
    loose = M.reciprocal_rank_fusion({"a": ["x", "y"]}, k=1)
    check("rrf: larger k compresses the rank-1/rank-2 gap",
          (tight[0][1] - tight[1][1]) < (loose[0][1] - loose[1][1]))


def t_determinism():
    a = M.reciprocal_rank_fusion({"a": ["x", "y"], "b": ["y", "x"]})
    b = M.reciprocal_rank_fusion({"a": ["x", "y"], "b": ["y", "x"]})
    check("rrf: tied candidates keep first-appearance order", a == b)
    check("rrf: tie broken toward first appearance", a[0][0] == "x")


def main():
    t_resolve_weights()
    t_weighted_vote_basic()
    t_weighted_vote_resolves_conflict_by_weight()
    t_abstain_is_not_a_no()
    t_quorum_gate()
    t_rrf()
    t_determinism()
    print(f"\n{_fails} FAILED" if _fails else "\nok")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
