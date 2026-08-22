# AI-hint: Reflection / self-assessment cluster extracted verbatim from server.py (strangler-fig wave).
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_lib_mios_agent_pipe_mios_pipe_routing_reflect_py.md
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
from mios_pipe.routing import consensus as _consensus
from mios_hitlflow import _recent_reflections


log = logging.getLogger("mios-agent-pipe")

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
CONSENSUS_ENABLED = False
CONSENSUS_LANES: list = []
CONSENSUS_THRESHOLD = 0.5
CONSENSUS_MIN_LANES = 2
CONSENSUS_TIMEOUT_S = 20.0
CONSENSUS_WEIGHT_FLOOR = 0.1
_consensus_reliability = None


def configure(*, db_read=None, db_write=None, emit_session_event=None,
              verb_catalog=None, refine_enabled=None, refine_model=None,
              refine_endpoint=None, refine_timeout_s=None,
              reflect_system=None, judge_examples=None,
              consensus_enabled=None, consensus_lanes=None,
              consensus_threshold=None, consensus_min_lanes=None,
              consensus_timeout_s=None, consensus_weight_floor=None,
              consensus_reliability=None) -> None:
    """Inject the server.py symbols the reflection helpers read. Each arg keeps its
    original server name as a module global; None means 'leave as-is' so a partial
    re-inject is safe."""
    global _db_read, _db_write, _emit_session_event, _VERB_CATALOG
    global REFINE_ENABLED, REFINE_MODEL, REFINE_ENDPOINT, REFINE_TIMEOUT_S
    global _REFLECT_SYSTEM, JUDGE_EXAMPLES
    global CONSENSUS_ENABLED, CONSENSUS_LANES, CONSENSUS_THRESHOLD
    global CONSENSUS_MIN_LANES, CONSENSUS_TIMEOUT_S, CONSENSUS_WEIGHT_FLOOR
    global _consensus_reliability
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
    if consensus_enabled is not None:
        CONSENSUS_ENABLED = consensus_enabled
    if consensus_lanes is not None:
        CONSENSUS_LANES = list(consensus_lanes)
    if consensus_threshold is not None:
        CONSENSUS_THRESHOLD = consensus_threshold
    if consensus_min_lanes is not None:
        CONSENSUS_MIN_LANES = consensus_min_lanes
    if consensus_timeout_s is not None:
        CONSENSUS_TIMEOUT_S = consensus_timeout_s
    if consensus_weight_floor is not None:
        CONSENSUS_WEIGHT_FLOOR = consensus_weight_floor
    if consensus_reliability is not None:
        _consensus_reliability = consensus_reliability


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
    if not rows:
        if intent == "chat":
            verdict = {
                "kind": "user_query_satisfied",
                "reason": "chat_no_tools_expected",
            }
        elif agent_answered:
            verdict = {
                "kind": "user_query_satisfied",
                "reason": "agent_answer_delivered",
                "agent_tools": [str(t) for t in (agent_tools_called or [])],
            }
        else:
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
    return list(reversed(rows))


async def _judge_lane_vote(query: str, answer: str, *, endpoint: str = "",
                           model: str = "", timeout_s: float = 0.0):
    """Ask ONE judge lane the DoD question: True / False / None (abstain --
    transport error, non-200, unparseable). Abstain is NOT a "no"; see ch52."""
    ep = (endpoint or REFINE_ENDPOINT or "").rstrip("/")
    if not ep:
        return None
    examples = JUDGE_EXAMPLES or "a punt, refusal, 'I cannot', or 'where to look'"
    payload = {
        "model": model or REFINE_MODEL,
        "messages": [
            {"role": "system", "content":
             "Reply ONLY 'yes' or 'no'. Does the ANSWER substantively "
             f"satisfy the QUERY with concrete specifics -- NOT {examples}?"},
            {"role": "user", "content":
             f"QUERY: {query[:400]}\n\nANSWER:\n{answer[:2000]} /no_think"}],
        "temperature": 0.0, "max_tokens": 8, "stream": False}
    try:
        async with httpx.AsyncClient(timeout=timeout_s or REFINE_TIMEOUT_S) as s:
            r = await s.post(f"{ep}/v1/chat/completions", json=payload,
                             headers={"Content-Type": "application/json"})
            if r.status_code != 200:
                return None
            _jm = ((r.json().get("choices") or [{}])[0]).get("message") or {}
            c = (_jm.get("content") or _jm.get("reasoning_content") or "").strip().lower()
            if not c:
                return None
            return not c.startswith("n")
    except Exception:  # noqa: BLE001
        return None


async def _judge_panel_verdict(query: str, answer: str):
    """CONS-01 panel: poll every lane concurrently, fold by weight. None when
    off, under-configured or short of quorum -- caller keeps single-lane."""
    if not CONSENSUS_ENABLED:
        return None
    lanes = [d for d in (CONSENSUS_LANES or []) if isinstance(d, dict)]
    if len(lanes) < max(2, int(CONSENSUS_MIN_LANES)):
        return None
    names = []
    tasks = []
    for idx, lane in enumerate(lanes):
        name = str(lane.get("name") or f"lane{idx}")
        names.append(name)
        tasks.append(_judge_lane_vote(
            query, answer,
            endpoint=str(lane.get("endpoint") or ""),
            model=str(lane.get("model") or ""),
            timeout_s=float(CONSENSUS_TIMEOUT_S or 0.0)))
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
    except Exception:  # noqa: BLE001
        return None
    verdicts = {}
    for name, res in zip(names, results):
        verdicts[name] = None if isinstance(res, BaseException) else res
    # Declared per-lane weight first; a reliability scorer, when one is wired,
    # overrides it. Neither is required -- absent both, the panel is uniform.
    declared = {}
    for idx, lane in enumerate(lanes):
        w = lane.get("weight")
        if w is not None:
            declared[names[idx]] = w
    reliability = declared
    if callable(_consensus_reliability):
        try:
            scored = _consensus_reliability(names) or {}
            if isinstance(scored, dict):
                reliability = {**declared, **scored}
        except Exception:  # noqa: BLE001
            pass
    weights = _consensus.resolve_weights(
        names, reliability, floor=float(CONSENSUS_WEIGHT_FLOOR))
    fold = _consensus.weighted_vote(
        verdicts, weights,
        threshold=float(CONSENSUS_THRESHOLD),
        min_lanes=int(CONSENSUS_MIN_LANES))
    if fold.get("decision") is None:
        log.debug("consensus: no quorum (%s live) -- falling back to single judge",
                  fold.get("live"))
        return None
    log.debug("consensus: decision=%s score=%.3f agreement=%.3f over %d lanes",
              fold["decision"], fold["score"], fold["agreement"], fold["live"])
    return bool(fold["decision"])


async def _judge_answer_satisfied(query: str, answer: str) -> bool:
    """Micro-LLM Definition-of-Done: does `answer` substantively satisfy
    `query` (concrete specifics, NOT a punt)? Drives the swarm deepen loop
    ("all loop until satisfied",). Degrades to True on any
    error so a judge hiccup never makes a node loop forever. With
    `[consensus].enable` on, a weighted quorum decides instead -- see ch52."""
    if not answer or not answer.strip():
        return False
    try:
        panel = await _judge_panel_verdict(query, answer)
        if panel is not None:
            return panel
    except Exception:  # noqa: BLE001
        pass
    vote = await _judge_lane_vote(query, answer)
    return True if vote is None else vote
