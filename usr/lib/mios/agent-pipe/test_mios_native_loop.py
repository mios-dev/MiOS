#!/usr/bin/env python3
# AI-hint: stdlib assert-script for mios_native_loop -- exercises the NATIVE
#   tool-loop responder's two loop-control branches with stubs (no network/DB):
#   (1) the deterministic `remember` fast-path TERMINATES the turn early WITHOUT
#   entering the secondary tool loop; (2) a neutral turn RUNS the secondary tool
#   loop (a tool message comes back) and then TERMINATES on the model's final
#   answer. Sibling imports (mios_secondary_loop / mios_verity / mios_sse) and
#   httpx are monkeypatched; every server-side dep is injected via configure().
# AI-related: ./mios_native_loop.py
# AI-functions: _run
"""Offline test for mios_native_loop._respond_native_loop_direct loop control."""

import asyncio
import contextvars
import json
import types

import mios_native_loop as M

FINAL_ANSWER = "The verified answer is 42."


def _async_const(value):
    async def _f(*a, **k):
        return value
    return _f


class _FakeResp:
    def __init__(self, content):
        self._c = content

    def json(self):
        return {"choices": [{"message": {"content": self._c}}]}


class _FakeClient:
    """Stands in for httpx.AsyncClient: only `.post` (final completion) is used
    on the non-streaming / no-emit path; `.stream` must NOT be touched."""

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, **k):
        return _FakeResp(FINAL_ANSWER)

    def stream(self, *a, **k):  # pragma: no cover - guard
        raise AssertionError("stream() should not run on the emit=None path")


_FAKE_HTTPX = types.SimpleNamespace(
    AsyncClient=_FakeClient,
    Timeout=lambda *a, **k: None,
)


def _base_configure(verb_catalog, dispatch_calls, loop_calls):
    async def _dispatch(verb, args, *, session_id=None):
        dispatch_calls.append((verb, args))
        return {"success": True}

    async def _secondary_loop(*a, **k):
        loop_calls.append(True)
        # a tool executed (tool message) then the model produced a final turn
        return [
            {"role": "assistant", "tool_calls": [
                {"function": {"name": "web_search"}}]},
            {"role": "tool", "content": "tool output evidence"},
            {"role": "assistant", "content": ""},
        ]

    M.configure(
        # config scalars
        BACKEND="http://x/v1", BACKEND_MODEL="m", _BACKEND_KEY=None,
        _BACKEND_HOSTPORT="x", REFINE_ENDPOINT="http://x/v1", REFINE_MODEL="m",
        STABLE_PREFIX=False, STABLE_PREFIX_HINT=False, STABLE_PREFIX_TAIL=0,
        NATIVE_LOOP_TOOL_CAP=0, NATIVE_LOOP_TIMEOUT_S=5.0,
        NATIVE_LOOP_CAPABILITY_GROUNDING=False, NATIVE_LOOP_PERSISTENCE=False,
        _NATIVE_LOOP_PERSISTENCE_PROSE="", NATIVE_LOOP_BREADTH_GUIDANCE=False,
        _NATIVE_LOOP_BREADTH_PROSE="", NATIVE_LOOP_REFLECTION=False,
        _NATIVE_LOOP_REFLECTION_PROSE="", NATIVE_LOOP_RECENCY_RANGE="day",
        NATIVE_LOOP_RECENCY_FANOUT=5, NATIVE_LOOP_RECENCY_DEFAULTS=False,
        NATIVE_LOOP_MATH_HINT=False, NATIVE_LOOP_DATE_ANCHOR=False,
        NATIVE_LOOP_QUERY_REFORMULATE=False, NATIVE_LOOP_STREAM_TOKENS=False,
        NATIVE_LOOP_STREAM_CHUNK=0, NATIVE_LOOP_STREAM_DELAY_MS=0,
        _ROUTING_DOMAINS={},
        # refs / contextvars
        _VERB_CATALOG=verb_catalog,
        _routed_domain_var=contextvars.ContextVar("rd", default=None),
        _orch_ctx_var=contextvars.ContextVar("orch", default=None),
        _recency_ctx_var=contextvars.ContextVar("rec", default=None),
        _worker_tools_core_cache=(lambda: None),
        # helpers
        dispatch_mios_verb=_dispatch,
        _usage_estimate=lambda p, c: {"total_tokens": 0},
        _identity_answer=lambda: "",
        _agent_contract=lambda: "",
        _capability_grounding=lambda vc: "",
        _env_grounding=lambda: "",
        _recall_agent_memory=_async_const(""),
        _recall_knowledge=_async_const(""),
        _rag_enrich=_async_const(""),
        _tool_pref_block=_async_const(""),
        _current_date_str=lambda: "2026-01-01",
        _worker_tools_surface_async=_async_const([]),
        _read_tool_enrich=_async_const(""),
        _needs_compute=_async_const(False),
        _src_record=lambda items: None,
        _src_collected=lambda: [],
        _src_record_from_text=lambda t: None,
        _endpoint_supports_parallel_tools=lambda ep: False,
        _filter_relevant_sources=lambda refs, *t: refs,
        _sources_markdown=lambda refs: "",
        _sources_annotations=lambda refs, t: [],
        _sources_metadata=lambda refs: [],
        _store_knowledge=lambda **k: None,
        _iter_answer_chunks=lambda text, size: [text],
        _write_skill_md_fire=lambda **k: None,
    )
    # directly-imported siblings (module attributes) -> patch in place
    M.httpx = _FAKE_HTTPX
    M.polish_response = _async_const("")
    M._v1_secondary_tool_loop = _secondary_loop


def _body_text(resp):
    return json.loads(bytes(resp.body).decode("utf-8"))["choices"][0]["message"]["content"]


def _run():
    # -- Branch 1: deterministic `remember` fast-path TERMINATES early ----------
    dcalls, lcalls = [], []
    _base_configure({"remember": {}}, dcalls, lcalls)
    resp = asyncio.run(M._respond_native_loop_direct(
        {"news": False, "web": False, "local_state": False},
        streaming=False, chat_id="c1", model="m", session_id="s1",
        last_user_text="remember that my editor is vim",
        persona_system="", messages=[{"role": "user", "content": "remember that my editor is vim"}],
        request=None, emit=None, tool_choice=None))
    txt = _body_text(resp)
    assert "vim" in txt, txt
    assert ("remember", {"fact": "my editor is vim"}) in dcalls, dcalls
    assert lcalls == [], "secondary tool loop must NOT run on the remember fast-path"
    print("branch-1 remember fast-path terminates early: OK ->", repr(txt))

    # -- Branch 2: neutral turn RUNS the tool loop then TERMINATES on final ----
    dcalls, lcalls = [], []
    _base_configure({}, dcalls, lcalls)  # no `remember`/`coderun` verbs -> no fast-path, no prefetch
    resp = asyncio.run(M._respond_native_loop_direct(
        {"news": False, "web": False, "local_state": False},
        streaming=False, chat_id="c2", model="m", session_id="s2",
        last_user_text="give me an overview of the project",
        persona_system="", messages=[{"role": "user", "content": "give me an overview of the project"}],
        request=None, emit=None, tool_choice=None))
    txt = _body_text(resp)
    assert lcalls == [True], "secondary tool loop must run exactly once"
    assert txt == FINAL_ANSWER, txt
    print("branch-2 tool loop runs then final answer terminates: OK ->", repr(txt))

    print("ALL OK")


class _FakeResp2:
    """status_code + .json() in the OpenAI (`choices`) shape -- MiOS is /v1-only --
    for the moved formulator/local-state tests. (`native` kept for signature
    compatibility; the retired `message` shape is no longer emitted.)"""
    def __init__(self, content, *, status=200, native=False):
        self._c = content
        self.status_code = status
        self.text = content
        self._native = native

    def json(self):
        if self._native:
            return {"message": {"content": self._c}}
        return {"choices": [{"message": {"content": self._c}}]}


def _fake_httpx_returning(content, **kw):
    class _C:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, **k):
            return _FakeResp2(content, **kw)

    return types.SimpleNamespace(AsyncClient=_C, Timeout=lambda *a, **k: None)


def _run_moved():
    """Cover the three functions extracted into mios_native_loop: the micro-LLM
    compute/web formulators + the local-state responder. All network is mocked;
    payload tokens are SYNTHETIC non-dictionary strings (no baked keywords)."""
    # _formulate_compute_snippet: empty -> "" with NO network call
    assert asyncio.run(M._formulate_compute_snippet("")) == ""
    # a fenced snippet is unwrapped to the runnable lines only
    M.httpx = _fake_httpx_returning("```python\nZZQX = 41 + 1\nprint(ZZQX)\n```")
    out = asyncio.run(M._formulate_compute_snippet("Vmbtok zzqx plff"))
    assert out == "ZZQX = 41 + 1\nprint(ZZQX)", repr(out)
    print("moved _formulate_compute_snippet fence-strip: OK ->", repr(out))

    # _formulate_web_query: <think> scratch is stripped (hybrid/local path)
    M.httpx = _fake_httpx_returning("<think>scratch</think>QRZL Vmbtok 9000")
    out = asyncio.run(M._formulate_web_query("zzqx plff", "GPU: QRZL-9000"))
    assert out == "QRZL Vmbtok 9000", repr(out)
    # empty user_text echoes the input unchanged (degrade-open, no network)
    assert asyncio.run(M._formulate_web_query("", "")) == ""
    print("moved _formulate_web_query think-strip + degrade: OK ->", repr(out))

    # _format_local_state: empty grounding -> None with NO network call
    M._env_grounding = lambda: ""
    M._LOCAL_STATE_SYSTEM = "SSOT-LOCAL-STATE-PROMPT"
    M._polish_post = (lambda ep, model, msgs, mx, temperature=0.0:
                      ("http://x/v1/chat/completions",
                       {"model": model, "messages": msgs}))
    assert asyncio.run(M._format_local_state("zzqx", "")) is None
    # /v1 (`choices`) shape -> content extracted via the polish call
    M.httpx = _fake_httpx_returning("QRZL Vmbtok enumerated")
    out = asyncio.run(M._format_local_state("zzqx plff", "live: QRZL=1"))
    assert out == "QRZL Vmbtok enumerated", repr(out)
    # empty/blank polished content collapses to None (the `or None` guard)
    M.httpx = _fake_httpx_returning("   ")
    assert asyncio.run(M._format_local_state("zzqx plff", "live: QRZL=1")) is None
    print("moved _format_local_state polish + native-shape extract: OK ->", repr(out))
    print("MOVED OK")


if __name__ == "__main__":
    _run()
    _run_moved()
