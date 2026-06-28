# AI-hint: Reflection / self-assessment cluster extracted verbatim from server.py (strangler-fig wave). Two cohesive async helpers that ASSESS execution outcomes and emit verdict/correction events: _inline_satisfaction_check (synchronous per-turn Definition-of-Done check -- AND-folds this turn's tool_call rows, or trusts a delivered agent answer, into a user_query_(un)satisfied event so polish can ground-truth the wrapped reply on the CURRENT turn instead of waiting for mios-daemon's 30s async loop; also carries the structural write-action-claim guard keyed on the verb-permission class) and reflect_on_step_failure (ReWOO-style single-step reflection -- routes a failed DAG node + its captured error back to the small REFINE model for ONE corrected step, emitting reflect_corrected / reflect_unfixable session events). Both moved byte-for-byte. The server-side DB writers (_db_read/_db_write/_emit_session_event), the live _VERB_CATALOG, the REFINE_* model-call constants and the _REFLECT_SYSTEM prompt are dependency-INJECTED via configure() under their EXACT original server names (one-way boundary -- this module NEVER imports server); the sibling readers _recent_reflections (mios_hitlflow) and loads_lenient (mios_jsonsalvage) are imported directly. server.py re-imports both names verbatim so its public surface is byte-identical.
# AI-related: ./server.py, ./mios_hitlflow.py, ./mios_jsonsalvage.py, ./test_mios_reflect.py
# AI-functions: _inline_satisfaction_check, reflect_on_step_failure, _recent_satisfaction_verdicts, _recent_tool_history, _judge_answer_satisfied, configure
"""Reflection / self-assessment cluster (per-turn DoD verdict + failed-step reflection).

Extracted verbatim from ``server.py``. ``_inline_satisfaction_check`` runs the
synchronous Definition-of-Done check on the CURRENT turn and emits a
``user_query_(un)satisfied`` event; ``reflect_on_step_failure`` is the ReWOO
single-step reflection that turns a failed DAG node into one corrected step.
``server.py`` re-imports both names under their original aliases so the public
surface is byte-identical.

The DB writers, the verb catalog, the REFINE_* model-call constants and the
``_REFLECT_SYSTEM`` prompt are injected via :func:`configure` (one-way module
boundary -- this module never imports ``server``); ``_recent_reflections`` and
``loads_lenient`` come from sibling modules directly.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Optional

import httpx

from mios_jsonsalvage import loads_lenient as _loads_lenient
from mios_hitlflow import _recent_reflections


log = logging.getLogger("mios-agent-pipe")

# -- Dependency-injection seam ----------------------------------------------
# Everything below stays in server.py (the _db_* writers + the session-event
# emitter, the live verb catalog, the REFINE_* model-call constants, the
# _REFLECT_SYSTEM prompt). server.py calls configure(...) with these AFTER they are
# all defined (one-way boundary: this module never imports server). They keep their
# ORIGINAL server.py names because the moved bodies reference them verbatim. The
# helpers are only invoked at request time -- well after configure() has injected
# everything; the placeholders below just keep import + the surface check working
# before injection.
_db_read = None
_db_write = None
_emit_session_event = None
_VERB_CATALOG: dict = {}
REFINE_ENABLED = False
REFINE_MODEL = ""
REFINE_ENDPOINT = ""
REFINE_TIMEOUT_S = 30
_REFLECT_SYSTEM = ""
JUDGE_EXAMPLES = ""


def configure(*, db_read=None, db_write=None, emit_session_event=None,
              verb_catalog=None, refine_enabled=None, refine_model=None,
              refine_endpoint=None, refine_timeout_s=None,
              reflect_system=None, judge_examples=None) -> None:
    """Inject the server.py symbols the reflection helpers read. Each arg keeps its
    original server name as a module global; None means 'leave as-is' so a partial
    re-inject is safe."""
    global _db_read, _db_write, _emit_session_event, _VERB_CATALOG
    global REFINE_ENABLED, REFINE_MODEL, REFINE_ENDPOINT, REFINE_TIMEOUT_S
    global _REFLECT_SYSTEM, JUDGE_EXAMPLES
    if db_read is not None:
        _db_read = db_read
    if db_write is not None:
        _db_write = db_write
    if emit_session_event is not None:
        _emit_session_event = emit_session_event
    if verb_catalog is not None:
        _VERB_CATALOG = verb_catalog
    if refine_enabled is not None:
        REFINE_ENABLED = refine_enabled
    if refine_model is not None:
        REFINE_MODEL = refine_model
    if refine_endpoint is not None:
        REFINE_ENDPOINT = refine_endpoint
    if refine_timeout_s is not None:
        REFINE_TIMEOUT_S = refine_timeout_s
    if reflect_system is not None:
        _REFLECT_SYSTEM = reflect_system
    if judge_examples is not None:
        JUDGE_EXAMPLES = judge_examples


async def _inline_satisfaction_check(
    session_id: Optional[str], refined: Optional[dict],
    *,
    agent_tools_called: Optional[list] = None,
    agent_answered: Optional[bool] = None,
) -> Optional[dict]:
    """CONFIRMATION ENGINE. Run a synchronous
    Definition-of-Done check on THIS turn and emit a
    user_query_(un)satisfied event for the current session. mios-daemon's
    async loop ticks every 30s and only sees PRIOR turns; without this
    inline check, polish never knows whether the current turn actually
    succeeded and can't ground-truth the wrapped reply against it.

    Two signal sources, in priority order:
      1. tool_call rows agent-pipe recorded this turn (dispatch / DAG
         fast-paths write these) -> AND-fold their success fields.
      2. The agent-path signals `agent_tools_called` (verb names the
         sub-agent invoked inside its OWN tool-loop, captured from the
         stream) + `agent_answered` (the sub-agent produced a non-empty
         final answer). Under unify-on a verb like mios-os-control runs
         INSIDE Hermes, so agent-pipe records NO tool_call row for it --
         "no rows" then means the agent handled the turn, NOT that it
         failed. Treating that as `no_tools_seen -> unsatisfied` was the
         false-negative that made polish report failure on a succeeded
         verb and made the critic re-litigate a done answer (the
         "succeeds early then reports failed" bug). A delivered answer
         is DoD-met: the turn is DONE. Whether the ACTION inside it
         succeeded is then carried by the agent's own answer + any
         recorded rows -- polish relays a failure the agent states, but
         is no longer told the whole turn failed.

    Returns the emitted verdict dict {kind, payload} or None when
    there is nothing to judge. The agent-path caller uses the returned
    kind to HALT the chain (skip the critic re-pass) on a confirmed
    success. Best-effort: any DB hiccup returns None instead of
    failing the turn."""
    if not session_id or not isinstance(refined, dict):
        return None
    intent = str(refined.get("intent") or "").strip()
    intended = str(refined.get("intended_outcome") or "")[:200]
    # Fetch this turn's tool_calls (since the refine row was
    # written). Use a generous 5-min lookback that comfortably
    # covers a slow refine + sub-agent loop. `ts` MUST be in the
    # projection: SurrealDB 3.x rejects an ORDER BY on a field that
    # isn't selected ("Missing order idiom `ts`") with an HTTP 400,
    # which made _db_post return None (and trip a 30s DB backoff) --
    # the check then always bailed once a real session_id existed.
    sql = (
        f"SELECT ts, tool, args, result_preview, success, "
        f"exit_code, latency_ms FROM tool_call "
        f"WHERE session = {session_id} "
        f"  AND ts > time::now() - 5m "
        f"ORDER BY ts ASC;"
    )
    try:
        r = await _db_read(sql, pg_sql=(
            "SELECT ts, tool, args, result_preview, success, exit_code, "
            "latency_ms FROM tool_call WHERE session_id = %(sid)s "
            "AND ts > now() - interval '5 minutes' ORDER BY ts ASC"),
            pg_params={"sid": session_id})
    except Exception:
        return None
    if not r:
        return None
    rows = (r[-1] or {}).get("result") or []
    if not isinstance(rows, list):
        return None
    # AND-fold (same logic shape as mios-daemon._emit_satisfaction
    # but inline). For intent=chat no tools is expected = satisfied.
    if not rows:
        if intent == "chat":
            verdict = {
                "kind": "user_query_satisfied",
                "reason": "chat_no_tools_expected",
            }
        elif agent_answered:
            # Agent path: the sub-agent ran its own tool-loop (results
            # internal to it -> no agent-pipe tool_call row) and
            # delivered an answer. Turn is DONE = DoD-met. Record which
            # verbs it invoked for the audit trail.
            verdict = {
                "kind": "user_query_satisfied",
                "reason": "agent_answer_delivered",
                "agent_tools": [str(t) for t in (agent_tools_called or [])],
            }
        else:
            # No recorded tools AND no agent answer: a genuine no-op
            # (empty backend reply / dead endpoint).
            verdict = {
                "kind": "user_query_unsatisfied",
                "reason": "no_tools_seen",
            }
    else:
        failed: list[dict] = []
        for tc in rows:
            if not bool(tc.get("success")):
                failed.append({
                    "tool": tc.get("tool"),
                    "exit_code": tc.get("exit_code"),
                    "stderr_preview": (
                        tc.get("result_preview") or "")[:200],
                })
        if not failed:
            verdict = {
                "kind": "user_query_satisfied",
                "tools_checked": len(rows),
                "all_succeeded": True,
            }
        else:
            verdict = {
                "kind": "user_query_unsatisfied",
                "tools_checked": len(rows),
                "failed_tools": failed,
            }
    # STRUCTURAL action-claim validation (P5; the operator's "LIE"):
    # language-agnostic -- NO action-word lists. If the refined PLAN intended a
    # WRITE-permission action (intent=agent/multi_task + a write-permission verb
    # in hint_tools) but NOT ONE write-permission verb was actually invoked this
    # turn (neither in the agent's own tool-loop nor a recorded successful
    # dispatch), the side-effecting action did NOT happen -> flag it so polish's
    # INVOKED-TOOL CHECK has an authoritative structural signal and won't let a
    # fabricated "done" stand. Conservative (fires only on ZERO write verbs) so
    # it never false-flags a turn that legitimately acted; hint_tools are
    # suggestions, hence we test the write-PERMISSION class, not the exact verb.
    try:
        if intent in ("agent", "multi_task"):
            def _is_write_verb(v) -> bool:
                return str((_VERB_CATALOG.get(str(v)) or {})
                           .get("permission", "")).lower() == "write"
            _write_hinted = sorted({
                str(h) for h in ((refined or {}).get("hint_tools") or [])
                if _is_write_verb(h)})
            if _write_hinted:
                _invoked = {str(t) for t in (agent_tools_called or [])}
                _invoked |= {str(tc.get("tool")) for tc in rows
                             if tc.get("success")}
                if not any(_is_write_verb(t) for t in _invoked):
                    verdict["write_action_unmet"] = {
                        "hinted": _write_hinted,
                        "reason": "plan_intended_write_action_none_invoked",
                    }
    except Exception:
        pass
    kind = verdict["kind"]
    summary = f"{kind}: {intent or '?'} ({intended[:60]})"
    body = {
        "refine_intent": intent,
        "intended_outcome": intended,
        "source": "mios-agent-pipe-inline",
        **verdict,
    }
    # Write synchronously so polish's subsequent query picks it
    # up as the most-recent verdict for this session.
    try:
        _db_write("event", {
            "source": "mios-agent-pipe",
            "kind": kind,
            "severity": "info" if kind == "user_query_satisfied" else "warn",
            "summary": summary,
            "payload": body,
        }, now_fields=("ts",))
    except Exception:
        pass
    return {"kind": kind, "payload": body}


async def reflect_on_step_failure(
    failed_node: dict,
    failed_result: dict,
    plan_context: dict,
    session_id: Optional[str] = None,
) -> Optional[dict]:
    """ReWOO-style reflection: route a failed DAG step back to the
    SAME small refine model with the failure context and ask for a
    single corrected step. Returns {tool, args, rationale} dict
    or None on timeout/empty.

    Distinct from the retry-same-args loop (PLANNER_REFLEXION_CAP):
    that retries transient errors; this REPLACES the args/tool when
    the failure is structural (wrong verb, missing arg, wrong path).
    Three-stage Reflect/Call/Final pipeline -- caller bounds the
    number of reflection turns to 1, so a stubborn failure surfaces
    as a real error instead of looping (per the published
    Structured Reflection termination contract)."""
    if not REFINE_ENABLED:
        return None
    failed_tool = failed_node.get("tool", "?")
    failed_args = failed_node.get("args") or {}
    error_preview = (
        (failed_result.get("stderr") or "")[:400]
        or (failed_result.get("error") or "")[:400]
        or (failed_result.get("output") or "")[:400]
        or "(empty)"
    )
    exit_code = failed_result.get("exit_code", "?")
    plan_summary = str(plan_context.get("summary") or "")[:200]
    # Reflexion read-back (ref AIOS B.3): prior corrections in this session
    # inform the new fix instead of re-deriving from scratch. Best-effort;
    # empty when there are none / no session. Feeds the REFLECTION prompt
    # (an internal pass), NOT the first-turn user message -- so it stays
    # clear of the NO-context-injection binding (which targets env auto-
    # injection into the user prompt).
    prior_hint = ""
    _prior = await _recent_reflections(session_id)
    if _prior:
        _lines = [f"  - {str(p.get('summary') or '').strip()}"
                  for p in _prior if str(p.get("summary") or "").strip()]
        if _lines:
            prior_hint = ("\nPrior fixes this session (reuse the pattern if "
                          "it matches this failure):\n" + "\n".join(_lines))
    user_msg = (
        f"Plan summary: {plan_summary}\n"
        f"Failed step: tool={failed_tool} "
        f"args={json.dumps(failed_args, separators=(',', ':'))[:300]}\n"
        f"Exit code: {exit_code}\n"
        f"Stderr/error: {error_preview}"
        f"{prior_hint}\n"
        "/no_think"
    )
    base = str(REFINE_ENDPOINT or "").rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    url = f"{base}/v1/chat/completions"
    payload = {
        "model": REFINE_MODEL,
        "messages": [
            {"role": "system", "content": _REFLECT_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        "stream": False,
        "temperature": 0.0,
        "max_tokens": 400,
        "response_format": {"type": "json_object"}
    }
    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=REFINE_TIMEOUT_S) as s:
            r = await s.post(url, json=payload,
                             headers={"Content-Type": "application/json"})
            if r.status_code != 200:
                log.warning("reflect: backend %s in %.1fs: %s", r.status_code, time.time() - t0, r.text[:200])
                return None
            body = r.json()
    except (httpx.HTTPError, asyncio.TimeoutError) as e:
        log.warning("reflect: timeout/http after %.1fs: %s",
                    time.time() - t0, e)
        return None
    except Exception as e:
        log.warning("reflect unexpected error: %s", e)
        return None
    elapsed = time.time() - t0
    # /api/chat shape {"message":{"content"}}; /v1 choices[] fallback.
    msg = body.get("message")
    if not isinstance(msg, dict):
        choices = body.get("choices") or []
        msg = (choices[0].get("message") if choices else {}) or {}
    content = (msg.get("content") or "").strip()
    if not content:
        log.warning("reflect: %.1fs empty_content", elapsed)
        return None
    content = re.sub(r"<think>.*?</think>\s*", "", content,
                     flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r"^\s*```(?:json)?\s*\n?", "", content)
    content = re.sub(r"\n?```\s*$", "", content)
    try:
        parsed = _loads_lenient(content)
    except json.JSONDecodeError as e:
        log.warning("reflect: %.1fs parse_fail: %s preview=%r",
                    elapsed, e, content[:200])
        return None
    if not isinstance(parsed, dict):
        return None
    new_tool = str(parsed.get("tool") or "").strip()
    if not new_tool:
        log.info("reflect: %.1fs marked unfixable", elapsed)
        _emit_session_event({
            "source": "mios-agent-pipe",
            "kind": "reflect_unfixable",
            "severity": "warn",
            "summary": f"reflection declined: {failed_tool}",
            "payload": {
                "failed_node": failed_node,
                "failed_result_preview": error_preview,
                "rationale": parsed.get("rationale", "")[:200],
                "elapsed_s": round(elapsed, 1),
            },
        }, session_id)
        return None
    log.info("reflect: %.1fs corrected tool=%s -> %s",
             elapsed, failed_tool, new_tool)
    _emit_session_event({
        "source": "mios-agent-pipe",
        "kind": "reflect_corrected",
        "severity": "info",
        "summary": f"{failed_tool} -> {new_tool}",
        "payload": {
            "failed_node": failed_node,
            "failed_result_preview": error_preview,
            "corrected": parsed,
            "elapsed_s": round(elapsed, 1),
        },
    }, session_id)
    return parsed


# ── Reflexion-buffer reads + per-node Definition-of-Done judge ─────────────
# Moved verbatim from server.py (strangler-fig wave). _recent_satisfaction_verdicts
# + _recent_tool_history are the reflexion-buffer reads polish grounds on -- they
# pull the cross-turn user_query_(un)satisfied verdict events and this session's
# tool_call rows; _judge_answer_satisfied is the micro-LLM per-node DoD judge that
# drives the swarm deepen loop. All three read only deps already injected above
# (_db_read + the REFINE_* model-call constants + httpx), so configure() is
# unchanged. server.py re-imports the three names under their exact original aliases
# so the importable surface stays byte-identical.
async def _recent_satisfaction_verdicts(limit: int = 3) -> list[dict]:
    """Pull recent mios-daemon satisfaction verdicts (Phase E.1).
    These are post-hoc audit rows the daemon emits every ~30s based
    on AND-folding tool_call outcomes against refine intent. Polish
    uses them to ground the response in CROSS-TURN truth -- if the
    operator's previous query was flagged unsatisfied, the next
    response shouldn't paraphrase it as having worked."""
    sql = (
        "SELECT ts, kind, summary, payload FROM event "
        "WHERE kind = 'user_query_satisfied' "
        "   OR kind = 'user_query_unsatisfied' "
        "ORDER BY ts DESC LIMIT " + str(int(limit)) + ";"
    )
    r = await _db_read(sql, pg_sql=(
        "SELECT ts, kind, summary, payload FROM event "
        "WHERE kind = 'user_query_satisfied' OR kind = 'user_query_unsatisfied' "
        "ORDER BY ts DESC LIMIT %(lim)s"), pg_params={"lim": int(limit)})
    if not r:
        return []
    rows = (r[-1] or {}).get("result") or []
    return rows if isinstance(rows, list) else []


async def _recent_tool_history(session_id: Optional[str],
                               limit: int = 6) -> list[dict]:
    """Pull the most recent tool_call rows for this session so polish
    has ground-truth on what actually happened. Returns oldest-first
    so the prompt reads chronologically."""
    if not session_id:
        return []
    sql = (
        f"SELECT ts, tool, args, success, "
        f"result_preview, exit_code "
        f"FROM tool_call WHERE session = {session_id} "
        f"ORDER BY ts DESC LIMIT {int(limit)};"
    )
    r = await _db_read(sql, pg_sql=(
        "SELECT ts, tool, args, success, result_preview, exit_code "
        "FROM tool_call WHERE session_id = %(sid)s "
        "ORDER BY ts DESC LIMIT %(lim)s"), pg_params={"sid": session_id, "lim": int(limit)})
    if not r:
        return []
    rows = (r[-1] or {}).get("result") or []
    # Reverse for chronological order in the prompt.
    return list(reversed(rows))


async def _judge_answer_satisfied(query: str, answer: str) -> bool:
    """Micro-LLM Definition-of-Done: does `answer` substantively satisfy
    `query` (concrete specifics, NOT a punt)? Drives the swarm deepen loop
    ("all loop until satisfied",). Degrades to True on any
    error so a judge hiccup never makes a node loop forever."""
    if not answer or not answer.strip():
        return False
    try:
        examples = JUDGE_EXAMPLES or "a punt, refusal, 'I cannot', or 'where to look'"
        payload = {
            "model": REFINE_MODEL,
            "messages": [
                {"role": "system", "content":
                 "Reply ONLY 'yes' or 'no'. Does the ANSWER substantively "
                 f"satisfy the QUERY with concrete specifics -- NOT {examples}?"},
                {"role": "user", "content":
                 f"QUERY: {query[:400]}\n\nANSWER:\n{answer[:2000]} /no_think"}],
            "temperature": 0.0, "max_tokens": 8, "stream": False}
        async with httpx.AsyncClient(timeout=REFINE_TIMEOUT_S) as s:
            r = await s.post(f"{REFINE_ENDPOINT}/v1/chat/completions", json=payload,
                             headers={"Content-Type": "application/json"})
            if r.status_code != 200:
                return True
            _jm = ((r.json().get("choices") or [{}])[0]).get("message") or {}
            c = (_jm.get("content") or _jm.get("reasoning_content") or "").strip().lower()
            return not c.startswith("n")
    except Exception:  # noqa: BLE001
        return True
