# AI-hint: DAG EXECUTION entrypoints extracted VERBATIM from server.py (refactor R8 wave). The planned-DAG execution brain: _execute_dag_node (run ONE node -- an agent delegation OR a tool verb -- with ReWOO #E ref resolution, action-hash dedup, A2A peer delegation, lane-aware token/deadline sizing, worker-tool surface + RBAC, retry/reflexion), _deepen_until_barrier (fast-lane work-steal coverage passes until the global barrier), _execute_dag_saturated (continuous ready-queue executor, SWARM_SATURATE), execute_dag (level-barrier path + saturate dispatch), _execute_dag_bounded (non-streaming TURN_DEADLINE backstop + client-disconnect cancel) and _execute_dag_emitting (streaming per-node endpoint emitters + live agent reasoning). Plus _record_dag_node_row (session-linked tool_call taint row) and the WS-6 run-template capture (RUN_TEMPLATE_ENABLE, _run_template_class, _capture_run_template). Moved byte-identically -- NO consolidation of the four execute_dag entrypoints (a separate future task). Every server-side dep (config scalars, _AGENT_REGISTRY, the ContextVars, dispatch_mios_verb, the agent-call/scratchpad/grounding/db/a2a/worker-tool helpers) is dependency-INJECTED via configure() (one-way boundary -- this module NEVER imports server). _call_agent_complete/_web_research_enrich/_dag_levels/the SSE node emitters/_env_grounding/_action_hash/the RBAC filters are imported directly from their sibling modules. server.py re-imports every moved name under its original alias (surface-parity zero-diff).
# AI-related: ./server.py, ./mios_config.py, ./mios_agent_call.py, ./mios_web_research.py, ./mios_planner.py, ./mios_sse.py, ./mios_grounding.py, ./mios_hitlflow.py, ./mios_policy.py, ./test_mios_dag_exec.py
# AI-functions: _deepen_until_barrier, _execute_dag_node, _record_dag_node_row, _execute_dag_saturated, _run_template_class, _capture_run_template, execute_dag, _execute_dag_bounded, _execute_dag_emitting, configure
"""DAG execution entrypoints (refactor R8).

Extracted VERBATIM from ``server.py`` -- the planned-DAG execution brain that
runs a topological DAG of agent/verb nodes with retry, grounding, work-steal
deepen and live per-node emit. The five execute_dag entrypoints
(``_execute_dag_node``, ``_execute_dag_saturated``, ``execute_dag``,
``_execute_dag_bounded``, ``_execute_dag_emitting``) are moved byte-identically;
their later consolidation is a SEPARATE task. ``server.py`` re-imports every name
under its original alias so the module's public surface is byte-identical.

Sibling functions (``_call_agent_complete``, ``_web_research_enrich``,
``_dag_levels``, the SSE node emitters, ``_env_grounding``, ``_action_hash``, the
RBAC filters, ``_toml_section``) are imported directly; every other server-side
symbol they touch (the config scalars, ``_AGENT_REGISTRY``, the ContextVars, the
broker ``dispatch_mios_verb``, the agent-call/scratchpad/db/a2a/worker-tool
helpers) is injected via :func:`configure` (one-way boundary -- this module never
imports ``server``).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from typing import Optional

import httpx

import mios_tokenize
from mios_config import _toml_section
from mios_agent_call import _call_agent_complete
from mios_web_research import _web_research_enrich
from mios_planner import _dag_levels
from mios_sse import _sse_reasoning, _node_status, _node_context
from mios_grounding import _env_grounding
from mios_hitlflow import _action_hash
from mios_jsonsalvage import loads_lenient as _loads_lenient
from mios_policy import _agent_rbac_filter, _user_rbac_filter

log = logging.getLogger("mios-agent-pipe")


# -- Dependency-injection seam --------------------------------------
# The DAG executors read server.py's config scalars, the live agent registry,
# the KV-fork / conv-key ContextVars and the per-chat supersede map, and call
# back into the broker dispatch + agent-call + scratchpad + grounding + db +
# a2a + worker-tool helpers. server.py calls configure() with those AFTER every
# one is defined (one-way boundary: this module never imports server). The
# placeholders below carry the documented defaults so a standalone
# ``import mios_dag_exec`` still succeeds; every consumer is async/runtime so
# nothing fires before configure() runs.

# config scalars (server SSOT/env-derived; injected at import-completion)
DEEPEN_FETCH = False
DEEPEN_DEADLINE_S = 45.0
DEEPEN_MAX_ITERS = 12
DEEPEN_WEB_TIMEOUT_S = 20.0
# A8 early-exit-on-satisfied (default OFF): when on, the deepen loop asks the per-node
# Definition-of-Done judge whether the node's current answer already satisfies its
# sub-query and STOPS deepening if so -- the heaviest compute is not spent re-answering
# an already-good node, and the freed lane lets slower nodes finish sooner. Default off
# == no behaviour change (degrade-open: with no judge wired the loop runs to its bound).
# DEEPEN_JUDGE_TIMEOUT_S bounds the (micro-LLM) judge so a hung judge can't stall a pass.
DEEPEN_EARLY_EXIT = False
DEEPEN_JUDGE_TIMEOUT_S = 6.0
DAG_NODE_MAX_TOKENS = 800
DAG_NODE_SLOW_MAX_TOKENS = 400
DAG_NODE_RETRY = 1
DAG_NODE_DEADLINE_S = 75.0
DAG_NODE_DEADLINE_SLOW_S = 150.0
SLOW_LANES: set = set()
KV_FORK_ENABLE = False
WORKER_TOOLS_ENABLE = False
WORKER_TOOL_CTX = 16384
WORKER_TOOL_CTX_SLOW = 6144
PLANNER_REFLEXION_CAP = 2
SWARM_SATURATE = False
REQUEST_CANCEL_ENABLE = True
REQUEST_CANCEL_POLL_S = 1.0
TURN_DEADLINE_S = 600.0
_PG_PRIMARY = False
# context-fit (num_ctx sizing) scalars read by _fit_context (moved home).
CTX_FIT = False
WORKER_TOOL_CTX_MAX = 24576
# fast/deepen lane set read by _node_deepens (moved home).
DEEPEN_LANES: set = set()
# CPU-lane runaway reaper scalars read by _reap_cpu_lane (moved home).
RUNAWAY_REAP_ENABLE = False
_LIGHT_LANE = ""

# mutable refs (injected BY REFERENCE -- server assigns each and the shared
# object stays live; _AGENT_REGISTRY is rebound on membership reload, so server
# re-injects it there).
_AGENT_REGISTRY: dict = {}
_CHAT_CANCEL: dict = {}
_kv_fork_parent_var = None
_conv_key_var = None

# server-side helpers (injected)
dispatch_mios_verb = None
_call_agent_stream = None
reflect_on_step_failure = None
# A8: the micro-LLM per-node Definition-of-Done judge (mios_reflect._judge_answer_satisfied),
# injected so mios_dag_exec never imports server. None until injected -> the deepen
# early-exit gate stays inert (degrade-open) even when DEEPEN_EARLY_EXIT is on.
_judge_answer_satisfied = None
_sanitize_tool_text = None
_scratchpad_note = None
_scratchpad_render = None
_agent_contract = None
_role_system = None
_agent_lane = None
_worker_tools_surface_async = None
_lane_tool_cap = None
_a2a_send_message_to_peer = None
_a2a_extract_text = None
_get_client = None
_db_fire = None
_db_post = None
_db_create = None
_db_read = None
_pg_mirror = None


def configure(*, deepen_fetch=None, deepen_deadline_s=None, deepen_max_iters=None,
              deepen_web_timeout_s=None, deepen_early_exit=None,
              deepen_judge_timeout_s=None, judge_answer_satisfied=None,
              dag_node_max_tokens=None,
              dag_node_slow_max_tokens=None, dag_node_retry=None,
              dag_node_deadline_s=None, dag_node_deadline_slow_s=None,
              slow_lanes=None, kv_fork_enable=None, worker_tools_enable=None,
              worker_tool_ctx=None, worker_tool_ctx_slow=None,
              planner_reflexion_cap=None, swarm_saturate=None,
              request_cancel_enable=None, request_cancel_poll_s=None,
              turn_deadline_s=None, pg_primary=None,
              ctx_fit=None, worker_tool_ctx_max=None, deepen_lanes=None,
              runaway_reap_enable=None, light_lane=None,
              agent_registry=None, chat_cancel=None, kv_fork_parent_var=None,
              conv_key_var=None,
              dispatch_mios_verb=None, call_agent_stream=None,
              reflect_on_step_failure=None,
              sanitize_tool_text=None, scratchpad_note=None,
              scratchpad_render=None, agent_contract=None, role_system=None,
              agent_lane=None, worker_tools_surface_async=None, lane_tool_cap=None,
              a2a_send_message_to_peer=None,
              a2a_extract_text=None, get_client=None,
              db_fire=None, db_post=None, db_create=None,
              db_read=None,
              pg_mirror=None) -> None:
    """Inject server.py's config scalars, the live registry / ContextVars and
    the runtime helpers the DAG executors call back into."""
    global DEEPEN_FETCH, DEEPEN_DEADLINE_S, DEEPEN_MAX_ITERS, DEEPEN_WEB_TIMEOUT_S
    global DEEPEN_EARLY_EXIT, DEEPEN_JUDGE_TIMEOUT_S, _judge_answer_satisfied
    global DAG_NODE_MAX_TOKENS, DAG_NODE_SLOW_MAX_TOKENS, DAG_NODE_RETRY
    global DAG_NODE_DEADLINE_S, DAG_NODE_DEADLINE_SLOW_S, SLOW_LANES
    global KV_FORK_ENABLE, WORKER_TOOLS_ENABLE, WORKER_TOOL_CTX, WORKER_TOOL_CTX_SLOW
    global PLANNER_REFLEXION_CAP, SWARM_SATURATE
    global REQUEST_CANCEL_ENABLE, REQUEST_CANCEL_POLL_S, TURN_DEADLINE_S, _PG_PRIMARY
    global CTX_FIT, WORKER_TOOL_CTX_MAX, DEEPEN_LANES, RUNAWAY_REAP_ENABLE, _LIGHT_LANE
    global _AGENT_REGISTRY, _CHAT_CANCEL, _kv_fork_parent_var, _conv_key_var
    global _call_agent_stream
    global _sanitize_tool_text, _scratchpad_note, _scratchpad_render
    global _agent_contract, _role_system, _agent_lane
    global _worker_tools_surface_async, _lane_tool_cap
    global _a2a_send_message_to_peer, _a2a_extract_text
    global _get_client, _db_fire, _db_post, _db_create, _pg_mirror, _db_read
    if db_read is not None:
        _db_read = db_read
    if deepen_fetch is not None:
        DEEPEN_FETCH = deepen_fetch
    if deepen_deadline_s is not None:
        DEEPEN_DEADLINE_S = deepen_deadline_s
    if deepen_max_iters is not None:
        DEEPEN_MAX_ITERS = deepen_max_iters
    if deepen_web_timeout_s is not None:
        DEEPEN_WEB_TIMEOUT_S = deepen_web_timeout_s
    if deepen_early_exit is not None:
        DEEPEN_EARLY_EXIT = deepen_early_exit
    if deepen_judge_timeout_s is not None:
        DEEPEN_JUDGE_TIMEOUT_S = deepen_judge_timeout_s
    if judge_answer_satisfied is not None:
        _judge_answer_satisfied = judge_answer_satisfied
    if dag_node_max_tokens is not None:
        DAG_NODE_MAX_TOKENS = dag_node_max_tokens
    if dag_node_slow_max_tokens is not None:
        DAG_NODE_SLOW_MAX_TOKENS = dag_node_slow_max_tokens
    if dag_node_retry is not None:
        DAG_NODE_RETRY = dag_node_retry
    if dag_node_deadline_s is not None:
        DAG_NODE_DEADLINE_S = dag_node_deadline_s
    if dag_node_deadline_slow_s is not None:
        DAG_NODE_DEADLINE_SLOW_S = dag_node_deadline_slow_s
    if slow_lanes is not None:
        SLOW_LANES = slow_lanes
    if kv_fork_enable is not None:
        KV_FORK_ENABLE = kv_fork_enable
    if worker_tools_enable is not None:
        WORKER_TOOLS_ENABLE = worker_tools_enable
    if worker_tool_ctx is not None:
        WORKER_TOOL_CTX = worker_tool_ctx
    if worker_tool_ctx_slow is not None:
        WORKER_TOOL_CTX_SLOW = worker_tool_ctx_slow
    if planner_reflexion_cap is not None:
        PLANNER_REFLEXION_CAP = planner_reflexion_cap
    if swarm_saturate is not None:
        SWARM_SATURATE = swarm_saturate
    if request_cancel_enable is not None:
        REQUEST_CANCEL_ENABLE = request_cancel_enable
    if request_cancel_poll_s is not None:
        REQUEST_CANCEL_POLL_S = request_cancel_poll_s
    if turn_deadline_s is not None:
        TURN_DEADLINE_S = turn_deadline_s
    if pg_primary is not None:
        _PG_PRIMARY = pg_primary
    if ctx_fit is not None:
        CTX_FIT = ctx_fit
    if worker_tool_ctx_max is not None:
        WORKER_TOOL_CTX_MAX = worker_tool_ctx_max
    if deepen_lanes is not None:
        DEEPEN_LANES = deepen_lanes
    if runaway_reap_enable is not None:
        RUNAWAY_REAP_ENABLE = runaway_reap_enable
    if light_lane is not None:
        _LIGHT_LANE = light_lane
    if agent_registry is not None:
        _AGENT_REGISTRY = agent_registry
    if chat_cancel is not None:
        _CHAT_CANCEL = chat_cancel
    if kv_fork_parent_var is not None:
        _kv_fork_parent_var = kv_fork_parent_var
    if conv_key_var is not None:
        _conv_key_var = conv_key_var
    if dispatch_mios_verb is not None:
        globals()["dispatch_mios_verb"] = dispatch_mios_verb
    if call_agent_stream is not None:
        _call_agent_stream = call_agent_stream
    if reflect_on_step_failure is not None:
        globals()["reflect_on_step_failure"] = reflect_on_step_failure
    if sanitize_tool_text is not None:
        _sanitize_tool_text = sanitize_tool_text
    if scratchpad_note is not None:
        _scratchpad_note = scratchpad_note
    if scratchpad_render is not None:
        _scratchpad_render = scratchpad_render
    if agent_contract is not None:
        _agent_contract = agent_contract
    if role_system is not None:
        _role_system = role_system
    if agent_lane is not None:
        _agent_lane = agent_lane
    if worker_tools_surface_async is not None:
        _worker_tools_surface_async = worker_tools_surface_async
    if lane_tool_cap is not None:
        _lane_tool_cap = lane_tool_cap
    if a2a_send_message_to_peer is not None:
        _a2a_send_message_to_peer = a2a_send_message_to_peer
    if a2a_extract_text is not None:
        _a2a_extract_text = a2a_extract_text
    if get_client is not None:
        _get_client = get_client
    if db_fire is not None:
        _db_fire = db_fire
    if db_post is not None:
        _db_post = db_post
    if db_create is not None:
        _db_create = db_create
    if pg_mirror is not None:
        _pg_mirror = pg_mirror


async def _deepen_until_barrier(node: dict, res: dict, barrier: "asyncio.Event",
                                session_id: Optional[str], client) -> dict:
    """A fast swarm node that finished its primary BEFORE the global barrier (i.e.
    it computed faster than its peers) keeps producing ADDITIONAL, DISTINCT
    coverage -- new angles / items / facets -- until the barrier fires (every
    node's primary done): it does NOT idle. The intent is "wait for ALL nodes to
    complete; the faster lanes just do another pass from ANOTHER facet -- everything
    concurrent, every source every turn". The slowest node trips the barrier and
    never enters here.

    EARLY-EXIT (A8, SSOT [dispatch].deepen_early_exit, default OFF): when enabled,
    each pass first asks the per-node Definition-of-Done judge whether the node's
    CURRENT answer already satisfies its sub-query; if so the node STOPS deepening so
    the heaviest compute is not spent re-answering an already-good node and the freed
    lane lets slower nodes finish sooner. Default off -> runs to the bound (no
    behaviour change). Degrade-open: the judge is bounded by DEEPEN_JUDGE_TIMEOUT_S
    and ANY timeout / error / absent judge falls THROUGH to the deadline-bound loop
    -- it can only ever STOP early on a clean 'satisfied', never under-compute.

 DETAIL-FILL ("also can loop to gather data in detail-fill
    passes"): when DEEPEN_FETCH is on AND the node carries a web-capable refined
    plan (a web/news turn), each pass FIRST fetches MORE web data on the facet
    (bounded by DEEPEN_WEB_TIMEOUT_S; the fan-out diversifies sub-queries so each
    pass surfaces fresh stories) and APPENDS the new stories to the shared
    grounding -- so the loop ENRICHES the facts, not just re-reasons them. The
    enriched grounding flows to the final synthesis. A non-web turn (no refined /
    no web hint) just reasons over the grounding in hand (no contention).
    Hard-bounded by DEEPEN_MAX_ITERS + DEEPEN_DEADLINE_S + the barrier."""
    aname = str(node.get("agent") or "")
    acfg = _AGENT_REGISTRY.get(aname) or {}
    base_q = str(node.get("_base_query") or node.get("title")
                 or node.get("prompt") or "")[:200]
    grounding = str(node.get("_grounding") or "")
    _refined = node.get("_refined") if isinstance(node.get("_refined"), dict) else None
    _fetch = bool(DEEPEN_FETCH and _refined and base_q)
    out = (res.get("output") or "").strip()
    iters = 0
    fetched = 0
    _deadline = time.monotonic() + DEEPEN_DEADLINE_S
    # Expand COVERAGE until the BARRIER (all nodes' primaries done). A fast node
    # keeps adding NEW facets/angles while slower nodes finish; detail-fill fetches
    # new stories per pass (when enabled) and APPENDS only genuinely new content.
    # When DEEPEN_EARLY_EXIT is enabled the loop ALSO stops once the DoD judge marks
    # the node satisfied (checked at the top of each pass, below).
    while (iters < DEEPEN_MAX_ITERS and time.monotonic() < _deadline
           and not barrier.is_set()):
        # A8 EARLY-EXIT: before spending another (heaviest) pass, ask the per-node
        # DoD judge whether the answer in hand already satisfies the sub-query; if so,
        # stop -- so an already-good node frees its lane instead of re-answering.
        # Bounded by DEEPEN_JUDGE_TIMEOUT_S; degrade-open -> any timeout/error/absent
        # judge falls through and the deadline-bound loop continues (never
        # under-computes). The judge returning truthy is the ONLY way out here; the
        # loop stays hard-bounded by the barrier + deadline + iter cap regardless.
        if (DEEPEN_EARLY_EXIT and _judge_answer_satisfied is not None
                and base_q and out.strip()):
            _jbudget = _deadline - time.monotonic()
            if _jbudget > 0:
                try:
                    if await asyncio.wait_for(
                            _judge_answer_satisfied(base_q, out),
                            timeout=max(1.0, min(_jbudget, DEEPEN_JUDGE_TIMEOUT_S))):
                        log.info("deepen: %s satisfied -> early exit after %d pass(es)",
                                 aname, iters)
                        break
                except Exception:  # noqa: BLE001 -- judge hiccup -> deadline-bound loop
                    pass
        iters += 1
        _budget = _deadline - time.monotonic()
        if _budget <= 0:
            break
        # DETAIL-FILL: gather NEW data this pass (bounded). The fan-out's diverse
        # sub-queries + article drill surface fresh stories on repeated calls; the
        # new content is appended to grounding (deduped by prefix) for this pass +
        # the final synthesis.
        if _fetch and not barrier.is_set():
            try:
                _new = await asyncio.wait_for(
                    _web_research_enrich(base_q, _refined, quick=True),
                    timeout=max(1.0, min(_budget, DEEPEN_WEB_TIMEOUT_S)))
            except Exception:  # noqa: BLE001
                _new = ""
            if _new and _new[:160] not in grounding:
                grounding = (grounding + "\n\n" + _new).strip()[:24000]
                fetched += 1
            _budget = _deadline - time.monotonic()
            if _budget <= 0 or barrier.is_set():
                break
        _msgs = [{"role": "user", "content":
                  "Task: " + base_q + "\n\nExpand COVERAGE: provide ADDITIONAL, "
                  "DISTINCT, specific points -- new angles / items / facets -- "
                  "that are NOT already listed below. Ground them in the research; "
                  "be concrete; do NOT repeat anything already covered and do NOT "
                  "punt. If there is genuinely nothing new to add, reply with a "
                  "single blank line.\n\nAlready covered:\n" + (out or "(none)")[:5000]
                  + (("\n\nResearch:\n" + grounding[:5000]) if grounding else "")}]
        body = {"model": acfg.get("model") or aname, "messages": _msgs,
                "max_tokens": DAG_NODE_MAX_TOKENS}
        try:
            # Cap the call by the REMAINING budget so a slow/stuck generation can't
            # overshoot (the `while` only gates STARTING an iter). Floor 1s.
            _, ans = await asyncio.wait_for(
                _call_agent_complete(
                    aname, acfg, body, {"Content-Type": "application/json"},
                    client, prefer_cpu=False),
                timeout=max(1.0, _budget))
            ans = (ans or "").strip()
            # Append only NEW content (skip an empty / near-duplicate pass).
            if ans and ans[:120].lower() not in out.lower():
                out = (out + "\n\n" + ans).strip()
        except Exception:  # noqa: BLE001  (incl. asyncio.TimeoutError)
            pass
    if iters:
        log.info("deepen: %s did %d coverage pass(es) (+%d detail-fill fetch) "
                 "until barrier", aname, iters, fetched)
        res = dict(res)
        res["output"] = out
        res["deepened"] = iters
        res["fetched"] = fetched
        res["success"] = bool(out)
        node["_grounding"] = grounding   # ENRICHED grounding -> final synthesis
    return res


async def _execute_dag_node(node: dict, results_by_id: dict,
                            seen_actions: dict, dag_summary: str,
                            session_id: Optional[str], client,
                            frag_q: "Optional[asyncio.Queue]" = None) -> dict:
    nid = str(node.get("id", "?"))
    tool = str(node.get("tool", "")).strip()
    aname = str(node.get("agent", ""))
    agent_label = f"agent:{aname}" if aname else f"tool:{tool}"
    task_desc = str(node.get("prompt") or tool)

    # 1. Log Progress Ledger assignment
    if session_id and _db_create and _db_fire and _db_post:
        try:
            sql = _db_create("progress_ledger", {
                "session_id": session_id,
                "agent": agent_label,
                "task": task_desc,
                "state": "assigned"
            }, now_fields=("assigned_at",))
            _db_fire(_db_post(sql))
        except Exception as _pl_err:
            log.warning("Failed to log progress_ledger assignment: %s", _pl_err)

    # 2. Check if this is a research vs action node
    is_research = bool(node.get("web") or node.get("news"))
    is_action = bool(node.get("local_state") or not is_research)

    # 3. Derive action node input from Fact Ledger
    if is_action and session_id and _db_read:
        try:
            fact_sql = f"SELECT claim, source FROM fact_ledger WHERE session_id = '{session_id}'"
            fact_rows = await _db_read(fact_sql, pg_sql=fact_sql)
            if fact_rows:
                fact_lines = []
                for row in fact_rows:
                    claim = row.get("claim")
                    source = row.get("source") or "unknown"
                    fact_lines.append(f"- Claim: {claim} (Source: {source})")
                fact_context = "\n[Grounded Facts from Research]:\n" + "\n".join(fact_lines) + "\n"
                
                # Append to agent node prompt
                if node.get("prompt"):
                    node["prompt"] = str(node.get("prompt")) + "\n" + fact_context
                # Or append to tool node query/args
                if node.get("args"):
                    args = node.get("args")
                    for key in ("prompt", "text", "query"):
                        if key in args and isinstance(args[key], str):
                            args[key] = args[key] + "\n" + fact_context
        except Exception as _fl_err:
            log.warning("Failed to read fact_ledger: %s", _fl_err)

    # 4. Execute the actual node core
    res = await _execute_dag_node_core(node, results_by_id, seen_actions,
                                       dag_summary, session_id, client, frag_q)

    # 5. Log Progress Ledger completion
    success = bool(res.get("success"))
    state_val = "completed" if success else "stalled"
    if session_id and _db_create and _db_fire and _db_post:
        try:
            sql = _db_create("progress_ledger", {
                "session_id": session_id,
                "agent": agent_label,
                "task": task_desc,
                "state": state_val
            }, now_fields=("completed_at",))
            _db_fire(_db_post(sql))
        except Exception as _pl_err:
            log.warning("Failed to log progress_ledger completion: %s", _pl_err)

    # 6. Parse and write claims to Fact Ledger if this is a successful research node
    if is_research and success and session_id and _db_create and _db_fire and _db_post:
        output_txt = str(res.get("output") or "")
        claims = parse_research_claims(output_txt)
        for c in claims:
            try:
                sql = _db_create("fact_ledger", {
                    "session_id": session_id,
                    "claim": c["claim"],
                    "source": c["source"] or "web_search"
                }, now_fields=("ts",))
                _db_fire(_db_post(sql))
            except Exception as _fact_err:
                log.warning("Failed to log fact_ledger: %s", _fact_err)

    return res


def parse_research_claims(output_str: str) -> list[dict]:
    output_str = (output_str or "").strip()
    if not output_str:
        return []
    
    # 1. Try JSON
    import json
    try:
        start_idx = min(output_str.find('['), output_str.find('{'))
        end_idx = max(output_str.rfind(']'), output_str.rfind('}'))
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            json_candidate = output_str[start_idx:end_idx+1]
            data = json.loads(json_candidate)
            claims = []
            if isinstance(data, dict):
                if "claim" in data:
                    claims.append({"claim": data.get("claim"), "source": data.get("source")})
                elif "claims" in data and isinstance(data["claims"], list):
                    for c in data["claims"]:
                        if isinstance(c, dict) and "claim" in c:
                            claims.append({"claim": c.get("claim"), "source": c.get("source")})
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "claim" in item:
                        claims.append({"claim": item.get("claim"), "source": item.get("source")})
            if claims:
                return [c for c in claims if c.get("claim")]
    except Exception:
        pass
    
    # 2. Fallback: Parse plain text lines
    claims = []
    lines = output_str.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if "claim" in line.lower() or "fact" in line.lower() or "source" in line.lower():
            parts = line.split("Source:")
            if len(parts) == 2:
                c = parts[0].replace("Claim:", "").replace("claim:", "").strip()
                s = parts[1].strip()
                claims.append({"claim": c, "source": s})
                continue
        if "[" in line and "]" in line:
            cites = re.findall(r"\[([^\]]+)\]", line)
            if cites:
                clean_claim = re.sub(r"\[[^\]]+\]", "", line).strip()
                claims.append({"claim": clean_claim, "source": ", ".join(cites)})
    
    if not claims:
        for line in lines[:5]:
            if len(line) > 20 and re.search(r"\b\d{3,}\b|http", line):
                claims.append({"claim": line, "source": "web_search"})
                
    return [c for c in claims if c.get("claim")]


async def _execute_dag_node_core(node: dict, results_by_id: dict,
                                 seen_actions: dict, dag_summary: str,
                                 session_id: Optional[str], client,
                                 frag_q: "Optional[asyncio.Queue]" = None) -> dict:
    """Execute ONE DAG node -- an `agent` delegation OR a `tool` verb --
    and return its node_result (standard tool_call shape + node_id + _act).
    READS the shared maps (a snapshot of completed levels) but does NOT
    mutate them; execute_dag merges results after each level so concurrent
    same-level nodes never race on writes. ReWOO #E<id> refs in args (verb)
    or in the prompt (agent) resolve against the completed-level outputs.
    When `frag_q` is supplied (the streaming DAG paths), an agent node STREAMS
    its reasoning LIVE onto that queue as ("SF", name, fragment) events so the
    emitting wrapper renders the agents' actual thinking into the dropdown --
    not just engage/done status pings (operator: 'no thinking blocks')."""
    nid = str(node.get("id", "?"))
    # ---- agent-delegation node: route a sub-task to a named sub-agent ----
    if node.get("agent"):
        aname = str(node.get("agent"))
        acfg = _AGENT_REGISTRY.get(aname) or {}
        prompt = _substitute_ek_refs(
            {"_p": str(node.get("prompt") or "")}, results_by_id).get("_p", "")
        _act = _action_hash(f"agent:{aname}", {"prompt": prompt})
        _prior = seen_actions.get(_act)
        if _prior is not None:
            d = dict(_prior)
            d["node_id"] = nid
            d["repeat_of"] = _prior.get("node_id")
            return d
        # A2A peer delegation (P0): a node/agent flagged with
        # an a2a_peer_id routes to an EXTERNAL agent over A2A instead of a local
        # /v1 endpoint. Same node_result shape as a local agent node.
        _peer = (node.get("a2a_peer_id")
                 or (acfg.get("a2a_peer_id") if isinstance(acfg, dict) else None))
        if _peer:
            _t0 = time.time()
            _env = await _a2a_send_message_to_peer(
                str(_peer), prompt, context_id=session_id)
            _txt = _a2a_extract_text(_env)
            return {
                "success": bool(_txt),
                "output": _txt,
                "latency_ms": int((time.time() - _t0) * 1000),
                "tool": f"agent:{aname}",
                "args": {},
                "node_id": nid,
                "retries": 0,
                "_act": _act,
            }
        t0 = time.time()
        # Inject the rolling scratchpad so this node sees checkpoints from
        # earlier DAG levels (sequential levels -> level N reads level N-1).
        _node_msgs: list = []
        # Universal agent contract FIRST : a swarm/DAG
        # worker was dispatched with NO SOUL, NO tools, NO contract -> it
        # fabricated or lied "I have no internet". Present the overlay .md
        # contract so every worker knows it is a MiOS agent with global tool
        # access + live internet + delegation, and must call tools, not
        # disclaim or invent. Grounding too, so no stale-year fabrication.
        _contract = _agent_contract()
        if _contract:
            _node_msgs.append({"role": "system",
                               "content": _contract + "\n\n" + _env_grounding()})
        _overlay = _role_system(aname)   # thin per-role DEVELOPER overlay (OpenAI pattern)
        if _overlay:
            _node_msgs.append({"role": "system", "content": _overlay})
        _sp_block = _scratchpad_render()
        if _sp_block:
            _node_msgs.append({"role": "system", "content": _sp_block})
        _node_msgs.append({"role": "user", "content": prompt})
        # Lane-aware budget: a SLOW lane (iGPU/phone) gets fewer tokens so it
        # FINISHES + computes instead of timing out empty.
        _lane = _agent_lane(acfg)
        _maxtok = (DAG_NODE_SLOW_MAX_TOKENS if _lane in SLOW_LANES
                   else DAG_NODE_MAX_TOKENS)
        body = {"model": acfg.get("model") or aname,
                "messages": _node_msgs,
                "max_tokens": _maxtok}
        # All tools to every agent : hand this worker the
        # OpenAI verb surface + raise its context so the surface fits + flag
        # write-execution (the agents ACT; the no-launch rule is Claude's alone).
        # The stream/complete paths run the pipe-side tool-loop over body.tools,
        # so the worker CALLS web_search/etc. + acts via the broker instead of
        # fabricating or disclaiming. Self-gating: a worker that needs no tool
        # just answers in one pass (no-op).
        # EVERY agent gets tools ("nothing toolless"); a weak
        # lane (iGPU llama.cpp / mobile) just gets a CAPPED subset it can grammar-
        # constrain in budget (the full 71 timed it out), prioritised read/web first.
        # A node carrying shared grounding (_no_tools, set by _ground_shared on a
        # casual turn) reasons over the injected facts and must NOT re-search --
        # that redundant per-node web_search is what blew the deadline.
        #
        # NODE/ENDPOINT-AWARE SIZING ("LOCAL CPU IS NEEDED...
        # planning isn't taking into account the nodes and endpoints it's being
        # deployed to"): a SLOW lane (CPU/iGPU/phone) was handed the SAME dGPU-sized
        # workload -- full 71-tool surface (cpu cap was 0) + 16K ctx + its own
        # web tool-loop -- which it can't run in the node deadline, so local-cpu was
        # ALWAYS abandoned. Now the work is sized to the hardware:
        #   * a slow lane that already HAS grounding (the fast lanes fetched it this
        #     turn via _ground_facets/_ground_shared) REASONS over those facts -- no
        #     heavy own tool-loop, no 16K prefill -> its ONE pass finishes + counts.
        #   * a slow lane WITHOUT grounding still gets a REAL but CAPPED tool surface
        #     (_lane_tool_cap now floors cpu at SLOW_LANE_TOOL_CAP) on the SMALLER
        #     WORKER_TOOL_CTX_SLOW window so its tool-loop fits the budget.
        #   * a fast lane (dGPU/accelerator) is unchanged: full surface + full ctx +
        #     work-steal deepen.
        # WS-A4: mark this fan-out node so its dispatch FORKS the turn's parent KV
        # (RadixAttention-style shared-prefix warm start). Inert unless
        # KV_FORK_ENABLE; the parent var stays "" on the primary path so the
        # primary never forks. The node task (created below) snapshots this value.
        if KV_FORK_ENABLE:
            _kv_fork_parent_var.set(_conv_key_var.get() or "")
        _slow_node = _lane in SLOW_LANES
        _grounded_node = bool(node.get("_grounding"))
        _reason_only = node.get("_no_tools") or (_slow_node and _grounded_node)
        if WORKER_TOOLS_ENABLE and not _reason_only:
            _wtools = await _worker_tools_surface_async(cap=_lane_tool_cap(_lane), intent=prompt)
            _wtools = _agent_rbac_filter(aname, _wtools)  # WS-2 per-agent RBAC
            _wtools = _user_rbac_filter(_wtools)          # #60 WS-6 per-user authz
            if _wtools:
                body["tools"] = _wtools
                body["num_ctx"] = _fit_context(
                    body.get("messages") or [], _wtools, _lane,
                    WORKER_TOOL_CTX_SLOW if _slow_node else WORKER_TOOL_CTX)
                body["_allow_write"] = True
        elif _slow_node:
            # Grounded reason-only slow node: cap its context so the trimmed
            # grounding + contract prefill stays fast on CPU (no tools attached, so
            # the tool-ctx block above is skipped -- set a sane window explicitly).
            body["num_ctx"] = WORKER_TOOL_CTX_SLOW
        # Structured output ("jsonish ??!!"): when the planner
        # marks a node format:json, constrain the agent to emit a REAL JSON object
        # so a downstream #E<id>.<field> ref reads the value DETERMINISTICALLY --
        # no brittle "jsonish" first-line guessing.
        if str(node.get("format") or "").lower() == "json":
            body["response_format"] = {"type": "json_object"}
        hdrs = {"Content-Type": "application/json"}

        # STREAM vs COMPLETE: with a fragment queue (streaming DAG paths) the
        # node streams its reasoning live into the dropdown via _call_agent_stream
        # (pushes ("SF", name, frag) onto frag_q -- the SAME merged-queue shape the
        # council secondaries use); without one (non-streaming) it collects the
        # full answer. Both keep the (name, full_text) contract + identical
        # dead-endpoint degradation, so the fallback/retry chain is unchanged.
        # prefer_cpu=False -> the agent's PRIMARY endpoint/model (a coding
        # sub-task must hit opencode proper, not its CPU twin).
        async def _run_node(prefer_cpu: bool) -> tuple:
            if frag_q is not None:
                return await _call_agent_stream(
                    aname, acfg, body, hdrs, client, frag_q,
                    prefer_cpu=prefer_cpu)
            return await _call_agent_complete(
                aname, acfg, body, hdrs, client, prefer_cpu=prefer_cpu)

        # All of the agent dispatch (primary + cpu-twin fallback + empty-retries)
        # runs under ONE wall-clock deadline so a slow/dead node can't gate the
        # turn (j). On timeout the node is abandoned empty and
        # the synthesiser uses whoever DID answer.
        async def _dispatch_with_retries() -> tuple:
            _, _txt = await _run_node(prefer_cpu=False)
            _txt = (_txt or "").strip()
            # Fallback: a stream-only gateway (the Hermes server) returns empty on
            # a non-streaming call. If the agent has a CPU twin, use it --
            # it answers a self-contained sub-task non-streaming cleanly. opencode
            # has no twin -> keeps hitting its real coder model.
            if not _txt and acfg.get("cpu_endpoint") and acfg.get("cpu_model"):
                _, _txt = await _run_node(prefer_cpu=True)
                _txt = (_txt or "").strip()
            # RE-ATTEMPT on empty so an assigned node ACTUALLY computes (operator
            #): a transient empty (timeout / stream-only gateway hiccup)
            # is retried -- agent calls are read-only, so a retry is side-effect-free.
            _n = 0
            while not _txt and _n < DAG_NODE_RETRY:
                _n += 1
                await asyncio.sleep(0.4)
                _, _txt = await _run_node(prefer_cpu=False)
                _txt = (_txt or "").strip()
            return _txt, _n
        # Lane-aware deadline ("LOCAL CPU IS NEEDED"): a slow
        # lane gets the longer DAG_NODE_DEADLINE_SLOW_S so its single grounded pass
        # is never guillotined just for being slow; the fast lanes work-steal while
        # it finishes. A fast lane keeps the tight deadline.
        _node_deadline = DAG_NODE_DEADLINE_SLOW_S if _slow_node else DAG_NODE_DEADLINE_S
        try:
            text, _ntry = await asyncio.wait_for(_dispatch_with_retries(),
                                                 timeout=_node_deadline)
        except asyncio.TimeoutError:
            text, _ntry = "", 0
            log.warning("DAG node %s (agent:%s lane=%s) exceeded %.0fs -> abandoned",
                        nid, aname, _lane, _node_deadline)
        return {
            "success": bool(text),
            "output": text,
            "latency_ms": int((time.time() - t0) * 1000),
            "tool": f"agent:{aname}",
            "args": {},
            "node_id": nid,
            "retries": _ntry,
            "_act": _act,
        }
    # ---- verb node: ONE MiOS dispatch verb via the broker ----------------
    tool = str(node.get("tool", "")).strip()
    args = _substitute_ek_refs(node.get("args") or {}, results_by_id)
    # Action-hash dedup guard: a duplicate (verb, resolved-args) already run
    # in an EARLIER level reuses the prior result (structural hash only --
    # NO-HARDCODED-ENGLISH binding). Same-level dupes may both run (the
    # snapshot has no in-level writes); that is a rare, harmless extra call.
    _act = _action_hash(tool, args)
    _prior = seen_actions.get(_act)
    if _prior is not None:
        d = dict(_prior)
        d["node_id"] = nid
        d["repeat_of"] = _prior.get("node_id")
        d["_act"] = _act
        return d
    attempt = 0
    # Phase A.3: forward session_id so the firewall pre-check sees taint.
    last_result = await dispatch_mios_verb(tool, args, session_id=session_id)
    if not last_result.get("success"):
        # ReWOO single-step reflection: one corrected re-dispatch before
        # the transient-retry loop (bounded, so a stubborn failure surfaces
        # as a real error instead of looping).
        correction = await reflect_on_step_failure(
            {"id": nid, "tool": tool, "args": args}, last_result,
            {"summary": dag_summary}, session_id=session_id)
        if correction and correction.get("tool"):
            tool = str(correction.get("tool", tool))
            args = _substitute_ek_refs(
                correction.get("args") or {}, results_by_id)
            last_result = await dispatch_mios_verb(
                tool, args, session_id=session_id)
    while not last_result.get("success") and attempt < PLANNER_REFLEXION_CAP:
        attempt += 1
        await asyncio.sleep(0.5)
        last_result = await dispatch_mios_verb(tool, args, session_id=session_id)
    res = dict(last_result)
    res["node_id"] = nid
    res["tool"] = tool
    res["args"] = args if isinstance(args, dict) else {}
    res["attempts"] = attempt
    res["_act"] = _act
    return res

def _record_dag_node_row(res: dict, session_id: Optional[str]) -> None:
    """Persist a DAG node's dispatch as a session-linked tool_call row so
    the confirmation engine + critics see the propagation/taint chain.
    Logs an action_repeat_dedup event when the node reused a prior result."""
    if res.get("repeat_of"):
        _db_fire(_db_post(_db_create("event", {
            "source": "mios-agent-pipe",
            "kind": "action_repeat_dedup",
            "severity": "info",
            "summary": f"node {res.get('node_id')} == {res.get('repeat_of')} "
                       f"({res.get('tool')})",
            "payload": {"tool": res.get("tool"), "node_id": res.get("node_id"),
                        "repeat_of": res.get("repeat_of")},
        }, now_fields=("ts",))))
        return
    _row = {
        "tool": res.get("tool", ""),
        "args": res.get("args") if isinstance(res.get("args"), dict) else {},
        "result_preview": _sanitize_tool_text(res.get("output") or "")[:500],
        "success": bool(res.get("success")),
        "latency_ms": int(res.get("latency_ms", 0)),
        "tainted": bool(res.get("tainted")),
        "taint_reason": (res.get("taint_reason") or "") or None,
    }
    sql = _db_create("tool_call", _row, now_fields=("ts",))
    if session_id:
        sql = sql.rstrip().rstrip(";") + f", session = {session_id};"
    _db_fire(_db_post(sql))

async def _execute_dag_saturated(dag: dict, *, session_id: Optional[str],
                                 event_q: "Optional[asyncio.Queue]" = None,
                                 deepen_barrier: bool = False) -> dict:
    """CONTINUOUS READY-QUEUE DAG executor ("nothing in the
    pipeline is idle until synthesis"). A node dispatches the MOMENT its own deps
    finish -- NOT at a topological-LEVEL barrier -- so a fast node's lane picks up
    the next ready node immediately instead of idling for the slowest node in its
    level. REAL concurrency is bounded by the global/endpoint/lane semaphores in
    _call_agent_complete (saturate to capacity, never over). A finished AGENT node
    deepens until the GLOBAL barrier (all primaries done) so no lane idles while
    the swarm finishes. Same recording / emit / ReWOO-#E / dedup semantics as the
    level path; dependents of a FAILED node are SKIPPED (independent branches keep
    running -- more robust than the level path's whole-DAG fail-fast). Gated by
    SWARM_SATURATE."""
    nodes = [n for n in (dag.get("nodes") or [])
             if isinstance(n, dict) and "id" in n]
    summary = dag.get("summary", "")
    by_id = {str(n["id"]): n for n in nodes}
    deps = {nid: {str(d) for d in (n.get("deps") or []) if str(d) in by_id}
            for nid, n in by_id.items()}
    results: list[dict] = []
    results_by_id: dict[str, dict] = {}
    seen_actions: dict[str, dict] = {}
    succeeded: set = set()
    failed: set = set()          # failed OR skipped -> poisons dependents
    client = await _get_client()
    # Global barrier for deepen: set when every node that WILL run has finished
    # its PRIMARY pass (expected shrinks as deps-failed nodes are skipped).
    _barrier = asyncio.Event()
    _primary_done = {"n": 0}
    _primary_expected = {"n": len(nodes)}
    _do_deepen = bool(deepen_barrier) and \
        sum(1 for n in nodes if n.get("agent")) > 1

    def _check_barrier() -> None:
        if _primary_done["n"] >= _primary_expected["n"]:
            _barrier.set()

    def _node_tool(node: dict) -> str:
        return str(node.get("tool") or
                   (f"agent:{node.get('agent')}" if node.get("agent") else ""))

    def _record(node: dict, res: dict) -> None:
        results.append(res)
        _record_dag_node_row(res, session_id)
        _scratchpad_note(res.get("tool") or f"agent:{node.get('agent') or '?'}",
                         str(res.get("output") or ""), phase="dag")
        if event_q is not None:
            event_q.put_nowait(("done", node, res))

    async def _run_node(node: dict):
        _r = await _execute_dag_node(node, results_by_id, seen_actions, summary,
                                     session_id, client, frag_q=event_q)
        _primary_done["n"] += 1            # atomic: no await between read+set
        _check_barrier()
        # Deepen FINISHED FAST-LANE nodes until the GLOBAL barrier (all primaries
        # done) so the dGPU/accelerator stays busy while the slow nodes finish --
        # bounded by the deepen deadline / iter cap (operator "nothing idle"). A
        # slow lane (CPU/iGPU) is excluded (_node_deepens): it does its one grounded
        # pass and waits, so it's never abandoned for spinning a second pass.
        if _do_deepen and _node_deepens(node) and not _barrier.is_set():
            _r = await _deepen_until_barrier(node, _r, _barrier,
                                             session_id, client)
        return node, _r

    pending: set = set(by_id.keys())
    running: dict = {}   # asyncio.Task -> node_id

    def _cascade_skips() -> None:
        # A pending node whose deps include a failed/skipped node is skipped;
        # the skip poisons its own dependents (cascade). Records a skip result so
        # node_results stays complete; shrinks the primary-expected count so the
        # deepen barrier still fires.
        changed = True
        while changed:
            changed = False
            for nid in list(pending):
                if deps[nid] & failed:
                    pending.discard(nid)
                    failed.add(nid)
                    _primary_expected["n"] -= 1
                    node = by_id[nid]
                    _record(node, {"success": False, "node_id": nid,
                                   "tool": _node_tool(node), "args": {},
                                   "output": f"node {nid} skipped: dependency failed"})
                    changed = True
        _check_barrier()

    _cascade_skips()
    while pending or running:
        # Launch EVERY currently-ready node (deps all succeeded); the semaphores
        # bound how many actually run at once -> saturate to capacity.
        for nid in [x for x in pending if deps[x] <= succeeded]:
            pending.discard(nid)
            node = by_id[nid]
            if event_q is not None:
                event_q.put_nowait(("engage", node, None))
            running[asyncio.create_task(_run_node(node))] = nid
        if not running:
            # nothing ready + nothing running -> cycle/dangling dep: force one
            # node (declaration order) so the DAG never hangs (same stance as
            # _dag_levels). Else done.
            if pending:
                nid = next(iter(pending))
                pending.discard(nid)
                node = by_id[nid]
                if event_q is not None:
                    event_q.put_nowait(("engage", node, None))
                running[asyncio.create_task(_run_node(node))] = nid
            else:
                break
        try:
            completed, _ = await asyncio.wait(
                set(running.keys()), return_when=asyncio.FIRST_COMPLETED)
        except asyncio.CancelledError:
            # Turn cancelled (client disconnect / deadline / supersede): asyncio
            # does NOT auto-cancel a cancelled task's children, so cancel every
            # in-flight node task here so they STOP dispatching to hermes / a
            # sub-agent lane instead of running on (runaway fix). Re-raise.
            for _t in list(running.keys()):
                if not _t.done():
                    _t.cancel()
            raise
        for t in completed:
            nid = running.pop(t)
            node = by_id[nid]
            try:
                node, res = t.result()
            except BaseException as e:  # noqa: BLE001
                res = {"success": False, "node_id": nid, "tool": _node_tool(node),
                       "args": {}, "output": f"node {nid} raised: {e}"}
            _record(node, res)
            if res.get("success"):
                succeeded.add(nid)
                results_by_id[nid] = res
                if res.get("_act"):
                    seen_actions[res["_act"]] = res
            else:
                failed.add(nid)
        _cascade_skips()
    if event_q is not None:
        event_q.put_nowait(None)  # sentinel: DAG complete, drainer can stop
    return {
        "success": not failed,
        "summary": summary,
        "nodes_total": len(nodes),
        "nodes_executed": len(results),
        "node_results": results,
    }

# ── WS-6 replayable DAG run-templates ───────────────────────────
# Determinism foundation: capture every planned DAG (the replayable plan shape)
# to the run_template table, keyed by a STRUCTURAL class hash (sorted tool/agent
# names + edge count -> no English, NO-HARDCODED-ENGLISH). This is the CAPTURE +
# observability half (GET /v1/run-templates); replay-REUSE (matching a new turn
# to a stored template + skipping planning) is a documented follow-up. Additive
# + fire-and-forget: capture can never affect a live run. ENABLED by default
# ('everything on'). SSOT [run_template].enable.
RUN_TEMPLATE_ENABLE = str(os.environ.get("MIOS_RUN_TEMPLATE")
                          or _toml_section("run_template").get("enable", "true")
                          ).strip().lower() in {"1", "true", "yes"}


def _run_template_class(dag: dict) -> str:
    """Structural intent-class key for a DAG: sorted tool/agent names + total
    edge count, hashed. Same plan SHAPE -> same class regardless of phrasing."""
    nodes = dag.get("nodes") or []
    sig = sorted(str(n.get("tool") or n.get("agent") or "?") for n in nodes)
    edges = sum(len(n.get("deps") or []) for n in nodes)
    raw = "|".join(sig) + f"#e{edges}"
    return hashlib.sha256(raw.encode("utf-8", "replace")).hexdigest()[:16]


def _capture_run_template(dag: dict, session_id: Optional[str]) -> None:
    """Fire-and-forget capture of a planned DAG as a replayable template. Never
    raises (degrade-open) -- capture must not affect the run."""
    if not RUN_TEMPLATE_ENABLE:
        return
    try:
        nodes = dag.get("nodes") or []
        if not nodes:
            return
        _pg_mirror("run_template", {                               # WS-9c
            "class": _run_template_class(dag),
            "summary": str(dag.get("summary") or "")[:500],
            "node_count": len(nodes),
            "dag": dag,
            "session_id": session_id,
        })
        sql = _db_create("run_template", {
            "class": _run_template_class(dag),
            "summary": str(dag.get("summary") or "")[:500],
            "node_count": len(nodes),
            "dag": dag,
        }, now_fields=("ts",), _mirror=False)
        if session_id:
            sql = sql.rstrip().rstrip(";") + f", session = {session_id};"
        if not _PG_PRIMARY:                      # WS-9c: pgvector mirror is primary
            _db_fire(_db_post(sql))
    except Exception:  # noqa: BLE001
        pass

async def execute_dag(dag: dict, *, session_id: Optional[str],
                      event_q: "Optional[asyncio.Queue]" = None,
                      deepen_barrier: bool = False) -> dict:
    """Execute the DAG. SWARM_SATURATE -> the continuous ready-queue
    (_execute_dag_saturated, "nothing idle until synthesis"); else the legacy
    concurrent topological-LEVEL path below (the proven fallback).

    LEVEL path: every node whose deps are satisfied runs in PARALLEL
    (asyncio.gather), so independent
    sub-tasks -- including agent-delegation nodes routed to DIFFERENT sub-
    agents -- run concurrently across the CPU + GPU lanes (operator
 "separate prompts per refinement step -> sub-agents...
    concurrent Compute"). A level only starts once all earlier levels
    finish, so ReWOO #E<id> refs always resolve. Reflexion-retries failed
    verb nodes; fail-fast when a level has an unrecoverable failure.
    Returns aggregate {success, node_results[], summary}."""
    _capture_run_template(dag, session_id)   # WS-6: additive, fire-and-forget
    if SWARM_SATURATE:
        return await _execute_dag_saturated(
            dag, session_id=session_id, event_q=event_q,
            deepen_barrier=deepen_barrier)
    levels = _dag_levels(dag.get("nodes") or [])
    summary = dag.get("summary", "")
    results: list[dict] = []
    results_by_id: dict[str, dict] = {}
    seen_actions: dict[str, dict] = {}
    all_ok = True
    client = await _get_client()
    for level_idx, level in enumerate(levels, start=1):
        superstep_id = f"superstep_{level_idx}"
        checkpoint_key = f"{session_id}:{superstep_id}"
        loaded_from_checkpoint = False
        if session_id and _db_read:
            try:
                ckpt_sql = f"SELECT meta FROM session WHERE id = '{checkpoint_key}' AND kind = 'checkpoint'"
                ckpt_rows = await _db_read(ckpt_sql, pg_sql=ckpt_sql)
                if ckpt_rows and ckpt_rows[0].get("meta"):
                    meta = ckpt_rows[0]["meta"]
                    if isinstance(meta, str):
                        meta = json.loads(meta)
                    log.info("Resuming DAG level %d from checkpoint %s", level_idx, checkpoint_key)
                    level_res = meta.get("level_res") or []
                    for res in level_res:
                        results.append(res)
                        nid = res.get("node_id")
                        if nid:
                            results_by_id[nid] = res
                        _act = res.get("_act")
                        if _act:
                            seen_actions[_act] = res
                        # Re-post scratchpad notes so subsequent levels have them
                        _scratchpad_note(
                            res.get("tool") or "agent",
                            str(res.get("output") or ""), phase="dag")
                    loaded_from_checkpoint = True
            except Exception as _ckpt_err:
                log.warning("Failed to load checkpoint %s: %s", checkpoint_key, _ckpt_err)

        if loaded_from_checkpoint:
            continue

        # Endpoint emitters: announce each node in this level as it ENGAGES
        # (a level's nodes run concurrently). The streaming wrapper turns
        # these queue items into live per-node SSE statuses (operator
        #). No queue (non-streaming) -> no-op.
        if event_q is not None:
            for n in level:
                event_q.put_nowait(("engage", n, None))
        # BARRIER-DEEPEN: every node runs its PRIMARY pass concurrently; the moment
        # all primaries finish a barrier fires. A node whose primary finishes BEFORE
        # the barrier then deepens (deeper web-research + re-answer) UNTIL the barrier,
        # so a fast lane keeps widening coverage instead of idling while the slow node
        # finishes. When [dispatch].deepen_early_exit is enabled it ALSO stops early
        # once the DoD judge marks the node satisfied (degrade-open; see
        # _deepen_until_barrier). The last node (barrier already set) skips deepen.
        # Only for a multi-node agent level (the swarm); off otherwise.
        _agent_level = [n for n in level if n.get("agent")]
        if deepen_barrier and len(_agent_level) > 1:
            _barrier = asyncio.Event()
            _bstate = {"done": 0}
            _btotal = len(level)

            async def _node_then_deepen(n: dict) -> dict:
                _r = await _execute_dag_node(n, results_by_id, seen_actions,
                                             summary, session_id, client,
                                             frag_q=event_q)
                _bstate["done"] += 1            # atomic: no await since the read
                if _bstate["done"] >= _btotal:  # last primary -> release barrier
                    _barrier.set()
                # FAST-lane nodes work-steal (deepen) for utilization (operator
                # "every single node always computes"; refined
                # "dGPU and accelerators that compute faster should just do another
                # pass") -- a finished fast node keeps looping until the barrier
                # (slowest primary done). A SLOW lane (CPU/iGPU) is excluded
                # (_node_deepens): it does its one grounded pass and waits, never
                # abandoned for a second pass. The LAST node (set the barrier) skips.
                if _node_deepens(n) and not _barrier.is_set():
                    _r = await _deepen_until_barrier(
                        n, _r, _barrier, session_id, client)
                return _r

            level_res = await asyncio.gather(
                *[_node_then_deepen(n) for n in level], return_exceptions=True)
        else:
            level_res = await asyncio.gather(*[
                _execute_dag_node(n, results_by_id, seen_actions, summary,
                                  session_id, client, frag_q=event_q)
                for n in level
            ], return_exceptions=True)
        for node, res in zip(level, level_res):
            nid = str(node.get("id", "?"))
            if isinstance(res, BaseException):
                res = {"success": False, "node_id": nid,
                       "tool": str(node.get("tool") or
                                   (f"agent:{node.get('agent')}"
                                    if node.get("agent") else "")),
                       "args": {}, "output": f"node {nid} raised: {res}"}
            results.append(res)
            _record_dag_node_row(res, session_id)
            # Post this node's outcome as a checkpoint so the NEXT level's
            # nodes (and other agents in the chain) read it from the scratchpad.
            _scratchpad_note(
                res.get("tool") or f"agent:{node.get('agent') or '?'}",
                str(res.get("output") or ""), phase="dag")
            if event_q is not None:
                event_q.put_nowait(("done", node, res))
            if res.get("success"):
                results_by_id[nid] = res
                if res.get("_act"):
                    seen_actions[res["_act"]] = res
            else:
                all_ok = False

        # Save checkpoint
        if session_id and _db_create and _db_fire and _db_post:
            try:
                ckpt_meta = {
                    "level_res": level_res,
                }
                del_sql = f"DELETE FROM session WHERE id = '{checkpoint_key}'"
                _db_fire(_db_post(del_sql))
                ins_sql = _db_create("session", {
                    "id": checkpoint_key,
                    "kind": "checkpoint",
                    "owui_chat_id": session_id,
                    "meta": ckpt_meta
                }, now_fields=("ts",))
                _db_fire(_db_post(ins_sql))
                log.info("Saved superstep checkpoint %s to database", checkpoint_key)
            except Exception as _ckpt_save_err:
                log.warning("Failed to save checkpoint %s: %s", checkpoint_key, _ckpt_save_err)

        # Fail-fast: don't launch a level that depends on a failed one.
        if not all_ok:
            break
    if event_q is not None:
        event_q.put_nowait(None)  # sentinel: DAG complete, drainer can stop
    return {
        "success": all_ok,
        "summary": summary,
        "nodes_total": len(dag.get("nodes") or []),
        "nodes_executed": len(results),
        "node_results": results,
    }

async def _execute_dag_bounded(dag: dict, *, session_id: Optional[str],
                               deepen_barrier: bool = False,
                               request=None) -> dict:
    """Non-streaming execute_dag with a hard TURN_DEADLINE_S wall-clock backstop
 (runaway fix) PLUS client-disconnect cancellation (T21,
) when `request` is provided: a non-streaming caller that hangs up
    stops the swarm IMMEDIATELY rather than churning DAG+deepen to the deadline.
    The STREAMING path self-bounds on disconnect in _execute_dag_emitting; this
    closes the non-streaming gap. On timeout/disconnect, wait_for/cancel stops the
    executor -> _execute_dag_saturated's CancelledError handler cancels in-flight
    node tasks so they stop dispatching. Returns a partial result. Degrade-open:
    request=None or REQUEST_CANCEL_ENABLE=false -> deadline-only (unchanged)."""
    _task = asyncio.create_task(
        execute_dag(dag, session_id=session_id, deepen_barrier=deepen_barrier))
    _disconnected = False
    _watch = None
    if request is not None and REQUEST_CANCEL_ENABLE:
        async def _watch_disconnect():
            nonlocal _disconnected
            while not _task.done():
                try:
                    if await request.is_disconnected():
                        _disconnected = True
                        _task.cancel()
                        return
                except Exception:  # never let the watcher break the turn
                    return
                await asyncio.sleep(REQUEST_CANCEL_POLL_S)
        _watch = asyncio.create_task(_watch_disconnect())
    try:
        return await asyncio.wait_for(_task, timeout=TURN_DEADLINE_S)
    except asyncio.TimeoutError:
        log.warning("non-streaming turn deadline %.0fs exceeded -> partial result",
                    TURN_DEADLINE_S)
        await _reap_cpu_lane("non-streaming deadline")
        return {"success": False, "summary": dag.get("summary", ""),
                "nodes_total": len(dag.get("nodes") or []), "nodes_executed": 0,
                "node_results": [], "timed_out": True}
    except asyncio.CancelledError:
        if _disconnected:
            log.info("non-streaming turn CANCELLED: client disconnected -> swarm stopped")
            await _reap_cpu_lane("client disconnect")
            return {"success": False, "summary": dag.get("summary", ""),
                    "nodes_total": len(dag.get("nodes") or []), "nodes_executed": 0,
                    "node_results": [], "disconnected": True}
        raise
    finally:
        if _watch is not None:
            _watch.cancel()

async def _execute_dag_emitting(dag: dict, *, session_id: Optional[str],
                                chat_id: str, model: str,
                                deepen_barrier: bool = False):
    """Run execute_dag while LIVE-yielding per-node endpoint emitter bytes
 ("endpoint emitters for each ai endpoint/node") AND
    the agents' streamed REASONING. Yields ("event", sse_bytes) as each DAG
    node ENGAGES + finishes, then a final ("result", dag_result). Agent nodes
    carry their registry endpoint / lane / model; verb nodes show 'verb
    · <tool>'. Agent nodes also stream their thinking ("SF", name, frag onto
    the shared queue) which is buffered per-agent and checkpoint-flushed as
    reasoning_content deltas -- so the think dropdown shows the facets ACTUALLY
    reasoning, not just engage/done pings (operator: "no thinking blocks
    populating it"). The 0.25s poll lets the drainer notice the DAG finishing
    even if the sentinel is lost to an unexpected raise -- then `await task`
    re-raises it (parity with a plain `await execute_dag`)."""
    # Supersede: a NEW turn for this chat cancels the PRIOR in-flight one
    #. Register THIS turn's cancel Event; signal any
    # predecessor for the same chat. Skipped for the shared 'default' key (non-OWUI
    # callers without a chat_id must not cancel each other).
    _my_cancel = asyncio.Event()
    _sup = bool(chat_id) and chat_id != "default"
    if _sup:
        _prev = _CHAT_CANCEL.get(chat_id)
        if _prev is not None:
            _prev.set()
        _CHAT_CANCEL[chat_id] = _my_cancel
    q: "asyncio.Queue" = asyncio.Queue()
    task = asyncio.create_task(
        execute_dag(dag, session_id=session_id, event_q=q,
                    deepen_barrier=deepen_barrier))
    # Per-agent reasoning buffers: each node's streamed tokens accumulate here and
    # are emitted ATOMICALLY as one labeled block on completion (live per-token
    # flushing interleaved N concurrent nodes into a token-salad --).
    _sec_bufs: dict = {}
    _sec_hdr: set = set()
    # name -> GENERATIVE function label (reasoning headers
    # must name the FUNCTION being performed, not the internal agent key). Filled
    # as each node ENGAGES (from its sub-task / role); the buffers are still
    # KEYED by the internal name (unique) but DISPLAYED via this map.
    _func_by_name: dict = {}

    def _disp(_nm: str) -> str:
        # NEVER surface the raw internal registry key ("NO
        # INTERNAL NAMES"): use the generative function label captured at engage,
        # else derive a clean function label from the agent's role/job/lane; strip
        # any node:/a2a: prefix only as the last resort.
        lbl = str(_func_by_name.get(_nm) or "").strip()
        if lbl and not lbl.startswith(("node:", "a2a:")):
            return lbl
        c = _AGENT_REGISTRY.get(_nm) or {}
        for cand in (c.get("role"), c.get("job"), c.get("lane")):
            s = str(cand or "").strip()
            if s:
                return s[:48]
        return (str(_nm).split(":")[-1] or "agent")[:48]

    _turn_deadline = time.monotonic() + TURN_DEADLINE_S
    try:
        while True:
            try:
                item = await asyncio.wait_for(q.get(), timeout=0.25)
            except asyncio.TimeoutError:
                if task.done():
                    break
                # Superseded by a newer turn for this chat -> stop (finally cancels).
                if _my_cancel.is_set():
                    log.info("turn superseded for chat %s -> cancelling DAG", chat_id)
                    break
                # TURN-WIDE deadline backstop (runaway fix):
                # a connected-but-runaway turn can't exceed TURN_DEADLINE_S -> stop
                # (the finally cancels the DAG). Per-node deepen caps don't bound
                # the whole turn.
                if time.monotonic() > _turn_deadline:
                    log.warning("turn deadline %.0fs exceeded -> cancelling DAG",
                                TURN_DEADLINE_S)
                    await _reap_cpu_lane("streaming idle deadline")
                    break
                continue
            if item is None:  # sentinel
                break
            # Deadline / supersede checked on the BUSY path too (operator
            #): the idle-branch check above never fires while items keep
            # flowing, so a busy runaway turn ran PAST the deadline (the 1074s
            # turn). The finally cancels the DAG.
            if _my_cancel.is_set() or time.monotonic() > _turn_deadline:
                log.warning("turn stop (deadline/supersede) chat %s -> cancel DAG",
                            chat_id)
                # Reap ONLY on a real deadline-exceed, NOT on supersede (the new
                # turn needs the CPU lane it just superseded this one for).
                if time.monotonic() > _turn_deadline and not _my_cancel.is_set():
                    await _reap_cpu_lane("streaming busy deadline")
                break
            # Streamed agent-reasoning fragment -> per-agent buffer (not a node
            # engage/done event; item[1] is the agent NAME, item[2] the fragment).
            if item and item[0] == "SF":
                # Buffer streamed tokens but do NOT emit them live: N concurrent
                # nodes' fragments interleave character-by-character in the single
                # flat dropdown stream ("garbled" reasoning).
                # Each node's full output is emitted ATOMICALLY as one clean labeled
                # block on completion (below), so blocks stay contiguous + readable;
                # liveness is preserved at NODE granularity (a block appears as each
                # node finishes) plus the live 🔎/📖 web-research + 🤖 engage emits.
                _sec_bufs[item[1]] = _sec_bufs.get(item[1], "") + (item[2] or "")
                continue
            kind, node, res = item
            aname = node.get("agent")
            if aname:
                name = str(aname)
                cfg = _AGENT_REGISTRY.get(aname) or {}
            else:
                name = str(node.get("tool") or "node")
                cfg = {"lane": "verb", "model": str(node.get("tool") or "")}
            if kind == "engage":
                _ctx = _node_context(node)
                # remember this node's GENERATIVE function label for its reasoning
                # header + finish emit (never display the internal name).
                _func_by_name[name] = _ctx or str((cfg or {}).get("role") or "")
                yield ("event", _node_status(chat_id=chat_id, model=model,
                                             name=name, cfg=cfg, state="engage",
                                             context=_ctx))
            else:
                ok = bool(isinstance(res, dict) and res.get("success"))
                # STREAM this node's output into the live reasoning block AS IT
                # FINISHES ("emits... NOT held back... not
                # dumped all last second"; "report for ALL stages/steps"). A node
                # whose agent did NOT token-stream (returned a blob -- the research
                # workers) would otherwise surface ONLY in the end-of-turn synthesis
                # envelope, so the whole think block dumps at once. Emit its output
                # now, ONCE -- the `_sec_hdr` guard skips nodes that already streamed
                # live via "SF" fragments, so there is NO duplication either way.
                if name not in _sec_hdr:
                    _nout = (_sec_bufs.get(name) or "").strip()
                    if not _nout:
                        _nout = (str(res.get("output") or "").strip()
                                 if isinstance(res, dict) else "")
                    if _nout:
                        _sec_hdr.add(name)
                        if name not in _func_by_name:
                            _func_by_name[name] = (_node_context(node)
                                                   or str((cfg or {}).get("role") or ""))
                        yield ("event", _sse_reasoning(
                            _sanitize_tool_text(f"\n\n🤝 {_disp(name)}:\n{_nout}\n"),
                            chat_id=chat_id, model=model))
                # Carry the sub-job into the FINISH emit too (
                # "per-node sub-job in emits") so ✅/💤 still names WHAT the node
                # did, not just its name -- parity with the engage emit above.
                yield ("event", _node_status(chat_id=chat_id, model=model,
                                             name=name, cfg=cfg,
                                             state="ok" if ok else "down",
                                             context=_node_context(node)))
        # Each node's reasoning was emitted ATOMICALLY on completion above, so
        # there is no trailing buffered reasoning to drain here (the old per-flush
        # drain is what produced the interleaved token-salad). Straight to synthesis.
        dag_result = await task
        yield ("result", dag_result)
    finally:
        # ABANDONED / runaway / deadline-exceeded turn -> CANCEL the in-flight DAG
        # so it STOPS instead of generating to completion through hermes -> a
        # sub-agent lane (runaway ROOT CAUSE fix). On client disconnect the
        # SSE generator is closed -> GeneratorExit lands here -> task.cancel() ->
        # _execute_dag_saturated cancels its node tasks. No-op on normal finish.
        if not task.done():
            task.cancel()
        # Deregister this turn's supersede slot (only if still ours -- a newer
        # turn may have already claimed it).
        if _sup and _CHAT_CANCEL.get(chat_id) is _my_cancel:
            _CHAT_CANCEL.pop(chat_id, None)


# -- DAG-execution support helpers (moved home; were server.py-resident + injected
# back into this module). _substitute_ek_refs (ReWOO #E ref resolution) + its
# _smart_extract_from_jsonish field-picker + the #E ref regexes, _fit_context
# (num_ctx sizing), _node_deepens (fast-lane work-steal gate) and _reap_cpu_lane
# (CPU-lane runaway reaper) are exclusively consumed by the DAG executors above;
# they now live in their natural home. server.py re-imports each under its exact
# name (surface parity); their config scalars are injected via configure().


_EK_REF_RE = re.compile(r"#E([A-Za-z0-9_]+)")


_EK_FIELD_REF_RE = re.compile(r"#E([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)")


def _smart_extract_from_jsonish(payload: str) -> str:
    """Pull the most-useful single field out of a JSON-ish blob so a
    ReWOO bare `#E<id>` ref doesn't paste the whole multi-line dump
    into a downstream arg. Trace failure: mios_apps returns NDJSON
    (one app per line). #En1 substituted the FULL stdout into
    open_app(name=...), producing args like
    `{"category":"linux-flatpak","name":"devel",...}\\n{"...":"..."}\\n`
    which mios-launch can't resolve to anything.

    Resolution order:
      1. Single JSON object -> prefer `name`, then `launch`, then
         `title`, then `id`, then `path`, then first string field.
      2. NDJSON (one object per line) -> use the FIRST object's
         best field via the same rule.
      3. Not JSON -> return the first line, capped at 1024 chars
         (matches the prior naive behavior for plain-text upstream)."""
    s = _sanitize_tool_text((payload or "").strip())
    if not s:
        return ""
    # Try a single JSON object first.
    try:
        obj = _loads_lenient(s)
        if isinstance(obj, dict):
            for k in ("name", "launch", "title", "id", "path"):
                v = obj.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()[:1024]
            for v in obj.values():
                if isinstance(v, str) and v.strip():
                    return v.strip()[:1024]
        elif isinstance(obj, list) and obj:
            first = obj[0]
            if isinstance(first, str):
                return first.strip()[:1024]
            if isinstance(first, dict):
                for k in ("name", "launch", "title", "id", "path"):
                    v = first.get(k)
                    if isinstance(v, str) and v.strip():
                        return v.strip()[:1024]
    except (json.JSONDecodeError, ValueError):
        pass
    # NDJSON: try the first line.
    first_line = s.splitlines()[0].strip()
    if first_line.startswith("{") and first_line.endswith("}"):
        try:
            obj = _loads_lenient(first_line)
            if isinstance(obj, dict):
                for k in ("name", "launch", "title", "id", "path"):
                    v = obj.get(k)
                    if isinstance(v, str) and v.strip():
                        return v.strip()[:1024]
        except (json.JSONDecodeError, ValueError):
            pass
    # Plain text fallback: first non-empty line, capped.
    return first_line[:1024]


def _substitute_ek_refs(args: dict, results_by_id: dict) -> dict:
    """ReWOO-style substitution: replace `#E<node-id>` tokens in arg
    values with the captured stdout of the upstream node. Two forms
    supported:

      #E<id>            -> smart-extract a single useful field from
                           the upstream output (handles JSON objects
                           + NDJSON streams; falls back to first line
                           for plain text). Caps at 1024 chars.
      #E<id>.<field>    -> extract a NAMED field from the upstream
                           JSON output. Use this when the planner
                           knows which field it needs (e.g.,
                           open_app(name='#En1.launch') to use the
                           launch line from a mios_apps row).

    Per ReWOO (Xu et al. 2023): the planner emits #E<id> placeholders
    and the worker substitutes them with actual outputs at execute
    time. Removes the per-step LLM re-plan that other frameworks
    need.

    Only handles string args (the common case for shell verbs).
    Object / list args pass through unchanged."""
    if not args:
        return args
    out: dict = {}
    for k, v in args.items():
        if isinstance(v, str) and "#E" in v:
            # Field-ref form #E<id>.<field> -- replace first since
            # the bare-ref regex also matches.
            def _sub_field(m: re.Match) -> str:
                ref, field = m.group(1), m.group(2)
                r = results_by_id.get(ref)
                if not r:
                    return m.group(0)
                payload = r.get("output") or ""
                try:
                    obj = _loads_lenient(payload)
                except (json.JSONDecodeError, ValueError):
                    # Try first line as JSON.
                    first = (payload.strip().splitlines() or [""])[0]
                    try:
                        obj = _loads_lenient(first)
                    except (json.JSONDecodeError, ValueError):
                        return m.group(0)
                if isinstance(obj, list) and obj:
                    obj = obj[0]
                if isinstance(obj, dict):
                    val = obj.get(field)
                    if isinstance(val, str):
                        return val[:1024]
                return m.group(0)
            v = _EK_FIELD_REF_RE.sub(_sub_field, v)
            # Bare-ref form #E<id> -- now smart-extract instead of
            # pasting the whole blob.
            def _sub_bare(m: re.Match) -> str:
                ref = m.group(1)
                r = results_by_id.get(ref)
                if not r:
                    return m.group(0)
                payload = r.get("output") or ""
                return _smart_extract_from_jsonish(payload)
            out[k] = _EK_REF_RE.sub(_sub_bare, v)
        else:
            out[k] = v
    return out


def _fit_context(messages: list, tools: list, lane: str, want_ctx: int) -> int:
    """AIOS gap5 L2: dynamically size num_ctx to FIT the actual prompt+tool weight.
    FAST lanes: raise toward WORKER_TOOL_CTX_MAX only as needed (never shrink, never
    trim the contract). SLOW lanes: leave pinned at want_ctx (Layer 1 already shrank
    their surface). Returns num_ctx. Degrade-open: CTX_FIT off / any error ->
    want_ctx (today's static value)."""
    if not CTX_FIT:
        return want_ctx
    try:
        if lane in SLOW_LANES:
            return want_ctx
        est = mios_tokenize.count_messages(messages, tools)  # WS-A5 tokenizer seam (was //4)
        return max(want_ctx, min(WORKER_TOOL_CTX_MAX, est + 512))
    except Exception:  # noqa: BLE001
        return want_ctx


def _node_deepens(node: dict) -> bool:
    """True only for a node on a FAST lane (DEEPEN_LANES: dGPU/accelerator) -- the
    work-stealing lanes that do EXTRA coverage passes until the barrier (operator
 "dGPU and accelerators that compute faster should just do another
    pass from another facet"). A SLOW lane (CPU/iGPU/phone) does its ONE grounded
    pass and then its primary trips the barrier for the fast lanes; it must NOT
    deepen (it can barely finish one pass) -- the runaway/abandon source the
    operator hit with local-cpu."""
    if not node.get("agent"):
        return False
    lane = _agent_lane(_AGENT_REGISTRY.get(str(node.get("agent"))) or {})
    return lane in DEEPEN_LANES


async def _reap_cpu_lane(reason: str) -> None:
    """No-op on the /v1 plane. A llama.cpp / llama-swap generation ABORTS the moment
    the client connection closes (unlike a legacy un-abortable backend), so a
    cancelled / deadline-exceeded turn releases the lane on its own -- there is no
    /v1 model-unload primitive to call and none is needed. Kept as a gated hook
    (RUNAWAY_REAP_ENABLE) should a future backend ever need an explicit reap; never
    raises into a turn."""
    if not RUNAWAY_REAP_ENABLE:
        return
    # The cancelled request already released the lane -- nothing to reap.
    log.debug("runaway reaper (%s): /v1 lane self-releases on cancel -- no-op", reason)
