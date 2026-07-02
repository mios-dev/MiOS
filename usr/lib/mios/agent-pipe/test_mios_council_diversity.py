# AI-hint: Stdlib offline unit tests for mios_council_diversity -- the council input-diversity gate (T-047 RouteMoA GAP-1) + confidence-aware aggregation bypass (T-048 MOSAIC GAP-2). No network / no DB / no live model: a deterministic text->vector stub embedder feeds the pure geometry (select_diverse / should_bypass / medoid_index) and the async orchestrator (apply_council_gates). Proves the two Done-When cases: two identical council responses -> the duplicate is replaced/dropped (one selected); three identical responses above threshold -> the aggregator is bypassed (caller skips it) + the aggregator_bypass event is logged. Also proves degrade-open (both gates off => no embed call, nodes unchanged; a missing embedding => no-op) and the bypassed_pct counter. Run: python test_mios_council_diversity.py
# AI-related: ./mios_council_diversity.py, ./mios_pipe/routing/swarm.py, ./mios_pipe/kernel/clusterhealth.py
# AI-functions: main
"""Stdlib offline unit tests for mios_council_diversity (T-047 / T-048)."""

import asyncio
import sys

import mios_council_diversity as M

_fails = 0


def check(name, cond):
    global _fails
    if cond:
        print(f"ok   - {name}")
    else:
        _fails += 1
        print(f"FAIL - {name}")


# Deterministic text -> unit vector stub (no model). Identical text -> identical
# vector -> cosine 1.0; the named vectors below give exact, checkable geometry.
_VEC = {
    "A":  [1.0, 0.0, 0.0],
    "B":  [0.0, 1.0, 0.0],
    "C":  [0.0, 0.0, 1.0],
    # near-A: cosine(A, An) ~= 0.9999 (well above both default thresholds)
    "An": [0.9999, 0.01414, 0.0],
    # moderately-similar to A: cosine ~= 0.80 (below thresholds -> diverse)
    "Am": [0.8, 0.6, 0.0],
}


def _mk_embed(missing=None):
    async def _embed(text):
        if missing is not None and text == missing:
            return None
        return list(_VEC.get(text, [0.0, 0.0, 0.0]))
    return _embed


def _nodes(*texts):
    return [{"output": t, "tag": t} for t in texts]


# -- pure geometry ---------------------------------------------------

def t_select_diverse():
    v = lambda k: list(_VEC[k])
    # Two identical -> only ONE selected (the duplicate is dropped/replaced). [T-047]
    sel = M.select_diverse([v("A"), v("A")], 0.92)
    check("select_diverse: two identical -> 1 selected", len(sel) == 1)
    # Two orthogonal -> both kept.
    sel = M.select_diverse([v("A"), v("B")], 0.92)
    check("select_diverse: two orthogonal -> both kept", sorted(sel) == [0, 1])
    # A, A(dup), B : the distinct B is the lowest-mean-similarity seed; ONE of the
    # two identical A's is kept, the other (redundant, sim>thr to the set) dropped.
    sel = M.select_diverse([v("A"), v("A"), v("B")], 0.92)
    check("select_diverse: {A,A,B} -> 2 selected (one A dropped)", len(sel) == 2)
    check("select_diverse: seed is the distinct response (lowest mean sim)",
          sel[0] == 2)
    check("select_diverse: exactly one of the identical A's survives",
          (0 in sel) ^ (1 in sel))
    # Three mutually diverse -> all kept.
    sel = M.select_diverse([v("A"), v("B"), v("C")], 0.92)
    check("select_diverse: three diverse -> all kept", len(sel) == 3)
    # near-duplicate (cosine>thr) is pruned; moderately-similar (cosine<thr) kept.
    sel = M.select_diverse([v("A"), v("An"), v("Am")], 0.92)
    check("select_diverse: near-dup pruned, moderate kept -> 2 selected",
          len(sel) == 2)
    # Single / empty inputs are pass-through.
    check("select_diverse: single -> pass-through", M.select_diverse([v("A")], 0.92) == [0])
    check("select_diverse: empty -> []", M.select_diverse([], 0.92) == [])


def t_should_bypass():
    v = lambda k: list(_VEC[k])
    ok, mean = M.should_bypass([v("A"), v("A"), v("A")], 0.95)
    check("should_bypass: three identical > thr -> True", ok is True)
    check("should_bypass: mean_similarity ~= 1.0", abs(mean - 1.0) < 1e-9)
    ok, _ = M.should_bypass([v("A"), v("An")], 0.95)
    check("should_bypass: two near-identical (>0.95) -> True", ok is True)
    ok, _ = M.should_bypass([v("A"), v("A"), v("B")], 0.95)
    check("should_bypass: one divergent pair -> False", ok is False)
    ok, mean = M.should_bypass([v("A")], 0.95)
    check("should_bypass: <2 responses -> (False, 0.0)", ok is False and mean == 0.0)


def t_medoid():
    v = lambda k: list(_VEC[k])
    # {A, A, B}: an A is the consensus medoid (highest mean sim to the others).
    mi = M.medoid_index([v("A"), v("A"), v("B")])
    check("medoid_index: {A,A,B} -> an identical A (index 0/1)", mi in (0, 1))
    check("medoid_index: single -> 0", M.medoid_index([v("A")]) == 0)


# -- async orchestrator ---------------------------------------------

def t_gates_off_noop():
    # Both gates OFF => embedder MUST NOT be called; nodes returned unchanged.
    called = {"n": 0}

    async def _boom(_t):
        called["n"] += 1
        return [1.0, 0.0, 0.0]

    nodes = _nodes("A", "A")
    sel, byp = asyncio.get_event_loop().run_until_complete(
        M.apply_council_gates(nodes, embed_one=_boom,
                              diversity_gate=False, aggregator_bypass=False))
    check("gates off: nodes unchanged", sel is nodes and byp is None)
    check("gates off: embedder NOT called (zero model calls)", called["n"] == 0)


def t_diversity_gate_prunes():
    # T-047: two identical council responses -> one is replaced/dropped.
    nodes = _nodes("A", "A")
    sel, byp = asyncio.get_event_loop().run_until_complete(
        M.apply_council_gates(nodes, embed_one=_mk_embed(),
                              diversity_gate=True, diversity_threshold=0.92,
                              aggregator_bypass=False))
    check("T-047 diversity: two identical -> 1 input kept", len(sel) == 1)
    check("T-047 diversity: no bypass", byp is None)
    # A diverse pair is untouched.
    nodes = _nodes("A", "B")
    sel, byp = asyncio.get_event_loop().run_until_complete(
        M.apply_council_gates(nodes, embed_one=_mk_embed(),
                              diversity_gate=True, aggregator_bypass=False))
    check("T-047 diversity: diverse pair kept whole", len(sel) == 2)


def t_aggregator_bypass():
    # T-048: three identical responses above threshold -> aggregator NOT called,
    # event logged. We mirror the swarm wiring: the aggregator runs ONLY when the
    # gate returns bypass=None.
    events = []
    aggregator_calls = {"n": 0}

    def _log(**kw):
        events.append(kw)

    nodes = _nodes("A", "A", "A")
    sel, byp = asyncio.get_event_loop().run_until_complete(
        M.apply_council_gates(nodes, embed_one=_mk_embed(),
                              diversity_gate=False,
                              aggregator_bypass=True,
                              aggregator_bypass_threshold=0.95,
                              log_event=_log))
    # caller decision (as in swarm._synthesise):
    if byp is None:
        aggregator_calls["n"] += 1
    check("T-048 bypass: bypass returned (aggregator skipped)", byp is not None)
    check("T-048 bypass: aggregator LLM NOT called", aggregator_calls["n"] == 0)
    check("T-048 bypass: highest-confidence individual response returned",
          byp is not None and (byp.get("node") or {}).get("output") == "A")
    check("T-048 bypass: council_size == 3",
          byp is not None and byp.get("council_size") == 3)
    check("T-048 bypass: event logged kind=aggregator_bypass",
          len(events) == 1 and events[0].get("kind") == "aggregator_bypass")
    check("T-048 bypass: event carries council_size + mean_similarity",
          events[0].get("council_size") == 3
          and abs(events[0].get("mean_similarity") - 1.0) < 1e-9)

    # A divergent council does NOT bypass -> aggregator runs.
    events2 = []
    nodes = _nodes("A", "B", "C")
    sel, byp = asyncio.get_event_loop().run_until_complete(
        M.apply_council_gates(nodes, embed_one=_mk_embed(),
                              diversity_gate=False, aggregator_bypass=True,
                              aggregator_bypass_threshold=0.95,
                              log_event=lambda **k: events2.append(k)))
    check("T-048 bypass: divergent council -> no bypass", byp is None)
    check("T-048 bypass: divergent council -> no event", events2 == [])


def t_degrade_open_missing_embed():
    # A missing embedding => cannot score => no-op (gates-off shape).
    nodes = _nodes("A", "A", "MISS")
    sel, byp = asyncio.get_event_loop().run_until_complete(
        M.apply_council_gates(nodes, embed_one=_mk_embed(missing="MISS"),
                              diversity_gate=True, aggregator_bypass=True))
    check("degrade-open: missing embedding -> nodes unchanged, no bypass",
          sel is nodes and byp is None)
    # Fewer than 2 nodes never gates.
    nodes = _nodes("A")
    sel, byp = asyncio.get_event_loop().run_until_complete(
        M.apply_council_gates(nodes, embed_one=_mk_embed(),
                              diversity_gate=True, aggregator_bypass=True))
    check("degrade-open: <2 nodes -> no-op", sel is nodes and byp is None)


def t_stats_counter():
    M.reset_stats()
    check("stats: pct 0.0 when no opportunities", M.bypassed_pct() == 0.0)
    M.note_aggregator(bypassed=True)
    M.note_aggregator(bypassed=False)
    M.note_aggregator(bypassed=False)
    M.note_aggregator(bypassed=True)
    check("stats: 2/4 bypassed -> 50.0 pct", M.bypassed_pct() == 50.0)
    M.reset_stats()
    check("stats: reset -> 0.0", M.bypassed_pct() == 0.0)


def main():
    # Own event loop (avoid DeprecationWarning churn across Python versions).
    asyncio.set_event_loop(asyncio.new_event_loop())
    t_select_diverse()
    t_should_bypass()
    t_medoid()
    t_gates_off_noop()
    t_diversity_gate_prunes()
    t_aggregator_bypass()
    t_degrade_open_missing_embed()
    t_stats_counter()
    print(f"\n{_fails} FAILED" if _fails else "\nok")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
