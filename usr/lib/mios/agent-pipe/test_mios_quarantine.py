# AI-hint: Offline stdlib-assert test for the F2 CaMeL dual-context QUARANTINE gate (the deeper half of T-033, mios_quarantine). Two layers: (1) the PURE evaluator -- evaluate() composes A (passed taint bool) with the SSOT-derived B (sensitive flag) + C (permission tier -> mios_ruleof2.is_state_change) and BITES on tainted AND (sensitive OR state-change) -- the STRICTER superset of Rule-of-Two's all-three; normalize_mode delegates to the shared T-033 enum, the action matrix is bite->gate/audit/proceed by mode and <no-bite>->always proceed, the seam stub quarantined_extract degrades to None. (2) the CHOKEPOINT WIRING through mios_dispatch with SYNTHETIC non-dictionary verbs -- enforce+tainted+sensitive(read) is GATED (quarantine_blocked, broker never reached), enforce+tainted+write GATED, enforce+tainted+read-only-non-sensitive PROCEEDS, enforce+UNtainted+privileged PROCEEDS (quarantine only bites on untrusted-present), audit logs a quarantine_audit event WITHOUT blocking, off mode is BYTE-IDENTICAL (the evaluator is never consulted), an explicit approval downgrades the enforce block, a taint-read error DEGRADES OPEN. SOUNDNESS: the SAME tainted+privileged dispatch is gated via BOTH the public dispatch_mios_verb (chat) entry AND the direct _dispatch_mios_verb_inner chokepoint -- the broker cmd-builder is never reached through either path (no bypass). No network / no DB / no broker.
# AI-related: ./mios_quarantine.py, ./mios_ruleof2.py, ./mios_hitl.py, ./mios_dispatch.py, ./mios_sandbox.py, ./mios_firewall.py
# AI-functions: (assert script)
"""Stdlib assert-script gates for mios_quarantine + its dispatch wiring -- run: python test_mios_quarantine.py"""
import asyncio
import contextlib
import contextvars
import sys
import time

import mios_quarantine as Q
import mios_hitl
import mios_dispatch

_RESULTS: list = []


def _check(name: str, ok: bool, detail: str = "") -> None:
    _RESULTS.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


# ─────────────────────────────────────────────────────────────────────────────
# 1. PURE EVALUATOR -- the CaMeL bite: tainted AND (sensitive OR state-change)
# ─────────────────────────────────────────────────────────────────────────────
def _bites(t, perm, sens):
    return Q.evaluate(session_tainted=t, permission_tier=perm, sensitive=sens,
                      mode=Q.MODE_ENFORCE).bites


def t_normalize_mode() -> None:
    # Delegates to the SHARED T-033 normaliser -> the two architectural-gate modes
    # can never drift in their parsing.
    _check("mode: off", Q.normalize_mode("off") == Q.MODE_OFF)
    _check("mode: audit", Q.normalize_mode("audit") == Q.MODE_AUDIT)
    _check("mode: enforce", Q.normalize_mode("enforce") == Q.MODE_ENFORCE)
    _check("mode: case-insensitive", Q.normalize_mode("ENFORCE") == Q.MODE_ENFORCE)
    _check("mode: unknown -> off (degrade-open)", Q.normalize_mode("bogus") == Q.MODE_OFF)
    _check("mode: None -> off", Q.normalize_mode(None) == Q.MODE_OFF)


def t_evaluate_bite_matrix() -> None:
    # The boundary BITES when untrusted content is present AND the verb is privileged
    # (sensitive-read OR state-change). This is STRICTER than Rule-of-Two (all three):
    # a sensitive READ (no state-change) in a tainted session already bites.
    _check("bite: tainted + sensitive-READ -> bites (stricter than ro2)", _bites(True, "read", True) is True)
    _check("bite: tainted + plain WRITE -> bites", _bites(True, "write", False) is True)
    _check("bite: tainted + sensitive WRITE -> bites", _bites(True, "write", True) is True)
    _check("bite: tainted + interactive -> bites", _bites(True, "interactive", False) is True)
    # NO bite: the verb is neither sensitive nor state-changing (a pure-info read).
    _check("bite: tainted + read-only non-sensitive -> NO bite", _bites(True, "read", False) is False)
    # NO bite: untainted session -- quarantine only constrains untrusted-present dataflow.
    _check("bite: UNtainted + sensitive write -> NO bite", _bites(False, "write", True) is False)
    _check("bite: UNtainted + sensitive read -> NO bite", _bites(False, "read", True) is False)
    _check("bite: UNtainted + plain write -> NO bite", _bites(False, "write", False) is False)


def t_evaluate_privileged() -> None:
    # "privileged" is the UNION B OR C (either reads sensitive data or changes state).
    def _priv(perm, sens):
        return Q.evaluate(session_tainted=False, permission_tier=perm, sensitive=sens).privileged
    _check("priv: sensitive read -> privileged (B)", _priv("read", True) is True)
    _check("priv: plain write -> privileged (C)", _priv("write", False) is True)
    _check("priv: sensitive write -> privileged (B and C)", _priv("write", True) is True)
    _check("priv: read-only non-sensitive -> NOT privileged", _priv("read", False) is False)


def t_evaluate_action_matrix() -> None:
    def _act(mode, *, t=True, perm="write", sens=True):
        return Q.evaluate(session_tainted=t, permission_tier=perm, sensitive=sens, mode=mode).action
    # On a BITE the action is the SSOT mode's posture.
    _check("action: bite + off -> proceed (not consulted-equivalent)", _act("off") == Q.ACT_PROCEED)
    _check("action: bite + audit -> audit", _act("audit") == Q.ACT_AUDIT)
    _check("action: bite + enforce -> gate", _act("enforce") == Q.ACT_GATE)
    _check("action: bite + unknown mode -> proceed (off-like)", _act("weird") == Q.ACT_PROCEED)
    # NO bite -> ALWAYS proceed, regardless of mode.
    for m in ("off", "audit", "enforce"):
        _check(f"action: read-only non-sensitive + {m} -> proceed",
               _act(m, perm="read", sens=False) == Q.ACT_PROCEED)
        _check(f"action: untainted privileged + {m} -> proceed",
               _act(m, t=False) == Q.ACT_PROCEED)


def t_evaluate_total() -> None:
    # Pure + total: a malformed tier never raises (degrades to state-change=True via the
    # SHARED mios_ruleof2.is_state_change fail-closed derivation).
    try:
        v = Q.evaluate(session_tainted=True, permission_tier=12345, sensitive=False, mode="enforce")
        _check("eval: malformed tier -> no raise + bites (fail-closed C)", v.bites is True, str(v.to_dict()))
    except Exception as e:  # noqa: BLE001
        _check("eval: malformed tier -> no raise", False, repr(e))


def t_to_dict() -> None:
    v = Q.evaluate(session_tainted=True, permission_tier="write", sensitive=True, mode="enforce")
    d = v.to_dict()
    _check("to_dict: properties keyed by the structural axes",
           d["properties"] == {Q.PROP_UNTRUSTED: True, Q.PROP_SENSITIVE: True, Q.PROP_STATECHANGE: True},
           str(d))
    _check("to_dict: privileged/bites/mode/action present",
           d["privileged"] is True and d["bites"] is True
           and d["mode"] == Q.MODE_ENFORCE and d["action"] == Q.ACT_GATE, str(d))


def t_seam_stub() -> None:
    # The Q-LLM extraction seam is STUBBED -- degrade-open to None (never newly-opens
    # the gate, which is independent of this seam).
    _check("seam: quarantined_extract -> None (stubbed)", Q.quarantined_extract("attacker text") is None)
    _check("seam: quarantined_extract(schema) -> None", Q.quarantined_extract("x", schema={"k": 1}) is None)


# ─────────────────────────────────────────────────────────────────────────────
# 2. decide() reconciliation -- the quarantine posture composes into the SINGLE
#    HITL resolver (stricter wins; approval downgrades) ALONGSIDE the ro2 posture.
# ─────────────────────────────────────────────────────────────────────────────
def t_decide_quarantine() -> None:
    _check("decide: quarantine_block -> BLOCK", mios_hitl.decide(quarantine_block=True) == mios_hitl.BLOCK)
    _check("decide: quarantine_block + approved -> OBSERVE",
           mios_hitl.decide(quarantine_block=True, approved=True) == mios_hitl.OBSERVE)
    _check("decide: no block flags -> PROCEED (inert default)", mios_hitl.decide() == mios_hitl.PROCEED)
    # stricter-wins: a quarantine BLOCK composes with the other gates (an audit-only
    # [ai] gate cannot soften it).
    _check("decide: quarantine_block + ai audit -> BLOCK still",
           mios_hitl.decide(quarantine_block=True, in_tier_scope=True, ai_mode="audit") == mios_hitl.BLOCK)
    # BYTE-IDENTICAL: the existing ro2/tier/scope verdicts are unchanged by the new flag.
    _check("decide: ro2_block still BLOCK (unchanged)", mios_hitl.decide(ro2_block=True) == mios_hitl.BLOCK)


# ─────────────────────────────────────────────────────────────────────────────
# 3. CHOKEPOINT WIRING -- drive mios_dispatch with SYNTHETIC (non-dictionary) verbs;
#    only the quarantine gate is under test (ro2 forced OFF, every other gate stubbed).
# ─────────────────────────────────────────────────────────────────────────────
# B-only = sensitive read-tier; C-only = plain write-tier; B+C = sensitive write-tier;
# neither = plain read-tier. Names are synthetic so no baked dictionary words leak in.
_CAT = {
    "zq_senread":  {"permission": "read",  "sensitive": True},   # B only  -> tainted bites
    "zq_plainwr":  {"permission": "write"},                       # C only  -> tainted bites
    "zq_senwrite": {"permission": "write", "sensitive": True},   # B + C   -> tainted bites
    "zq_roplain":  {"permission": "read"},                        # neither -> never bites
}
_conv = contextvars.ContextVar("conv", default="conv-q")
_appr = contextvars.ContextVar("appr", default=None)
_agent = contextvars.ContextVar("agent", default="")
_evspy = {"n": 0}
_ORIG_EVALUATE = Q.evaluate          # captured BEFORE any spy patch (so the spy can delegate)
_ORIG_BUILD = mios_dispatch._build_dispatch_cmd  # captured to restore after the broker-spy tests


def _spy_evaluate(*a, **k):
    _evspy["n"] += 1
    return _ORIG_EVALUATE(*a, **k)


@contextlib.asynccontextmanager
async def _noop_cm(*a, **k):
    yield


class _NoConflict:
    """Stub Tool-Manager conflict gate -- guard() yields immediately (no serialization)."""
    def guard(self, *a, **k):
        return _noop_cm()


def _configure(mode, *, tainted):
    """Wire mios_dispatch for the quarantine gate in isolation: synthetic catalog, the
    chosen quarantine mode, ro2 forced OFF, the taint signal stubbed, the public-path
    trace/conflict machinery stubbed (so dispatch_mios_verb reaches the inner chokepoint),
    and every OTHER gate stubbed to pass-through."""
    _created: list = []
    mios_dispatch.configure(
        verb_catalog=_CAT,
        high_privilege_verbs=frozenset(),     # keep the firewall block out of the way
        launch_verbs=frozenset(),
        rule_of_two_mode="off",               # isolate: ONLY the quarantine gate decides
        quarantine_mode=mode,
        dispatch_dedup=False,                 # straight to _dispatch_bounded (no dedup state)
        web_dispatch_jitter_s=0.0,
        launcher_sock="/nonexistent/launcher.sock",
        dispatch_inflight={},
        conv_key_var=_conv,
        proposal_var=contextvars.ContextVar("p", default=None),
        recency_ctx_var=contextvars.ContextVar("r", default=None),
        dispatch_agent_var=_agent,
        hitl_approved_var=_appr,
        tool_conflict=_NoConflict(),
        trace_span=_noop_cm,
        resolve_verb_key=lambda n: n,
        current_date_str=lambda: time.strftime("%Y-%m-%d"),
        emit_dispatch_dedup_event=lambda *a, **k: None,
        db_create=lambda table, row=None, **k: _created.append((table, row)) or (table, row),
        db_post=lambda sql: sql,
        db_fire=lambda x: None,
    )
    # Upstream gates stubbed to pass-through so ONLY the quarantine gate decides.
    mios_dispatch._dispatch_pdp_reason = lambda tool: None
    mios_dispatch._dispatch_quota_reason = lambda tool: None
    mios_dispatch._validate_enum_args = lambda t, a: None
    mios_dispatch._hitl_block_reason = lambda tool, args: None
    mios_dispatch._HITL_ARBITER_URL = ""
    mios_dispatch._hitl_record_pending = lambda *a, **k: None
    mios_dispatch._build_dispatch_cmd = _ORIG_BUILD   # restore (a prior broker-spy test may have patched)

    async def _gate_none(*a, **k):
        return None
    mios_dispatch._hitl_gate = _gate_none

    async def _taint(session_id):
        return (bool(tainted), "zq_src->external" if tainted else "")
    mios_dispatch._session_is_tainted = _taint
    # spy on the evaluator so off-mode-never-consults-it is provable (mios_dispatch calls
    # mios_quarantine.evaluate -- the SAME shared module object as Q).
    Q.evaluate = _spy_evaluate
    return _created


def _run_inner(tool, args, session_id="s-q"):
    return asyncio.run(mios_dispatch._dispatch_mios_verb_inner(tool, args, session_id=session_id))


def _run_public(tool, args, session_id="s-q"):
    return asyncio.run(mios_dispatch.dispatch_mios_verb(tool, args, session_id=session_id))


def t_enforce_blocks_tainted_sensitive() -> None:
    # tainted + sensitive READ (B only, NO state-change) = a bite under quarantine even
    # though Rule-of-Two would let it through (only 2 of 3). This is the stricter posture.
    _evspy["n"] = 0
    _appr.set(None)
    _configure("enforce", tainted=True)
    res = _run_inner("zq_senread", {"k": "v"})
    _check("enforce: tainted+sensitive-read -> quarantine_blocked", res.get("quarantine_blocked") is True, str(res))
    _check("enforce: tainted+sensitive-read -> not success", res.get("success") is False)
    _check("enforce: tainted+sensitive-read -> hitl_pending shape", res.get("hitl_pending") is True, str(res))
    _check("enforce: evaluator WAS consulted", _evspy["n"] >= 1)


def t_enforce_blocks_tainted_write() -> None:
    # tainted + plain WRITE (C only, not sensitive) = a bite (state-change under untrusted).
    _configure("enforce", tainted=True)
    res = _run_inner("zq_plainwr", {"k": "v"})
    _check("enforce: tainted+write -> quarantine_blocked", res.get("quarantine_blocked") is True, str(res))
    # tainted + sensitive WRITE (B+C) = a bite too (the all-three case is a subset).
    res2 = _run_inner("zq_senwrite", {"k": "v"})
    _check("enforce: tainted+sensitive-write -> quarantine_blocked", res2.get("quarantine_blocked") is True, str(res2))


def t_enforce_proceeds_non_bite() -> None:
    # tainted + read-only NON-sensitive (neither B nor C) = NO bite -> proceeds.
    _configure("enforce", tainted=True)
    res = _run_inner("zq_roplain", {"k": "v"})
    _check("enforce: tainted+read-only-non-sensitive -> NOT blocked", not res.get("quarantine_blocked"), str(res))
    # UNtainted + privileged (sensitive write) = NO bite -> proceeds (quarantine only bites
    # when untrusted content is present).
    _configure("enforce", tainted=False)
    res2 = _run_inner("zq_senwrite", {"k": "v"})
    _check("enforce: untainted+privileged -> NOT blocked (quarantine needs untrusted-present)",
           not res2.get("quarantine_blocked"), str(res2))
    res3 = _run_inner("zq_senread", {"k": "v"})
    _check("enforce: untainted+sensitive-read -> NOT blocked", not res3.get("quarantine_blocked"), str(res3))


def t_audit_non_blocking() -> None:
    _evspy["n"] = 0
    created = _configure("audit", tainted=True)
    res = _run_inner("zq_senread", {"k": "v"})
    _check("audit: bite -> NOT blocked (non-blocking)", not res.get("quarantine_blocked"), str(res))
    _check("audit: evaluator consulted", _evspy["n"] >= 1)
    kinds = [(r or {}).get("kind") for (t, r) in created if t == "event"]
    _check("audit: emitted a quarantine_audit event", "quarantine_audit" in kinds, str(kinds))
    _check("audit: did NOT emit a block event", "quarantine_block" not in kinds, str(kinds))


def t_off_byte_identical() -> None:
    # DEFAULT-OFF: the evaluator is NOT consulted (the chokepoint mode-guard short-
    # circuits) -> behaviour is byte-identical to pre-feature dispatch. Drive the
    # all-bite candidate through BOTH entries to prove neither consults the gate.
    _evspy["n"] = 0
    _configure("off", tainted=True)
    res_i = _run_inner("zq_senwrite", {"k": "v"})
    res_p = _run_public("zq_senwrite", {"k": "v"})
    _check("off: inner -> NOT blocked (gate inert)", not res_i.get("quarantine_blocked"), str(res_i))
    _check("off: public -> NOT blocked (gate inert)", not res_p.get("quarantine_blocked"), str(res_p))
    _check("off: evaluator NEVER consulted (byte-identical)", _evspy["n"] == 0,
           f"evaluate called {_evspy['n']}x in off mode")


def t_approval_downgrade() -> None:
    # An explicit same-turn ask-to-run approval of THIS exact action downgrades the
    # enforce block so the approved action runs.
    _configure("enforce", tainted=True)
    _ah = mios_dispatch._pending_hash("zq_senwrite", {"k": "v"})
    _appr.set(_ah)
    try:
        res = _run_inner("zq_senwrite", {"k": "v"})
        _check("enforce: approved bite -> downgraded (NOT blocked)",
               not res.get("quarantine_blocked"), str(res))
    finally:
        _appr.set(None)


def t_degrade_open() -> None:
    # The taint read raises -> the gate degrades OPEN (no crash, no spurious block).
    _configure("enforce", tainted=True)

    async def _boom(session_id):
        raise RuntimeError("taint store down")
    mios_dispatch._session_is_tainted = _boom
    res = _run_inner("zq_senwrite", {"k": "v"})
    _check("degrade-open: taint error -> NOT quarantine_blocked", not res.get("quarantine_blocked"), str(res))
    _check("degrade-open: dispatch still returns a dict", isinstance(res, dict))


def t_soundness_no_bypass() -> None:
    # SOUNDNESS: the SAME tainted + privileged dispatch must be gated via BOTH the public
    # dispatch_mios_verb (the chat tool-loop / HTTP entry) AND the direct
    # _dispatch_mios_verb_inner chokepoint -- and the broker cmd-builder must be reached by
    # NEITHER (the gate short-circuits before the broker). This proves there is no second
    # action path that bypasses the single-chokepoint composition.
    _appr.set(None)
    _configure("enforce", tainted=True)
    _broker = {"n": 0}

    def _spy_cmd(tool, args):
        _broker["n"] += 1
        raise AssertionError("broker cmd-builder reached on a quarantined verb!")
    mios_dispatch._build_dispatch_cmd = _spy_cmd
    try:
        r_inner = _run_inner("zq_senwrite", {"k": "v"}, session_id="s-direct")
        _check("no-bypass: DIRECT inner chokepoint gated", r_inner.get("quarantine_blocked") is True, str(r_inner))
        r_pub = _run_public("zq_senwrite", {"k": "v"}, session_id="s-public")
        _check("no-bypass: PUBLIC chat entry (dispatch_mios_verb) gated",
               r_pub.get("quarantine_blocked") is True, str(r_pub))
        _check("no-bypass: broker cmd-builder reached via NEITHER path", _broker["n"] == 0,
               f"broker reached {_broker['n']}x")
    finally:
        mios_dispatch._build_dispatch_cmd = _ORIG_BUILD


def main() -> int:
    for t in (t_normalize_mode, t_evaluate_bite_matrix, t_evaluate_privileged,
              t_evaluate_action_matrix, t_evaluate_total, t_to_dict, t_seam_stub,
              t_decide_quarantine,
              t_enforce_blocks_tainted_sensitive, t_enforce_blocks_tainted_write,
              t_enforce_proceeds_non_bite, t_audit_non_blocking, t_off_byte_identical,
              t_approval_downgrade, t_degrade_open, t_soundness_no_bypass):
        t()
    passed = sum(1 for _, ok in _RESULTS if ok)
    total = len(_RESULTS)
    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
