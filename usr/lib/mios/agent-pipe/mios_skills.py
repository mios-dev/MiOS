# AI-hint: SKILLS execution cluster extracted verbatim from server.py (refactor R7/mios_skills wave). Skill row readers (_skill_fetch/_skill_list, pg-native when primary), the engine that runs a promoted skill's step list 1:1 via dispatch_mios_verb (execute_skill -- sequence/try-each modes, expand_from fan-out, invocation open/close + tool_call attribution, last_used_at bump, skill_run events), and the OpenAI function-tool projectors consumed verbatim by Hermes/OpenCode (_skill_to_openai_tool, _mcp_tool_to_openai_tool, _make_schema_strict). Pure pieces (_skill_to_openai_tool/_make_schema_strict/_mcp_tool_to_openai_tool) need no server state; mios_pg imported directly for rid_to_pg_id. The server-side DB helpers (_db_read/_db_post/_db_update/_db_write), the verb dispatcher (dispatch_mios_verb), the invocation/attribution helpers (_skill_invocation_open/_skill_invocation_close/_skill_attribute_tool_call), the arg renderer (_skill_render_args), the $-token regex (_PARAM_TOKEN_RE) and the SKILLS_ENABLED flag are dependency-INJECTED via configure() (one-way boundary -- mios_skills NEVER imports server). ALSO owns the episodic SKILL.md mirror (closed-loop self-learning): _write_skill_md_fire (fire-and-forget public entry injected back into the chat/native-loop/verity paths) + its private _slug_for_skill / _render_skill_md, with the target dir + enable flag injected as server-owned SSOT and _a2a_now (canonical UTC-ISO stamp) imported directly from mios_a2a. server.py re-imports every name verbatim under its original alias (surface-parity zero-diff).
# AI-related: ./server.py, ./mios_config.py, ./mios_pg.py, ./mios_a2a.py, ./test_mios_skills.py
# AI-functions: _skill_fetch, _skill_list, execute_skill, _skill_to_openai_tool, _make_schema_strict, _mcp_tool_to_openai_tool, _slug_for_skill, _render_skill_md, _write_skill_md_fire, configure
"""SKILLS execution cluster -- skill readers, the step engine, and the
OpenAI function-tool projectors.

Extracted verbatim from ``server.py``. ``_skill_fetch`` / ``_skill_list``
read promoted-skill rows (pg-native when pgvector is primary);
``execute_skill`` maps a skill body's steps 1:1 onto ``dispatch_mios_verb``
calls (sequence / try-each modes, ``expand_from`` fan-out, invocation
open/close + tool_call attribution); ``_skill_to_openai_tool`` /
``_mcp_tool_to_openai_tool`` / ``_make_schema_strict`` project skills and
external MCP tools into OpenAI strict function-tool schemas consumed
verbatim by Hermes + OpenCode. ``server.py`` re-imports every name under
its original alias so the module's public surface is byte-identical.

The server-side DB-event helpers, the verb dispatcher, the
invocation/attribution helpers, the arg renderer, the ``$``-token regex
and the ``SKILLS_ENABLED`` flag are injected via :func:`configure`
(one-way module boundary -- this module never imports ``server``).
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from typing import Optional

import mios_pg as _mios_pg
from mios_a2a import _a2a_now
from mios_a2a_principal import _passport_sign

log = logging.getLogger("mios-agent-pipe")


# ── Dependency-injection seam ─────────────────────────────────
# execute_skill runs skill steps through server.py's dispatch_mios_verb and
# persists outcomes via its DB helpers + invocation/attribution helpers; the
# readers call _db_read. server.py calls configure() with these AFTER they are
# all defined (one-way boundary: this module never imports server). They stay
# None/default until then; every consumer is async/runtime so a standalone
# ``import mios_skills`` still succeeds. The injected globals keep their ORIGINAL
# server.py names because the moved bodies reference them verbatim.
_db_read = None
_db_post = None
_db_update = None
_db_write = None
_pg_mirror = None
dispatch_mios_verb = None
SKILLS_ENABLED = True
# Episodic SKILL.md mirror: the target dir + on/off flag are server-owned SSOT
# (env MIOS_SKILLS_EPISODIC_* -> server consts) and stay None until configure()
# injects them. The writer degrades-open (disabled flag -> no-op) so a standalone
# ``import mios_skills`` stays side-effect-free.
_SKILLS_EPISODIC_DIR = None
_SKILLS_EPISODIC_ENABLED = None


def configure(*, db_read=None, db_post=None, db_update=None, db_write=None,
              pg_mirror=None, dispatch_verb=None, skills_enabled=None,
              skills_episodic_dir=None, skills_episodic_enabled=None) -> None:
    """Inject the server.py runtime helpers the skills engine calls back into.

    The invocation/attribution lifecycle, the arg renderer and the $-token regex
    now LIVE in this module (no longer injected); only the DB-event helpers, the
    verb dispatcher, the pg outcome mirror and the SKILLS_ENABLED flag are
    server-owned. _passport_sign is imported directly from mios_a2a_principal.
    The episodic SKILL.md mirror's target dir + enable flag are server-owned SSOT
    (env-read) and injected here; _a2a_now is imported directly from mios_a2a."""
    global _db_read, _db_post, _db_update, _db_write, _pg_mirror
    global dispatch_mios_verb, SKILLS_ENABLED
    global _SKILLS_EPISODIC_DIR, _SKILLS_EPISODIC_ENABLED
    if db_read is not None:
        _db_read = db_read
    if db_post is not None:
        _db_post = db_post
    if db_update is not None:
        _db_update = db_update
    if db_write is not None:
        _db_write = db_write
    if pg_mirror is not None:
        _pg_mirror = pg_mirror
    if dispatch_verb is not None:
        dispatch_mios_verb = dispatch_verb
    if skills_enabled is not None:
        SKILLS_ENABLED = skills_enabled
    if skills_episodic_dir is not None:
        _SKILLS_EPISODIC_DIR = skills_episodic_dir
    if skills_episodic_enabled is not None:
        _SKILLS_EPISODIC_ENABLED = skills_episodic_enabled


async def _skill_fetch(name: str) -> Optional[dict]:
    """Read one skill row by name. Returns the row dict (with body
    + status fields) or None if not found."""
    if not name:
        return None
    sql = (
        f"SELECT id, name, body, status, source, version, "
        f"description, support, confidence "
        f"FROM skill WHERE name = {json.dumps(name)} LIMIT 1;"
    )
    # R15/G10: read pg when primary -- the surreal `skill` table is empty after
    # the agent-plane migration (the promoted skills live in pgvector), so a raw
    # _db_post here made the agent skill-blind. Falls back to surreal in dual.
    r = await _db_read(sql, pg_sql=(
        "SELECT id, name, body, status, source, version, "
        "description, support, confidence FROM skill "
        "WHERE name = %(n)s LIMIT 1"), pg_params={"n": name})
    if not r:
        return None
    rows = (r[-1] or {}).get("result") or []
    return rows[0] if rows else None

async def _skill_list(*, status: str = "promoted",
                      source: Optional[str] = None,
                      limit: int = 200) -> list[dict]:
    where = []
    if status and status != "all":
        where.append(f"status = {json.dumps(status)}")
    if source and source != "all":
        where.append(f"source = {json.dumps(source)}")
    clause = " AND ".join(where) if where else "true"
    sql = (
        f"SELECT name, description, body, source, status, "
        f"support, confidence, version "
        f"FROM skill WHERE {clause} "
        f"ORDER BY name LIMIT {int(limit)};"
    )
    # R15/G10: pg-native list when primary (surreal skill table is empty; the
    # promoted skills are in pgvector). Param-bound clause; surreal fallback.
    pg_where, pg_params = [], {}
    if status and status != "all":
        pg_where.append("status = %(status)s"); pg_params["status"] = status
    if source and source != "all":
        pg_where.append("source = %(source)s"); pg_params["source"] = source
    pg_clause = " AND ".join(pg_where) if pg_where else "true"
    r = await _db_read(sql, pg_sql=(
        "SELECT name, description, body, source, status, support, "
        f"confidence, version FROM skill WHERE {pg_clause} "
        f"ORDER BY name LIMIT {int(limit)}"), pg_params=pg_params)
    if not r:
        return []
    return (r[-1] or {}).get("result") or []

async def execute_skill(name: str, params: dict, *,
                        session_id: Optional[str] = None) -> dict:
    """Run a skill by name. Returns the same envelope shape an
    execute_dag run returns -- success, steps[], failures[],
    aborted -- so every gateway in the stack consumes skill output
    with identical code.

    The skill body steps are mapped 1:1 to dispatch_mios_verb calls;
    each tool_call row produced is attributed to the skill via
    RELATE skill_invocation->emitted->tool_call. The Phase B.3
    firewall, Phase A.3 taint chain, and Phase A.1 reflexion cap
    all apply unchanged because we route through the same
    dispatch_mios_verb the planner uses."""
    if not SKILLS_ENABLED:
        return {"success": False,
                "skill": name,
                "error": "skills_disabled",
                "steps": [],
                "failures": ["skills disabled via MIOS_SKILLS_ENABLE"]}
    row = await _skill_fetch(name)
    if not row:
        return {"success": False, "skill": name,
                "error": "not_found", "steps": [], "failures": []}
    if row.get("status") != "promoted":
        return {"success": False, "skill": name,
                "error": "not_promoted",
                "status": row.get("status"),
                "steps": [], "failures": []}
    body = row.get("body") or {}
    steps = body.get("steps") or []
    if not steps:
        return {"success": False, "skill": name,
                "error": "empty_body", "steps": [], "failures": []}
    # Execution mode -- "sequence" (default) halts on first FAILURE;
    # "try-each" halts on first SUCCESS. The latter is the generic
    # primitive resilience skills need (try variant A, then B, then
    # C, ... succeed when any one lands). Operator directive "no
    # hardcoded fallbacks -- ALL TOOLS AND SKILLS to solve for this":
    # the engine extension is generic infrastructure;
    # specific fallback orderings live in individual skill bodies.
    mode = str(body.get("mode") or "sequence").lower()
    inv_id = await _skill_invocation_open(
        row.get("id"), params or {}, session_id)
    # expand_from: a step annotated with {"expand_from": "<param>",
    # "bind_as": "<token>"} fans out into one step per element of
    # the named array param, binding `$<token>` to each value. Used
    # by try-each skills to walk an arbitrary list (e.g. browser
    # fallback chain) without hardcoding the list in the skill. The
    # expansion happens here so the rest of the engine (logging,
    # event emission, invocation_close) sees a flat step list.
    expanded: list[dict] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        ef = step.get("expand_from")
        if not ef:
            expanded.append(step)
            continue
        ba = step.get("bind_as") or "item"
        seq = (params or {}).get(ef)
        if not isinstance(seq, list) or not seq:
            # No values to expand -> skip the step. Counts as a
            # silent no-op rather than a missing-params failure;
            # try-each callers can still resolve on a later step.
            continue
        for v in seq:
            inst = {k: w for k, w in step.items()
                    if k not in ("expand_from", "bind_as")}
            inst_params = {**(params or {}), ba: v}
            inst["args"] = _skill_render_args(
                inst.get("args") or {}, inst_params)
            inst["_expanded_from"] = ef
            inst["_bound_value"] = v
            expanded.append(inst)
    steps = expanded
    results: list[dict] = []
    failures: list[str] = []
    for idx, step in enumerate(steps):
        verb = (step or {}).get("verb") or ""
        raw_args = (step or {}).get("args") or {}
        # Already-rendered args from expand_from pass through; raw
        # args (literal step) still need rendering. Detect by
        # presence of the _expanded_from marker.
        if step.get("_expanded_from"):
            rendered = raw_args
        else:
            rendered = _skill_render_args(raw_args, params or {})
        # Detect un-substituted $-tokens (operator forgot a param).
        leftover = [
            v for v in rendered.values()
            if isinstance(v, str) and _PARAM_TOKEN_RE.search(v)
        ]
        if leftover:
            failures.append(
                f"step {idx} ({verb}): missing params {leftover}")
            results.append({"step": idx, "verb": verb,
                            "success": False,
                            "error": "missing_params",
                            "leftover": leftover})
            # Halt -- can't dispatch with un-bound tokens.
            await _skill_invocation_close(inv_id, success=False)
            return {"success": False, "skill": name, "steps": results,
                    "failures": failures, "aborted": True}
        r = await dispatch_mios_verb(
            verb, rendered, session_id=session_id)
        results.append({
            "step": idx, "verb": verb, "args": rendered,
            "success": bool(r.get("success", False)),
            "exit_code": r.get("exit_code"),
            "output": r.get("output", "")[:400],
            "stderr": r.get("stderr", "")[:400],
            "tainted": r.get("tainted", False),
            "taint_reason": r.get("taint_reason", ""),
            # T-049: surface the dispatch-emitted Semantic-Firewall / HITL block
            # markers (parallel to `tainted`) so the pass^k promotion gate can veto
            # on a firewall_block or HITL escalation EVEN when a try-each skill
            # recovered on a later step. Structured booleans, not text.
            "firewall_blocked": bool(r.get("firewall_blocked", False)),
            "hitl_blocked": bool(
                r.get("hitl_blocked", False) or r.get("hitl_pending", False)),
        })
        # Attribute the tool_call to this invocation. The
        # dispatch_mios_verb path emits the tool_call row itself;
        # we re-query to find the most recent matching row and
        # RELATE it. Best-effort; the audit chain isn't load-bearing
        # for skill correctness, just for miner-side dedup.
        if session_id:
            q = (
                f"SELECT id, ts FROM tool_call "
                f"WHERE session = {session_id} "
                f"  AND tool = {json.dumps(verb)} "
                f"ORDER BY ts DESC LIMIT 1;"
            )
            qr = await _db_post(q)
            if qr:
                tc_rows = (qr[-1] or {}).get("result") or []
                if tc_rows:
                    await _skill_attribute_tool_call(
                        inv_id, tc_rows[0].get("id"), idx)
        step_ok = bool(r.get("success", False))
        if mode == "try-each":
            # try-each: halt on first SUCCESS. A failed step records
            # the failure and continues; a successful step closes the
            # skill as a win (any-of-N semantics).
            if step_ok:
                await _skill_invocation_close(inv_id, success=True)
                # WS-MEM-TIER: dead _db_post(UPDATE) on pgvector-primary left the
                # skill's last_used_at (configurator UI + recency signal) un-bumped;
                # route through _db_update with a parameterized PG UPDATE.
                await _db_update(
                    f"UPDATE {row.get('id')} SET last_used_at = time::now();",
                    pg_sql="UPDATE skill SET last_used_at = now() WHERE id = %(id)s",
                    pg_params={"id": _mios_pg.rid_to_pg_id(row.get('id'))})
                _db_write("event", {
                    "source": "agent-pipe",
                    "kind": "skill_run",
                    "severity": "info",
                    "summary": f"{name} ok at step {idx} (try-each)",
                    "payload": {"skill": name, "winning_step": idx,
                                "mode": "try-each",
                                "steps_attempted": idx + 1},
                }, now_fields=("ts",))
                return {"success": True, "skill": name, "steps": results,
                        "failures": failures, "aborted": False,
                        "winning_step": idx, "mode": "try-each"}
            # Failure under try-each: record + keep going. Only halt
            # when we run out of steps below (the for-loop falls out).
            failures.append(
                f"step {idx} ({verb}): "
                f"exit={r.get('exit_code')} "
                f"stderr={r.get('stderr','')[:200]}")
            continue
        # mode == "sequence" (default).
        if not step_ok:
            failures.append(
                f"step {idx} ({verb}): "
                f"exit={r.get('exit_code')} "
                f"stderr={r.get('stderr','')[:200]}")
            # Stop on first failure -- operator can re-run with
            # corrected params instead of cascading half-state.
            await _skill_invocation_close(inv_id, success=False)
            _db_write("event", {
                "source": "agent-pipe",
                "kind": "skill_run",
                "severity": "warn",
                "summary": f"{name} failed at step {idx}",
                "payload": {"skill": name, "step": idx,
                            "verb": verb,
                            "stderr": r.get("stderr", "")[:300]},
            }, now_fields=("ts",))
            return {"success": False, "skill": name, "steps": results,
                    "failures": failures, "aborted": True}
    # Loop fell off the end. For try-each that means every step
    # failed (no win); for sequence that means every step succeeded.
    if mode == "try-each":
        await _skill_invocation_close(inv_id, success=False)
        _db_write("event", {
            "source": "agent-pipe",
            "kind": "skill_run",
            "severity": "warn",
            "summary": f"{name} exhausted (try-each)",
            "payload": {"skill": name, "mode": "try-each",
                        "steps_attempted": len(steps)},
        }, now_fields=("ts",))
        return {"success": False, "skill": name, "steps": results,
                "failures": failures, "aborted": True,
                "mode": "try-each"}
    await _skill_invocation_close(inv_id, success=True)
    # Update last_used_at on the skill row for the configurator UI.
    # WS-MEM-TIER: dead _db_post(UPDATE) on pgvector-primary -> route via _db_update.
    await _db_update(
        f"UPDATE {row.get('id')} SET last_used_at = time::now();",
        pg_sql="UPDATE skill SET last_used_at = now() WHERE id = %(id)s",
        pg_params={"id": _mios_pg.rid_to_pg_id(row.get('id'))})
    _db_write("event", {
        "source": "agent-pipe",
        "kind": "skill_run",
        "severity": "info",
        "summary": f"{name} ok ({len(steps)} steps)",
        "payload": {"skill": name, "steps_run": len(steps)},
    }, now_fields=("ts",))
    return {"success": True, "skill": name, "steps": results,
            "failures": [], "aborted": False}

def _skill_to_openai_tool(row: dict) -> dict:
    """Render one skill row as an OpenAI function-tool schema.
    Hermes + OpenCode consume this dump verbatim so their tool
    surface auto-extends every time the operator promotes a skill --
    no code changes per skill on either client."""
    name = row.get("name") or ""
    description = row.get("description") or f"MiOS skill {name}"
    body = row.get("body") or {}
    params = body.get("params") or []
    properties = {
        p: {"type": "string",
            "description": f"value for ${p}"} for p in params
    }
    # OpenAI STRICT mode (audit P2): skill params are all required by
    # construction (required == params), so strict mode is satisfied by just adding
    # strict:True + additionalProperties:False -- no nullable rework needed. Brings
    # promoted-skill tools (mios_skill__*, consumed verbatim by Hermes + OpenCode) to
    # the same strict contract as verbs (_verb_to_openai_tool).
    return {
        "type": "function",
        "function": {
            "name": f"mios_skill__{re.sub(r'[^A-Za-z0-9_]', '_', name)}",
            "description": description,
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": params,
                "additionalProperties": False,
            },
        },
        "x-mios-skill": name,
    }

def _make_schema_strict(schema: dict) -> dict:
    if not isinstance(schema, dict):
        return {"type": "object", "properties": {}, "required": [], "additionalProperties": False}
    s = dict(schema)
    if s.get("type") == "object":
        properties = s.get("properties") or {}
        if not isinstance(properties, dict):
            properties = {}
        s["properties"] = dict(properties)
        
        required = s.get("required") or []
        if not isinstance(required, list):
            required = []
            
        new_required = list(required)
        for prop_name, prop_val in s["properties"].items():
            if isinstance(prop_val, dict):
                prop_val = _make_schema_strict(prop_val)
                s["properties"][prop_name] = prop_val
                if prop_name not in required:
                    new_required.append(prop_name)
                    t = prop_val.get("type")
                    if isinstance(t, str):
                        prop_val["type"] = [t, "null"]
                    elif isinstance(t, list):
                        if "null" not in t:
                            prop_val["type"] = list(t) + ["null"]
                    else:
                        prop_val["type"] = ["object", "null"]
            else:
                prop_val = {"type": ["string", "null"]}
                s["properties"][prop_name] = prop_val
                if prop_name not in required:
                    new_required.append(prop_name)
        s["required"] = new_required
        s["additionalProperties"] = False
    elif s.get("type") == "array":
        items = s.get("items")
        if isinstance(items, dict):
            s["items"] = _make_schema_strict(items)
    return s

def _mcp_tool_to_openai_tool(key: str, info: dict) -> dict:
    """Project a registered external MCP tool (key 'mcp.<server>.<tool>', raw
    MCP inputSchema) into OpenAI function-tool shape so it joins the worker tool
 surface (P0: wire the MCP CLIENT into the agent loop).
    MCP inputSchema IS JSON-Schema -> drops straight into function.parameters.
    Strictified for OpenAI compliance."""
    schema = info.get("inputSchema")
    strict_schema = _make_schema_strict(schema)
    return {
        "type": "function",
        "function": {
            "name": key,
            "description": info.get("description") or f"MCP tool {key}",
            "strict": True,
            "parameters": strict_schema,
        },
        "x-mios-mcp-server": info.get("server_id"),
    }


# ── Skill invocation/attribution lifecycle + arg renderer ─────────
# The $-token arg renderer (_skill_render_args / _PARAM_TOKEN_RE) and the
# skill_invocation open/close/attribute DB lifecycle live here alongside the
# engine that drives them (execute_skill). They were previously defined in
# server.py and injected back; co-locating them removes the injection while
# keeping server.py's importable surface byte-identical (it re-imports each).
# _passport_sign is imported directly from mios_a2a_principal; the DB-event
# helpers (_db_post) + the pg outcome mirror (_pg_mirror) are injected via
# configure(). One-way boundary: this module never imports server.
_PARAM_TOKEN_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")


def _skill_render_args(args: dict, params: dict) -> dict:
    """Substitute $-tokens in skill step args using the params map.
    Pure helper -- the skill body holds the template, the params
    dict holds the concrete operator-supplied values.

    Operator-supplied params override mined defaults. Missing
    params leave the $-token literal (so the dispatch errors
    visibly instead of silently swallowing the gap)."""
    out: dict = {}
    for k, v in (args or {}).items():
        if isinstance(v, str):
            def _sub(m: re.Match) -> str:
                key = m.group(1)
                if key in params and params[key] is not None:
                    return str(params[key])
                return m.group(0)
            out[k] = _PARAM_TOKEN_RE.sub(_sub, v)
        else:
            out[k] = v
    return out


# P4-A0: open->close carry for the pg outcome mirror. Under pg-primary the
# SurrealDB CREATE in _skill_invocation_open is short-circuited (returns None),
# so skill outcomes would persist to NOTHING and the skill miner's success-rate
# has no data. Keyed by the (real OR synthesized) inv_id; popped at close.
_SKILL_INV_META: dict = {}


async def _skill_invocation_open(skill_id: str,
                                 params: dict,
                                 session_id: Optional[str]) -> Optional[str]:
    """Open a skill_invocation row; returns the new row id (or
    None if the DB write failed). The caller closes the row via
    _skill_invocation_close with ended_at + success.

    Hand-built CREATE -- _db_create json.dumps-quotes every value,
    but SurrealDB 3.0+ requires record<...> references UNQUOTED
    (`skill = skill:abc123`, not `skill = "skill:abc123"`). The
    quoted form produces a coerce error response that the caller
    can't interpret as success."""
    parts = [
        "started_at = time::now()",
        f"skill = {skill_id}",
        f"params = {json.dumps(params or {})}",
    ]
    if session_id:
        parts.append(f"session = {session_id}")
    # Phase C.3: passport. Same algorithm as _db_create -- include
    # the record-ref strings (skill_id, session_id) in the hash so
    # tampering with the attribution links re-derives a different
    # op_hash on verify.
    hash_fields = {
        "started_at": "time::now()",
        "skill": skill_id,
        "params": params or {},
    }
    if session_id:
        hash_fields["session"] = session_id
    envelope = _passport_sign("skill_invocation", hash_fields)
    if envelope is not None:
        parts.append(f"passport = {json.dumps(envelope)}")
    sql = "CREATE skill_invocation SET " + ", ".join(parts) + " RETURN AFTER;"
    r = await _db_post(sql)
    inv_id = None
    if r:
        last = r[-1] or {}
        if last.get("status") == "OK":
            rows = last.get("result") or []
            if isinstance(rows, list) and rows and isinstance(rows[0], dict):
                inv_id = rows[0].get("id")
    # P4-A0: under pg-primary the SurrealDB CREATE is short-circuited (r=None) so
    # inv_id is None and the outcome would persist to NOTHING -- the skill miner's
    # success-rate then has no data. Synthesize an id + remember {skill,session}
    # so _skill_invocation_close can mirror the outcome row to pg. (SurrealDB/dual
    # keeps the real record id; this is purely additive.)
    if not inv_id:
        inv_id = "skill_invocation:pg-" + uuid.uuid4().hex
    _SKILL_INV_META[inv_id] = {"skill": skill_id, "session": session_id}
    return inv_id


async def _skill_invocation_close(inv_id: Optional[str],
                                  success: bool) -> None:
    if not inv_id:
        return
    # P4-A0: persist the OUTCOME to pg (the SurrealDB UPDATE below no-ops under
    # pg-primary). One row per completed invocation: {skill, success, session_id}.
    # _pg_mirror is drift-tolerant (filters to live columns) + degrade-open, so a
    # schema/type mismatch can never break the close.
    meta = _SKILL_INV_META.pop(inv_id, None)
    if meta:
        try:
            _pg_mirror("skill_invocation", {
                "skill": meta.get("skill"),
                "success": bool(success),
                "session_id": meta.get("session"),
            })
        except Exception:  # noqa: BLE001 -- never break the close
            pass
    sql = (
        f"UPDATE {inv_id} SET ended_at = time::now(), "
        f"success = {str(bool(success)).lower()};"
    )
    await _db_post(sql)


async def _skill_attribute_tool_call(inv_id: Optional[str],
                                     tool_call_id: Optional[str],
                                     step_index: int) -> None:
    """RELATE the tool_call back to the skill_invocation so the
    miner subtracts skill-emitted runs from future candidate
    populations (Phase C.2 closes the loop on its own output)."""
    if not inv_id or not tool_call_id:
        return
    sql = (
        f"RELATE {inv_id}->emitted->{tool_call_id} "
        f"SET step_index = {int(step_index)};"
    )
    await _db_post(sql)


# ── Episodic SKILL.md mirror (closed-loop self-learning) ───────────────────────
# After a substantive turn the polish/native-loop path writes a self-contained
# SKILL.md to _SKILLS_EPISODIC_DIR so the next similar query recalls it as
# exemplar context. _slug_for_skill + _render_skill_md are private to
# _write_skill_md_fire (the fire-and-forget public entry, injected back into the
# chat / native-loop / verity paths). The target dir + enable flag are server-
# owned SSOT injected via configure(); _a2a_now is the canonical UTC-ISO stamp
# imported from mios_a2a (one-way boundary -- this module never imports server).
def _slug_for_skill(query: str) -> str:
    """Stable, filesystem-safe slug from the user query. Length-capped so a
    long prompt doesn't blow past max-filename on tmpfs."""
    s = (query or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s[:60] or "skill"


def _render_skill_md(query: str, answer: str,
                     tool_history: Optional[list],
                     session_id: Optional[str]) -> str:
    """Render a self-contained SKILL.md (operator brief L6 'closed-loop self-
    learning'): YAML frontmatter (re-usable by OpenViking-style L0/L1/L2 +
    Obsidian) + Goal + Workflow (per-tool-call line) + Outcome. Kept compact
    so the file fits a single tokenizer window when the next similar query
    recalls it as exemplar context."""
    th = [t for t in (tool_history or []) if isinstance(t, dict)]
    verbs = sorted({str(t.get("tool", "")) for t in th if t.get("tool")})
    front = [
        "---",
        f"name: skill-{int(time.time())}-{_slug_for_skill(query)}",
        f"ts: {_a2a_now()}",
        "source: episodic",
        f"session: {session_id or 'unknown'}",
        f"verbs_used: [{', '.join(verbs)}]",
        f"goal: {(query or '').strip()[:200]!r}",
        "---",
        "",
    ]
    body = [
        "# Goal",
        (query or "").strip(),
        "",
        "# Workflow",
    ]
    if not th:
        body.append("(answer produced without explicit tool calls)")
    else:
        for i, t in enumerate(th, 1):
            tool = str(t.get("tool", "?"))
            args = t.get("args") or {}
            try:
                arg_repr = json.dumps(args, default=str)[:200]
            except Exception:  # noqa: BLE001
                arg_repr = str(args)[:200]
            body.append(f"{i}. `{tool}` with args {arg_repr}")
    body += [
        "",
        "# Outcome",
        (answer or "").strip()[:4000],
        "",
        "# Re-use",
        ("This run is recorded as episodic memory; semantic-recall via "
         "the knowledge table surfaces it when a similar query lands. "
         "Treat as prior work, NOT fresh ground truth."),
    ]
    return "\n".join(front) + "\n".join(body) + "\n"


def _write_skill_md_fire(*, query: str, answer: str,
                         tool_history: Optional[list] = None,
                         session_id: Optional[str] = None) -> None:
    """Fire-and-forget SKILL.md write to _SKILLS_EPISODIC_DIR. Never raises --
    a write failure is logged + ignored; the answer is already returned."""
    if not _SKILLS_EPISODIC_ENABLED:
        log.info("skill md: disabled by env")
        return
    q = (query or "").strip()
    a = (answer or "").strip()
    if not q or not a:
        log.info("skill md: empty q=%s a=%s -> skip",
                 bool(q), bool(a))
        return
    try:
        os.makedirs(_SKILLS_EPISODIC_DIR, exist_ok=True)
        slug = _slug_for_skill(q)
        ts = time.strftime("%Y-%m-%dT%H-%M-%S")
        fname = f"{ts}-{slug}.md"
        path = os.path.join(_SKILLS_EPISODIC_DIR, fname)
        with open(path, "w", encoding="utf-8") as f:
            f.write(_render_skill_md(q, a, tool_history, session_id))
        log.info("skill md: wrote %s", path)
    except Exception as e:  # noqa: BLE001
        log.warning("skill md write skipped: %s", e)
