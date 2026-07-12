# AI-hint: HITL ask-to-run + runtime approval-gate flow extracted verbatim from server.py (refactor R7 security wave). The chat-native human-in-the-loop plane: the WS-6 runtime gate (_hitl_gate / _hitl_is_approved / _hitl_record_pending -- scoped-verb dispatch interception, gate/log modes), the structural action identity (_action_hash verb+sorted-args; _pending_hash NULL-free sha256 for the pg pending_action store), the ask-to-run round-trip (_read_recent_pending / _mark_pending_decided / _classify_approval_reply MODEL-classified approve/reject/unrelated with NO keyword list / _ask_to_run_completion stream-aware result / _maybe_run_pending_approval propose->approve->per-action-hash bypass->re-dispatch), and the Reflexion read-side (_recent_reflections). SECURITY-CRITICAL: gates are NAME-KEYED on verb keys + permission tiers (mios_secset/mios_hitl decision helpers) -- never rename a verb key, gate name, or tier; a silent gate-disable is the worst regression. mios_hitl (decision helpers), mios_jsonsalvage, mios_pg, mios_sse are imported direct; every server symbol they touch (the HITL/ASK config scalars, ROUTER/PLANNER endpoints, _PG_PRIMARY, the _db_*/_pg_mirror DB helpers, _emit_session_event, _row_age_seconds, _usage_estimate, the _hitl_approved_var ContextVar, dispatch_mios_verb) is dependency-INJECTED via configure() (one-way boundary -- this module NEVER imports server). The /v1/hitl/* endpoints + the HITL/ASK config-constant definitions stay in server.py, which re-imports every moved name verbatim under its original alias (surface-parity zero-diff).
# AI-related: ./server.py, ./mios_config.py, ./mios_hitl.py, ./mios_secset.py, ./mios_jsonsalvage.py, ./mios_pg.py, ./mios_sse.py, ./test_mios_hitlflow.py
# AI-functions: _action_hash, _pending_hash, _hitl_is_approved, _hitl_record_pending, _hitl_gate, _classify_approval_reply, _read_recent_pending, _mark_pending_decided, _ask_to_run_completion, _maybe_run_pending_approval, _recent_reflections, hitl_approve_logic, hitlflow_router, hitl_pending, hitl_approve, configure
"""mios_hitlflow -- HITL ask-to-run + runtime approval-gate flow.

Extracted verbatim from ``server.py`` (R7 security wave). Holds the WS-6 runtime
HITL gate, the structural action-identity hashers, the chat-native ask-to-run
approval round-trip (propose -> model-classified approval -> per-action-hash
bypass -> re-dispatch) and the Reflexion episodic read-side. ``server.py``
re-imports every name under its original alias so the public surface is
byte-identical.

SECURITY-CRITICAL: the gates are NAME-KEYED on verb keys + permission tiers.
Nothing is renamed; the moved bodies are unchanged. ``mios_hitl`` (pure decision
helpers), ``mios_jsonsalvage``, ``mios_pg`` and ``mios_sse`` are imported
directly from their sibling modules; every other server-side symbol the flow
touches (the HITL/ASK config scalars, the router/planner endpoints, the
``_db_*`` / ``_pg_mirror`` DB helpers, ``_emit_session_event``,
``_row_age_seconds``, ``_usage_estimate``, the ``_hitl_approved_var``
ContextVar and ``dispatch_mios_verb``) is injected via :func:`configure`
(one-way module boundary -- this module never imports ``server``).
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from mios_jsonsalvage import loads_lenient as _loads_lenient
import mios_hitl   # the shared HITL verdict resolver (mios_hitl.decide) both gates route through
from mios_hitl import (requires_approval as _hitl_requires,
                       block_result as _hitl_block_result)
from mios_sse import _sse_chunk, _stream_answer, _sse_done
import mios_pg as _mios_pg

log = logging.getLogger("mios-agent-pipe")


# -- Dependency-injection seam --------------------------------------
# The gate + ask-to-run flow read server.py's HITL/ASK config scalars + the
# router/planner endpoints, and call back into the DB-event helpers, the session
# event emitter, the broker dispatch and a ContextVar. server.py calls
# configure() with those AFTER every one is defined (one-way boundary: this
# module never imports server). The placeholders below carry documented defaults
# so a standalone ``import mios_hitlflow`` still succeeds; every consumer is
# async/runtime so nothing fires before configure() runs.

# config scalars (server SSOT/env-derived; injected at import-completion)
HITL_ENABLE = True
HITL_MODE = "log"
HITL_SCOPE: set = set()
ASK_TO_RUN_ENABLE = True
ASK_TO_RUN_TTL_S = 1800
ROUTER_MODEL = ""
PLANNER_ENDPOINT = ""
PLANNER_TIMEOUT_S = 20.0
_PG_PRIMARY = False

# server-side helpers / ContextVar (injected)
_db_read = None
_db_post = None
_db_create = None
_db_fire = None
_db_update = None
_pg_mirror = None
_emit_session_event = None
_row_age_seconds = None
_usage_estimate = None
_passport_sign = None
_hitl_approved_var = None
dispatch_mios_verb = None


def configure(*, hitl_enable=None, hitl_mode=None, hitl_scope=None,
              ask_to_run_enable=None, ask_to_run_ttl_s=None,
              router_model=None, planner_endpoint=None, planner_timeout_s=None,
              pg_primary=None, db_read=None, db_post=None, db_create=None,
              db_fire=None, db_update=None, pg_mirror=None,
              emit_session_event=None, row_age_seconds=None,
              usage_estimate=None, passport_sign=None, hitl_approved_var=None,
              dispatch_mios_verb=None) -> None:
    """Inject server.py's HITL/ASK config scalars, the router/planner endpoints,
    the DB-event helpers, the session event emitter, the passport signer, the
    ContextVar and the broker dispatch the gate + ask-to-run flow call back into."""
    global HITL_ENABLE, HITL_MODE, HITL_SCOPE
    global ASK_TO_RUN_ENABLE, ASK_TO_RUN_TTL_S
    global ROUTER_MODEL, PLANNER_ENDPOINT, PLANNER_TIMEOUT_S, _PG_PRIMARY
    global _db_read, _db_post, _db_create, _db_fire, _db_update, _pg_mirror
    global _emit_session_event, _row_age_seconds, _usage_estimate, _passport_sign
    global _hitl_approved_var
    if hitl_enable is not None:
        HITL_ENABLE = hitl_enable
    if hitl_mode is not None:
        HITL_MODE = hitl_mode
    if hitl_scope is not None:
        HITL_SCOPE = hitl_scope
    if ask_to_run_enable is not None:
        ASK_TO_RUN_ENABLE = ask_to_run_enable
    if ask_to_run_ttl_s is not None:
        ASK_TO_RUN_TTL_S = ask_to_run_ttl_s
    if router_model is not None:
        ROUTER_MODEL = router_model
    if planner_endpoint is not None:
        PLANNER_ENDPOINT = planner_endpoint
    if planner_timeout_s is not None:
        PLANNER_TIMEOUT_S = planner_timeout_s
    if pg_primary is not None:
        _PG_PRIMARY = pg_primary
    if db_read is not None:
        _db_read = db_read
    if db_post is not None:
        _db_post = db_post
    if db_create is not None:
        _db_create = db_create
    if db_fire is not None:
        _db_fire = db_fire
    if db_update is not None:
        _db_update = db_update
    if pg_mirror is not None:
        _pg_mirror = pg_mirror
    if emit_session_event is not None:
        _emit_session_event = emit_session_event
    if row_age_seconds is not None:
        _row_age_seconds = row_age_seconds
    if usage_estimate is not None:
        _usage_estimate = usage_estimate
    if passport_sign is not None:
        _passport_sign = passport_sign
    if hitl_approved_var is not None:
        _hitl_approved_var = hitl_approved_var
    if dispatch_mios_verb is not None:
        globals()["dispatch_mios_verb"] = dispatch_mios_verb


def _action_hash(tool: str, args: dict) -> str:
    """Stable identity of a (verb, resolved-args) dispatch for the
    in-run loop/dedup guard. Structural only -- verb name + sorted
    args -- so it carries no English/topic content (NO-HARDCODED-
    ENGLISH binding)."""
    try:
        canon = json.dumps(args or {}, sort_keys=True,
                           separators=(",", ":"), ensure_ascii=False,
                           default=str)
    except (TypeError, ValueError):
        canon = repr(args)
    return f"{tool}\x00{canon}"


def _pending_hash(tool: str, args: dict) -> str:
    """NULL-FREE action identity for the ask-to-run pending_action store + approval
    match. _action_hash embeds a \\x00 separator (fine in-memory) which Postgres TEXT
    columns REJECT -> the pending insert silently failed. sha256 is null-free, fixed-
    length, deterministic over the SAME (verb, resolved-args), and leaks no content."""
    return hashlib.sha256(
        _action_hash(tool, args).encode("utf-8", "replace")).hexdigest()


async def _hitl_is_approved(session_id: Optional[str], action_hash: str) -> bool:
    """True if this (session, action) was approved out-of-band (gate mode)."""
    try:
        where = f"action_hash = {json.dumps(action_hash)} AND status = 'approved'"
        pg_where = "action_hash = %(ah)s AND status = 'approved'"
        pg_params = {"ah": action_hash}
        if session_id:
            where += f" AND session = {session_id}"
            pg_where += " AND session_id = %(sid)s"
            pg_params["sid"] = session_id
        resp = await _db_read(
            f"SELECT id FROM pending_action WHERE {where} LIMIT 1;",
            pg_sql=f"SELECT id FROM pending_action WHERE {pg_where} LIMIT 1",
            pg_params=pg_params)
        for st in (resp or []):
            if isinstance(st, dict) and isinstance(st.get("result"), list) \
                    and st["result"]:
                return True
    except Exception:  # noqa: BLE001
        pass
    return False


def _hitl_record_pending(tool: str, args: dict, action_hash: str,
                         session_id: Optional[str]) -> None:
    """Persist a pending_action row (gate mode) so /v1/hitl/approve can find +
    approve it. Fire-and-forget; degrade-open."""
    try:
        _pg_mirror("pending_action", {"tool": tool, "args": args,  # WS-9c
                                      "action_hash": action_hash,
                                      "status": "pending",
                                      "session_id": session_id})
        sql = _db_create("pending_action", {
            "tool": tool, "args": args, "action_hash": action_hash,
            "status": "pending",
        }, now_fields=("ts",), _mirror=False)
        if session_id:
            sql = sql.rstrip().rstrip(";") + f", session = {session_id};"
        if not _PG_PRIMARY:                      # WS-9c: pgvector mirror is primary
            _db_fire(_db_post(sql))
    except Exception:  # noqa: BLE001
        pass


async def _hitl_gate(tool: str, args: dict,
                     session_id: Optional[str]) -> "Optional[dict]":
    """The runtime HITL gate ([hitl] verb-scope half), called from
    _dispatch_mios_verb_inner for scoped verbs. Returns a block_result dict to REFUSE
    the dispatch (gate mode, not yet approved) or None to PROCEED. The block/proceed
    verdict is computed by the SINGLE shared resolver (``mios_hitl.decide``) that the
    [ai] risk-tier gate also routes through, so the two HITL gates can no longer
    disagree. Always emits an observability event. Never raises -> degrade-open to
    PROCEED (an agent is never wedged by the gate failing)."""
    try:
        if not _hitl_requires(tool, HITL_ENABLE, HITL_SCOPE):
            return None
        ah = _action_hash(tool, args)
        approved = (await _hitl_is_approved(session_id, ah)
                    if HITL_MODE == "gate" else False)
        # Route the verb-scope decision through the one shared resolver: this verb is
        # already in scope (the guard above), so feed its scope posture + approval.
        verdict = mios_hitl.decide(in_name_scope=True, hitl_enable=HITL_ENABLE,
                                   hitl_mode=HITL_MODE, approved=approved)
        blocked = verdict == mios_hitl.BLOCK
        outcome = mios_hitl.BLOCK if blocked else mios_hitl.PROCEED
        _emit_session_event({
            "source": "agent-pipe", "kind": "hitl_request",
            "severity": "high" if blocked else "info",
            "summary": f"hitl {HITL_MODE}: {tool} -> {outcome}",
            "payload": {"tool": tool, "args": args, "mode": HITL_MODE,
                        "outcome": outcome, "approved": approved},
        }, session_id)
        if blocked:
            _hitl_record_pending(tool, args, ah, session_id)
            return _hitl_block_result(tool, args, ah)
        return None
    except Exception:  # noqa: BLE001 -- the gate must never break a dispatch
        return None


async def _classify_approval_reply(user_text: str, proposal: str) -> str:
    """Generative judge (NO phrase list -- operator "NOTHING HARDCODED"): given the
    PROPOSED action + the user's reply, classify BY MEANING as 'approve' (run it now),
    'reject' (skip it), or 'unrelated' (a new request, not an answer to the proposal).
    Only called when a proposal is actually pending. Degrade -> 'unrelated' on any
    error (SAFE: the action stays un-run; the user can re-confirm). Never auto-runs on
    ambiguity."""
    if not (user_text or "").strip():
        return "unrelated"
    sys = (
        "The assistant PROPOSED an action and asked the user to approve it. Read the "
        "user's reply and classify it PURELY by what it MEANS relative to that proposal "
        "-- never by matching specific words. 'approve' = the reply AGREES to run the "
        "proposed action now. 'reject' = the reply DECLINES or cancels it. 'unrelated' = "
        "the reply is a NEW request or a different question, not an answer to the "
        "proposal. If the reply is ambiguous between approve and unrelated, choose "
        "'unrelated' -- NEVER auto-run on ambiguity.")
    payload = {
        "model": ROUTER_MODEL,
        "messages": [{"role": "system", "content": sys},
                     {"role": "user", "content":
                      f"PROPOSED ACTION: {proposal[:400]}\n\nUSER REPLY: {user_text[:600]}"}],
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "approval", "strict": True, "schema": {
                "type": "object",
                "properties": {"decision": {"type": "string",
                                            "enum": ["approve", "reject", "unrelated"]}},
                "required": ["decision"], "additionalProperties": False}}},
        "chat_template_kwargs": {"enable_thinking": False},
        "temperature": 0.0, "max_tokens": 20, "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=PLANNER_TIMEOUT_S) as s:
            r = await s.post(f"{PLANNER_ENDPOINT}/v1/chat/completions", json=payload,
                             headers={"Content-Type": "application/json"})
        if r.status_code != 200:
            return "unrelated"
        content = ((r.json().get("choices") or [{}])[0].get("message", {})
                   .get("content") or "")
        _d = (_loads_lenient(content) or {}).get("decision")
        return _d if _d in ("approve", "reject", "unrelated") else "unrelated"
    except Exception as e:  # noqa: BLE001 -- degrade to 'unrelated' (never auto-run)
        log.debug("approval judge failed (-> unrelated): %s", e)
        return "unrelated"


async def _read_recent_pending(session_id: "Optional[str]") -> "Optional[dict]":
    """The most-recent un-decided PENDING proposal for this chat within the TTL window,
    or None. Backs the ask-to-run approval round-trip. Degrade-open -> None."""
    if not session_id:
        return None
    try:
        resp = await _db_read(
            "SELECT id, tool, args, action_hash, ts FROM pending_action "
            f"WHERE status = 'pending' AND session = {session_id} ORDER BY ts DESC LIMIT 1;",
            pg_sql=("SELECT id, tool, args, action_hash, ts FROM pending_action "
                    "WHERE status = 'pending' AND session_id = %(sid)s "
                    "ORDER BY ts DESC LIMIT 1"),
            pg_params={"sid": session_id})
        # _db_read wraps rows in the legacy result envelope [{"result": [...]}].
        _rows = ((resp[0] or {}).get("result") or []) if isinstance(resp, list) and resp else []
        if not _rows:
            return None
        row = _rows[0]
        _age = _row_age_seconds(row.get("ts"))
        if _age is not None and ASK_TO_RUN_TTL_S > 0 and _age > ASK_TO_RUN_TTL_S:
            return None                       # proposal expired (TTL)
        return row
    except Exception:  # noqa: BLE001
        return None


async def _mark_pending_decided(rid, status: str) -> None:
    """Set a pending_action's status (approved/denied) so it isn't re-offered."""
    try:
        _pgid = _mios_pg.rid_to_pg_id(str(rid)) if rid is not None else None
        await _db_update(
            f"UPDATE {rid} SET status = {json.dumps(status)}, decided_at = time::now();",
            pg_sql=("UPDATE pending_action SET status = %(s)s, decided_at = now() "
                    "WHERE id = %(id)s"),
            pg_params={"s": status, "id": _pgid})
    except Exception:  # noqa: BLE001
        pass


def _ask_to_run_completion(chat_id: str, model: str, content: str,
                           *, streaming: bool = False) -> Any:
    """A chat.completion (streaming SSE or JSON) for an ask-to-run approval/rejection
    result -- stream-aware so OWUI/CLI (which request stream=true) get valid SSE."""
    if streaming:
        async def _stream_atr() -> "AsyncGenerator[bytes, None]":
            yield _sse_chunk("", chat_id=chat_id, model=model, role="assistant")
            async for _b in _stream_answer(content, chat_id=chat_id, model=model):
                yield _b
            yield _sse_chunk("", chat_id=chat_id, model=model, finish_reason="stop")
            yield _sse_done()
        return StreamingResponse(_stream_atr(), media_type="text/event-stream")
    return JSONResponse(content={
        "id": chat_id, "object": "chat.completion", "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content},
                     "finish_reason": "stop"}],
        "usage": _usage_estimate("", content), "mios_mode": "ask-to-run"})


async def _maybe_run_pending_approval(user_text: str, session_id: "Optional[str]",
                                      *, chat_id: str, model: str,
                                      streaming: bool = False) -> Any:
    """ASK-TO-RUN round-trip. If a proposal is pending for this chat AND the user's reply
    APPROVES it (model-classified), execute it (per-action-hash approval, gate otherwise
    unchanged) and return the result as a chat.completion. 'reject' -> drop it. Otherwise
    (unrelated / none / disabled) -> None so the turn proceeds normally."""
    if not ASK_TO_RUN_ENABLE:
        return None
    pend = await _read_recent_pending(session_id)
    if not pend:
        return None
    _tool = str(pend.get("tool") or "")
    _args = pend.get("args")
    if isinstance(_args, str):
        _args = _loads_lenient(_args) or {}
    if not isinstance(_args, dict):
        _args = {}
    _ah = str(pend.get("action_hash") or "")
    if not _tool or not _ah:
        return None
    _summary = f"{_tool}({json.dumps(_args, default=str)[:200]})"
    decision = await _classify_approval_reply(user_text, _summary)
    if decision == "unrelated":
        return None                            # not an answer to the proposal -> proceed
    if decision == "reject":
        await _mark_pending_decided(pend.get("id"), "denied")
        log.info("ask-to-run: user DECLINED %s", _tool)
        return _ask_to_run_completion(chat_id, model, f"Okay — I won't run `{_tool}`. Skipped.")
    # approve: run EXACTLY this hashed action (the gate lets it through this turn only)
    _hitl_approved_var.set(_ah)
    log.info("ask-to-run: user APPROVED %s -> executing", _tool)
    try:
        res = await dispatch_mios_verb(_tool, _args, session_id=session_id)
    except Exception as e:  # noqa: BLE001
        res = {"success": False, "stderr": f"{type(e).__name__}: {e}"}
    await _mark_pending_decided(pend.get("id"), "approved")
    _ok = isinstance(res, dict) and res.get("success")
    _out = ((res.get("output") or res.get("stderr") or "") if isinstance(res, dict)
            else str(res)).strip()
    _ans = (f"✅ Ran `{_tool}`.\n\n{_out[:3000]}" if _ok
            else f"⚠️ I tried to run `{_tool}` but it did not succeed:\n\n{_out[:1500]}")
    return _ask_to_run_completion(chat_id, model, _ans)


async def _recent_reflections(session_id: Optional[str],
                              limit: int = 4) -> list[dict]:
    """Reflexion episodic buffer (ref AIOS B.3 / Shinn et al. 2023): pull
    recent `reflect_corrected` events for THIS session so a fresh
    reflection can REUSE a prior fix instead of re-deriving it. The audit
    flagged these rows as write-only -- this is the missing read side.
    Best-effort: returns [] on any DB miss so reflection never blocks."""
    if not session_id:
        return []
    sql = (
        f"SELECT summary, ts FROM event "
        f"WHERE kind = 'reflect_corrected' AND session = {session_id} "
        f"ORDER BY ts DESC LIMIT {int(limit)};"
    )
    r = await _db_read(sql, pg_sql=(
        "SELECT summary, ts FROM event WHERE kind = 'reflect_corrected' "
        "AND session_id = %(sid)s ORDER BY ts DESC LIMIT %(lim)s"),
        pg_params={"sid": session_id, "lim": int(limit)})
    if not r:
        return []
    rows = (r[-1] or {}).get("result") or []
    return rows if isinstance(rows, list) else []


async def hitl_approve_logic(request: Request) -> JSONResponse:
    """WS-6: approve (or deny) a pending action by record id. The decision is
    passport-signed (the cryptographic HITL signature). In gate mode an approved
    (session, action_hash) lets the agent's RETRY of that exact action pass."""
    try:
        body = _loads_lenient(await request.body() or b"{}")
    except Exception:  # noqa: BLE001
        body = {}
    rid = str(body.get("id") or "").strip()
    # WS-MEM-TIER: accept a legacy record-id ('pending_action:NNN') OR a bare
    # pgvector bigint id -- the old `":" not in rid` guard REJECTED every valid pg
    # id, so HITL approve/deny was unreachable on pgvector-primary.
    _pgid = _mios_pg.rid_to_pg_id(rid)
    if not rid or (":" not in rid and _pgid is None):
        return JSONResponse({"success": False,
                             "error": "missing/invalid 'id' (a pending_action "
                                      "id from /v1/hitl/pending)"})
    status = "approved" if bool(body.get("approved", True)) else "denied"
    approver = str(body.get('approver') or 'operator')
    try:
        env = _passport_sign("pending_action", {"id": rid, "status": status})
        sets = [f"status = {json.dumps(status)}",
                "decided_at = time::now()",
                f"approver = {json.dumps(approver)}"]
        if env is not None:
            sets.append(f"approval_passport = {json.dumps(env)}")
        # WS-MEM-TIER: the raw _db_post(UPDATE) was a dead no-op on
        # pgvector-primary, so an approval/denial was NEVER persisted (the gate
        # could never record its decision). Route through _db_update with a
        # parameterized PG UPDATE (passport cast to jsonb) so the decision lands.
        await _db_update(
            f"UPDATE {rid} SET " + ", ".join(sets) + ";",
            pg_sql=("UPDATE pending_action SET status = %(status)s, "
                    "decided_at = now(), approver = %(approver)s, "
                    "approval_passport = %(passport)s::jsonb WHERE id = %(id)s"),
            pg_params={"status": status, "approver": approver,
                       "passport": (json.dumps(env) if env is not None else None),
                       "id": _pgid})
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"success": False, "error": str(e)})
    return JSONResponse({"success": True, "id": rid, "status": status})


# -- @app -> APIRouter migration (refactor R13 batch 3: HITL surface) -------------
# The two WS-6 HITL endpoints whose state this module owns -- the pending-approval
# list + live gate posture (/v1/hitl/pending) and the passport-signed approve/deny
# (/v1/hitl/approve) -- moved off server.py's @app onto this co-located
# hitlflow_router (the same routes->APIRouter pattern the /a2a wave established).
# server.py imports hitlflow_router + the two handler NAMES (re-imported there so its
# importable `provided` surface is unchanged) and mounts the router via
# app.include_router(hitlflow_router); the served path/method set is identical (the
# live-app route gate proves it). The pending-list body moved VERBATIM and reads this
# module's already-injected HITL_ENABLE/HITL_MODE/HITL_SCOPE + _db_read (no new
# injection); approve calls the module-resident hitl_approve_logic DIRECTLY (no
# sys.modules hop). One-way boundary: this module never imports server.
hitlflow_router = APIRouter()


@hitlflow_router.get("/v1/hitl/pending")
async def hitl_pending() -> JSONResponse:
    """WS-6: list pending HITL approvals (gate mode) + the live gate posture."""
    rows: list = []
    try:
        resp = await _db_read(
            "SELECT id, tool, args, action_hash, status, ts FROM pending_action "
            "WHERE status = 'pending' ORDER BY ts DESC LIMIT 100;",
            pg_sql="SELECT id, tool, args, action_hash, status, ts FROM "
                   "pending_action WHERE status = 'pending' ORDER BY ts DESC LIMIT 100")
        for st in (resp or []):
            if isinstance(st, dict) and isinstance(st.get("result"), list):
                rows = st["result"]
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"object": "mios.hitl.pending", "error": str(e),
                             "pending": []})
    return JSONResponse({"object": "mios.hitl.pending", "enabled": HITL_ENABLE,
                         "mode": HITL_MODE, "scope": sorted(HITL_SCOPE),
                         "count": len(rows), "pending": rows})


@hitlflow_router.post("/v1/hitl/approve")
async def hitl_approve(request: Request) -> JSONResponse:
    """WS-6 approve (or deny) a pending action by record id. The decision is
    passport-signed; in gate mode an approved (session, action_hash) lets the
    agent's RETRY of that exact action pass. Calls hitl_approve_logic (same
    module)."""
    return await hitl_approve_logic(request)
