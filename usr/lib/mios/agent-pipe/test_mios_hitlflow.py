# AI-hint: Stdlib assert-script for mios_hitlflow (R7 security wave) -- the HITL
#   ask-to-run + runtime approval gate. Asserts _action_hash determinism + key-order
#   invariance, _pending_hash NULL-free per-action bypass keying (an approval reused for
#   an identical action, never crossing to a different one), _hitl_gate NAME-KEYED gating
#   over the REAL mios_secset high-privilege builder + mios_hitl helpers (scoped
#   privileged verb blocks, safe verb proceeds), and _classify_approval_reply with a
#   stubbed model (approve / reject, degrade-open to 'unrelated' on error). No net/DB.
# AI-related: mios_hitlflow.py, mios_hitl.py, mios_secset.py
"""Stdlib assert-script for mios_hitlflow (R7 security wave).

Covers the security-critical decisions of the HITL ask-to-run + runtime
approval-gate flow:
  * _action_hash determinism + structural (key-order invariant) identity.
  * _pending_hash NULL-free, deterministic, per-action bypass key behavior
    (same action -> same key so an approval bypasses a later identical
    dispatch; a DIFFERENT action -> a DIFFERENT key so the approval never
    crosses over).
  * _hitl_gate NAME-KEYED gating using the REAL mios_secset high-privilege
    builder + the REAL mios_hitl decision helpers: a scoped high-privilege
    verb BLOCKS (gate mode, unapproved); a safe verb PROCEEDS.
  * _classify_approval_reply with a stubbed model returns approve / reject
    correctly (and degrades to 'unrelated' on error).

Run: python test_mios_hitlflow.py
"""

import asyncio
import json

import mios_secset
import mios_hitlflow as M


# ── _action_hash ────────────────────────────────────────────────────
def test_action_hash():
    h1 = M._action_hash("web_search", {"q": "x", "n": 3})
    h2 = M._action_hash("web_search", {"n": 3, "q": "x"})   # key order swapped
    assert h1 == h2, "action_hash must be key-order invariant (sorted keys)"
    assert h1 == M._action_hash("web_search", {"q": "x", "n": 3}), "must be deterministic"
    assert M._action_hash("web_search", {"q": "y"}) != h1, "different args -> different hash"
    assert M._action_hash("other_verb", {"q": "x", "n": 3}) != h1, "different verb -> different hash"
    assert "\x00" in h1, "action_hash uses the in-memory \\x00 separator"
    print("ok: _action_hash determinism + structural identity")


# ── _pending_hash (per-action bypass key) ───────────────────────────
def test_pending_hash():
    p1 = M._pending_hash("powershell_run", {"cmd": "ls", "n": 1})
    p2 = M._pending_hash("powershell_run", {"n": 1, "cmd": "ls"})   # reordered
    assert p1 == p2, "pending_hash must be key-order invariant"
    assert p1 == M._pending_hash("powershell_run", {"cmd": "ls", "n": 1}), "deterministic"
    # NULL-free + sha256 hex (the whole point: pg TEXT rejects \x00)
    assert "\x00" not in p1 and len(p1) == 64, "pending_hash must be null-free sha256 hex"
    assert all(c in "0123456789abcdef" for c in p1), "pending_hash must be lowercase hex"
    # per-action bypass: a DIFFERENT action yields a DIFFERENT key, so approving
    # one action can NEVER bypass the gate for another.
    assert M._pending_hash("powershell_run", {"cmd": "rm -rf /"}) != p1, \
        "different args must not share a bypass key"
    assert M._pending_hash("winget_install", {"cmd": "ls", "n": 1}) != p1, \
        "different verb must not share a bypass key"
    print("ok: _pending_hash null-free + per-action bypass-key isolation")


# ── _hitl_gate NAME-KEYED gating (real mios_secset + mios_hitl) ──────
def test_hitl_gate_namekeyed():
    # Build the scope from the REAL mios_secset high-privilege builder.
    scope = mios_secset.high_privilege_set(
        ["powershell_run", "winget_install", "memory_forget"], [])
    assert "powershell_run" in scope

    events = []
    M.configure(
        hitl_enable=True, hitl_mode="gate", hitl_scope=scope,
        emit_session_event=lambda fields, sid: events.append(fields),
        # gate mode -> _hitl_is_approved reads the DB; stub -> never approved.
        db_read=_aret([]),
        # _hitl_record_pending path (with _PG_PRIMARY=True only hits these):
        pg_primary=True,
        pg_mirror=lambda *a, **k: None,
        db_create=lambda *a, **k: "",
        db_fire=lambda *a, **k: None,
        db_post=_aret(None),
    )

    # A scoped high-privilege verb, unapproved -> BLOCK (the gate's whole job).
    blocked = asyncio.run(M._hitl_gate("powershell_run", {"cmd": "whoami"}, "sess1"))
    assert isinstance(blocked, dict) and blocked.get("hitl_pending") is True, \
        "SECURITY: a scoped high-privilege verb must BLOCK in gate mode"
    assert blocked.get("success") is False

    # A safe verb NOT in scope -> PROCEED (None).
    proceed = asyncio.run(M._hitl_gate("web_search", {"q": "x"}, "sess1"))
    assert proceed is None, "a non-scoped safe verb must PROCEED"

    # log mode (non-blocking) -> always proceed even for a scoped verb.
    M.configure(hitl_mode="log")
    assert asyncio.run(M._hitl_gate("powershell_run", {"cmd": "x"}, "s")) is None, \
        "log mode must be non-blocking (proceed)"
    assert events, "the gate must always emit an observability event"
    print("ok: _hitl_gate NAME-KEYED block/proceed (real mios_secset + mios_hitl)")


# ── _classify_approval_reply with a stubbed model ───────────────────
class _FakeResp:
    def __init__(self, decision):
        self.status_code = 200
        self._decision = decision

    def json(self):
        return {"choices": [{"message": {"content": '{"decision": "%s"}' % self._decision}}]}


class _FakeClient:
    """Async-context-manager httpx.AsyncClient stand-in."""
    _decision = "approve"
    _raise = False

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, *a, **k):
        if _FakeClient._raise:
            raise RuntimeError("planner down")
        return _FakeResp(_FakeClient._decision)


class _FakeHttpx:
    AsyncClient = _FakeClient


def test_classify_approval_reply():
    orig_httpx = M.httpx
    M.httpx = _FakeHttpx
    M.configure(router_model="router", planner_endpoint="http://x", planner_timeout_s=5.0)
    try:
        _FakeClient._raise = False
        _FakeClient._decision = "approve"
        assert asyncio.run(M._classify_approval_reply("yes do it", "run powershell_run(...)")) == "approve"
        _FakeClient._decision = "reject"
        assert asyncio.run(M._classify_approval_reply("no thanks", "run powershell_run(...)")) == "reject"
        # empty user reply -> never auto-run
        assert asyncio.run(M._classify_approval_reply("", "run x")) == "unrelated"
        # planner error -> degrade to 'unrelated' (SAFE: never auto-run on error)
        _FakeClient._raise = True
        assert asyncio.run(M._classify_approval_reply("yes", "run x")) == "unrelated"
    finally:
        M.httpx = orig_httpx
    print("ok: _classify_approval_reply approve/reject/degrade (stubbed model)")


def _aret(value):
    """Build an async function that ignores its args and returns `value`."""
    async def _f(*a, **k):
        return value
    return _f


# ── hitl_approve_logic (the moved /v1/hitl/approve body) ────────────
class _FakeReq:
    """Minimal request stand-in: async body() returns the JSON payload as the str
    the real mios_jsonsalvage.loads_lenient consumes (the same salvage parser
    server.py injects into the live handler)."""
    def __init__(self, obj):
        self._b = json.dumps(obj)

    async def body(self):
        return self._b


def _json_body(resp):
    """Decode a (real fastapi) JSONResponse rendered body into a dict."""
    return json.loads(bytes(resp.body).decode("utf-8"))


def test_hitl_approve_logic():
    updates = []

    async def _fake_update(*a, **k):
        updates.append(k)
        return None

    # passport_sign returns a signed envelope; db_update is the persist sink.
    M.configure(
        passport_sign=lambda table, fields: {"sig": "x", "table": table},
        db_update=_fake_update,
    )

    # APPROVE: a bare pgvector bigint id -> persists a parameterized UPDATE and
    # returns {success, id, status:approved}. The pg id is the parsed bigint.
    r = asyncio.run(M.hitl_approve_logic(_FakeReq({"id": "42", "approved": True})))
    body = _json_body(r)
    assert body == {"success": True, "id": "42", "status": "approved"}, body
    assert updates and updates[-1].get("pg_params", {}).get("id") == 42, updates
    assert updates[-1]["pg_params"]["status"] == "approved"

    # DENY: a SurrealDB-style record id is accepted too; status flips to denied.
    r = asyncio.run(M.hitl_approve_logic(_FakeReq({"id": "pending_action:7",
                                                   "approved": False})))
    body = _json_body(r)
    assert body["status"] == "denied" and body["id"] == "pending_action:7", body

    # INVALID-ID GATE: a missing id is REFUSED and never persists (no db_update).
    n_before = len(updates)
    r = asyncio.run(M.hitl_approve_logic(_FakeReq({})))
    body = _json_body(r)
    assert body.get("success") is False and "id" in body.get("error", ""), body
    assert len(updates) == n_before, "an invalid id must not persist a decision"

    # DB-ERROR: a failing persist degrades to {success: False, error} (never 500).
    async def _boom(*a, **k):
        raise RuntimeError("pg down")

    M.configure(db_update=_boom)
    r = asyncio.run(M.hitl_approve_logic(_FakeReq({"id": "9"})))
    body = _json_body(r)
    assert body.get("success") is False and "pg down" in body.get("error", ""), body
    print("ok: hitl_approve_logic approve/deny/invalid-id/db-error")


if __name__ == "__main__":
    test_action_hash()
    test_pending_hash()
    test_hitl_gate_namekeyed()
    test_classify_approval_reply()
    test_hitl_approve_logic()
    print("\nALL mios_hitlflow TESTS PASSED")
