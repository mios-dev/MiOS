# AI-hint: The agent-pipe CHAT-COMPLETIONS router-brain, extracted VERBATIM from
#   server.py (strangler-fig refactor capstone). chat_completions_logic is the
#   central per-turn orchestrator: it runs the full routing precedence -- vision
#   -> client-tools -> OS fast-path -> trivial-chat -> memory/local-state ->
#   native single-agent loop -> multi-task decompose -> council/swarm fan-out ->
#   critic/polish -> backend self-proxy -- with every guard, header seed, budget
#   admit/release, scratchpad rehydrate/render, source-turn accounting and SSE
#   stream pump moved byte-identically. Each dispatched responder already lives in
#   a sibling (mios_vision/_oscontrol/_native_loop/_swarm/_dag_exec/...) imported
#   DIRECTLY here; every remaining server-resident helper, config scalar, ContextVar,
#   the live verb catalog and the agent registry are dependency-INJECTED via
#   configure() under their EXACT original names (one-way boundary -- this module
#   NEVER imports server). server.py keeps the @app.post('/v1/chat/completions')
#   route + async def chat_completions as a THIN wrapper that reaches this logic
#   through sys.modules, so the importable HTTP/symbol surface is byte-identical.
# AI-related: ./server.py, ./mios_vision.py, ./mios_oscontrol.py, ./mios_native_loop.py, ./mios_swarm.py, ./mios_dag_exec.py, ./mios_refine.py, ./mios_planner.py, ./mios_grounding.py, ./mios_verity.py, ./test_mios_chat.py
# AI-functions: chat_completions_logic, responses_api_logic, chat_router, responses_api, configure, _quick_chat_reply, _is_memory_question, _ask_for_location, _hints_write_action, _needs_external_knowledge, _shadow_queue_tasks, _budget_num, _budget_bucket, _budget_window_total, _budget_debit, _budget_prune_inflight, _budget_admit, _budget_release_inflight
"""CHAT-COMPLETIONS router-brain (strangler-fig refactor capstone).

Extracted VERBATIM from ``server.py``. :func:`chat_completions_logic` is the
per-turn orchestrator that routes a request through the precedence vision ->
client-tools -> OS fast-path -> trivial-chat -> memory/local-state -> native
loop -> multi-task -> council/swarm -> polish, keeping every heuristic, guard
and comment byte-identical. The dispatched responders are imported directly
from their siblings; every server-resident helper/scalar/ContextVar plus the
live verb catalog and agent registry are injected via :func:`configure` under
their exact original names (one-way boundary -- this module never imports
``server``). ``server.py`` keeps the route + ``chat_completions`` handler as a
thin wrapper reaching this logic through ``sys.modules`` so the importable
surface stays byte-identical.
"""

from __future__ import annotations

import asyncio
import collections
import json
import logging
import os
import re
import time
import uuid
from typing import Any, AsyncGenerator, Optional

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

import mios_trace
import mios_pg as _mios_pg   # WS-9 Postgres client (canonical kanban upsert)
from mios_config import (   # layered mios.toml SSOT reader (aggregate-budget cluster + REFINE/ROUTER lanes)
    _cfg_num, _toml_section, REFINE_MODEL, REFINE_ENDPOINT, REFINE_TIMEOUT_S,
    ROUTER_MODEL, PLANNER_ENDPOINT, PLANNER_TIMEOUT_S)

# Dispatched responders + leaf helpers live in siblings -- import DIRECTLY
# (one-way boundary: this module never imports server).
from mios_agent_call import _call_agent_complete
from mios_dag_exec import _execute_dag_bounded, _execute_dag_emitting
from mios_dci import critic_then_maybe_flow
from mios_dispatch import dispatch_mios_verb
from mios_fanout import _pick_fanout_agents
from mios_grounding import _env_grounding
from mios_knowledge import _recall_knowledge, _store_knowledge
from mios_native_loop import _respond_local_state, _respond_native_loop_direct
from mios_oscontrol import _respond_os_control
from mios_planner import decompose_intent
import mios_preempt   # T-019/SCHED-01: turn-boundary preemption seam (flag-gated, degrade-open)
from mios_refine import refine_intent
from mios_routing import _deterministic_action_route
from mios_sse import _sse_chunk, _sse_status, _stream_answer
from mios_swarm import _agent_dag_from_tasks, _respond_agent_dag
import mios_tokenize
from mios_tokenize import _usage_estimate
from mios_verity import polish_response
from mios_vision import _client_tools_complete, _has_client_tools, _vision_complete
from mios_web_research import _web_research_enrich

log = logging.getLogger("mios-agent-pipe")


# -- Dependency-injection seam ----------------------------------------
# chat_completions_logic reads server.py's config scalars + routing flags, the
# live verb catalog + agent registry, a set of request-scoped ContextVars, and
# calls back into many server-side helpers (grounding, recall, scratchpad,
# budget admit/release, source accounting, header seeds, the kernel facade ...).
# server.py injects all of them via configure() AFTER every one is defined (the
# wrapper sits at the very end of server.py, so every dep is already bound). The
# placeholders below let a standalone import succeed; every consumer is per-
# request, long after configure() runs. _AGENT_REGISTRY is re-injected by
# server's _reload_membership on a live agent add/drop.
ASK_CLARIFY_ENABLE = None
AUTONOMOUS_PRIORITY = None
AUTO_FORCE_TOOL = None
BACKEND = None
GATEWAY_QUEUE = None
BACKEND_MODEL = None
CLIENT_TOOLS_PASSTHROUGH = None
COUNCIL_DEFAULT = None
DCI_ENABLED = None
KERNEL_ROUTE = None
KERNEL_DISPATCH = None
LOCAL_STATE_FASTPATH = None
MAX_DISPATCH_DEPTH = None
NATIVE_LOOP_ENABLE = None
NATIVE_LOOP_MATH_HINT = None
PLANNER_ENABLED = None
POLISH_ENABLED = None
SLOW_LANES = None
SLOW_LANE_BLOCK_CHARS = None
SWARM_DECOMPOSE_DEFAULT = None
SWARM_DECOMPOSE_MIN_WORDS = None
SWARM_MAX_WIDTH = None
SWARM_TRUST_ATOMIC = None
VISION_ENABLE = None
VISION_MODEL = None
WORKER_TOOLS_ENABLE = None
WORKER_TOOL_CTX = None
_AGENT_REGISTRY = None
_BACKEND_IS_LIGHT = None
_BACKEND_KEY = None
_BROWSER_ACTION_ALT = None
_FASTPATH_VERBS = None
_HOP_HEADER = None
_HUMAN_LABELS = None
_INGRESS_KEY = None
_KERNEL = None
_SRC_TURN_HEADER = None
_THINK_ORPHAN_RE = None
_TOOL_BACKEND = None
_TOOL_BACKEND_MODEL = None
_VERB_CATALOG = None
_VIA_HEADER = None
_agent_contract = None
_agent_lane = None
_agent_offload_engine = None
_build_agent_hint = None
_call_agent_stream = None
_casual_agent_label = None
_client_env = None
_client_env_var = None
_conv_key_var = None
_council_mode_var = None
_council_role_lens = None
_critic_refine_agent = None
_current_year = None
_db_create = None
_db_fire = None
_db_post = None
_depth_exhausted = None
_dispatch_depth = None
_endpoint_supports_tool_choice = None
_expand_facets = None
_extract_last_user_text = None
_filter_relevant_sources = None
_get_client = None
_inline_satisfaction_check = None
_is_action_domain = None
_lane_tool_cap = None
_live_agent_names = None
_loads_lenient = None
_maybe_run_pending_approval = None
_messages_have_image = None
_multi_task_preamble = None
_needs_compute = None
_node_status = None
_pick_agent = None
_plan_swarm = None
_rag_enrich = None
_read_tool_enrich = None
_recall_agent_memory = None
_role_system = None
_route_domain = None
_routed_domain_var = None
_sanitize_tool_text = None
_sched_priority = None
_scratchpad_key = None
_scratchpad_note = None
_scratchpad_rehydrate = None
_scratchpad_render = None
_seed_hop_from_headers = None
_sources_annotations = None
_sources_markdown = None
_sources_metadata = None
_sources_var = None
_span_id_var = None
_src_collected = None
_src_record_from_text = None
_src_turn_init = None
_src_turn_key = None
_src_turn_var = None
_sse_done = None
_sse_reasoning = None
_sse_status_phase = None
_strip_owui_scaffold = None
_strip_think_tags = None
_trace_id_var = None
_turn_volatile_var = None
_vram_checkpoint = None
_worker_tools_surface_async = None
_write_skill_md_fire = None
classify_intent = None
LETTA_MEMORY_BACKEND = False
_LETTA_CLIENT = None


_INJECTED = frozenset((
    "LETTA_MEMORY_BACKEND", "_LETTA_CLIENT",
    "ASK_CLARIFY_ENABLE", "AUTONOMOUS_PRIORITY", "AUTO_FORCE_TOOL", "BACKEND", "BACKEND_MODEL",
    "GATEWAY_QUEUE",
    "CLIENT_TOOLS_PASSTHROUGH", "COUNCIL_DEFAULT", "DCI_ENABLED", "KERNEL_ROUTE", "KERNEL_DISPATCH",
    "LOCAL_STATE_FASTPATH", "MAX_DISPATCH_DEPTH", "NATIVE_LOOP_ENABLE",
    "NATIVE_LOOP_MATH_HINT", "PLANNER_ENABLED", "POLISH_ENABLED", "SLOW_LANES",
    "SLOW_LANE_BLOCK_CHARS", "SWARM_DECOMPOSE_DEFAULT",
    "SWARM_DECOMPOSE_MIN_WORDS", "SWARM_MAX_WIDTH", "SWARM_TRUST_ATOMIC", "VISION_ENABLE",
    "VISION_MODEL", "WORKER_TOOLS_ENABLE", "WORKER_TOOL_CTX", "_AGENT_REGISTRY",
    "_BACKEND_IS_LIGHT", "_BACKEND_KEY", "_BROWSER_ACTION_ALT", "_FASTPATH_VERBS",
    "_HOP_HEADER", "_HUMAN_LABELS", "_INGRESS_KEY", "_KERNEL", "_SRC_TURN_HEADER",
    "_THINK_ORPHAN_RE", "_TOOL_BACKEND", "_TOOL_BACKEND_MODEL", "_VERB_CATALOG", "_VIA_HEADER",
    "_agent_contract", "_agent_lane", "_agent_offload_engine",
    "_build_agent_hint", "_call_agent_stream",
    "_casual_agent_label", "_client_env", "_client_env_var", "_conv_key_var",
    "_council_mode_var", "_council_role_lens", "_critic_refine_agent", "_current_year",
    "_db_create", "_db_fire", "_db_post", "_depth_exhausted", "_dispatch_depth",
    "_endpoint_supports_tool_choice", "_expand_facets", "_extract_last_user_text",
    "_filter_relevant_sources", "_get_client",
    "_inline_satisfaction_check", "_is_action_domain", "_lane_tool_cap",
    "_live_agent_names", "_loads_lenient", "_maybe_run_pending_approval",
    "_messages_have_image", "_multi_task_preamble", "_needs_compute",
    "_node_status", "_pick_agent", "_plan_swarm",
    "_rag_enrich", "_read_tool_enrich", "_recall_agent_memory",
    "_role_system", "_route_domain", "_routed_domain_var", "_sanitize_tool_text",
    "_sched_priority", "_scratchpad_key", "_scratchpad_note", "_scratchpad_rehydrate",
    "_scratchpad_render", "_seed_hop_from_headers",
    "_sources_annotations", "_sources_markdown", "_sources_metadata", "_sources_var",
    "_span_id_var", "_src_collected", "_src_record_from_text", "_src_turn_init",
    "_src_turn_key", "_src_turn_var", "_sse_done", "_sse_reasoning", "_sse_status_phase",
    "_strip_owui_scaffold", "_strip_think_tags", "_trace_id_var",
    "_turn_volatile_var", "_vram_checkpoint", "_worker_tools_surface_async",
    "_write_skill_md_fire", "classify_intent",
))


def configure(**deps) -> None:
    """Inject server-side deps under their EXACT original names (one-way boundary).

    Called from ``server.py`` after every injected symbol is defined; re-called by
    ``_reload_membership`` with ``_AGENT_REGISTRY`` on a live agent add/drop. Each
    keyword equals the module global it sets; unknown keys are ignored.
    """
    g = globals()
    if "_KERNEL" in deps and deps["_KERNEL"] is not None:
        deps["_KERNEL"].dispatcher._handlers["chat"] = _kernel_chat_handler
        deps["_KERNEL"].dispatcher._handlers["dispatch"] = _kernel_dispatch_handler
        deps["_KERNEL"].dispatcher._handlers["multi_task"] = _kernel_multi_task_handler
        deps["_KERNEL"].dispatcher._handlers["agent"] = _kernel_agent_handler
    for _k, _v in deps.items():
        if _k in _INJECTED:
            g[_k] = _v


# ── Roster/slow-lane prefix leaf helpers -- moved here from server.py: their
# SOLE consumer is chat_completions_logic, so they live with it instead of being
# injected back (reverse-the-injection). _pretty_name is pure; _trim_sys_prefix
# reads the slow-lane SSOT scalars (SLOW_LANES / SLOW_LANE_BLOCK_CHARS, injected
# by value) + the identity-contract pin (_agent_contract, injected by reference)
# and routes truncation through the tokenizer seam. One-way boundary: this module
# never imports server.
def _pretty_name(n: str) -> str:
    """Display name for roster/credit emits -- strips the internal node:/a2a:
 namespacing so emits never show raw registry keys (
    'NO INTERNAL NAMES')."""
    s = str(n)
    for _pre in ("node:", "a2a:"):
        if s.startswith(_pre):
            return s[len(_pre):]
    return s


def _trim_sys_prefix(sys_prefix: list, lane: str) -> list:
    """Cap each system-prefix block for a SLOW lane ("add
    per-lane context trimming") so a slow-prefill node (iGPU / phone / remote
    accelerator) finishes within its read budget instead of being abandoned
    mid-compute by the big ~7K pipeline web-research block. The gist survives
    (top stories / top RAG hits lead each block); the tail is dropped. gpu + cpu
    (local) keep the FULL prefix. Returns the list unchanged for a fast lane."""
    if lane not in SLOW_LANES or SLOW_LANE_BLOCK_CHARS <= 0:
        return sys_prefix
    # WS-B NEVER truncate the /MiOS.md identity+grounding contract on a
    # slow lane -- it was being cut to ~25% on iGPU/phone/remote, so those council
    # members lost the contract entirely. Identify it BY CONTENT (no non-standard
    # key added to the message dict, so nothing leaks to a strict backend). Only
    # the big web-research / RAG blocks are meant to shrink here.
    _pin = _agent_contract()
    trimmed: list = []
    for m in sys_prefix:
        c = str(m.get("content", ""))
        if _pin and c == _pin:
            trimmed.append(m)
            continue
        if len(c) > SLOW_LANE_BLOCK_CHARS:
            # WS-A5: route through the tokenizer seam (token-budget truncation).
            c = (mios_tokenize.truncate_to_tokens(c, SLOW_LANE_BLOCK_CHARS // 4)
                 + "\n[...trimmed for the light lane...]")
        trimmed.append({**m, "content": c})
    return trimmed


# ── Micro-LLM early-reply helpers (intent=chat reply, memory-hit judge,
# location-ask) -- moved here from server.py: their SOLE consumer is
# chat_completions_logic, so they live with it instead of being injected back.
# Each opens its OWN short-timeout httpx client against the REFINE lane (SSOT
# REFINE_* from mios_config) and degrades open (returns ''/False/a plain
# fallback) on any miss -- never blocks or crashes a turn. One-way boundary:
# this module never imports server.
async def _quick_chat_reply(user_text: str, history: list = None) -> str:
    """Generate the conversational reply for an intent=chat turn.

    Separate from refine because the JSON classifier reliably tags chat
 but does NOT reliably emit a `reply` field (operator test
    greetings classified chat with reply=None -> the turn fell through to
    Hermes, which then tried a nonexistent 'chat' verb). think=False on
    the micro lane; plain prose, GENERATED in the user's language (never
    a canned/hardcoded string)."""
    if not user_text or not user_text.strip():
        return ""
    msgs = [{"role": "system",
             "content": ("You are MiOS AI. Reply to the user directly and "
                         "concisely, in ENGLISH by default -- switch to "
                         "another language ONLY if the user's own message "
                         "is clearly written in it. Never drift to a "
                         "language the user did not use. Plain text only -- "
                         "no tools, no JSON.\n\n" + _env_grounding())}]
    if history:
        for h in history[-2:]:
            if isinstance(h, dict) and h.get("role") in ("user", "assistant"):
                msgs.append({"role": h["role"],
                             "content": mios_tokenize.truncate_to_tokens(
                                 str(h.get("content", "")), 50)})  # WS-A5 seam (was [:200])
    msgs.append({"role": "user", "content": user_text[:500]})
    # OpenAI /v1 (mios-llm-light :11450). The old ollama /api/chat 404'd post
    # ollama-retirement -> refine returned "" = NO refined routing/decompose/
    # grounding hints, silently degrading every turn.
    payload = {
        "model": REFINE_MODEL,
        "messages": msgs,
        "stream": False,
        "temperature": 0.5,
        # 1024 (was 200): gemma4:12b is the REASONING model -- 200 tokens truncate
        # mid-reasoning so the classification JSON is incomplete -> mis-parse
        # (e.g. local_state=true on a research comparison) -> wrong route. Give it
        # room to finish reasoning + emit the full JSON..
        "max_tokens": 1024,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    try:
        async with httpx.AsyncClient(timeout=REFINE_TIMEOUT_S) as s:
            r = await s.post(f"{REFINE_ENDPOINT}/v1/chat/completions", json=payload,
                             headers={"Content-Type": "application/json"})
            if r.status_code != 200:
                return ""
            body = r.json()
    except Exception:
        return ""
    msg = (((body.get("choices") or [{}])[0]).get("message")
           if isinstance(body, dict) else {}) or {}
    # gemma4 (reasoning model) sometimes emits to reasoning_content with empty
    # content -> fall back so refine doesn't silently return "".
    return (msg.get("content") or msg.get("reasoning_content") or "").strip()


async def _is_memory_question(user_text: str, facts: str) -> bool:
    """FOCUSED yes/no judge (using REFINE_MODEL) to verify if the user's question
    is ACTUALLY asking for the retrieved facts, to prevent false-positive
    deterministic short-circuits. Robust to synonyms and weak structural overlaps."""
    if not facts or not facts.strip():
        return False
    try:
        msgs = [{"role": "system",
                 "content": ("You are a strict YES/NO judge. The user is asking a question. "
                             "Does the following saved fact directly answer the user's question? "
                             "Reply with ONLY 'YES' or 'NO'.\n\nFacts:\n" + facts)},
                {"role": "user", "content": (user_text or "")[:500]}]
        payload = {"model": REFINE_MODEL, "messages": msgs,
                   "stream": False, "temperature": 0.1, "max_tokens": 10}
        async with httpx.AsyncClient(timeout=3.0) as s:
            r = await s.post(f"{REFINE_ENDPOINT}/v1/chat/completions", json=payload,
                             headers={"Content-Type": "application/json"})
            if r.status_code == 200:
                _lm = (((r.json().get("choices") or [{}])[0]).get("message") or {})
                ans = str(_lm.get("content") or "").strip().upper()
                return "YES" in ans
    except Exception:  # noqa: BLE001
        pass
    return False


async def _ask_for_location(user_text: str) -> str:
    """Brief reply asking the user for their city when the request NEEDS their
 physical location but none was forwarded this session (
    "check the weather for tomorrow" must ASK, never fabricate a city -- it
    invented "San Fernando del Valle de Catamarca, Argentina"). GENERATED in the
    user's language; NEVER guesses a location. Falls back to a sane default."""
    try:
        msgs = [{"role": "system", "content":
                 ("You are MiOS AI. The user's request needs their physical "
                  "location, but none was shared this session. Reply BRIEFLY (1-2 "
                  "sentences): say you can help but need their city/area, and ask "
                  "them to name it. Do NOT guess, assume, or state ANY city or "
                  "country. Reply in the user's language -- English by default, "
                  "match the user's language only if their message is clearly in "
                  "it. Plain text only.")},
                {"role": "user", "content": (user_text or "")[:500] + " /no_think"}]
        payload = {"model": REFINE_MODEL, "messages": msgs,
                   "stream": False, "temperature": 0.3, "max_tokens": 200}
        async with httpx.AsyncClient(timeout=REFINE_TIMEOUT_S) as s:
            r = await s.post(f"{REFINE_ENDPOINT}/v1/chat/completions", json=payload,
                             headers={"Content-Type": "application/json"})
            if r.status_code == 200:
                _lm = ((r.json().get("choices") or [{}])[0]).get("message") or {}
                c = (_lm.get("content") or _lm.get("reasoning_content") or "").strip()
                c = re.sub(r"<think>.*?</think>\s*", "", c,
                           flags=re.DOTALL | re.IGNORECASE).strip()
                if c:
                    return c
    except Exception:  # noqa: BLE001
        pass
    return ("I can help with that — but I don't have your location this session. "
            "Which city or area should I use?")


# ── Refine-driven orchestration helpers -- moved here from server.py: their SOLE
# consumer is chat_completions_logic, so they live with it instead of being
# injected back (reverse-the-injection). _hints_write_action is pure over the
# injected verb catalog; _needs_external_knowledge is a micro-LLM judge (SSOT
# ROUTER_/PLANNER_* from mios_config, the injected lenient-JSON loader) sharing the
# degrade-open shape of the early-reply judges above; _shadow_queue_tasks upserts
# the canonical pg kanban (mios_pg) via the injected event-DB writers. One-way
# boundary: this module never imports server.
def _hints_write_action(refined: "Optional[dict]") -> bool:
    """True when refine hinted a state-changing (NON-read permission) verb -- the
    turn INTENDS an action, so the executor should be FORCED to emit the call
    rather than narrate it. Data-driven by verb permission (no English action-
    word list, per the no-hardcode binding). Skips chat-class turns."""
    if not isinstance(refined, dict):
        return False
    if refined.get("intent") not in ("agent", "multi_task", "dispatch"):
        return False
    for h in (refined.get("hint_tools") or []):
        perm = str((_VERB_CATALOG.get(str(h).strip()) or {}).get(
            "permission", "")).lower()
        if perm and perm != "read":
            return True
    return False


async def _needs_external_knowledge(user_text: str) -> bool:
    """Generative knowledge-gap judge ("use web tools for
    knowledge gaps EVERY TURN"; NO keyword lists). For a LOCAL-STATE turn, decide
    whether FULLY answering ALSO requires facts that exist only OFF this machine --
    published/theoretical specs, benchmarks, capabilities, ratings, reviews, prices,
    or whether an installed version is the latest. Inspecting the machine yields its
    own identity/state (which GPU/CPU/app it HAS, live usage) but NOT such external
    facts, so a small model collapses "the theoretical specs of MY GPU" to local-only
    and then DROPS or FABRICATES the external half. A focused yes/no (constrained
    enum, thinking-off) is far more reliable than asking the big refine call to juggle
    local+web. True only on a confident yes; degrade-CLOSED (error/None -> False =
    unchanged pure-local behaviour, so 'what's open'/'list my games' never web-search)."""
    if not (user_text or "").strip():
        return False
    sys = (
        "A query about THIS local machine was received. Inspecting this machine "
        "reveals its OWN state + identity (which CPU/GPU/app/version it HAS, and live "
        "usage) but NOT external knowledge ABOUT those things. Decide, by MEANING not "
        "keywords: to FULLY answer the user, is EXTERNAL knowledge required that "
        "CANNOT be obtained by inspecting this machine -- e.g. a component's "
        "published or theoretical specifications, benchmarks, capabilities, ratings, "
        "reviews, prices, or whether an installed version is the newest? Examples: "
        "'what's open' / 'what GPU do I have' / 'list my games' / 'check service "
        "status' -> false (its own identity/state is the whole answer). 'the "
        "theoretical performance of my GPU' / 'is my installed X the latest version' "
        "/ 'how good is my CPU for AI' -> true (needs off-machine facts).")
    payload = {
        "model": ROUTER_MODEL,
        "messages": [{"role": "system", "content": sys},
                     {"role": "user", "content": user_text[:2000]}],
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "kgap", "strict": True, "schema": {
                "type": "object",
                "properties": {"needs_external": {"type": "boolean"}},
                "required": ["needs_external"], "additionalProperties": False}}},
        "chat_template_kwargs": {"enable_thinking": False},
        "temperature": 0.0, "max_tokens": 30, "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=PLANNER_TIMEOUT_S) as s:
            r = await s.post(f"{PLANNER_ENDPOINT}/v1/chat/completions", json=payload,
                             headers={"Content-Type": "application/json"})
        if r.status_code != 200:
            return False
        content = ((r.json().get("choices") or [{}])[0].get("message", {})
                   .get("content") or "")
        return (_loads_lenient(content) or {}).get("needs_external") is True
    except Exception as e:  # noqa: BLE001 -- degrade-CLOSED (-> pure-local, unchanged)
        log.debug("knowledge-gap judge failed (-> local-only): %s", e)
        return False


def _shadow_queue_tasks(tasks: list[dict],
                        session_id: Optional[str]) -> list[dict]:
    """Write one row per refined multi-task entry to the CANONICAL pg `kanban`
    table. Returns the same list augmented with `hermes_task_id` so the
    dispatcher + polish can refer to each row by id.

    WS-A3: this was the SurrealDB `kanban_shadow` shadow-queue, which silently
    no-op'd once SurrealDB (:8000) was retired (and whose pg mirror targeted a
    `kanban_shadow` table that doesn't exist) -- so the multi-task queue was
    invisible. It now upserts the canonical pg `kanban` (id/title/status/detail
    jsonb) via a PARAMETERIZED statement (psycopg binds values; never spliced),
    giving every agent a single pg-visible queue. Hermes (or whichever sub-agent
    picks up a task) syncs its native kanban entry back via the existing path."""
    if not isinstance(tasks, list) or not tasks:
        return []
    out: list[dict] = []
    for i, t in enumerate(tasks):
        if not isinstance(t, dict):
            continue
        # Stable id so the same task in a retried request collapses onto the
        # same kanban row (id is the PK -> ON CONFLICT upserts the latest status).
        tid = (
            "mt-"
            + (session_id or "anon")[:12].replace(":", "")
            + "-"
            + f"{i:02d}"
        )
        title = str(t.get("title") or t.get("refined_text") or "")[:200]
        # First task -> in_progress; rest -> todo. The dispatcher
        # immediately runs index 0, so its status reflects that.
        status = "in_progress" if i == 0 else "todo"
        prio = t.get("priority")
        prio_str = str(prio) if prio is not None else None
        detail = json.dumps({
            "hermes_task_id": tid,
            "priority": prio_str,
            "tags": ["multi_task", "agent-pipe-refined"],
            "session_id": session_id,
        }, default=str)
        # Parameterized upsert into the canonical pg kanban table (degrade-open
        # via mios_pg; fire-and-forget so streaming is never delayed).
        _db_fire(_mios_pg.execute(
            "INSERT INTO kanban (id, title, status, detail) "
            "VALUES (%(id)s, %(title)s, %(status)s, %(detail)s::jsonb) "
            "ON CONFLICT (id) DO UPDATE SET title = EXCLUDED.title, "
            "status = EXCLUDED.status, detail = EXCLUDED.detail, ts = now()",
            {"id": tid, "title": title, "status": status, "detail": detail},
            fetch=False))
        out.append({**t, "hermes_task_id": tid, "status": status})
    _db_fire(_db_post(_db_create("event", {
        "source": "mios-agent-pipe",
        "kind": "multi_task_queued",
        "severity": "info",
        "summary": f"queued {len(out)} tasks from refine",
        "payload": {"task_ids": [t["hermes_task_id"] for t in out],
                    "titles": [t.get("title", "") for t in out]},
    }, now_fields=("ts",))))
    return out


# ── W0-T3 aggregate token/turn budget + autonomous isolation (the missing
# runaway tripwire). The per-generation num_predict cap + the per-turn wall-clock
# bound the latency of ONE turn, but nothing bounded the AGGREGATE compute a
# single conversation -- or, worse, an UNATTENDED autonomous source firing on a
# timer -- could rack up over a window. A wedged cron loop (the 3x OOM wedges)
# could re-fire research turns indefinitely with no human present. This adds a
# time-windowed token ledger debited per conversation AND per autonomous source;
# when a bucket exhausts its ceiling, NEW dispatch HARD-HALTS (a graceful "budget
# exhausted" answer) instead of dispatching more compute. This admission cluster
# is a chat-turn concern (the only consumer is chat_completions_logic's admit/
# release), so it lives HERE rather than being injected back from server.py.
#
# DEGRADE-OPEN + GENEROUS DEFAULTS: the ceilings default LARGE so normal
# interactive use never trips; only a runaway/looping source hits them. ANY error
# in the ledger fails OPEN (dispatch proceeds) -- the budget is a backstop, never
# allowed to block a legitimate turn on a bookkeeping bug. SSOT [budget].*.
_BUDGET_TOML = _toml_section("budget")


def _budget_num(env: str, key: str, default, cast=int):
    """env override -> mios.toml [budget].<key> -> literal default (preserves 0)."""
    return _cfg_num(_BUDGET_TOML, env, key, default, cast)


# Per-conversation aggregate token ceiling over the rolling window. Generous:
# a normal interactive chat (refine + council + polish over a window) is well
# under this; a wedged/looping conversation that keeps re-dispatching trips it.
BUDGET_CONV_TOKEN_CEIL = _budget_num(
    "MIOS_BUDGET_CONV_TOKEN_CEIL", "conversation_token_ceil", 2_000_000)
# Per-autonomous-source aggregate token ceiling over the window. SEPARATE bucket
# from the conversation ledger: an unattended cron/timer source is bounded on its
# OWN aggregate so a misfiring schedule can't burn the host with no human present.
BUDGET_AUTO_TOKEN_CEIL = _budget_num(
    "MIOS_BUDGET_AUTO_TOKEN_CEIL", "autonomous_token_ceil", 1_000_000)
# Max CONCURRENT in-flight autonomous turns across ALL autonomous sources. A
# foreground turn always preempts (its priority is unchanged); this only caps how
# many BACKGROUND turns dispatch at once so a runaway scheduler can't stack turns.
BUDGET_AUTO_MAX_INFLIGHT = _budget_num(
    "MIOS_BUDGET_AUTO_MAX_INFLIGHT", "autonomous_max_inflight", 2)
# Rolling window (seconds) over which the token ledgers accumulate. Old debits
# outside the window age out so a long-lived conversation isn't permanently
# starved -- the ceiling bounds RATE, not lifetime total.
BUDGET_WINDOW_S = _budget_num("MIOS_BUDGET_WINDOW_S", "window_s", 3600, float)
# Master switch. Default ON but with ceilings so generous it's a pure backstop;
# set false to disable the tripwire entirely (degrade to pre-T3 behaviour).
BUDGET_ENABLE = str(os.environ.get(
    "MIOS_BUDGET_ENABLE",
    str(_BUDGET_TOML.get("enable", "true")))).strip().lower() not in {"0", "false", "no"}

# key -> deque[(monotonic_ts, tokens)] rolling-window ledgers. Two namespaces:
# "conv:<conv_key>" and "auto:<source>". OrderedDict so stale buckets LRU-evict.
_BUDGET_LEDGER: "collections.OrderedDict" = collections.OrderedDict()
_BUDGET_LEDGER_MAX = int(os.environ.get("MIOS_BUDGET_LEDGER_MAX", "1024"))
# Per-turn token ESTIMATE debited at admission (debit-on-admit). The actual
# usage is unknown until the turn finishes (and a streaming turn returns the
# generator BEFORE it runs), so we debit a conservative per-turn estimate up
# front; the rolling window ages it out. This makes the ledger a RATE limiter on
# the NUMBER of turns a source/conversation fires per window (the runaway shape)
# without instrumenting every return path. Generous default keeps the ceilings
# reachable only by a genuinely looping source. SSOT [budget].per_turn_estimate.
BUDGET_PER_TURN_ESTIMATE = _budget_num(
    "MIOS_BUDGET_PER_TURN_ESTIMATE", "per_turn_estimate", 8192)
# token -> monotonic_ts of in-flight autonomous turns. A TTL dict (not a set) so
# a crashed/abandoned turn's token AGES OUT instead of leaking a slot forever
# (the streaming path returns the generator before the turn ends -> no reliable
# explicit-removal point). Pruned on each admission. TTL >> a normal turn.
_BUDGET_AUTO_INFLIGHT: dict = {}
BUDGET_INFLIGHT_TTL_S = _budget_num(
    "MIOS_BUDGET_INFLIGHT_TTL_S", "inflight_ttl_s", 900, float)
_BUDGET_LOCK = asyncio.Lock()


def _budget_bucket(key: str) -> "collections.deque":
    dq = _BUDGET_LEDGER.get(key)
    if dq is None:
        dq = collections.deque()
        _BUDGET_LEDGER[key] = dq
        while len(_BUDGET_LEDGER) > max(16, _BUDGET_LEDGER_MAX):
            _BUDGET_LEDGER.popitem(last=False)
    else:
        _BUDGET_LEDGER.move_to_end(key)
    return dq


def _budget_window_total(key: str, now: float) -> int:
    """Sum tokens debited to `key` within the rolling window; ages out the rest."""
    dq = _BUDGET_LEDGER.get(key)
    if not dq:
        return 0
    cutoff = now - BUDGET_WINDOW_S
    while dq and dq[0][0] < cutoff:
        dq.popleft()
    return sum(t for _ts, t in dq)


def _budget_debit(key: str, tokens: int, now: Optional[float] = None) -> None:
    """Record `tokens` against `key`'s window ledger (best-effort, degrade-open)."""
    if not BUDGET_ENABLE or tokens <= 0:
        return
    try:
        _now = now if now is not None else time.monotonic()
        _budget_bucket(key).append((_now, int(tokens)))
    except Exception:  # noqa: BLE001 -- ledger is a backstop, never crashes a turn
        log.debug("budget debit failed for %s", key, exc_info=True)


def _budget_prune_inflight(now: float) -> None:
    """Drop in-flight autonomous tokens older than the TTL (crash/abandon safety;
    caller holds _BUDGET_LOCK)."""
    if not _BUDGET_AUTO_INFLIGHT:
        return
    cutoff = now - BUDGET_INFLIGHT_TTL_S
    for tok in [t for t, ts in _BUDGET_AUTO_INFLIGHT.items() if ts < cutoff]:
        _BUDGET_AUTO_INFLIGHT.pop(tok, None)


async def _budget_admit(conv_key: str, autonomous_source: Optional[str],
                        turn_token: Optional[str] = None) -> tuple:
    """Aggregate-budget admission for a NEW turn. Returns (allowed, reason).

    HARD-HALTS (allowed=False) when the conversation OR the autonomous-source
    token ceiling is already exhausted within the window, or when the concurrent
    autonomous in-flight cap is reached. On ADMIT it debit-on-admits a
    conservative per-turn estimate to both relevant buckets and (for an
    autonomous turn with a turn_token) registers the turn in-flight -- so the
    NEXT turn for an exhausted bucket is refused, which is the runaway tripwire
    (it stops the SOURCE re-firing). DEGRADE-OPEN: any error -> allowed.

    The check is BEFORE this turn's real tokens are known; the rolling window
    ages the estimate out, so the ceiling bounds the RATE of turns per window."""
    if not BUDGET_ENABLE:
        return True, ""
    try:
        now = time.monotonic()
        async with _BUDGET_LOCK:
            conv_used = _budget_window_total("conv:" + conv_key, now)
            if BUDGET_CONV_TOKEN_CEIL > 0 and conv_used >= BUDGET_CONV_TOKEN_CEIL:
                return False, ("conversation token budget exhausted "
                               f"({conv_used}/{BUDGET_CONV_TOKEN_CEIL} in "
                               f"{int(BUDGET_WINDOW_S)}s)")
            if autonomous_source:
                _budget_prune_inflight(now)
                auto_used = _budget_window_total("auto:" + autonomous_source, now)
                if (BUDGET_AUTO_TOKEN_CEIL > 0
                        and auto_used >= BUDGET_AUTO_TOKEN_CEIL):
                    return False, ("autonomous token budget exhausted "
                                   f"({auto_used}/{BUDGET_AUTO_TOKEN_CEIL} in "
                                   f"{int(BUDGET_WINDOW_S)}s)")
                if (BUDGET_AUTO_MAX_INFLIGHT > 0
                        and len(_BUDGET_AUTO_INFLIGHT) >= BUDGET_AUTO_MAX_INFLIGHT):
                    return False, ("autonomous concurrency limit reached "
                                   f"({len(_BUDGET_AUTO_INFLIGHT)}/"
                                   f"{BUDGET_AUTO_MAX_INFLIGHT} in flight)")
            # ADMITTED -> debit-on-admit + register in-flight (atomic under lock).
            _budget_debit("conv:" + conv_key, BUDGET_PER_TURN_ESTIMATE, now)
            if autonomous_source:
                _budget_debit("auto:" + autonomous_source,
                              BUDGET_PER_TURN_ESTIMATE, now)
                if turn_token:
                    _BUDGET_AUTO_INFLIGHT[turn_token] = now
        return True, ""
    except Exception:  # noqa: BLE001 -- degrade-open: never block a turn on a bug
        log.warning("budget admit check failed, degrading open", exc_info=True)
        return True, ""


async def _budget_release_inflight(turn_token: Optional[str]) -> None:
    """Drop an autonomous turn's in-flight token (best-effort; degrade-open).
    Idempotent. The autonomous turn registers in-flight in _budget_admit; this
    is the PROMPT release for paths that have a clean terminal point. The
    leak-proof backstop is _budget_prune_inflight (TTL): the streaming path
    returns its generator BEFORE the turn truly ends, so there is no single
    reliable removal point in the giant handler -- the TTL guarantees no slot
    leaks even when no explicit release fires."""
    if not turn_token:
        return
    try:
        async with _BUDGET_LOCK:
            _BUDGET_AUTO_INFLIGHT.pop(turn_token, None)
    except Exception:  # noqa: BLE001
        log.debug("budget inflight release failed for %s", turn_token, exc_info=True)


async def chat_completions_logic(request: Request) -> Any:
    try:
        body_bytes = await request.body()
        body = _loads_lenient(body_bytes.decode("utf-8", errors="replace")) if body_bytes else {}
    except json.JSONDecodeError:
        return JSONResponse(
            content={"error": {"message": "invalid JSON body",
                               "type": "invalid_request_error"}},
            status_code=400,
        )

    streaming = bool(body.get("stream", False))
    messages = body.get("messages") or []
    if not messages or not isinstance(messages, list):
        # Tier-0 conformance: a request with no usable `messages` returns a clean
        # OpenAI error object (was crashing downstream -> connection drop / HTTP 000).
        return JSONResponse(
            content={"error": {"message": "you must provide a 'messages' array",
                               "type": "invalid_request_error",
                               "param": "messages", "code": None}},
            status_code=400)

    # Strip duplicate canonical/default system prompts sent by the client
    # to prevent prompt duplication on the orchestrator.
    if isinstance(messages, list):
        filtered_messages = []
        for m in messages:
            if isinstance(m, dict) and m.get("role") == "system":
                content = str(m.get("content") or "")
                if ("# MiOS Grounding / Knowledge Base" in content
                        or "Operate under `/MiOS.md`." in content
                        or "You are the MiOS local agent." in content):
                    log.info("Stripped duplicate/canonical client system prompt from request messages")
                    continue
            filtered_messages.append(m)
        messages = filtered_messages
        body["messages"] = messages

    last_user_text = _extract_last_user_text(messages)
    # UN-TEMPLATE : if OWUI wrapped the question in its RAG
    # task template ("### Task: Respond to the user query using the provided
    # context ... <user_query>REAL Q</user_query>"), recover the real question
    # BEFORE it seeds refine / the swarm titles / per-node prompts / synthesis.
    # Rewrite the last user message in-place too, so refine_intent(messages) and
    # any node that consumes the raw history see the clean query, not the
    # boilerplate that tells them to RAG-answer instead of calling tools.
    _clean_user = _strip_owui_scaffold(last_user_text)
    if _clean_user != last_user_text:
        log.info("un-templated OWUI task scaffold: %d -> %d chars",
                 len(last_user_text), len(_clean_user))
        for _i in range(len(messages) - 1, -1, -1):
            _m = messages[_i]
            if isinstance(_m, dict) and _m.get("role") == "user" \
                    and isinstance(_m.get("content"), str):
                messages[_i] = {**_m, "content": _clean_user}
                break
        last_user_text = _clean_user
    model = body.get("model") or BACKEND_MODEL
    chat_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    # Per-chat scratchpad key from the forwarded OpenAI metadata.chat_id
    # (stable across this conversation's turns); falls back to a per-request
    # id for non-OWUI callers. Read by _scratchpad_note/_render downstream.
    _conv_key_var.set(_scratchpad_key(body, chat_id))
    # WS-A2: rehydrate this chat's working memory from the durable pg `scratch`
    # table on the first turn after a restart (once per chat key; degrade-open).
    await _scratchpad_rehydrate(_conv_key_var.get())
    if LETTA_MEMORY_BACKEND and _LETTA_CLIENT:
        try:
            import mios_tokenize
            _tok_count = mios_tokenize.count_messages(messages)
            _letta_ctx_limit = 8000
            _fill = _tok_count / _letta_ctx_limit
            _session_id = _conv_key_var.get() or "default"
            if _fill >= 1.0:
                log.info("Letta context fill >= 100%% (%d tokens), triggering oldest context message flush", _tok_count)
                await _LETTA_CLIENT.sync_to_pg(_session_id, lambda table, fields: _db_fire(_db_post(_db_create(table, fields, now_fields=("ts",)))))
                await _LETTA_CLIENT.flush_oldest(_session_id)
            elif _fill >= 0.7:
                log.info("Letta context fill >= 70%% (%d tokens), triggering native summarization loop", _tok_count)
                await _LETTA_CLIENT.trigger_compaction(_session_id)
        except Exception as _letta_err:
            log.warning("Letta memory context threshold logic failed: %s", _letta_err)
    # ASK-TO-RUN approval round-trip : if a high-tier action was
    # PROPOSED on a prior turn of THIS chat (a pending_action keyed by the conv key) and
    # the user's reply APPROVES it (MODEL-classified, no keyword list), execute it now and
    # return -- before refine/dispatch. The judge runs ONLY when a proposal is pending, so
    # a normal turn pays nothing. The portable text/metadata proposal is rendered as a
    # NATIVE prompt by the OWUI pipe + Hermes app; this is the server-side round-trip.
    try:
        _atr = await _maybe_run_pending_approval(
            last_user_text, _conv_key_var.get(),
            chat_id=chat_id, model=model, streaming=streaming)
        if _atr is not None:
            return _atr
    except Exception as _atre:  # noqa: BLE001 -- never break the turn on the approval path
        log.debug("ask-to-run approval check skipped: %s", _atre)
    # Turn-scoped REAL-SOURCE collector : every web_search this
    # turn -- native loop, council secondaries, DAG workers -- records its result URLs
    # here (child asyncio tasks inherit this contextvar), and the final answer attaches
    # a real **Sources:** list + structured mios_sources metadata, so sources are
    # grounded metadata, never model-invented prose.
    _sources_var.set([])
    # WS-A8: adopt an inbound X-MiOS-Trace header (continue an upstream caller's
    # trace) or mint a fresh trace id for this request. Pipeline stages open
    # child spans under it; the id is propagated outbound to the Hermes hop.
    _inbound_trace = (request.headers.get("x-mios-trace") or "").strip()
    _trace_id_var.set(_inbound_trace or mios_trace.new_trace_id())
    _span_id_var.set("")
    # P0 cross-hop recursion bound: seed the dispatch depth + Via chain from the
    # incoming headers so the runaway-loop guard survives the HTTP hop (a worker that
    # re-enters :8640 inherits the upstream depth + is degrade-closed if it sees its
    # own id in the chain). Degrade-open when absent (== single-process behaviour).
    _seed_hop_from_headers(request.headers.get(_HOP_HEADER),
                           request.headers.get(_VIA_HEADER))
    _incoming_turn = request.headers.get(_SRC_TURN_HEADER)
    if _incoming_turn:
        # SUB-request dispatched by a council/DAG node: inherit the parent turn so
        # our web_search sources land in the PARENT's registry bucket. Do NOT
        # re-init (that would wipe the parent's already-collected sources).
        _src_turn_var.set(_incoming_turn)
    else:
        # TOP-LEVEL turn: pin the turn-id (= conv key) and open a fresh bucket.
        _src_turn_var.set(_src_turn_key())
        _src_turn_init()
    # Per-request client environment (location / timezone / locale / time)
    # the OWUI pipe forwarded as metadata.variables. Threaded into every
    # grounded prompt via _env_grounding so "near me" resolves + "today"/
    # "tomorrow" use the USER's wall clock.
    _client_env_var.set(_client_env(body, request.headers))
    # Stage-1 domain router: classify ONCE per request (thinking-off enum); all
    # paths (planner + tool-loop + swarm) read _routed_domain_var to shrink the
    # verb surface to this domain. None (router off / unsure) -> full surface.
    _routed_domain_var.set(await _route_domain(last_user_text))
    # SWARM toggles : per-request force flags set by the
    # OWUI chat-bar toggle-filters, injected into body.mios_flags and
    # forwarded here verbatim by the pipe. They OVERRIDE the mios.toml SSOT
    # defaults for THIS turn only (the tool_choice-style 'forced vs natural'
    # control). Stripped from proxy_body before Hermes sees it.
    #   force_council  -> engage the FULL swarm (every eligible agent)
    #   force_delegate -> force per-agent DAG decomposition (swarm planner)
    #   force_tool     -> tool_choice=required on the executor (anti-narrate)
    _mflags = body.get("mios_flags")
    _mflags = _mflags if isinstance(_mflags, dict) else {}
    _force_council = bool(_mflags.get("force_council"))
    _force_delegate = bool(_mflags.get("force_delegate"))
    _force_tool = bool(_mflags.get("force_tool"))
    if _mflags:
        log.info("swarm flags: council=%s delegate=%s tool=%s",
                 _force_council, _force_delegate, _force_tool)
    # AUTONOMOUS turn (wedge fix): a cron/timer-fired run
    # (mios-scheduled-research, @<prompt> briefings) sets metadata.mios_autonomous.
    # Such a turn fires UNATTENDED, so it must NEVER trigger the WIDE research
    # fan-out (the swarm DAG OR the council pulling in every 2-4GB research_only
    # worker across all lanes) -- that periodic cold-load storm is exactly what
    # OOM-wedged the VM 3x with no human present. Read ONCE here; gate BOTH the
    # swarm-DAG path (_is_research) AND the council path on it.
    _meta_top = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}
    _autonomous = bool(_meta_top.get("mios_autonomous"))
    # W0-T3 per-autonomous-source budget key: prefer a finer identifier (the
    # cron rule / schedule id) when the source provides one, so distinct
    # schedules get distinct ceilings; else all autonomous turns share one
    # "autonomous" aggregate bucket. Only meaningful when _autonomous is set.
    _autonomous_source = None
    if _autonomous:
        _autonomous_source = str(
            _meta_top.get("mios_source") or _meta_top.get("rule_id")
            or _meta_top.get("schedule_id") or _meta_top.get("cron_id")
            or "autonomous")
        log.info("AUTONOMOUS turn (source=%s) -> bounded (no wide research fan-out on either path)",
                 _autonomous_source)
    # Operator-facing persona + environment/language/locale guidance the
    # OWUI pipe injected as system message(s). Captured once so the final
    # polish can apply the operator's voice + the correct language
    # ("polish the final response with persona
    # applied"). Joined; polish frames it as STYLE-only.
    _persona_system = "\n\n".join(
        str(m.get("content") or "").strip()
        for m in messages
        if isinstance(m, dict) and m.get("role") == "system"
        and str(m.get("content") or "").strip()
    )[:2000]

    # VISION: an image-bearing turn can't be served by the text executor --
    # route it DIRECTLY to the local VLM, bypassing
    # refine / planning / Hermes. No session or refine overhead.
    if VISION_ENABLE and _messages_have_image(messages):
        log.info("vision: image turn -> %s", VISION_MODEL)
        return await _vision_complete(body, streaming, chat_id, model)

    # CLIENT-SIDE TOOL-CALLING passthrough (Zen smart-window):
    # a caller that supplied its OWN tools[] (browser/IDE assistants) executes them
    # itself and expects tool_calls back -- bypass orchestration and relay verbatim
    # to a tool-capable backend. Placed AFTER vision (an image turn needs the VLM)
    # and BEFORE session/refine/council so client tools are never dropped as
    # "hallucinations" nor executed server-side. Invisible to OWUI (strips tools)
    # and the mios CLI (Hermes-direct) -> they never set tools[]. See the config
    # block + _client_tools_complete.
    if CLIENT_TOOLS_PASSTHROUGH and _has_client_tools(body):
        if _INGRESS_KEY:
            _auth = (request.headers.get("authorization") or "")
            if _auth.removeprefix("Bearer ").strip() != _INGRESS_KEY:
                return JSONResponse(
                    content={"error": {"message": "unauthorized",
                                       "type": "invalid_request_error"}},
                    status_code=401)
        # DETERMINISTIC OS-ACTION PRECEDENCE ("UNIFY"): an
        # unambiguous single OS action ("open X" / "type 'Y'") must take the
        # SERVER-SIDE deterministic fast-path (launch + read-back-verified type-chain)
        # EVEN when the caller supplied client tools -- otherwise the hermes REPL /
        # desktop app's tools force the weak client-tools-HYBRID loop (granite) for an
        # action the orchestrator handles reliably (the REPL's "open notepad and type
        # X" took the hybrid path + the literal-text/echo failures). Only the
        # UNAMBIGUOUS deterministic route is intercepted; browser/IDE tool turns
        # (navigate/click/edit) don't match it -> they still pass through untouched.
        _ct_user = ""
        for _m in reversed(body.get("messages") or []):
            if isinstance(_m, dict) and _m.get("role") == "user" and isinstance(_m.get("content"), str):
                _ct_user = _m["content"]
                break
        _ct_det = _deterministic_action_route(_ct_user) if _ct_user else None
        if _ct_det and str(_ct_det.get("tool") or "") in _FASTPATH_VERBS:
            log.info("client-tools: deterministic OS-action %s -> SERVER-SIDE "
                     "fast-path (bypassing client-tools hybrid)", _ct_det["tool"])
            return await _respond_os_control(
                _ct_det["tool"], _ct_det.get("args") or {}, _ct_det,
                streaming=streaming, chat_id=chat_id, model=model,
                session_id=None, last_user_text=_ct_user, persona_system="")
        # WEB-GROUND a research turn on the client-tools path too (operator
        # anti-fabrication): the hybrid loop has the web_search tool but a small model
        # ANSWERS FROM MEMORY instead of calling it -> fabrication (the unified hermes
        # REPL said "latest kernel 6.12.1" vs the live 7.1). When the turn already
        # routed to the `web` domain (_routed_domain_var, classified above), PRE-FETCH
        # web_search + inject the LIVE results -- the SAME deterministic grounding the
        # native-loop uses -- so the client-tools model synthesises from real data.
        # Degrade-open; non-web client-tools turns (browser/IDE) are untouched.
        if _ct_user and _routed_domain_var.get(None) == "web":
            try:
                _refined = await refine_intent(_ct_user)
                if not _refined or _refined.get("intent") != "chat":
                    _search_q = str((_refined or {}).get("refined_text") or "").strip() or _ct_user
                    _time_sensitive = bool((_refined or {}).get("news")) or any(
                        re.search(r"\b" + re.escape(w) + r"\b", _search_q.lower())
                        for w in ["today", "todays", "recent", "recently", "latest", "now", "current", "this week", "this month", "yesterday", "breaking", "trending"]
                    )
                    if _time_sensitive and not re.search(r"\b(?:19|20)\d{2}\b", _search_q):
                        _search_q = f"{_search_q} {_current_year()}".strip()
                        if isinstance(_refined, dict):
                            _refined["refined_text"] = _search_q
                    _wtext = await _web_research_enrich(_search_q, _refined)
                    if _wtext.strip():
                        body = dict(body)
                        body["messages"] = list(body.get("messages") or []) + [{
                            "role": "system", "content": _wtext}]
                        log.info("client-tools: web-grounded research turn "
                                 "(prefetched deep web_research, anti-fabrication)")
            except Exception as _e:  # noqa: BLE001 -- degrade-open
                log.debug("client-tools web prefetch skipped: %s", _e)
        # FILE-SEARCH GROUND a files-domain turn on the client-tools path (operator
        #): a multi-step "find the mios.toml, read it, tell me the port"
        # made the granite hybrid LOOP without converging -> "no final response". A
        # filename token in the ask -> PRE-FETCH the real path(s) (everything_search=
        # Windows, fs_search=Linux) + inject, so the model can read_file the ACTUAL
        # path directly (one step, converges) instead of tool-looping a discovery it
        # answers from memory. Same pattern as the native-loop file prefetch + the
        # web grounding above. Degrade-open; non-files turns untouched.
        if _ct_user and _routed_domain_var.get(None) == "files":
            _mfn = (re.search(r"['\"]([^'\"]+\.[A-Za-z0-9]{1,8})['\"]", _ct_user)
                    or re.search(r"\b([\w.+-]+\.[A-Za-z0-9]{1,8})\b", _ct_user))
            _fn = _mfn.group(1).strip() if _mfn else None
            if _fn:
                _hits = []
                for _sv in ("everything_search", "fs_search"):
                    if _sv not in _VERB_CATALOG:
                        continue
                    try:
                        _sr = await dispatch_mios_verb(_sv, {"query": _fn},
                                                       session_id=None)
                        _st = (str(_sr.get("output") or _sr.get("result") or _sr)
                               if isinstance(_sr, dict) else str(_sr or "")).strip()
                        if _st and _st not in ("{}", "null", "[]", '""'):
                            _hits.append(_sv + " -> " + _st[:1500])
                    except Exception:  # noqa: BLE001 -- degrade-open
                        pass
                if _hits:
                    body = dict(body)
                    body["messages"] = list(body.get("messages") or []) + [{
                        "role": "system", "content":
                        "LIVE local file-search results for '" + _fn + "' on THIS "
                        "machine (real paths). To answer, read_file the ACTUAL path "
                        "below; do NOT invent a path or answer from memory:\n"
                        + "\n".join(_hits)}]
                    log.info("client-tools: file-search grounded files turn "
                             "(prefetched '%s')", _fn)
        log.info("client-tools passthrough: %d tool(s) -> %s (%s)",
                 len(body.get("tools") or []), _TOOL_BACKEND_MODEL, _TOOL_BACKEND)
        return await _client_tools_complete(body, streaming, chat_id, model)

    # session row -- the record id is captured for
    # downstream tool_call linking + the inline confirmation engine.
    # passport_sign=False: the `session` table is SCHEMAFULL and has
    # NO `passport` field, so attaching the default Ed25519 envelope
    # made SurrealDB reject the CREATE with a per-statement ERR
    # ("Found field 'passport', but no such field exists for table
    # 'session'"). That ERR comes back inside an HTTP 200, so _db_post
    # returned a list whose statement result was an error STRING (not a
    # row list) -> session_id stayed None on EVERY agent turn. That
    # silently disabled session-scoped machinery: tool_call session
    # links, taint propagation, AND the inline satisfaction /
    # confirmation check (which bails on a None session_id). The
    # session row is lightweight bookkeeping; the audit-relevant
    # tool_call / event / firewall_block rows keep their passports
    # (those tables carry the field)..
    session_id: Optional[str] = None
    try:
        resp = await _db_post(_db_create(
            "session",
            {"platform": "mios-agent-pipe",
             "model": model},
            now_fields=("started_at",),
            extra="RETURN id",
            passport_sign=False,
        ))
        if isinstance(resp, list) and resp:
            last = resp[-1] or {}
            rows = last.get("result") or []
            if isinstance(rows, list) and rows:
                rid = rows[0].get("id")
                if rid:
                    session_id = str(rid)
    except Exception as e:
        log.debug("session open failed: %s", e)

    # Phase D.5 -- refine FIRST when input isn't trivial. The
    # quick-refine pass on the iGPU lane produces a structured
    # plan {intent, refined_text, intended_outcome, target_agent,
    # hint_tools, hint_skills}. Operator directive
    # "should always be refined/processed/enhanced", but ALSO
    # "FAST AND EFFICIENT FOR PURE LOCAL COMPUTE" -- so trivial
    # input (short greeting / single-token status check) skips
    # refine and goes straight to the layer-1 router which has
    # its own chat-reply fast path. Refine returns None on the
    # bypass case; refine_intent + classify_intent are
    # complementary, not redundant.
    # Turn checkpoint : clear VRAM as needed so the
    # pipeline-critical refine+polish models stay warm instead of thrashing
    # against a squatting transient (e.g. the 7B coder). No-op with headroom.
    await _vram_checkpoint()
    refined = await refine_intent(last_user_text, messages)
    # Anti-stale-recall ("data/time of requests should be weighed
    # appropriately in an AIOS environment"): flag this turn VOLATILE when the model
    # classified it as live local-state / current-events / location-bound -- its answer
    # is a point-in-time snapshot (cwd, open windows, weather, latest news) that must be
    # answered LIVE and NEVER cached into / recalled from the durable store. Read by
    # _recall_knowledge (skip injection) + _store_knowledge (skip persist). Model-
    # classified (refine flags), NOT a keyword list. Degrade-open: any error -> False.
    try:
        _turn_volatile_var.set(bool(refined and (
            refined.get("local_state") or refined.get("news")
            or refined.get("needs_location"))))
    except Exception:  # noqa: BLE001
        pass
    # Turn priority (P1): resurrect the AIOS priority score
    # (complexity+urgency+intent) so the capacity-aware _admit gate orders fan-out
    # dispatches under load. Threaded into the council fan-out calls below. Guard:
    # refined may be None (trivial-bypass turn) -> _sched_priority handles it ->
    # neutral 5.0. ADVISORY when MIOS_ADMIT_ENABLE is off (no-op).
    try:
        _turn_priority = float(_sched_priority(refined).get("score", 5.0))
    except Exception:  # noqa: BLE001
        _turn_priority = 5.0
    # W0-T3 autonomous isolation: an UNATTENDED (mios_autonomous) turn is BACKGROUND
    # work -- it must yield the next freed GPU slot to any operator FOREGROUND turn.
    # Clamp its priority DOWN to AUTONOMOUS_PRIORITY (default 1.0 << neutral 5.0) so
    # the existing _priority_gate / _admit ordering admits foreground first; only
    # lower it (never raise a turn that scored below the floor). Foreground turns
    # keep their _sched_priority score, so a human at the keyboard always preempts.
    if _autonomous:
        _turn_priority = min(_turn_priority, AUTONOMOUS_PRIORITY)
        log.info("autonomous turn priority clamped to %.2f (foreground preempts)",
                 _turn_priority)

    # T-019 (SCHED-01) turn-boundary preemption seam. This is THE point a scheduler
    # decides whether to preempt -- the turn's AIOS priority is now known. DEFAULT-OFF
    # ([scheduler].preempt_enable=false) -> a pass-through no-op, so the turn runs
    # byte-identically. When enabled, mios_preempt.turn_boundary may snapshot + yield
    # this turn to a higher-priority waiter and resume it (per the PreemptScheduler
    # API; the live "higher-priority-waiting" probe is the global PriorityGate, wired
    # in server.py). The hook is itself degrade-open; the extra guard here is belt-and-
    # suspenders so the seam can NEVER drop/corrupt a turn. Substrate for T-020/T-058.
    try:
        await mios_preempt.turn_boundary(task_id=str(chat_id), priority=_turn_priority)
    except Exception:  # noqa: BLE001 -- degrade-open: a seam failure never breaks a turn
        pass

    # T-020 (SCHED-02) token-time-sliced priority queue. Register this turn so the
    # scheduler can ORDER it against concurrent turns by priority and account its token
    # slices; at each token-slice boundary the generation path calls
    # mios_preempt.slice_boundary, which re-evaluates via the turn_boundary mechanism
    # (yield the lane to a higher-priority waiter, else continue). FLAG-GATED on
    # [scheduler].queue_enable (DEFAULT-OFF -> this block is SKIPPED, so turns admit/run
    # byte-identically -- no queue interposition) and DEGRADE-OPEN (any queue error
    # never breaks a turn). The queue is bounded + a re-enqueue refreshes in place, so a
    # follow-up turn on the same chat never duplicates or leaks. The live token feed
    # (slice_boundary) + the precise gate-relative enqueue/dispatch placement are
    # operator-live-validated; this is the turn-lifecycle registration.
    if mios_preempt.QUEUE_ENABLE:
        try:
            mios_preempt._TURN_QUEUE.enqueue(str(chat_id), _turn_priority)
            mios_preempt._TURN_QUEUE.dispatch()
        except Exception:  # noqa: BLE001 -- degrade-open: the queue never breaks a turn
            pass

    # W0-T3 aggregate budget HARD-HALT (the runaway tripwire). Before dispatching
    # ANY compute for this turn, check the rolling-window token ledgers: the
    # per-conversation ceiling AND (for an autonomous source) the per-source
    # ceiling + concurrent-in-flight cap. If a bucket is exhausted, return a
    # graceful "budget exhausted" answer instead of dispatching -- this stops a
    # wedged/looping conversation or a misfiring unattended schedule from racking
    # up unbounded compute. DEGRADE-OPEN: _budget_admit returns allowed on any
    # error, so a bookkeeping bug never blocks a legitimate turn.
    # This turn's in-flight token (autonomous turns only). Registered inside
    # _budget_admit on admit; aged out by TTL even if no explicit release fires
    # (the streaming path returns its generator before the turn truly ends).
    _budget_turn_token = (chat_id if (_autonomous and _autonomous_source) else None)
    _budget_ok, _budget_reason = await _budget_admit(
        _scratchpad_key(body, chat_id), _autonomous_source, _budget_turn_token)
    if not _budget_ok:
        log.warning("budget HARD-HALT: %s (chat=%s autonomous=%s)",
                    _budget_reason, chat_id, _autonomous)
        _halt_msg = (
            "I'm pausing here: this conversation has reached its aggregate "
            "compute budget for now (" + _budget_reason + "). Please try again "
            "shortly, or rephrase as a single focused request.")
        if streaming:
            async def _budget_halt_stream():
                yield _sse_chunk("", chat_id=chat_id, model=model, role="assistant")
                async for _ab in _stream_answer(_halt_msg, chat_id=chat_id, model=model):
                    yield _ab
                yield _sse_chunk("", chat_id=chat_id, model=model, finish_reason="stop")
                yield _sse_done()
            return StreamingResponse(_budget_halt_stream(),
                                     media_type="text/event-stream")
        return JSONResponse(content={
            "id": chat_id, "object": "chat.completion",
            "created": int(time.time()), "model": model,
            "choices": [{"index": 0,
                         "message": {"role": "assistant", "content": _halt_msg},
                         "finish_reason": "stop"}],
        })

    if _KERNEL:
        _kdec = _KERNEL.router.route(refined)
        log.info("kernel dispatch: routing mode=%s", _kdec.mode)
        ctx = locals().copy()
        try:
            return await _KERNEL.dispatcher.run(_kdec, **ctx)
        finally:
            await _budget_release_inflight(_budget_turn_token)
    raise RuntimeError("Kernel not configured")


async def responses_api_logic(request: Request) -> Any:
    """OpenAI Responses API (Tier-2, additive). A THIN facade: translates the
    Responses request to a chat/completions call against THIS server's own full
    pipeline (self-proxy -> reuse refine/route/swarm/polish, no duplication), then
    reshapes the answer into the Responses items model. /v1/chat/completions is
    untouched. Minimal v1: text/message `input` -> one output_text message item +
    usage; `instructions` -> a system message. Streaming/items/hosted-tools TODO."""
    try:
        body = _loads_lenient(await request.body() or b"{}")
    except Exception:
        return JSONResponse(content={"error": {"message": "invalid JSON body",
                            "type": "invalid_request_error"}}, status_code=400)
    model = body.get("model") or BACKEND_MODEL
    inp = body.get("input")
    msgs: list = []
    if body.get("instructions"):
        msgs.append({"role": "system", "content": str(body["instructions"])})
    if isinstance(inp, str):
        msgs.append({"role": "user", "content": inp})
    elif isinstance(inp, list):
        for it in inp:
            if not isinstance(it, dict):
                continue
            c = it.get("content")
            if isinstance(c, list):
                c = "".join(p.get("text", "") for p in c if isinstance(p, dict)
                            and p.get("type") in ("input_text", "output_text", "text"))
            msgs.append({"role": it.get("role") or "user", "content": str(c or "")})
    if not msgs:
        return JSONResponse(content={"error": {"message": "you must provide 'input'",
            "type": "invalid_request_error", "param": "input", "code": None}},
            status_code=400)
    _port = os.environ.get("MIOS_PORT_AGENT_PIPE", "8640")
    try:
        async with httpx.AsyncClient(timeout=300.0) as s:
            r = await s.post(f"http://127.0.0.1:{_port}/v1/chat/completions",
                             json={"model": model, "messages": msgs, "stream": False},
                             headers={"Content-Type": "application/json"})
        cc = r.json()
    except Exception as e:  # noqa: BLE001
        return JSONResponse(content={"error": {"message": str(e)[:200],
                            "type": "api_error"}}, status_code=502)
    answer = (((cc.get("choices") or [{}])[0].get("message") or {}).get("content") or "")
    return JSONResponse(content={
        "id": "resp_" + uuid.uuid4().hex[:24], "object": "response",
        "created_at": int(time.time()), "model": model, "status": "completed",
        "output": [{"type": "message", "id": "msg_" + uuid.uuid4().hex[:24],
                    "status": "completed", "role": "assistant",
                    "content": [{"type": "output_text", "text": answer}]}],
        "output_text": answer,
        "usage": cc.get("usage") or _usage_estimate("", answer),
    })


# -- @app -> APIRouter migration (refactor R13): the chat-pipeline routes -----------
# The OpenAI Responses API self-proxy facade (/v1/responses, cohesive with the chat-
# completions pipeline it self-proxies into) AND the capstone /v1/chat/completions route
# both moved off server.py's @app onto this co-located chat_router. server.py imports
# chat_router + the handler NAMES and mounts it via app.include_router(chat_router); the
# names are re-imported there so server's importable `provided` surface is unchanged and
# the served path/method set is byte-identical (the live-app route gate proves it). Each
# body calls its module-resident logic (responses_api_logic / chat_completions_logic)
# DIRECTLY (same module -- no sys.modules hop). One-way boundary: this module never
# imports server (its deps arrive via configure()). APIRouter()/method decorators are
# structural, not config.
chat_router = APIRouter()


@chat_router.post("/v1/responses")
async def responses_api(request: Request) -> Any:
    """OpenAI Responses API (Tier-2, additive) route. Calls responses_api_logic
    (same module)."""
    return await responses_api_logic(request)


@chat_router.post("/v1/chat/completions")
async def chat_completions(request: Request) -> Any:
    """OpenAI Chat Completions route -- the capstone router-brain entrypoint. The
    router-brain body lives in ``chat_completions_logic`` (same module); this thin
    handler calls it directly. Every routing-precedence guard/branch lives in the
    logic function, behaviour-identical.
    """
    return await chat_completions_logic(request)


async def _kernel_chat_handler(decision, **ctx):
    import re, time
    from fastapi.responses import JSONResponse, StreamingResponse
    refined = ctx.get("refined")
    _force_council = ctx.get("_force_council")
    _force_delegate = ctx.get("_force_delegate")
    last_user_text = ctx.get("last_user_text")
    messages = ctx.get("messages")
    streaming = ctx.get("streaming")
    chat_id = ctx.get("chat_id")
    model = ctx.get("model")
    session_id = ctx.get("session_id")
    _routed_domain_var = ctx.get("_routed_domain_var") or globals().get("_routed_domain_var")
    
    _chat_reply = ""
    if not _force_council and not _force_delegate:
        _mem_block = await _recall_agent_memory(last_user_text)
        _mem_scores = [float(_s) for _s in re.findall(r"\[(\d(?:\.\d+)?)\]", _mem_block or "")]
        _mem_top = max(_mem_scores) if _mem_scores else 0.0
        if _mem_block and _mem_block.strip() and _mem_top >= 0.6:
            _kept = []
            for _ln in _mem_block.splitlines():
                _ms = re.search(r"\[(\d(?:\.\d+)?)\]", _ln)
                if _ms and float(_ms.group(1)) >= 0.6:
                    _kept.append(_ln)
            _facts = re.sub(r"\[\d(?:\.\d+)?\]\s*", "", "\n".join(_kept))
            _seen_f = set()
            _flines = []
            for _l in _facts.splitlines():
                _l = _l.rstrip()
                _key = _l.strip().lower().lstrip("- ")
                if _l.strip() and _key not in _seen_f:
                    _seen_f.add(_key)
                    _flines.append(_l)
            _facts = "\n".join(_flines)
            if _facts.strip():
                if await _is_memory_question(last_user_text, _facts):
                    _chat_reply = "From what you've told me before:\n" + _facts
                    log.info("memory-recall short-circuit: surfaced saved facts deterministically")

    if (not _chat_reply and len((last_user_text or "").split()) < SWARM_DECOMPOSE_MIN_WORDS
            and not (refined.get("web") or refined.get("news")
                     or refined.get("domain_type") in ("external", "both")
                     or _routed_domain_var.get(None) == "web")
            and not _force_council and not _force_delegate):
        _chat_reply = str(refined.get("reply") or "").strip()
        if not _chat_reply:
            _chat_reply = await _quick_chat_reply(last_user_text, messages)

    if _chat_reply:
        reply = _chat_reply
        log.info("refine short-circuit: chat reply (no router/backend)")
        _store_knowledge(query=last_user_text, answer=reply, session_id=session_id, tool_history=[])
        _write_skill_md_fire(query=last_user_text, answer=reply, tool_history=[], session_id=session_id)
        if streaming:
            async def _stream_refine_chat():
                yield _sse_status_phase(chat_id=chat_id, model=model, phase="prompt")
                yield _sse_status_phase(chat_id=chat_id, model=model, phase="refine")
                yield _sse_chunk("", chat_id=chat_id, model=model, role="assistant")
                async for _b in _stream_answer(reply, chat_id=chat_id, model=model):
                    yield _b
                yield _sse_status_phase(chat_id=chat_id, model=model, phase="chat_done", done=True)
                yield _sse_chunk("", chat_id=chat_id, model=model, finish_reason="stop")
                yield _sse_done()
            return StreamingResponse(_stream_refine_chat(), media_type="text/event-stream")
        return JSONResponse(content={
            "id": chat_id, "object": "chat.completion", "created": int(time.time()),
            "model": model, "choices": [{"index": 0, "message": {"role": "assistant", "content": reply}, "finish_reason": "stop"}],
        })

    decision.mode = "agent"
    return await _KERNEL.dispatcher.run(decision, **ctx)



async def _kernel_dispatch_handler(decision, **ctx):
    refined = ctx.get("refined")
    _force_council = ctx.get("_force_council")
    _force_delegate = ctx.get("_force_delegate")
    last_user_text = ctx.get("last_user_text")
    streaming = ctx.get("streaming")
    chat_id = ctx.get("chat_id")
    model = ctx.get("model")
    session_id = ctx.get("session_id")
    _persona_system = ctx.get("_persona_system")

    _os_tool = str(refined.get("tool") or "").strip()
    _os_args = refined.get("args") if isinstance(refined.get("args"), dict) else {}
    if _os_tool in _FASTPATH_VERBS and not _force_council and not _force_delegate:
        log.info("fast-path dispatch: %s args=%s (deterministic, no fan-out)", _os_tool, _os_args)
        return await _respond_os_control(
            _os_tool, _os_args, refined,
            streaming=streaming, chat_id=chat_id, model=model,
            session_id=session_id, last_user_text=last_user_text,
            persona_system=_persona_system)
    
    log.info("refine dispatch tool=%r not a fast-path verb -> agent", _os_tool)
    decision.mode = "agent"
    return await _KERNEL.dispatcher.run(decision, **ctx)


async def _kernel_multi_task_handler(decision, **ctx):
    refined = ctx.get("refined")
    last_user_text = ctx.get("last_user_text")
    messages = ctx.get("messages")
    streaming = ctx.get("streaming")
    chat_id = ctx.get("chat_id")
    model = ctx.get("model")
    session_id = ctx.get("session_id")
    _persona_system = ctx.get("_persona_system")
    _force_council = ctx.get("_force_council")
    _force_delegate = ctx.get("_force_delegate")
    request = ctx.get("request")

    if (refined and refined.get("intent") == "multi_task"
            and isinstance(refined.get("tasks"), list)
            and len(refined["tasks"]) >= 2):
        queued = _shadow_queue_tasks(refined["tasks"], session_id)
        if queued:
            log.info(
                "multi_task: queued=%d active=%r others=%r",
                len(queued),
                queued[0].get("title", ""),
                [t.get("title", "") for t in queued[1:]],
            )
            if PLANNER_ENABLED:
                try:
                    _vdag = await decompose_intent(last_user_text)
                except Exception:  # noqa: BLE001
                    _vdag = None
                _vnodes = (_vdag.get("nodes") or []) if _vdag else []
                _has_act = any(
                    str((_VERB_CATALOG.get(str(n.get("tool"))) or {})
                        .get("permission", "")).lower() == "write"
                    for n in _vnodes)
                if _has_act and len(_vnodes) >= 2:
                    log.info("multi_task -> verb-DAG (action fires): %s",
                             [n.get("tool") or ("agent:" + str(n.get("agent")))
                              for n in _vnodes])
                    return await _respond_agent_dag(
                        _vdag, refined, request=request, streaming=streaming, chat_id=chat_id,
                        model=model, session_id=session_id,
                        last_user_text=last_user_text,
                        persona_system=_persona_system)

            if PLANNER_ENABLED:
                _adag = _agent_dag_from_tasks(queued)
                if len(_adag.get("nodes") or []) >= 2:
                    log.info("multi_task -> concurrent agent DAG (%d): %s",
                             len(_adag["nodes"]),
                             [n["agent"] for n in _adag["nodes"]])
                    return await _respond_agent_dag(
                        _adag, refined, request=request, streaming=streaming, chat_id=chat_id,
                        model=model, session_id=session_id,
                        last_user_text=last_user_text,
                        persona_system=_persona_system)

            active = queued[0]
            ctx["last_user_text"] = str(active.get("refined_text")
                                 or active.get("title", "")
                                 or last_user_text)
            for k in ("refined_text", "intended_outcome",
                      "target_agent", "hint_tools", "hint_skills"):
                if active.get(k) is not None:
                    refined[k] = active[k]
            refined["intent"] = "agent"
            refined["_multi_task_queue"] = queued
            refined["_multi_task_active_idx"] = 0
            decision.mode = "agent"
            return await _KERNEL.dispatcher.run(decision, **ctx)

    _swarm_nodes = await _plan_swarm(last_user_text, messages)
    if not _swarm_nodes:
        log.info("multi_task decomposition yielded 0 nodes -> falling back to full council")
        ctx["_force_council"] = True
        decision.mode = "agent"
        return await _KERNEL.dispatcher.run(decision, **ctx)

    if not SWARM_TRUST_ATOMIC and len(_swarm_nodes) == 1:
        log.info("multi_task yielded 1 node (trust_atomic=false) -> running as normal agent turn")
        refined["intent"] = "agent"
        refined["deep"] = True
        decision.mode = "agent"
        return await _KERNEL.dispatcher.run(decision, **ctx)

    _dag = _agent_dag_from_tasks(_swarm_nodes, last_user_text)
    return await _respond_agent_dag(
        _dag, refined, request=request, streaming=streaming, chat_id=chat_id, model=model,
        session_id=session_id, original_query=last_user_text,
        persona_system=_persona_system)


async def _kernel_agent_handler(decision, **ctx):
    refined = ctx.get("refined")
    _force_council = ctx.get("_force_council")
    _force_delegate = ctx.get("_force_delegate")
    last_user_text = ctx.get("last_user_text")
    messages = ctx.get("messages")
    streaming = ctx.get("streaming")
    chat_id = ctx.get("chat_id")
    model = ctx.get("model")
    session_id = ctx.get("session_id")
    _routed_domain_var = ctx.get("_routed_domain_var") or globals().get("_routed_domain_var")
    _persona_system = ctx.get("_persona_system")
    _mflags = ctx.get("_mflags")
    reply_prefix = ctx.get("reply_prefix", "")

    _domain = _routed_domain_var.get(None)
    if (not refined.get("web") and not refined.get("news")
            and _domain != "web"
            and "local_state" in str(refined.get("domain", ""))
            and not _force_council and not _force_delegate):
        if await _needs_external_knowledge(last_user_text, messages):
            log.info("hybrid promotion: local_state query needs external facts -> web=True")
            refined["web"] = True
            refined["domain_type"] = "both"
            _routed_domain_var.set("both")

    if (LOCAL_STATE_FASTPATH and "local_state" in str(refined.get("domain", ""))
            and not refined.get("web") and not refined.get("news")
            and not _force_council and not _force_delegate):
        log.info("local-state fast-path: routing %r to system_status/local scripts", last_user_text)
        return await _respond_local_state(
            refined, streaming=streaming, chat_id=chat_id, model=model,
            session_id=session_id, last_user_text=last_user_text,
            persona_system=_persona_system)

    if not _force_council and not _force_delegate and _mflags.get("force_council") is None:
        _agent_match = _pick_agent(last_user_text)
        if _agent_match and _agent_match != "MiOS":
            log.info("legacy explicit route: %r matched -> forcing delegate to %s",
                     last_user_text, _agent_match)
            _force_delegate = _agent_match

    if not _force_council and _force_delegate:
        if _force_delegate == "MiOS":
            _force_delegate = ""
        else:
            log.info("force_delegate: skipping council, 100%% weight to %s", _force_delegate)

    _selected = [_force_delegate] if _force_delegate else []
    if _force_council or (not _force_delegate and (
            refined.get("deep") or _routed_domain_var.get(None) in ("web", "local_files")
            or refined.get("web") or refined.get("news"))):
        _selected = await _pick_fanout_agents(last_user_text, refined, _force_council)
        if len(_selected) > 1:
            log.info("council fan-out (%d): %s", len(_selected), _selected)
        elif len(_selected) == 1:
            log.info("council fan-out yielded 1 agent -> delegating to %s", _selected[0])
            _force_delegate = _selected[0]

    return await _respond_native_loop_direct(
        refined, force_delegate=_force_delegate, target_agents=_selected,
        streaming=streaming, chat_id=chat_id, model=model,
        session_id=session_id, last_user_text=last_user_text,
        persona_system=_persona_system, reply_prefix=reply_prefix)
