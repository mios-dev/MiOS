# AI-hint: Stdlib assert-script for mios_hitlflow (R7 security wave) -- the HITL
# AI-related: mios_hitlflow.py, mios_hitl.py, mios_secset.py

import asyncio
import json

import mios_secset
import mios_hitlflow as M


def test_action_hash():
    h1 = M._action_hash("web_search", {"q": "x", "n": 3})
    h2 = M._action_hash("web_search", {"n": 3, "q": "x"})   # key order swapped
    assert h1 == h2, "action_hash must be key-order invariant (sorted keys)"
    assert h1 == M._action_hash("web_search", {"q": "x", "n": 3}), "must be deterministic"
    assert M._action_hash("web_search", {"q": "y"}) != h1, "different args -> different hash"
    assert M._action_hash("other_verb", {"q": "x", "n": 3}) != h1, "different verb -> different hash"
    assert "\x00" in h1, "action_hash uses the in-memory \\x00 separator"
    print("ok: _action_hash determinism + structural identity")


def test_pending_hash():
    p1 = M._pending_hash("powershell_run", {"cmd": "ls", "n": 1})
    p2 = M._pending_hash("powershell_run", {"n": 1, "cmd": "ls"})   # reordered
    assert p1 == p2, "pending_hash must be key-order invariant"
    assert p1 == M._pending_hash("powershell_run", {"cmd": "ls", "n": 1}), "deterministic"
    assert "\x00" not in p1 and len(p1) == 64, "pending_hash must be null-free sha256 hex"
    assert all(c in "0123456789abcdef" for c in p1), "pending_hash must be lowercase hex"
    assert M._pending_hash("powershell_run", {"cmd": "rm -rf /"}) != p1, \
        "different args must not share a bypass key"
    assert M._pending_hash("winget_install", {"cmd": "ls", "n": 1}) != p1, \
        "different verb must not share a bypass key"
    print("ok: _pending_hash null-free + per-action bypass-key isolation")


def test_hitl_gate_namekeyed():
    scope = mios_secset.high_privilege_set(
        ["powershell_run", "winget_install", "memory_forget"], [])
    assert "powershell_run" in scope

    events = []
    M.configure(
        hitl_enable=True, hitl_mode="gate", hitl_scope=scope,
        emit_session_event=lambda fields, sid: events.append(fields),
        db_read=_aret([]),
        pg_primary=True,
        pg_mirror=lambda *a, **k: None,
        db_create=lambda *a, **k: "",
        db_fire=lambda *a, **k: None,
        db_post=_aret(None),
    )

    blocked = asyncio.run(M._hitl_gate("powershell_run", {"cmd": "whoami"}, "sess1"))
    assert isinstance(blocked, dict) and blocked.get("hitl_pending") is True, \
        "SECURITY: a scoped high-privilege verb must BLOCK in gate mode"
    assert blocked.get("success") is False

    proceed = asyncio.run(M._hitl_gate("web_search", {"q": "x"}, "sess1"))
    assert proceed is None, "a non-scoped safe verb must PROCEED"

    M.configure(hitl_mode="log")
    assert asyncio.run(M._hitl_gate("powershell_run", {"cmd": "x"}, "s")) is None, \
        "log mode must be non-blocking (proceed)"
    assert events, "the gate must always emit an observability event"
    print("ok: _hitl_gate NAME-KEYED block/proceed (real mios_secset + mios_hitl)")


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
        assert asyncio.run(M._classify_approval_reply("", "run x")) == "unrelated"
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

    M.configure(
        passport_sign=lambda table, fields: {"sig": "x", "table": table},
        db_update=_fake_update,
    )

    r = asyncio.run(M.hitl_approve_logic(_FakeReq({"id": "42", "approved": True})))
    body = _json_body(r)
    assert body == {"success": True, "id": "42", "status": "approved"}, body
    assert updates and updates[-1].get("pg_params", {}).get("id") == 42, updates
    assert updates[-1]["pg_params"]["status"] == "approved"

    r = asyncio.run(M.hitl_approve_logic(_FakeReq({"id": "pending_action:7",
                                                   "approved": False})))
    body = _json_body(r)
    assert body["status"] == "denied" and body["id"] == "pending_action:7", body

    n_before = len(updates)
    r = asyncio.run(M.hitl_approve_logic(_FakeReq({})))
    body = _json_body(r)
    assert body.get("success") is False and "id" in body.get("error", ""), body
    assert len(updates) == n_before, "an invalid id must not persist a decision"

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
