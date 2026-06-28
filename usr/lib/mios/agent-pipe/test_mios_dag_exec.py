#!/usr/bin/env python3
# AI-hint: Stdlib assert-test for mios_dag_exec (refactor R8 DAG execution wave).
# Stubs every injected dep (no network/DB) and asserts: (1) _execute_dag_node
# dispatches a VERB node through the broker (dispatch_mios_verb) vs an AGENT node
# through the agent-call path, returning the correct node_result shape for each;
# (2) _dag_levels topological layering puts a dependent node strictly after its
# dependency; (3) execute_dag (level path) actually executes nodes in dep order.
# AI-related: ./mios_dag_exec.py
# AI-functions: test
"""Offline assert-script for mios_dag_exec. Run: python test_mios_dag_exec.py"""
import asyncio

import mios_dag_exec as M


def _configure_common():
    """Inject lightweight stubs for the deps both node kinds touch."""
    M.configure(
        agent_contract=lambda: "",                       # falsy -> skip env_grounding
        role_system=lambda name: "",
        scratchpad_render=lambda: "",
        agent_lane=lambda cfg: "gpu",                    # not in SLOW_LANES (empty)
        slow_lanes=set(),
        worker_tools_enable=False,
        kv_fork_enable=False,
        planner_reflexion_cap=2,
        dag_node_retry=1,
        dag_node_deadline_s=30.0,
        dag_node_deadline_slow_s=60.0,
        dag_node_max_tokens=128,
        dag_node_slow_max_tokens=64,
    )


def test_verb_node_dispatches_via_broker():
    _configure_common()
    seen = {"calls": []}

    async def _fake_dispatch(tool, args, *, session_id=None):
        seen["calls"].append((tool, dict(args), session_id))
        return {"success": True, "output": "broker-ran", "latency_ms": 3}

    M.configure(dispatch_mios_verb=_fake_dispatch)

    node = {"id": "v1", "tool": "web_search", "args": {"q": "hello"}}
    res = asyncio.run(
        M._execute_dag_node(node, {}, {}, "summary", "sess-1", object()))

    assert res["tool"] == "web_search", res
    assert res["success"] is True, res
    assert res["output"] == "broker-ran", res
    assert res["node_id"] == "v1", res
    assert res["args"] == {"q": "hello"}, res
    assert "_act" in res, res
    # The broker was the ONLY execution path (no agent call).
    assert seen["calls"] == [("web_search", {"q": "hello"}, "sess-1")], seen
    print("[PASS] verb node dispatches via broker (dispatch_mios_verb)")


def test_agent_node_dispatches_via_agent_call():
    _configure_common()
    captured = {"name": None, "body": None}

    async def _fake_complete(name, cfg, body, headers, client, *,
                             prefer_cpu=True, priority=None):
        captured["name"] = name
        captured["body"] = body
        return (name, "AGENT-ANSWER")

    # Force the verb broker to blow up so we PROVE the agent branch never touches it.
    async def _boom(tool, args, *, session_id=None):
        raise AssertionError("agent node must NOT dispatch a verb")

    M.configure(dispatch_mios_verb=_boom)
    M._call_agent_complete = _fake_complete   # imported sibling -> module-attr stub

    node = {"id": "a1", "agent": "researcher", "prompt": "investigate X"}
    res = asyncio.run(
        M._execute_dag_node(node, {}, {}, "summary", "sess-2", object()))

    assert res["tool"] == "agent:researcher", res
    assert res["success"] is True, res
    assert res["output"] == "AGENT-ANSWER", res
    assert res["node_id"] == "a1", res
    assert captured["name"] == "researcher", captured
    # The prompt was carried into the agent body as a user message.
    msgs = captured["body"]["messages"]
    assert any(m.get("content") == "investigate X" for m in msgs), msgs
    print("[PASS] agent node dispatches via agent-call (not the broker)")


def test_dag_levels_topo_order():
    # Chain A -> B -> C: each must land in its own level, in order.
    nodes = [
        {"id": "A"},
        {"id": "B", "deps": ["A"]},
        {"id": "C", "deps": ["B"]},
    ]
    levels = M._dag_levels(nodes)
    ids = [[str(n["id"]) for n in lvl] for lvl in levels]
    assert ids == [["A"], ["B"], ["C"]], ids
    # Two independent roots share one level (concurrent).
    nodes2 = [{"id": "X"}, {"id": "Y"}, {"id": "Z", "deps": ["X", "Y"]}]
    lv2 = M._dag_levels(nodes2)
    ids2 = [sorted(str(n["id"]) for n in lvl) for lvl in lv2]
    assert ids2 == [["X", "Y"], ["Z"]], ids2
    print("[PASS] _dag_levels topological layering (dependent after dependency)")


def test_execute_dag_runs_in_dep_order():
    _configure_common()
    M.RUN_TEMPLATE_ENABLE = False          # skip the run-template capture path
    M.configure(swarm_saturate=False)      # level-barrier path

    order = []

    async def _fake_node(node, results_by_id, seen_actions, summary,
                         session_id, client, frag_q=None):
        nid = str(node.get("id"))
        order.append(nid)
        return {"success": True, "output": "ok", "node_id": nid,
                "tool": str(node.get("tool") or "verb"), "args": {},
                "_act": f"act-{nid}"}

    async def _fake_client():
        return object()

    M._execute_dag_node = _fake_node
    M._record_dag_node_row = lambda res, sid: None
    M.configure(get_client=_fake_client, scratchpad_note=lambda *a, **k: None)
    # _node_deepens is native now; DEEPEN_LANES defaults empty -> never deepen.

    dag = {"summary": "s", "nodes": [
        {"id": "A", "tool": "t1", "args": {}},
        {"id": "B", "tool": "t2", "args": {}, "deps": ["A"]},
        {"id": "C", "tool": "t3", "args": {}, "deps": ["B"]},
    ]}
    result = asyncio.run(M.execute_dag(dag, session_id=None))

    assert result["success"] is True, result
    assert result["nodes_executed"] == 3, result
    # A strictly before B strictly before C (dep order preserved).
    assert order.index("A") < order.index("B") < order.index("C"), order
    print("[PASS] execute_dag executes nodes in dependency order")


def test_smart_extract_resolves_field_ndjson_plain():
    """_smart_extract_from_jsonish (moved home): named-field preference, NDJSON
    first-object, plain-text first-line. Synthetic tokens (no dictionary words);
    the JSON keys are the module's own structural extraction contract."""
    M.configure(sanitize_tool_text=lambda s: s)   # identity sanitizer for the test
    # Single JSON object -> 'name' wins over 'id' (module's structural order).
    assert M._smart_extract_from_jsonish('{"id": "zqxw0", "name": "vlkn7"}') == "vlkn7"
    # NDJSON -> the FIRST object's best field.
    assert M._smart_extract_from_jsonish('{"name": "alfa9"}\n{"name": "bra8"}') == "alfa9"
    # Non-JSON -> first non-empty line, capped.
    assert M._smart_extract_from_jsonish("plain-tok-42\nsecond-tok") == "plain-tok-42"
    print("[PASS] _smart_extract_from_jsonish field/NDJSON/plain resolution")


def test_substitute_ek_refs_field_bare_passthrough():
    """_substitute_ek_refs (moved home): #E<id>.<field>, bare #E<id> smart-extract,
    and non-ref passthrough -- all via the native regexes + smart-extractor."""
    M.configure(sanitize_tool_text=lambda s: s)
    results = {"n1": {"output": '{"launch": "exec-tok9"}'}}
    assert M._substitute_ek_refs({"cmd": "#En1.launch"}, results)["cmd"] == "exec-tok9"
    assert M._substitute_ek_refs({"cmd": "#En1"}, results)["cmd"] == "exec-tok9"
    assert M._substitute_ek_refs({"k": "no-ref-tok"}, results) == {"k": "no-ref-tok"}
    print("[PASS] _substitute_ek_refs field/bare/passthrough resolution")


def test_fit_context_degrade_and_slow_pin():
    """_fit_context (moved home): CTX_FIT off -> want_ctx verbatim (degrade-open);
    on + slow lane -> pinned at want_ctx."""
    M.configure(ctx_fit=False, slow_lanes=set(), worker_tool_ctx_max=24576)
    assert M._fit_context([], [], "gpu", 4096) == 4096
    M.configure(ctx_fit=True, slow_lanes={"cpu"})
    assert M._fit_context([{"role": "user", "content": "x"}], [], "cpu", 4096) == 4096
    print("[PASS] _fit_context degrade-open + slow-lane pin")


def test_node_deepens_fast_lane_only():
    """_node_deepens (moved home): only a fast (DEEPEN_LANES) agent node deepens;
    no-agent and slow-lane nodes never do."""
    M.configure(deepen_lanes={"gpu"}, agent_lane=lambda cfg: "gpu",
                agent_registry={"a1": {}})
    assert M._node_deepens({"agent": "a1"}) is True
    assert M._node_deepens({"tool": "t"}) is False
    M.configure(agent_lane=lambda cfg: "cpu")
    assert M._node_deepens({"agent": "a1"}) is False
    print("[PASS] _node_deepens fast-lane-only gate")


def test_reap_cpu_lane_disabled_noop():
    """_reap_cpu_lane (moved home): no-op when RUNAWAY_REAP_ENABLE is off (never
    raises, never touches the network)."""
    M.configure(runaway_reap_enable=False)
    asyncio.run(M._reap_cpu_lane("test"))   # must return without error / no I/O
    print("[PASS] _reap_cpu_lane disabled no-op")


def test_deepen_early_exit():
    """A8: _deepen_until_barrier early-exits on a SATISFIED node only when the SSOT
    flag is on; degrade-open -> a judge error/timeout falls through to the
    deadline-bound loop (never under-computes). Four scenarios, observed via the
    number of (stubbed) agent coverage passes."""
    _BOUND = 4
    calls = {"agent": 0, "judge": 0}

    async def _fake_complete(name, cfg, body, headers, client, *,
                             prefer_cpu=False, priority=None):
        calls["agent"] += 1
        return (name, f"distinct coverage point {calls['agent']}")

    # Deepen with NO web fetch + a small iter bound + fast stubbed passes.
    M._call_agent_complete = _fake_complete
    M.configure(
        deepen_fetch=False,
        deepen_max_iters=_BOUND,
        deepen_deadline_s=30.0,
        deepen_web_timeout_s=1.0,
        dag_node_max_tokens=64,
        agent_registry={"facet": {"model": "m"}},
        deepen_judge_timeout_s=5.0,
    )
    node = {"agent": "facet", "_base_query": "what is the status of X", "title": "X"}
    base_res = {"output": "a concrete primary answer", "success": True}

    def _run():
        return asyncio.run(M._deepen_until_barrier(
            dict(node), dict(base_res), asyncio.Event(), "sess", object()))

    # (1) DISABLED (the default): runs to the iter bound -- current behavior.
    calls["agent"] = 0
    M.configure(deepen_early_exit=False, judge_answer_satisfied=None)
    r = _run()
    assert calls["agent"] == _BOUND, calls
    assert r.get("deepened") == _BOUND, r

    # (2) ENABLED + judge says SATISFIED: exits before burning any deepen pass.
    calls["agent"] = 0
    calls["judge"] = 0

    async def _judge_yes(q, a):
        calls["judge"] += 1
        return True

    M.configure(deepen_early_exit=True, judge_answer_satisfied=_judge_yes)
    r = _run()
    assert calls["agent"] == 0, calls          # satisfied -> zero extra passes
    assert calls["judge"] >= 1, calls          # the judge WAS consulted

    # (3) ENABLED + judge says UNSATISFIED: runs to the iter bound (never short-circuits).
    calls["agent"] = 0

    async def _judge_no(q, a):
        return False

    M.configure(deepen_early_exit=True, judge_answer_satisfied=_judge_no)
    r = _run()
    assert calls["agent"] == _BOUND, calls
    assert r.get("deepened") == _BOUND, r

    # (4) ENABLED + judge ERRORS: degrade-open -> fall through to the deadline-bound
    #     loop (never under-computes), so the node still runs its full coverage.
    calls["agent"] = 0

    async def _judge_boom(q, a):
        raise RuntimeError("judge backend down")

    M.configure(deepen_early_exit=True, judge_answer_satisfied=_judge_boom)
    r = _run()
    assert calls["agent"] == _BOUND, calls
    assert r.get("deepened") == _BOUND, r

    print("[PASS] deepen early-exit: disabled / satisfied / unsatisfied / judge-error")


if __name__ == "__main__":
    test_verb_node_dispatches_via_broker()
    test_agent_node_dispatches_via_agent_call()
    test_dag_levels_topo_order()
    test_execute_dag_runs_in_dep_order()
    test_smart_extract_resolves_field_ndjson_plain()
    test_substitute_ek_refs_field_bare_passthrough()
    test_fit_context_degrade_and_slow_pin()
    test_node_deepens_fast_lane_only()
    test_reap_cpu_lane_disabled_noop()
    test_deepen_early_exit()
    print("\nok")
