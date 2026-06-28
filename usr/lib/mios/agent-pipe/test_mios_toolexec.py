#!/usr/bin/env python3
# AI-hint: Stdlib assert-script for mios_toolexec. Stubs every injected dep (no
# network/no broker) then exercises the LOAD-BEARING narrated-tool-call RESCUE
# corpus (_rescue_tool_calls over Qwen <function=> XML, ```json fences,
# <tool_call>{json}</tool_call> markup, an OpenAI {"function":...} blob, and an
# opencode-style narrated/fenced "lie"), the _norm_tool_call arg-canonicalisation,
# the _verb_result_cap/_cap_verb_result ACI capping, _format_tool_error shaping,
# and the _exec_tool_calls permission gate (read auto-runs, write skipped when
# allow_write=False). Run: python test_mios_toolexec.py
# AI-related: ./mios_toolexec.py
# AI-functions: (test)
"""Offline regression for mios_toolexec -- rescue corpus + executor shaping."""

import asyncio
import contextvars
import json

import mios_toolexec as T


# ── Inject stubs (no network, no broker) ───────────────────────────
_VERB_CATALOG = {
    "web_search": {"permission": "read"},
    "web_extract": {"permission": "read", "max_result_chars": 4000},
    "delete_file": {"permission": "write"},
    "os_recipe": {"permission": "read"},
}
_DISPATCHED = []


async def _fake_dispatch(verb, args):
    _DISPATCHED.append((verb, args))
    return {"ok": True, "output": json.dumps({"results": [
        {"title": "T", "url": "http://x"}]})}


_octx = contextvars.ContextVar("orch", default={})

T.configure(
    read_tool_enrich_chars=1500,
    read_tool_enrich_timeout=5.0,
    aci_max_lines=160,
    aci_head_frac=0.6,
    code_mode_enable=False,
    code_mode_heavy_only=False,
    max_dispatch_depth=2,
    verb_catalog=_VERB_CATALOG,
    recipe_catalog={},
    high_privilege_verbs=set(),
    web_enrich_verbs={"web_search", "web_extract", "crawl"},
    orch_ctx_var=_octx,
    dispatch_mios_verb=_fake_dispatch,
    mcp_call_tool=None,
    record_mcp_tool_call=lambda *a, **k: None,
    plan_swarm=None,
    live_agent_names=None,
    agent_dag_from_tasks=None,
    respond_agent_dag=None,
    depth_exhausted=lambda: False,
    dispatch_depth=lambda: 0,
    enter_dispatch_hop=lambda: 1,
    resolve_verb_key=lambda n: n,
    session_is_tainted=None,
    db_fire=lambda coro: None,
    db_post=lambda *a, **k: None,
    db_create=lambda *a, **k: None,
    src_record=lambda items: None,
)

PASS = 0


def ok(cond, label):
    global PASS
    assert cond, "FAIL: " + label
    PASS += 1
    print("  ok:", label)


# ── _norm_tool_call: arg canonicalisation ──────────────────────────
print("[_norm_tool_call]")
n = T._norm_tool_call("web_search", {"query": "hi"}, 0)
ok(n["type"] == "function" and n["function"]["name"] == "web_search",
   "norm shapes an OpenAI tool_call")
ok(json.loads(n["function"]["arguments"]) == {"query": "hi"},
   "norm canonicalises dict args to a JSON string")
n2 = T._norm_tool_call("web_search", '{"query": "s"}', 1)
ok(json.loads(n2["function"]["arguments"]) == {"query": "s"},
   "norm parses a JSON-STRING arg")
n3 = T._norm_tool_call("web_search", "not json at all", 2)
ok(json.loads(n3["function"]["arguments"]) == {},
   "norm degrades malformed args to {}")


# ── _rescue_tool_calls: the narrated-tool-call salvage corpus ──────
print("[_rescue_tool_calls]")
TOOLS = [{"type": "function", "function": {"name": "web_search"}},
         {"type": "function", "function": {"name": "web_extract"}}]


def _one(rescued):
    assert len(rescued) == 1, "expected exactly one rescued call, got %r" % rescued
    fn = rescued[0]["function"]
    return fn["name"], json.loads(fn["arguments"])

# (a) Qwen <function=NAME><parameter=K>V</parameter></function> XML
xml = ("Sure, let me look that up.\n"
       "<function=web_search>\n<parameter=query>mios refactor</parameter>\n</function>")
name, args = _one(T._rescue_tool_calls(xml, TOOLS))
ok(name == "web_search" and args == {"query": "mios refactor"},
   "rescues Qwen <function=> XML markup")

# (b) ```json fenced {"name","arguments"}
fenced = ("Here you go:\n```json\n"
          '{"name": "web_search", "arguments": {"query": "fenced"}}\n```')
name, args = _one(T._rescue_tool_calls(fenced, TOOLS))
ok(name == "web_search" and args == {"query": "fenced"},
   "rescues a ```json fenced {name,arguments} block")

# (c) <tool_call>{json}</tool_call> Qwen/Hermes content markup
tc = ('thinking...<tool_call>{"name": "web_extract", "arguments": '
      '{"url": "http://e"}}</tool_call>')
name, args = _one(T._rescue_tool_calls(tc, TOOLS))
ok(name == "web_extract" and args == {"url": "http://e"},
   "rescues <tool_call>{json}</tool_call> markup")

# (d) OpenAI {"function":{"name","arguments"}} bare whole-content object
openai_blob = '{"function": {"name": "web_search", "arguments": "{\\"query\\": \\"blob\\"}"}}'
name, args = _one(T._rescue_tool_calls(openai_blob, TOOLS))
ok(name == "web_search" and args == {"query": "blob"},
   "rescues a bare OpenAI {function:{name,arguments}} object")

# (e) opencode-style narrated lie: prose + a fenced {"tool","args"} blob
opencode = ("I'll call the web_search tool to find that.\n\n"
            "```json\n{\"tool\": \"web_search\", \"args\": {\"query\": \"opencode\"}}\n```")
name, args = _one(T._rescue_tool_calls(opencode, TOOLS))
ok(name == "web_search" and args == {"query": "opencode"},
   "rescues the opencode narrated/fenced {tool,args} lie")

# (f) GUARD: an unknown / un-offered tool name is NOT promoted
guard = '```json\n{"name": "rm_rf_everything", "arguments": {}}\n```'
ok(T._rescue_tool_calls(guard, TOOLS) == [],
   "guard: an un-offered tool name is never promoted")

# (g) plain prose with no call -> nothing
ok(T._rescue_tool_calls("just a normal answer, nothing to call here.", TOOLS) == [],
   "plain prose yields no rescued calls")


# ── _verb_result_cap / _cap_verb_result ────────────────────────────
print("[_cap_verb_result]")
ok(T._verb_result_cap("web_search") == 1500,
   "verb_result_cap falls back to READ_TOOL_ENRICH_CHARS")
ok(T._verb_result_cap("web_extract") == 4000,
   "verb_result_cap honours a verb's max_result_chars")
short = "small result"
ok(T._cap_verb_result("web_search", short) == short,
   "cap_verb_result returns a within-budget string unchanged")
big = "x" * 5000
capped = T._cap_verb_result("web_search", big)
ok(isinstance(capped, str) and len(capped) < len(big),
   "cap_verb_result truncates an over-budget string")


# ── _format_tool_error ─────────────────────────────────────────────
print("[_format_tool_error]")
ok(T._format_tool_error({"results": []}) is None,
   "no error on a normal result dict")
e = T._format_tool_error({"success": False, "error": "boom"})
ok(e and e["error"]["message"] == "boom" and e["error"]["code"] == "tool_execution_failed",
   "shapes success=False into an error envelope")
e2 = T._format_tool_error({"ok": False, "stderr": "bad"})
ok(e2 and e2["error"]["message"] == "bad",
   "shapes ok=False (stderr fallback) into an error envelope")
ok(T._format_tool_error("not a dict") is None,
   "non-dict result is not an error")


# ── _exec_tool_calls: permission gate ──────────────────────────────
print("[_exec_tool_calls]")
_pushed = []


def _push(s):
    _pushed.append(s)


async def _run():
    # read verb auto-executes even when allow_write=False
    tcs_read = [{"id": "c1", "function": {
        "name": "web_search", "arguments": '{"query": "x"}'}}]
    msgs, ran = await T._exec_tool_calls(tcs_read, _push, allow_write=False)
    ok(ran is True and len(msgs) == 1 and msgs[0]["role"] == "tool",
       "read verb auto-executes (allow_write=False)")
    ok(msgs[0].get("tool_call_id") == "c1" and msgs[0].get("name") == "web_search",
       "tool message carries id + name linkage")
    ok(("web_search", {"query": "x"}) in _DISPATCHED,
       "read verb dispatched with canonicalised args")
    # write verb skipped when allow_write=False
    tcs_write = [{"id": "c2", "function": {"name": "delete_file", "arguments": "{}"}}]
    msgs2, ran2 = await T._exec_tool_calls(tcs_write, _push, allow_write=False)
    ok(ran2 is False and "skipped" in msgs2[0]["content"],
       "write verb skipped when writes disabled")

    # ── A2: a HYPHENATED read recipe (mios_recipe__disk_usage) must resolve via the
    # underscore->hyphen normalization and RUN on a read-only turn (it was wrongly
    # dropped because _RECIPE_CATALOG is keyed hyphenated but the lookup used the
    # underscored, name-mangled tool name) ──
    T.configure(recipe_catalog={
        "disk-usage": {"permission": "read"},
        "shutdown": {"permission": "write"}})
    _DISPATCHED.clear()
    tcs_recipe = [{"id": "r1", "function": {
        "name": "mios_recipe__disk_usage", "arguments": "{}"}}]
    msgs3, ran3 = await T._exec_tool_calls(tcs_recipe, _push, allow_write=False)
    ok(ran3 is True and "skipped" not in msgs3[0]["content"],
       "A2: hyphenated read recipe runs on a read-only turn (not dropped)")
    ok(("os_recipe", {"name": "disk-usage", "params": {}}) in _DISPATCHED,
       "A2: read recipe dispatched via os_recipe with the canonical hyphenated name")
    # a WRITE recipe stays gated on a read-only turn
    tcs_wrecipe = [{"id": "r2", "function": {
        "name": "mios_recipe__shutdown", "arguments": "{}"}}]
    msgs4, ran4 = await T._exec_tool_calls(tcs_wrecipe, _push, allow_write=False)
    ok(ran4 is False and "skipped" in msgs4[0]["content"],
       "A2: write recipe still skipped when writes disabled")

asyncio.run(_run())

print("\nALL %d ASSERTIONS PASSED" % PASS)
