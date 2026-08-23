#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_reflect (strangler-fig extraction). Pure stdlib, no server.py/DB/network/pytest.
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_lib_mios_agent_pipe_test_mios_reflect_py.md
"""Unit tests for mios_reflect (strangler-fig extraction)."""

import asyncio
import sys
import types

import mios_reflect as r

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    line = f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else "")
    try:
        print(line)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "ascii"
        print(line.encode(enc, "replace").decode(enc))


def _mk_db_read(rows):
    async def _f(sql, *, pg_sql=None, pg_params=None):
        return [{"result": rows}]
    return _f


def _wire_inline(rows):
    r.configure(
        db_read=_mk_db_read(rows),
        db_write=lambda *a, **k: None,
        verb_catalog={},
    )


def t_inline_gate():
    _wire_inline([])
    check("inline: no session -> None",
          asyncio.run(r._inline_satisfaction_check(None, {"intent": "chat"})) is None)
    check("inline: non-dict refine -> None",
          asyncio.run(r._inline_satisfaction_check("123", None)) is None)


def t_inline_chat():
    _wire_inline([])
    out = asyncio.run(r._inline_satisfaction_check("123", {"intent": "chat"}))
    check("inline: chat/no-tools -> satisfied",
          out and out["kind"] == "user_query_satisfied"
          and out["payload"].get("reason") == "chat_no_tools_expected", repr(out))


def t_inline_success():
    _wire_inline([{"tool": "open_app", "success": True,
                   "exit_code": 0, "result_preview": ""}])
    out = asyncio.run(r._inline_satisfaction_check("123", {"intent": "agent"}))
    check("inline: all-success -> satisfied(all_succeeded)",
          out and out["kind"] == "user_query_satisfied"
          and out["payload"].get("all_succeeded") is True, repr(out))


def t_inline_failed():
    _wire_inline([{"tool": "open_app", "success": False,
                   "exit_code": 2, "result_preview": "boom"}])
    out = asyncio.run(r._inline_satisfaction_check("123", {"intent": "agent"}))
    check("inline: failure -> unsatisfied(failed_tools)",
          out and out["kind"] == "user_query_unsatisfied"
          and out["payload"].get("failed_tools"), repr(out))


class _FakeResp:
    status_code = 200
    text = ""

    def __init__(self, content):
        self._content = content

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


def _mk_client(content):
    class _FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, **k):
            return _FakeResp(content)

    return _FakeClient


async def _no_reflections(*a, **k):
    return []


def _wire_reflect(content):
    r.configure(
        refine_enabled=True,
        refine_model="m",
        refine_endpoint="http://127.0.0.1:0",
        refine_timeout_s=5,
        reflect_system="SYS",
        emit_session_event=lambda fields, sid: None,
    )
    r.httpx = types.SimpleNamespace(AsyncClient=_mk_client(content), HTTPError=Exception)
    r._recent_reflections = _no_reflections


_NODE = {"tool": "broken_verb", "args": {"x": 1}}
_RESULT = {"stderr": "unknown verb", "exit_code": 2}
_PLAN = {"summary": "do a thing"}


def t_reflect_gate():
    r.configure(refine_enabled=False)
    out = asyncio.run(r.reflect_on_step_failure(_NODE, _RESULT, _PLAN))
    check("reflect: refine-disabled -> None", out is None, repr(out))


def t_reflect_corrected():
    _wire_reflect('{"tool": "open_app", "args": {"name": "x"}, "rationale": "swap verb"}')
    out = asyncio.run(r.reflect_on_step_failure(_NODE, _RESULT, _PLAN, session_id="123"))
    check("reflect: returns corrected step",
          out and out.get("tool") == "open_app", repr(out))


def t_reflect_unfixable():
    _wire_reflect('{"tool": "", "args": {}, "rationale": "unfixable"}')
    out = asyncio.run(r.reflect_on_step_failure(_NODE, _RESULT, _PLAN, session_id="123"))
    check("reflect: unfixable -> None", out is None, repr(out))


def t_recent_verdicts():
    r.configure(db_read=_mk_db_read([{"kind": "user_query_unsatisfied"}]))
    out = asyncio.run(r._recent_satisfaction_verdicts(limit=3))
    check("verdicts: returns the result rows",
          out == [{"kind": "user_query_unsatisfied"}], repr(out))

    async def _empty(sql, *, pg_sql=None, pg_params=None):
        return None
    r.configure(db_read=_empty)
    check("verdicts: no rows -> []",
          asyncio.run(r._recent_satisfaction_verdicts()) == [])


def t_recent_tool_history():
    check("tool-history: no session -> []",
          asyncio.run(r._recent_tool_history(None)) == [])
    r.configure(db_read=_mk_db_read([{"tool": "a"}, {"tool": "b"}]))
    out = asyncio.run(r._recent_tool_history("123"))
    check("tool-history: reversed to chronological",
          out == [{"tool": "b"}, {"tool": "a"}], repr(out))


class _JResp:
    text = ""

    def __init__(self, content, status=200):
        self._content = content
        self.status_code = status

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


def _mk_judge_client(content, status=200):
    class _C:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, **k):
            return _JResp(content, status)

    return _C


def _wire_judge(content, status=200):
    r.configure(refine_model="m", refine_endpoint="http://127.0.0.1:0",
                refine_timeout_s=5)
    r.httpx = types.SimpleNamespace(AsyncClient=_mk_judge_client(content, status),
                                    HTTPError=Exception)


def t_judge_empty():
    check("judge: empty answer -> False",
          asyncio.run(r._judge_answer_satisfied("q", "")) is False)


def t_judge_yes_no():
    _wire_judge("yes")
    check("judge: 'yes' -> satisfied",
          asyncio.run(r._judge_answer_satisfied("q", "a real answer")) is True)
    _wire_judge("no")
    check("judge: 'no' -> not satisfied",
          asyncio.run(r._judge_answer_satisfied("q", "a punt")) is False)


def t_judge_degrade():
    _wire_judge("whatever", status=503)
    check("judge: non-200 -> True (degrade-open)",
          asyncio.run(r._judge_answer_satisfied("q", "x")) is True)


def _mk_panel_client(by_host):
    """Judge-panel stub: `by_host` maps a host:port fragment to (content, status),
    so each lane in the panel can answer differently."""
    class _C:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, **k):
            for frag, (content, status) in by_host.items():
                if frag in url:
                    if status == "boom":
                        raise RuntimeError("lane transport failure")
                    return _JResp(content, status)
            return _JResp("yes", 200)

    return _C


_LANES = [{"name": "a", "endpoint": "http://127.0.0.1:1"},
          {"name": "b", "endpoint": "http://127.0.0.1:2"},
          {"name": "c", "endpoint": "http://127.0.0.1:3"}]


def _wire_panel(by_host, *, enable=True, lanes=None, weights=None, min_lanes=2):
    lanes = [dict(x) for x in (lanes if lanes is not None else _LANES)]
    if weights:
        for lane in lanes:
            if lane["name"] in weights:
                lane["weight"] = weights[lane["name"]]
    r.configure(refine_model="m", refine_endpoint="http://127.0.0.1:0",
                refine_timeout_s=5, consensus_enabled=enable,
                consensus_lanes=lanes, consensus_threshold=0.5,
                consensus_min_lanes=min_lanes, consensus_timeout_s=5,
                consensus_weight_floor=0.1)
    r.httpx = types.SimpleNamespace(AsyncClient=_mk_panel_client(by_host),
                                    HTTPError=Exception)


def t_panel_off_is_single_lane():
    # Gate closed: the panel must not be consulted at all, so the lone
    # single-lane endpoint (:0) decides even though the panel lanes say yes.
    _wire_panel({":0": ("no", 200), ":1": ("yes", 200), ":2": ("yes", 200)},
                enable=False)
    check("panel: disabled -> single-lane verdict wins",
          asyncio.run(r._judge_answer_satisfied("q", "a")) is False)


def t_panel_majority():
    _wire_panel({":0": ("yes", 200), ":1": ("no", 200),
                 ":2": ("no", 200), ":3": ("no", 200)})
    check("panel: majority no -> not satisfied",
          asyncio.run(r._judge_answer_satisfied("q", "a")) is False)
    _wire_panel({":0": ("no", 200), ":1": ("yes", 200),
                 ":2": ("yes", 200), ":3": ("yes", 200)})
    check("panel: majority yes overrides the single lane",
          asyncio.run(r._judge_answer_satisfied("q", "a")) is True)


def t_panel_weight_beats_headcount():
    # Two light lanes say no, one heavy lane says yes: weight decides.
    _wire_panel({":0": ("no", 200), ":1": ("yes", 200),
                 ":2": ("no", 200), ":3": ("no", 200)},
                weights={"a": 3.0, "b": 0.5, "c": 0.5})
    check("panel: a heavy lane outvotes two light ones",
          asyncio.run(r._judge_answer_satisfied("q", "a")) is True)


def t_panel_abstain_not_a_no():
    # One lane dead, one says yes: the dead lane must not read as a rejection.
    _wire_panel({":0": ("no", 200), ":1": ("yes", 200),
                 ":2": ("yes", 200), ":3": ("x", "boom")})
    check("panel: a dead lane abstains rather than voting no",
          asyncio.run(r._judge_answer_satisfied("q", "a")) is True)


def t_panel_no_quorum_falls_back():
    # Every panel lane is down -> no quorum -> the single-lane answer stands.
    _wire_panel({":0": ("no", 200), ":1": ("x", "boom"),
                 ":2": ("x", "boom"), ":3": ("x", "boom")})
    check("panel: whole panel down -> single-lane verdict",
          asyncio.run(r._judge_answer_satisfied("q", "a")) is False)

    # Under-configured panel (one lane) never engages.
    _wire_panel({":0": ("no", 200), ":1": ("yes", 200)},
                lanes=[{"name": "a", "endpoint": "http://127.0.0.1:1"}])
    check("panel: fewer lanes than min_lanes -> single-lane verdict",
          asyncio.run(r._judge_answer_satisfied("q", "a")) is False)


def main():
    t_inline_gate()
    t_inline_chat()
    t_inline_success()
    t_inline_failed()
    t_reflect_gate()
    t_reflect_corrected()
    t_reflect_unfixable()
    t_recent_verdicts()
    t_recent_tool_history()
    t_judge_empty()
    t_judge_yes_no()
    t_judge_degrade()
    t_panel_off_is_single_lane()
    t_panel_majority()
    t_panel_weight_beats_headcount()
    t_panel_abstain_not_a_no()
    t_panel_no_quorum_falls_back()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
