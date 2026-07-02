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


# ── 5b. NO SILENT BYPASS: the [ai] risk-tier HITL gate is ALSO enforced at the inner
#       universal chokepoint, so a DIRECT _dispatch_mios_verb_inner caller (the
#       computer-use loop bypasses the public dispatch_mios_verb entry) cannot run a
#       tier-gated verb un-blocked. Synthetic verb; PDP/quota/firewall stubbed to
#       pass and the [hitl] verb-scope gate stubbed to a no-op so ONLY the [ai] gate
#       is under test. The two former gates now share the mios_hitl.decide resolver. ─
async def _aret_none(*a, **k):
    return None


def test_hitl_inner_chokepoint_no_bypass():
    _base_configure()
    mios_dispatch._dispatch_pdp_reason = lambda tool: None
    mios_dispatch._dispatch_quota_reason = lambda tool: None
    mios_dispatch._validate_enum_args = lambda t, a: None
    mios_dispatch._HITL_ARBITER_URL = ""
    mios_dispatch._hitl_gate = _aret_none

    # HITL OFF: the [ai] gate returns None -> the inner does NOT HITL-block (the verb
    # fails later for a benign reason -- unknown synthetic verb -- never hitl_blocked).
    mios_dispatch._hitl_block_reason = lambda tool, args: None
    res_off = asyncio.run(mios_dispatch._dispatch_mios_verb_inner(
        "zzz_synth_verb", {"a": 1}, session_id="s1"))
    assert not res_off.get("hitl_blocked"), res_off

    # HITL ENABLED: the [ai] gate refuses -> the inner chokepoint BLOCKS before the
    # broker, even on this DIRECT-inner (computer-use style) bypass path.
    mios_dispatch._hitl_block_reason = lambda tool, args: "human approval required"
    res_on = asyncio.run(mios_dispatch._dispatch_mios_verb_inner(
        "zzz_synth_verb", {"a": 1}, session_id="s1"))
    assert res_on.get("hitl_blocked") is True, res_on
    assert res_on.get("exit_code") == 126 and res_on.get("success") is False, res_on
    print("[PASS] inner chokepoint enforces the [ai] HITL gate (no silent bypass)")


test_hitl_inner_chokepoint_no_bypass()


# ── 6. A9/F2: a tainted verb via /v1/dispatch persists a tool_call row that the
#       Semantic Firewall then sees as a session taint (closes the dispatch-path
#       taint-blind hole). No broker/network/DB -- the dispatch verb + the DB
#       writers + the firewall reader are all stubbed. ─────────────────────────
def test_dispatch_persists_taint_row():
    _base_configure()
    captured = {}

    def _cap_create(table, row=None, **kw):
        captured["table"] = table
        captured["row"] = row
        return "INSERT_SQL;"          # representative SQL the splice appends to

    def _cap_post(sql):
        captured["posted"] = sql
        return ("POSTED", sql)

    def _cap_fire(x):
        captured["fired"] = x

    mios_dispatch.configure(db_create=_cap_create, db_post=_cap_post, db_fire=_cap_fire)

    # The verb EXECUTED and its own result is tainted (e.g. external open_url) --
    # this is exactly the dict the dispatch chokepoint returns after the broker.
    async def _fake_dispatch(tool, args, *, session_id=None):
        return {"success": True, "tool": "open_url",
                "args": {"url": "https://x.test"},
                "output": "fetched external page", "latency_ms": 7,
                "tainted": True, "taint_reason": "external_open_url:https://x.test"}

    orig_dispatch = mios_dispatch.dispatch_mios_verb
    try:
        mios_dispatch.dispatch_mios_verb = _fake_dispatch

        body = {"tool": "open_url", "args": {"url": "https://x.test"}, "session_id": "s9"}
        asyncio.run(mios_dispatch.dispatch_verb(body))

        # A tool_call row was written for the dispatch-executed verb, carrying its taint.
        assert captured.get("table") == "tool_call", captured
        row = captured.get("row") or {}
        assert row.get("tainted") is True, row
        assert row.get("taint_reason") == "external_open_url:https://x.test", row
        assert row.get("tool") == "open_url", row
        assert captured.get("fired") is not None, "row write must fire"
        # session-scoped so _session_is_tainted (keyed on session) can find it.
        assert "session = s9" in str(captured.get("posted") or ""), captured

        # Closing the loop: feed that recorded row back through the firewall's taint-chain
        # reader -> the session is now seen as tainted (was invisible before A9).
        import mios_firewall

        async def _fake_read(sql, pg_sql=None, pg_params=None):
            if row.get("tainted"):
                return [{"result": [{"ts": "t", "tool": row["tool"],
                                     "taint_reason": row["taint_reason"]}]}]
            return [{"result": []}]

        mios_firewall._db_read = _fake_read
        tainted, chain = asyncio.run(mios_firewall._session_is_tainted("s9"))
        assert tainted is True and "open_url" in chain, (tainted, chain)

        # Degrade-open: a write failure (writer raises) must NOT break dispatch.
        def _boom_post(sql):
            raise RuntimeError("db down")
        mios_dispatch.configure(db_post=_boom_post)
        out = asyncio.run(mios_dispatch.dispatch_verb(body))
        assert out is not None, "dispatch must still return when the audit write fails"
        print("[PASS] /v1/dispatch persists a tainting tool_call row (A9/F2)")
    finally:
        mios_dispatch.dispatch_mios_verb = orig_dispatch


test_dispatch_persists_taint_row()


# ── 7. A6: write/exec verbs OPT IN to a real sandbox profile; read verbs don't ──
# The dead-bwrap gap was that ZERO verbs declared sandbox_profile, so flipping
# [dispatch].sandbox_enforce confined nothing. This gate drives off each verb's SSOT
# `permission`/`sandbox_profile` metadata (NOT a runtime verb-name list): it proves
# the opt-in set is now non-empty, every tagged profile is a REAL confining profile
# on a non-read verb, and read-only verbs sensibly carry none.
def test_sandbox_profile_coverage():
    import os
    import mios_sandbox
    try:
        import tomllib
    except ImportError:  # py<3.11
        import tomli as tomllib
    _here = os.path.dirname(os.path.abspath(__file__))
    _cands = [os.environ.get("MIOS_TOML"),
              os.path.join(_here, "..", "..", "..", "share", "mios", "mios.toml"),
              "/usr/share/mios/mios.toml"]
    _path = next((p for p in _cands if p and os.path.exists(p)), None)
    assert _path, f"mios.toml not found (tried {_cands})"
    with open(_path, "rb") as _f:
        verbs = (tomllib.load(_f).get("verbs") or {})
    assert verbs, "no [verbs.*] catalog in mios.toml"

    tagged = {}
    for name, v in verbs.items():
        if not isinstance(v, dict):
            continue
        prof = v.get("sandbox_profile")
        perm = str(v.get("permission", "read")).lower()
        if prof is None:
            continue
        tagged[name] = (prof, perm)
        # (a) names a REAL profile that resolves to CONFINED (catches a typo'd name).
        assert mios_sandbox.resolve_profile(perm, explicit=prof).confined, \
            f"{name}: sandbox_profile={prof!r} did not resolve to a confined profile"
        # (b) only a side-effecting (non-read) verb opts into confinement; a read-only
        #     verb declaring one would be a classification error.
        assert perm != "read", \
            f"{name}: read-only verb must not declare sandbox_profile"

    # (c) the opt-in set is NON-EMPTY (the gap was 0 of N) AND covers the canonical
    #     arbitrary-code-execution + file-mutation verbs -- exactly what a dead
    #     sandbox most needs to confine. Derived from catalog presence (a verb absent
    #     in this build is skipped), so this is coverage, not a re-declared name map.
    assert tagged, "A6 regression: ZERO verbs declare sandbox_profile (dead bwrap)"
    _must_confine = [n for n in ("run_code", "coderun", "code_mode",
                                 "text_create", "text_str_replace", "text_insert",
                                 "file_edit", "powershell_run") if n in verbs]
    _missing = [n for n in _must_confine if n not in tagged]
    assert not _missing, f"A6: code/file-mutation verbs missing sandbox_profile: {_missing}"
    print(f"[PASS] A6 sandbox_profile coverage: {len(tagged)} verbs opt in, "
          "all resolve confined + non-read")


test_sandbox_profile_coverage()


def test_agent_access_control():
    # Configure mios_dispatch with a mock catalog and agent registry
    _test_catalog = {
        "container_restart": {"cmd": "echo restarting", "tier": "destructive"},
        "safe_verb": {"cmd": "echo safe", "tier": "routine"},
    }
    _test_agents = {
        "routine_agent": {"privilege_group": "routine"},
        "privileged_agent": {"privilege_group": "privileged"},
    }
    
    # Save original mocks
    orig_hitl_block_reason = mios_dispatch._hitl_block_reason
    orig_pdp = mios_dispatch._dispatch_pdp_reason
    orig_quota = mios_dispatch._dispatch_quota_reason
    orig_enum = mios_dispatch._validate_enum_args
    orig_gate = mios_dispatch._hitl_gate
    orig_arbiter = mios_dispatch._HITL_ARBITER_URL
    orig_bounded = mios_dispatch._dispatch_bounded

    mios_dispatch._hitl_block_reason = lambda tool, args: None
    mios_dispatch._dispatch_pdp_reason = lambda tool: None
    mios_dispatch._dispatch_quota_reason = lambda tool: None
    mios_dispatch._validate_enum_args = lambda t, a: None
    async def _mock_void(*a, **k): return None
    mios_dispatch._hitl_gate = _mock_void
    mios_dispatch._HITL_ARBITER_URL = ""
    async def _mock_bounded(tool, args, *, session_id=None):
        return {"success": True, "output": f"ok-{tool}"}
    mios_dispatch._dispatch_bounded = _mock_bounded

    # Configure variables
    mios_dispatch.configure(
        verb_catalog=_test_catalog,
        agent_registry=_test_agents,
        db_fire=lambda *a, **k: None,
        db_post=lambda *a, **k: None,
        db_create=lambda *a, **k: {},
    )
    
    try:
        # Run calling as routine_agent
        ctx1 = contextvars.copy_context()
        def _run_routine():
            _agent.set("routine_agent")
            # should fail/route to HITL
            res = asyncio.run(mios_dispatch.dispatch_mios_verb("container_restart", {}))
            assert res.get("hitl_blocked") is True, f"routine_agent calling destructive verb should be HITL blocked: {res}"
            
            # calling safe verb should succeed
            res2 = asyncio.run(mios_dispatch.dispatch_mios_verb("safe_verb", {}))
            assert res2.get("hitl_blocked") is not True, f"routine_agent calling safe verb should NOT be blocked: {res2}"
            assert res2.get("output") == "ok-safe_verb", res2
            
        ctx1.run(_run_routine)
        
        # Run calling as privileged_agent
        ctx2 = contextvars.copy_context()
        def _run_privileged():
            _agent.set("privileged_agent")
            # should proceed (fail on socket since launcher is /nonexistent, but NOT HITL blocked)
            res = asyncio.run(mios_dispatch.dispatch_mios_verb("container_restart", {}))
            assert res.get("hitl_blocked") is not True, f"privileged_agent calling destructive verb should not be HITL blocked: {res}"
            assert res.get("output") == "ok-container_restart", res
            
        ctx2.run(_run_privileged)
    finally:
        # Restore original mocks
        mios_dispatch._hitl_block_reason = orig_hitl_block_reason
        mios_dispatch._dispatch_pdp_reason = orig_pdp
        mios_dispatch._dispatch_quota_reason = orig_quota
        mios_dispatch._validate_enum_args = orig_enum
        mios_dispatch._hitl_gate = orig_gate
        mios_dispatch._HITL_ARBITER_URL = orig_arbiter
        mios_dispatch._dispatch_bounded = orig_bounded
        _base_configure()
        
    print("[PASS] agent access control: routine blocked on destructive, privileged allowed")


test_agent_access_control()

print("test_mios_dispatch: ALL PASS")
