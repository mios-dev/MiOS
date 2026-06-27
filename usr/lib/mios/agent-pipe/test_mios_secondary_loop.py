#!/usr/bin/env python3
# AI-hint: Stdlib assert-script for mios_secondary_loop (the /v1 sub-agent tool-loop + its
# anti-disclaimer / closed-loop guards). Stubs the injected server deps + the
# mios_toolexec._exec_tool_calls executor + a fake httpx-shaped client so NO network/import
# of server is needed. Proves the LOAD-BEARING behaviours: (1) a no-tool-call DISCLAIMER
# response triggers the _TOOL_NUDGE re-loop; (2) a no-tool-call response AFTER a FAILED tool
# batch triggers the _REPLAN_NUDGE closed-loop re-engage (with _daemon_diagnose folded in);
# (3) a clean final answer (no tool calls, no disclaimer, no prior failure) terminates the
# loop in one pass.
# AI-related: ./mios_secondary_loop.py, ./mios_toolexec.py
# AI-functions: (test script)
"""Offline unit test for mios_secondary_loop. Run: python test_mios_secondary_loop.py"""

import asyncio
import json

import mios_toolexec
import mios_secondary_loop as M


# ---- stubs for the injected server-side deps -------------------------------
# NOTE: _looks_like_disclaimer / _tool_call_sig / _tmsgs_indicate_failure are no
# longer injected -- they now live in mios_secondary_loop itself (moved home), so
# the loops use the module's own definitions. Direct unit tests for those moved
# functions are at the bottom of this file.


def _apply_outbound_auth(hdrs, ep):
    # no-op stub: real impl sets an outbound bearer; the loop only needs it callable
    return None


def _endpoint_supports_parallel_tools(ep):
    return False


# ---- a fake httpx-shaped client driven by a scripted response queue --------
class _Resp:
    def __init__(self, payload):
        self.status_code = 200
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


class _FakeClient:
    """Returns one scripted assistant message per POST, in order."""
    def __init__(self, scripted_messages):
        self._q = list(scripted_messages)
        self.calls = 0

    async def post(self, url, content=None, headers=None, timeout=None):
        self.calls += 1
        msg = self._q.pop(0) if self._q else {"content": "done."}
        return _Resp({"choices": [{"message": msg}]})


def _msg(content="", tool_calls=None):
    m = {"content": content}
    if tool_calls is not None:
        m["tool_calls"] = tool_calls
    return m


# ---- configure the module with the stubs -----------------------------------
def _wire(*, exec_result):
    """Inject stubs. exec_result is the (tmsgs, ran_read) the executor returns."""
    async def _fake_exec(tcs, push, allow_write=False):
        return exec_result
    mios_toolexec._exec_tool_calls = _fake_exec  # noqa: SLF001
    M._exec_tool_calls = _fake_exec             # the loop binds the name at import
    # rescue must NOT promote our plain-text disclaimers into tool calls
    M._rescue_tool_calls = lambda content, tools=None: []
    M.configure(
        secondary_tool_max_iters=4,
        secondary_replan_max=1,
        daemon_diagnose_model="stub",
        daemon_diagnose_endpoint="http://stub/v1",
        daemon_diagnose_enable=False,   # degrade-open -> generic nudge, no extra net call
        apply_outbound_auth=_apply_outbound_auth,
        endpoint_supports_parallel_tools=_endpoint_supports_parallel_tools,
    )


def _run(scripted, exec_result=([], False)):
    _wire(exec_result=exec_result)
    nudges = []
    client = _FakeClient(scripted)
    tools = [{"function": {"name": "web_search"}}]
    msgs = [{"role": "user", "content": "what's the latest news?"}]
    out = asyncio.run(M._v1_secondary_tool_loop(
        client, "http://ep/v1", "m", {}, msgs, tools, None,
        nudges.append))
    return out, nudges, client


# === TEST 1: disclaimer with NO tool call -> _TOOL_NUDGE injected, re-loops ===
out, nudges, client = _run([
    _msg(content="I cannot do that, use my tools."),   # disclaim -> nudge
    _msg(content="The latest news is X."),              # clean final after nudge
])
assert any(m.get("role") == "user" and m.get("content") == M._TOOL_NUDGE
           for m in out), "TOOL_NUDGE not injected on a no-tool-call disclaimer"
assert client.calls == 2, f"expected re-loop after nudge, got {client.calls} calls"
print("TEST 1 PASS: disclaimer triggers _TOOL_NUDGE re-loop")

# === TEST 2: a FAILED tool batch then a give-up -> _REPLAN_NUDGE closed loop ===
# turn 1: model calls a tool -> executor returns a FAILURE -> _last_failed=True
# turn 2: model gives up (no tool calls, not a disclaimer) -> REPLAN nudge fires
fail_tmsgs = [{"role": "tool", "content": json.dumps({"success": False})}]
_wire(exec_result=(fail_tmsgs, True))
M._rescue_tool_calls = lambda content, tools=None: []
nudges = []
client = _FakeClient([
    _msg(tool_calls=[{"id": "1", "function": {"name": "web_search",
                                              "arguments": "{}"}}]),
    _msg(content="I'll stop here."),   # give-up, not a disclaimer
    _msg(content="Re-attempted; here is the answer."),
])
out = asyncio.run(M._v1_secondary_tool_loop(
    client, "http://ep/v1", "m", {}, [{"role": "user", "content": "go"}],
    [{"function": {"name": "web_search"}}], None, nudges.append))
assert any(m.get("role") == "user"
           and str(m.get("content") or "").startswith(M._REPLAN_NUDGE)
           for m in out), "REPLAN_NUDGE not injected after a failed tool batch + give-up"
print("TEST 2 PASS: failed tool batch + give-up triggers _REPLAN_NUDGE closed loop")

# === TEST 3: clean final answer, no tools/disclaimer/failure -> ONE pass ====
out, nudges, client = _run([
    _msg(content="Here is a plain final answer."),
])
assert client.calls == 1, f"clean answer should be one pass, got {client.calls}"
assert not any(m.get("content") in (M._TOOL_NUDGE,) for m in out), \
    "no nudge should be injected on a clean answer"
assert not any(str(m.get("content") or "").startswith(M._REPLAN_NUDGE)
               for m in out), "no replan on a clean answer"
print("TEST 3 PASS: clean final answer terminates in one pass")

# === TEST 4: _daemon_diagnose degrade-open returns '' when disabled =========
M.configure(daemon_diagnose_enable=False)
diag = asyncio.run(M._daemon_diagnose(_FakeClient([]), "it failed", "the goal"))
assert diag == "", f"disabled daemon-diagnose must return '', got {diag!r}"
print("TEST 4 PASS: _daemon_diagnose degrade-open when disabled")

# === TEST 5: _ollama_secondary_tool_loop (moved home) -> disclaimer re-loop ===
# Symmetric sibling of _v1_secondary_tool_loop for a RAW ollama node: a no-tool
# disclaimer must inject the module's own _TOOL_NUDGE and re-call once.
_wire(exec_result=([], False))
M._rescue_tool_calls = lambda content, tools=None: []   # don't promote plain text
nudges = []
client = _FakeClient([
    _msg(content="I cannot do that, use my search tools."),  # disclaim -> nudge
    _msg(content="The latest news is X."),                   # clean final
])
out = asyncio.run(M._ollama_secondary_tool_loop(
    client, "http://node", "m",
    [{"role": "user", "content": "what's the latest news?"}],
    [{"function": {"name": "web_search"}}], None, nudges.append))
assert any(m.get("role") == "user" and m.get("content") == M._TOOL_NUDGE
           for m in out), "ollama loop: _TOOL_NUDGE not injected on a disclaimer"
assert client.calls == 2, f"ollama loop: expected re-loop, got {client.calls} calls"
print("TEST 5 PASS: _ollama_secondary_tool_loop nudges + re-loops on a disclaimer")

# === TEST 6: the moved loop-guard helpers, tested directly ===================
# _tool_call_sig: stable + order-independent over the args dict.
sig_a = M._tool_call_sig({"function": {"name": "web_search",
                                       "arguments": {"q": "x", "n": 3}}})
sig_b = M._tool_call_sig({"function": {"name": "web_search",
                                       "arguments": {"n": 3, "q": "x"}}})
sig_c = M._tool_call_sig({"function": {"name": "web_search",
                                       "arguments": '{"q": "x", "n": 3}'}})  # JSON str
assert sig_a == sig_b == sig_c, "tool_call_sig must be stable + arg-order independent"
assert M._tool_call_sig({"function": {"name": "open_url"}}) != sig_a, \
    "different verbs must produce different signatures"
# _looks_like_disclaimer: marker hit vs clean miss.
assert M._looks_like_disclaimer("I cannot find that, no data available.")
assert not M._looks_like_disclaimer("Here is the concrete answer you asked for.")
assert not M._looks_like_disclaimer("")
# _tmsgs_indicate_failure: broker success=False (JSON) + a text marker, not empty.
assert M._tmsgs_indicate_failure(
    [{"role": "tool", "content": json.dumps({"success": False})}])
assert M._tmsgs_indicate_failure(
    [{"role": "tool", "content": "dispatch error: text_not_delivered"}])
assert not M._tmsgs_indicate_failure(
    [{"role": "tool", "content": json.dumps({"success": True, "data": []})}])
assert not M._tmsgs_indicate_failure([{"role": "tool", "content": ""}])
print("TEST 6 PASS: _tool_call_sig / _looks_like_disclaimer / _tmsgs_indicate_failure")

print("ALL TESTS PASSED")
