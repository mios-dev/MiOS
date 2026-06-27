#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_reflect (strangler-fig extraction). Pure stdlib, no server.py/DB/network/pytest. Pins the self-assessment invariants of the extracted cluster: _inline_satisfaction_check early-returns None on a missing session / non-dict refine (the cheap gate), folds a chat-with-no-tools turn to user_query_satisfied(chat_no_tools_expected), an all-success tool_call set to user_query_satisfied(all_succeeded), and a failed tool_call to user_query_unsatisfied(failed_tools) -- every DB read/write stubbed via configure(); reflect_on_step_failure early-returns None when REFINE is disabled (the gate), returns the model's corrected step dict on a canned 200, and returns None on an empty-tool "unfixable" verdict -- httpx monkeypatched + _recent_reflections + the session-event emitter stubbed. Guards the moved bodies + their configure() DI seam so a later move can't silently change verdict/correction behaviour.
# AI-related: ./mios_reflect.py
# AI-functions: check, _mk_db_read, _wire_inline, t_inline_gate, t_inline_chat, t_inline_success, t_inline_failed, _wire_reflect, t_reflect_gate, t_reflect_corrected, t_reflect_unfixable, t_recent_verdicts, t_recent_tool_history, _mk_judge_client, _wire_judge, t_judge_empty, t_judge_yes_no, t_judge_degrade, main
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


# ── _inline_satisfaction_check (DB stubbed via configure) ──────────
def _mk_db_read(rows):
    async def _f(sql, *, pg_sql=None, pg_params=None):
        # The function reads rows from the LAST result envelope.
        return [{"result": rows}]
    return _f


def _wire_inline(rows):
    r.configure(
        db_read=_mk_db_read(rows),
        db_write=lambda *a, **k: None,
        verb_catalog={},
    )


def t_inline_gate():
    # Missing session_id OR non-dict refine short-circuits before any DB touch.
    _wire_inline([])
    check("inline: no session -> None",
          asyncio.run(r._inline_satisfaction_check(None, {"intent": "chat"})) is None)
    check("inline: non-dict refine -> None",
          asyncio.run(r._inline_satisfaction_check("123", None)) is None)


def t_inline_chat():
    # chat intent + no recorded tools = expected -> satisfied.
    _wire_inline([])
    out = asyncio.run(r._inline_satisfaction_check("123", {"intent": "chat"}))
    check("inline: chat/no-tools -> satisfied",
          out and out["kind"] == "user_query_satisfied"
          and out["payload"].get("reason") == "chat_no_tools_expected", repr(out))


def t_inline_success():
    # An all-success tool_call set -> satisfied(all_succeeded).
    _wire_inline([{"tool": "open_app", "success": True,
                   "exit_code": 0, "result_preview": ""}])
    out = asyncio.run(r._inline_satisfaction_check("123", {"intent": "agent"}))
    check("inline: all-success -> satisfied(all_succeeded)",
          out and out["kind"] == "user_query_satisfied"
          and out["payload"].get("all_succeeded") is True, repr(out))


def t_inline_failed():
    # A failed tool_call -> unsatisfied(failed_tools) carrying the failure detail.
    _wire_inline([{"tool": "open_app", "success": False,
                   "exit_code": 2, "result_preview": "boom"}])
    out = asyncio.run(r._inline_satisfaction_check("123", {"intent": "agent"}))
    check("inline: failure -> unsatisfied(failed_tools)",
          out and out["kind"] == "user_query_unsatisfied"
          and out["payload"].get("failed_tools"), repr(out))


# ── reflect_on_step_failure (httpx + sibling readers stubbed) ──────
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
    # _recent_reflections is imported from mios_hitlflow (needs server-side DI we
    # don't run here); stub it to an empty buffer for the offline test.
    r._recent_reflections = _no_reflections


_NODE = {"tool": "broken_verb", "args": {"x": 1}}
_RESULT = {"stderr": "unknown verb", "exit_code": 2}
_PLAN = {"summary": "do a thing"}


def t_reflect_gate():
    # REFINE disabled -> None before any model call.
    r.configure(refine_enabled=False)
    out = asyncio.run(r.reflect_on_step_failure(_NODE, _RESULT, _PLAN))
    check("reflect: refine-disabled -> None", out is None, repr(out))


def t_reflect_corrected():
    _wire_reflect('{"tool": "open_app", "args": {"name": "x"}, "rationale": "swap verb"}')
    out = asyncio.run(r.reflect_on_step_failure(_NODE, _RESULT, _PLAN, session_id="123"))
    check("reflect: returns corrected step",
          out and out.get("tool") == "open_app", repr(out))


def t_reflect_unfixable():
    # Empty tool name = the model declined -> None (caller aborts the chain).
    _wire_reflect('{"tool": "", "args": {}, "rationale": "unfixable"}')
    out = asyncio.run(r.reflect_on_step_failure(_NODE, _RESULT, _PLAN, session_id="123"))
    check("reflect: unfixable -> None", out is None, repr(out))


# ── _recent_satisfaction_verdicts / _recent_tool_history (DB stubbed) ──────
def t_recent_verdicts():
    # The cross-turn verdict reader returns the rows from the LAST result
    # envelope, and degrades to [] when the DB read yields nothing.
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
    # Missing session_id gates before any DB touch.
    check("tool-history: no session -> []",
          asyncio.run(r._recent_tool_history(None)) == [])
    # DESC fetch is reversed so the prompt reads oldest-first.
    r.configure(db_read=_mk_db_read([{"tool": "a"}, {"tool": "b"}]))
    out = asyncio.run(r._recent_tool_history("123"))
    check("tool-history: reversed to chronological",
          out == [{"tool": "b"}, {"tool": "a"}], repr(out))


# ── _judge_answer_satisfied (httpx stubbed) ────────────────────────
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
    # An empty answer never calls the model -> False.
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
    # Non-200 degrades to True so a judge hiccup never loops a node forever.
    _wire_judge("whatever", status=503)
    check("judge: non-200 -> True (degrade-open)",
          asyncio.run(r._judge_answer_satisfied("q", "x")) is True)


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
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
