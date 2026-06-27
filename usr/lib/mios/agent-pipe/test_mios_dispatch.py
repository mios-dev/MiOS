# AI-hint: Offline stdlib-assert test for mios_dispatch (the verb->bash dispatch chokepoint). Verifies _build_dispatch_cmd shapes a representative verb's argv (both a hardcoded branch and an SSOT cmd-template verb), that the dispatch table covers a sample of planner-emittable verbs, and that a guarded verb STAYS GATED -- a HITL-blocked verb is refused (exit 126, hitl_blocked) WITHOUT ever reaching the broker (the bounded/broker leg is stubbed to raise if called), and a tainted high-privilege verb is firewall_block'd at the inner gate before the broker. No network / no DB / no broker socket.
# AI-related: ./mios_dispatch.py, ./server.py
# AI-functions: (assert script)
"""Stdlib assert-script gates for mios_dispatch -- run: python test_mios_dispatch.py"""
import asyncio
import contextvars
import time

import mios_dispatch


# Representative planner-emittable verbs with SSOT cmd templates + the hardcoded
# branches (pc_key etc.). The dispatch table must cover every one of these.
_CATALOG = {
    "web_search": {"cmd": "mios-web-search -n {limit=5} {query!}"},
    "open_url": {"cmd": "mios-open-url {url!}"},
    "knowledge_search": {"cmd": "mios-knowledge {query!}"},
    "launch_app": {"cmd": "mios-launch {name!}", "cmd_args": "mios-launch {name!}{args*}"},
}

_conv = contextvars.ContextVar("conv", default="conv-1")
_prop = contextvars.ContextVar("prop", default=None)
_rec = contextvars.ContextVar("rec", default=None)
_agent = contextvars.ContextVar("agent", default="")


def _base_configure():
    mios_dispatch.configure(
        verb_catalog=_CATALOG,
        high_privilege_verbs=frozenset({"open_url"}),
        launch_verbs=frozenset({"launch_app", "open_url"}),
        web_dispatch_jitter_s=0.0,
        dispatch_dedup=False,
        native_loop_date_in_query=False,
        launcher_sock="/nonexistent/launcher.sock",
        dispatch_inflight={},
        conv_key_var=_conv,
        recency_ctx_var=_rec,
        proposal_var=_prop,
        dispatch_agent_var=_agent,
        resolve_verb_key=lambda n: n,
        current_date_str=lambda: time.strftime("%Y-%m-%d"),
        emit_dispatch_dedup_event=lambda *a, **k: None,
        db_fire=lambda coro: None,
        db_post=lambda *a, **k: None,
        db_create=lambda *a, **k: {},
    )


# ── 1. _build_dispatch_cmd shapes argv -- hardcoded branch ──────────────────
_base_configure()
cmd = mios_dispatch._build_dispatch_cmd("pc_key", {"key": "Ctrl+S"})
assert cmd == "mios-pc-control key-combo Ctrl+S", repr(cmd)
cmd = mios_dispatch._build_dispatch_cmd("pc_key", {"key": "Enter"})  # single key
assert cmd == "mios-pc-control key Enter", repr(cmd)
cmd = mios_dispatch._build_dispatch_cmd("pc_click", {"x": 10, "y": 20, "button": "left"})
assert cmd == "mios-pc-control click 10 20 left", repr(cmd)

# ── 2. _build_dispatch_cmd shapes argv -- SSOT cmd-template verb ─────────────
cmd = mios_dispatch._build_dispatch_cmd("web_search", {"query": "hello world", "limit": 3})
assert cmd == "mios-web-search -n 3 'hello world'", repr(cmd)
# required {url!} empty -> template aborts -> None (verb known, args rejected)
assert mios_dispatch._build_dispatch_cmd("open_url", {"url": ""}) is None
cmd = mios_dispatch._build_dispatch_cmd("open_url", {"url": "https://x.test"})
assert cmd == "mios-open-url https://x.test", repr(cmd)

# ── 3. dispatch table covers the planner-emittable verb sample ──────────────
_planner_sample = ["web_search", "open_url", "knowledge_search", "pc_key", "pc_click"]
for v in _planner_sample:
    args = {"query": "q", "url": "https://x.test", "key": "a", "x": 1, "y": 2}
    out = mios_dispatch._build_dispatch_cmd(v, args)
    assert out, f"dispatch table missing planner verb {v!r}: {out!r}"
# unknown verb -> None
assert mios_dispatch._build_dispatch_cmd("totally_unknown_verb", {}) is None

# ── 3b. moved helpers: _arg_with_synonyms / _validate_enum_args / sandbox ────
# These four were extracted from server.py into mios_dispatch (their sole consumer).
# Run BEFORE the gate tests below, which monkeypatch _validate_enum_args. Synthetic
# (non-dictionary) verb/arg tokens so no baked English example words leak in.
_SYN_CATALOG = {
    "zqx_verb": {
        "params": {
            "mode_qq": {"enum": ["aa1", "bb2", "cc3"]},
            "free_kk": {},  # no enum -> never enum-validated
        },
    },
}
_SYN_MAP = {"zqx_verb": {"mode_qq": ["mq_alias"]}}
mios_dispatch.configure(
    verb_catalog=_SYN_CATALOG,
    verb_arg_synonyms=_SYN_MAP,
    sandbox_enforce=False,
    sandbox_self_confined=("xx-selfwrap",),
)

# _arg_with_synonyms: canonical first, then a declared synonym, else ''
assert mios_dispatch._arg_with_synonyms("zqx_verb", "mode_qq", {"mode_qq": "aa1"}) == "aa1"
assert mios_dispatch._arg_with_synonyms("zqx_verb", "mode_qq", {"mq_alias": "bb2"}) == "bb2"
assert mios_dispatch._arg_with_synonyms("zqx_verb", "mode_qq", {"nope": "x"}) == ""

# _validate_enum_args: in-enum -> None; out-of-enum -> error str; undeclared -> None
assert mios_dispatch._validate_enum_args("zqx_verb", {"mode_qq": "bb2"}) is None
_err = mios_dispatch._validate_enum_args("zqx_verb", {"mode_qq": "zzz9"})
assert _err and "not allowed" in _err, repr(_err)
assert mios_dispatch._validate_enum_args("zqx_verb", {"free_kk": "whatever"}) is None
assert mios_dispatch._validate_enum_args("unknown_verb_xx", {"a": "b"}) is None

# _dispatch_sandbox_profile -> a SandboxProfile; _sandbox_wrap_cmd enforce OFF = passthrough
_prof = mios_dispatch._dispatch_sandbox_profile("zqx_verb")
assert hasattr(_prof, "confined") and callable(getattr(_prof, "to_dict", None)), _prof
_c, _ws = mios_dispatch._sandbox_wrap_cmd("zqx_verb", "echo zz", _prof)
assert _c == "echo zz" and _ws is None, (_c, _ws)

# enforce ON + opted-in confined verb: a self-confined cmd is NOT double-wrapped,
# while a plain cmd IS wrapped through mios-sandbox-exec with a workspace.
_SELF_CATALOG = {"wrapme_vv": {"permission": "write", "sandbox_profile": "workspace"}}
mios_dispatch.configure(verb_catalog=_SELF_CATALOG, sandbox_enforce=True,
                        sandbox_self_confined=("xx-selfwrap",))
_prof_c = mios_dispatch._dispatch_sandbox_profile("wrapme_vv")
assert _prof_c.confined is True, _prof_c.to_dict()
_c3, _ws3 = mios_dispatch._sandbox_wrap_cmd("wrapme_vv", "xx-selfwrap echo hi", _prof_c)
assert _c3 == "xx-selfwrap echo hi" and _ws3 is None, (_c3, _ws3)
_c4, _ws4 = mios_dispatch._sandbox_wrap_cmd("wrapme_vv", "echo hi", _prof_c)
assert _c4 != "echo hi" and "mios-sandbox-exec" in _c4 and _ws4 is not None, (_c4, _ws4)

# ── 4. a GUARDED verb STAYS GATED -- HITL block refuses before the broker ───
_broker_called = {"n": 0}


async def _explode_bounded(*a, **k):
    _broker_called["n"] += 1
    raise AssertionError("broker/_dispatch_bounded reached on a gated verb!")


def test_hitl_gate():
    _base_configure()
    # imported-direct gates monkeypatched in the module namespace (no DB/network)
    mios_dispatch._dispatch_bounded = _explode_bounded
    mios_dispatch._hitl_block_reason = lambda tool, args: "human approval required"
    mios_dispatch._HITL_ARBITER_URL = ""
    mios_dispatch._pending_hash = lambda tool, args: "deadbeef"
    mios_dispatch._hitl_record_pending = lambda *a, **k: None
    res = asyncio.run(mios_dispatch.dispatch_mios_verb("open_url", {"url": "https://x.test"},
                                                       session_id="s1"))
    assert res.get("hitl_blocked") is True, res
    assert res.get("exit_code") == 126, res
    assert res.get("success") is False, res
    assert _broker_called["n"] == 0, "broker must NOT be reached on a HITL-gated verb"


test_hitl_gate()

# ── 5. second gate: tainted high-privilege verb -> firewall_block (no broker) ─
def test_firewall_gate():
    _base_configure()
    mios_dispatch._dispatch_pdp_reason = lambda tool: None
    mios_dispatch._dispatch_quota_reason = lambda tool: None
    mios_dispatch._validate_enum_args = lambda t, a: None

    async def _tainted(session_id):
        return True, "open_url->external"
    mios_dispatch._session_is_tainted = _tainted
    # open_url is in _HIGH_PRIVILEGE_VERBS (configured above) -> inner refuses it.
    res = asyncio.run(mios_dispatch._dispatch_mios_verb_inner(
        "open_url", {"url": "https://x.test"}, session_id="s1"))
    assert res.get("tainted") is True, res
    assert res.get("success") is False, res
    assert "firewall_block" in (res.get("stderr") or ""), res


test_firewall_gate()

print("test_mios_dispatch: ALL PASS")
