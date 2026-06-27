# AI-hint: stdlib assert-script gate for mios_swarm (the SWARM brain). Drives the
# extracted _respond_agent_dag (non-streaming) with fully stubbed deps -- NO
# network / DB -- to assert the LOAD-BEARING anti-fabrication synthesis survives
# the verbatim move: (1) PUNT-DROP -- a sibling node that punts ("I cannot
# provide...") is excluded from the polish synthesis input while a grounded
# fact-bearing node is kept (exercises the nested _is_punt marker+facty logic);
# (2) HONEST-WHEN-EMPTY -- a web turn whose RAW RESEARCH is empty never ships
# fabricated content: it routes through the native-loop fallback and the polish
# input carries the explicit "couldn't find specific results from live sources"
# grounding rule. Also asserts configure() injection + module boundary.
# AI-related: ./mios_swarm.py, ./server.py
# AI-functions: _stub_deps, _run, main
import asyncio
import contextvars
import json

import mios_swarm


class _FakeResp:
    """Minimal stand-in for the JSONResponse the native-loop fallback decodes."""
    def __init__(self, payload: dict):
        self.body = json.dumps(payload).encode("utf-8")


def _stub_deps(*, polish_holder, dag_result, native_payload=None,
               native_calls=None):
    """Inject pure in-process stubs (no network/DB) for every server-side dep
    _respond_agent_dag touches on the non-streaming path."""
    async def _exec_dag_bounded(*a, **k):
        return dag_result

    async def _polish(synth_in, refined, **kw):
        polish_holder.append(synth_in)
        # Echo a deterministic marker so `main` is inspectable; honest tests
        # override via native fallback.
        return "[POLISHED] " + (synth_in[:40] if synth_in else "")

    async def _read_enrich(*a, **k):
        return ""

    async def _web_enrich(*a, **k):
        return ""

    async def _live_names():
        return set()

    async def _native(*a, **k):
        if native_calls is not None:
            native_calls.append(1)
        if native_payload is None:
            return None
        return _FakeResp(native_payload)

    rdv = contextvars.ContextVar("routed_domain", default=None)

    mios_swarm.configure(
        swarm_max_width=6, swarm_max_cpu_nodes=2, swarm_deepen_enabled=False,
        slow_lane_block_chars=1500, dag_replan_max=1,
        dag_empty_native_fallback=True, slow_lanes=set(),
        agent_registry={}, verb_catalog={}, routed_domain_var=rdv,
        pick_agent=lambda r: ("a", {}),
        dedup_pool_by_target=lambda p: p,
        is_slow_lane_ep=lambda ep: False,
        agent_lane=lambda c: "light",
        live_agent_names=_live_names,
        read_tool_enrich=_read_enrich,
        respond_native_loop_direct=_native,
        strip_think_tags=lambda t: t,
        filter_relevant_sources=lambda refs, *t: [],
        sources_markdown=lambda refs: "",
        sources_annotations=lambda refs, t: [],
        sources_metadata=lambda refs: [],
        src_collected=lambda: [],
        src_record_from_text=lambda t: None,
        usage_estimate=lambda p, c: {},
    )
    # _web_research_enrich is a direct sibling import -> monkeypatch on the module.
    mios_swarm._web_research_enrich = _web_enrich
    mios_swarm._execute_dag_bounded = _exec_dag_bounded
    mios_swarm.polish_response = _polish


def _call(refined, dag_result, **kw):
    dag = {"summary": "s", "nodes": [
        {"id": "t1", "agent": "a", "prompt": "do it", "title": "facet one"}]}
    resp = asyncio.run(
        mios_swarm._respond_agent_dag(
            dag, refined, streaming=False, chat_id="c1", model="m",
            session_id=None, last_user_text="what is happening",
            persona_system="", request=None))
    return resp


def test_punt_drop():
    """A punting sibling is dropped from synthesis; the grounded node is kept."""
    PUNT = "I cannot provide any specific information about that right now."
    GOOD = ("The summit concluded on March 4 2026 with a signed accord [1]. "
            "Delegates from 14 nations ratified the framework, allocating "
            "4200 units across three phases, with the first phase opening in "
            "April 2026 and the review scheduled for 2027. The accord text "
            "lists concrete commitments, funding figures, and named annexes "
            "that run well past the length threshold so the synthesis treats "
            "this as a real grounded answer rather than a marker-only punt. "
            "Additional detail [1] keeps the body fact-dense and long.")
    dag_result = {
        "summary": "s", "nodes_total": 2, "nodes_executed": 2, "success": True,
        "node_results": [
            {"tool": "agent:a", "node_id": "t1", "success": True,
             "satisfied": True, "output": PUNT, "latency_ms": 1},
            {"tool": "agent:b", "node_id": "t2", "success": True,
             "satisfied": True, "output": GOOD, "latency_ms": 1},
        ],
    }
    holder = []
    _stub_deps(polish_holder=holder, dag_result=dag_result)
    _call({"web": False, "refined_text": "q"}, dag_result)
    assert holder, "polish_response was never called"
    synth_in = holder[-1]
    # punt-drop: the grounded node's facts are fed to polish, the punt is not.
    assert "signed accord" in synth_in, "grounded node dropped from synthesis"
    assert PUNT not in synth_in, "punt node was NOT dropped from synthesis"
    print("test_punt_drop: PASS")


def test_honest_when_empty():
    """A web turn with EMPTY raw research never fabricates: it routes to the
    native-loop fallback and the polish input carries the honest-empty rule."""
    PUNT = "I do not have enough information; would you like me to search again?"
    dag_result = {
        "summary": "s", "nodes_total": 1, "nodes_executed": 1, "success": False,
        "node_results": [
            {"tool": "agent:a", "node_id": "t1", "success": True,
             "satisfied": True, "output": PUNT, "latency_ms": 1},
        ],
    }
    holder = []
    calls = []
    _stub_deps(polish_holder=holder, dag_result=dag_result,
               native_payload={"choices": [{"message": {
                   "content": "I couldn't find specific live results for today."}}],
                   "mios_sources": []},
               native_calls=calls)
    resp = _call({"web": True, "refined_text": "world news today"}, dag_result)
    # The honest-empty grounding rule must be present in the synthesis prompt
    # (the load-bearing anti-fabrication instruction moved byte-identically).
    synth_in = holder[-1]
    assert "couldn't find specific results from live sources" in synth_in, \
        "honest-when-empty grounding rule missing from synthesis input"
    # An ungrounded web turn routes to the native-loop fallback (no fabrication).
    assert calls, "ungrounded web turn did NOT engage the native-loop fallback"
    body = json.loads(bytes(resp.body).decode("utf-8"))
    main = body["choices"][0]["message"]["content"]
    assert "couldn't find specific live results" in main, \
        "fallback honest answer not adopted"
    print("test_honest_when_empty: PASS")


def test_boundary_and_surface():
    assert hasattr(mios_swarm, "_agent_dag_from_tasks")
    assert hasattr(mios_swarm, "_respond_agent_dag")
    assert hasattr(mios_swarm, "_plan_swarm")
    assert hasattr(mios_swarm, "_expand_facets")
    assert hasattr(mios_swarm, "configure")
    src = open("mios_swarm.py", encoding="utf-8").read()
    for bad in ("import server", "from server "):
        assert bad not in src, f"boundary violation: {bad!r} in mios_swarm.py"
    print("test_boundary_and_surface: PASS")


# -- swarm DECOMPOSER pair (_plan_swarm / _expand_facets) ----------------------

class _FakePlannerResp:
    """Stand-in for the httpx response the planner reads (.status_code/.json())."""
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body

    def json(self):
        return self._body


def _fake_httpx(*, status=200, body=None):
    """A fake `httpx` whose AsyncClient.post returns a fixed response -- the
    decomposer pair calls `httpx.AsyncClient(...)` directly, so swapping the
    module attribute keeps the test fully in-process (no network)."""
    resp = _FakePlannerResp(status, body or {})

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, *a, **k):
            return resp

    ns = type("httpx", (), {})()
    ns.AsyncClient = _Client
    ns.HTTPError = type("HTTPError", (Exception,), {})
    return ns


async def _live_none():
    return set()


def _stub_planner(*, depth_exhausted=None):
    """Inject ONLY the deps the decomposer pair reads + monkeypatch the
    module-level config / sibling import so no SSOT or network is required."""
    mios_swarm.configure(
        max_dispatch_depth=2, swarm_model="test-model",
        swarm_system_head="SWARM HEAD\n", agent_catalog_rendered="ROSTER",
        depth_exhausted=(depth_exhausted or (lambda: False)),
        dispatch_depth=lambda: 2,
        render_agent_catalog=lambda reg: "RENDERED",
        agent_registry={"a": {}, "b": {}},
        live_agent_names=_live_none,
    )
    mios_swarm._env_grounding = lambda: "ENV"
    mios_swarm.PLANNER_ENABLED = True
    mios_swarm.PLANNER_ENDPOINT = "http://test/v1"
    mios_swarm.PLANNER_TIMEOUT_S = 5
    mios_swarm.PLANNER_MAX_TOKENS = 256


def _content_body(text):
    """Shape a chat-completion body carrying `text` as message.content."""
    return {"choices": [{"message": {"content": text}}]}


def test_plan_swarm_gates():
    """Every early-return gate yields [] -- BEFORE any model call (a fake model
    that WOULD split is installed, so a gate that failed to fire would leak it)."""
    _stub_planner()
    mios_swarm.httpx = _fake_httpx(body=_content_body(
        '{"subtasks":[{"agent":"a","task":"leak","query":"leak"}]}'))
    mios_swarm.PLANNER_ENABLED = False
    assert asyncio.run(mios_swarm._plan_swarm("a real splittable ask")) == [], \
        "disabled planner must return []"
    mios_swarm.PLANNER_ENABLED = True
    assert asyncio.run(mios_swarm._plan_swarm("   ")) == [], \
        "blank ask must return []"
    _stub_planner(depth_exhausted=lambda: True)
    mios_swarm.httpx = _fake_httpx(body=_content_body(
        '{"subtasks":[{"agent":"a","task":"leak","query":"leak"}]}'))
    assert asyncio.run(mios_swarm._plan_swarm("a real splittable ask")) == [], \
        "recursion-depth-exhausted must degrade closed to []"
    print("test_plan_swarm_gates: PASS")


def test_plan_swarm_splits():
    """A splittable ask + a stubbed model returns >=2 shaped sub-tasks."""
    _stub_planner()
    mios_swarm.httpx = _fake_httpx(body=_content_body(
        '{"subtasks":['
        '{"agent":"a","task":"research the economy angle","query":"economy news"},'
        '{"agent":"b","task":"research the technology angle","query":"tech news"}'
        ']}'))
    tasks = asyncio.run(mios_swarm._plan_swarm("what is happening in the world"))
    assert len(tasks) >= 2, f"expected >=2 sub-tasks, got {tasks!r}"
    for t in tasks:
        assert t.get("refined_text"), f"sub-task missing refined_text: {t!r}"
        assert "target_agent" in t and "title" in t
    assert tasks[0]["target_agent"] == "a"
    print("test_plan_swarm_splits: PASS")


def test_expand_facets_gate():
    """need <= 0 (target already met) returns [] BEFORE the model call (a fake
    model that WOULD return facets is installed to prove the short-circuit)."""
    _stub_planner()
    mios_swarm.httpx = _fake_httpx(body=_content_body('{"facets":["unused"]}'))
    out = asyncio.run(mios_swarm._expand_facets("ask", ["x", "y", "z"], 2))
    assert out == [], f"need<=0 must return [] (gate before model call), got {out!r}"
    print("test_expand_facets_gate: PASS")


def test_expand_facets_positive():
    """New, deduped facets are returned: existing ones filtered, capped to need."""
    _stub_planner()
    mios_swarm.httpx = _fake_httpx(body=_content_body(
        '{"facets":["renewable energy adoption","ev battery supply chain","a"]}'))
    out = asyncio.run(mios_swarm._expand_facets("clean energy", ["a"], 3))
    assert "a" not in out, "existing facet must be deduped out"
    assert len(out) == 2, f"expected need=2 new facets, got {out!r}"
    assert "renewable energy adoption" in out
    print("test_expand_facets_positive: PASS")


def main():
    test_boundary_and_surface()
    test_punt_drop()
    test_honest_when_empty()
    test_plan_swarm_gates()
    test_plan_swarm_splits()
    test_expand_facets_gate()
    test_expand_facets_positive()
    print("ALL mios_swarm TESTS PASSED")


if __name__ == "__main__":
    main()
