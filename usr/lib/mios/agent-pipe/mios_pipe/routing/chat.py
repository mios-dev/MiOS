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

    # COUNCIL-BY-DEFAULT : engage the full multi-agent council
    # for SUBSTANTIVE turns by default (intent agent/multi_task, or chat >= MIN_WORDS)
    # when [dispatch].council_default is on and the user hasn't explicitly toggled
    # force_council. This makes the swarm + live thinking/emitters the DEFAULT
    # instead of the single-brain native loop; trivial chat stays single. Bounded by
    # council_max + admission + lane/sub-lane semaphores. Explicit toggle (None ->
    # unset) still wins; force_delegate (DAG mode) takes precedence if set.
    # WS-A11/WS-3 Stage 2a SHADOW route (default-off): log the decomposed Router's
    # decision alongside the live inline cascade so the operator can confirm parity
    # on real traffic BEFORE the Stage-2b execution swap. Pure classification only
    # -- it never alters control flow. Inert unless MIOS_KERNEL_ROUTE is on.
    if KERNEL_ROUTE and refined:
        try:
            _kdec = _KERNEL.router.route(refined)
            log.info("kernel shadow-route: %s", _kdec.to_dict())
        except Exception:  # noqa: BLE001 -- observability must never break a turn
            pass

    if KERNEL_DISPATCH and _KERNEL and refined:
        _kdec = _KERNEL.router.route(refined)
        log.info("kernel dispatch: routing mode=%s", _kdec.mode)
        ctx = locals().copy()
        # KERNEL.dispatcher.run will execute the injected handlers.
        return await _KERNEL.dispatcher.run(_kdec, **ctx)
    if (COUNCIL_DEFAULT and refined and not _force_council and not _force_delegate
            and _mflags.get("force_council") is None):
        _ci = str(refined.get("intent") or "")
        # Council BY DEFAULT for genuinely BROAD work -- gated on refine's OWN
        # breadth judgment (deep / web / news / multi_task), NOT merely "is it an
        # agent question". A simple factual ask ("capital of Norway") is intent=agent
        # but deep=false -> it must NOT trigger a multi-node web-research swarm (that
        # made a 1-word answer take 52s,). Broad/research/
        # comparison asks (deep or web or news or multi_task) DO council by default.
        # All four are the MODEL's classification (refine), not a hardcoded keyword
        # list. The native loop still handles non-broad agent turns + self-fans-out
        # via dispatch_to_nodes when IT judges a turn parallelizable.
        # web/news alone NO LONGER force the council: its research nodes don't reliably
        # call web_search (weak local model -> fabricated "trending news", operator
        #), whereas the NATIVE loop now deterministically PRE-FETCHES
        # web_search for web/news turns (real results injected, no fabrication). So route
        # web/news here to the native loop + its prefetch; keep the council for genuinely
        # BROAD/DEEP work (deep or multi_task), where the model still self-fans-out via
        # dispatch_to_nodes. Working-single-agent-with-real-search beats council-that-fabricates.
        _broad = (_ci == "multi_task" or bool(refined.get("deep")))
        if _broad and _ci in ("agent", "multi_task", "chat"):
            _force_council = True
            log.info("council-default: full council for intent=%s (broad)", _ci)

    # SHORT-CIRCUIT: when refine emitted intent=chat with a reply,
    # we already have the final answer. No router + no sub-agent
    # delegation needed. Operator-flagged trace: short
    # greetings like "hey! How's it going?" were ending up at
    # Hermes (which then ran tool cascades) because the router
    # was independently re-classifying them as `agent`. Refine
    # already nailed the chat-classification at 25s; using its
    # verdict directly saves the 30-90s Hermes roundtrip on every
    # conversational message.
    _chat_reply = ""
    # DETERMINISTIC memory-RECALL short-circuit : a `memory`-domain
    # QUESTION ("what is my favorite color?") that refine misreads as plain chat must be
    # answered from the user's OWN saved facts -- NOT refine's pre-recall reply, and NOT a
    # model hop (granite-8b denies the fact ~consistently even when it is injected right
    # beside the question, ignoring even the "It is FALSE to say you don't have it"
    # directive). Recall the durable facts directly; a confident hit (self-gated at
    # MIN_SCORE) is surfaced verbatim. STORE turns ("remember X") are intent=agent, so they
    # never enter this chat branch -- they fast-path `remember` below. No hit -> fall
    # through (honest "I don't have that").
    if (refined and refined.get("intent") == "chat"
            and not _force_council and not _force_delegate):
        _mem_block = await _recall_agent_memory(last_user_text)
        # Gate ONLY on the recall SCORE -- the question must CONFIDENTLY match a stored
        # fact (>=0.6). The router's `memory` tag is NOT a reliable trigger: it is a small
        # model that misclassifies BOTH ways -- "what is my dog called?" -> files (a real
        # recall it would MISS) AND "who are you and who made you?" -> memory (an identity
        # question it would WRONGLY surface user facts for). The embedding score is the
        # honest signal: real recalls score high ("favorite color" 0.84, "dog called"
        # >=0.6) while a misrouted identity/greeting stays low ("who are you" 0.52 -> falls
        # through to the proper answer). The 0.45 self-gate already dropped the weakest hits.
        _mem_scores = [float(_s) for _s in re.findall(r"\[(\d(?:\.\d+)?)\]", _mem_block or "")]
        _mem_top = max(_mem_scores) if _mem_scores else 0.0
        if _mem_block and _mem_block.strip() and _mem_top >= 0.6:
            # Keep only the fact lines that CONFIDENTLY match (>=0.6) -- "what is my dog
            # called?" must not also surface a faintly-matched favourite-colour fact. The
            # block's framing/header lines carry no [score], so they drop out here too.
            _kept = []
            for _ln in _mem_block.splitlines():
                _ms = re.search(r"\[(\d(?:\.\d+)?)\]", _ln)
                if _ms and float(_ms.group(1)) >= 0.6:
                    _kept.append(_ln)
            _facts = re.sub(r"\[\d(?:\.\d+)?\]\s*", "", "\n".join(_kept))
            # Dedup identical facts (the same fact re-saved across turns returns as N
            # near-duplicate hits) -- order-preserved, case-insensitive on the fact text.
            _seen_f: set = set()
            _flines: list = []
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
                else:
                    log.info("memory-recall short-circuit: fact matched but rejected by judge")
    # Short-circuit ONLY TRIVIAL chat (greetings/banter < MIN_WORDS) to a direct
    # reply ("concurrent true swarm / unfired nodes"): a
    # SUBSTANTIVE chat/knowledge question (e.g. "pros and cons of REST vs GraphQL")
    # was being answered on ONE node here, bypassing the swarm entirely. Now it
    # falls through to the multi-node swarm (it's intent=chat + >= MIN_WORDS).
    if (not _chat_reply and refined and refined.get("intent") == "chat"
            and len((last_user_text or "").split()) < SWARM_DECOMPOSE_MIN_WORDS
            # NOT a SHORT current-events / external-fact ask ("what is new today?",
            # "latest on X") -- those are < MIN_WORDS so they LOOK like trivial banter,
            # but the model flagged them web/news/external (or the router routed them to
            # domain=web), meaning they need WEB GROUNDING. Short-circuiting them to a
            # direct reply is exactly the fabrication the operator hit ("What
            # is new today?" -> a fabricated "here are today's headlines:" with NO sources).
            # Let them fall through to the web-promotion + native-loop prefetch below.
            and not (refined.get("web") or refined.get("news")
                     or refined.get("domain_type") in ("external", "both")
                     or _routed_domain_var.get(None) == "web")
            and not _force_council and not _force_delegate):
        _chat_reply = str(refined.get("reply") or "").strip()
        if not _chat_reply:
            # The JSON classifier reliably tags chat but often omits the
            # `reply` field -- generate it now so a greeting never falls
            # through to Hermes (which tried a bogus 'chat' verb, operator
            #). Generated, not canned. Empty -> fall through.
            _chat_reply = await _quick_chat_reply(last_user_text, messages)
    if _chat_reply:
        reply = _chat_reply
        log.info("refine short-circuit: chat reply (no router/backend)")
        # P5.7: also capture short-circuit chats as episodic SKILL.md +
        # knowledge rows, so trivia chats (greetings, small Q+A) also feed
        # the self-learn loop. Mirrors polish_response's hook for the
        # substantive path.
        _store_knowledge(query=last_user_text, answer=reply,
                         session_id=session_id, tool_history=[])
        _write_skill_md_fire(query=last_user_text, answer=reply,
                             tool_history=[], session_id=session_id)
        if streaming:
            async def _stream_refine_chat() -> AsyncGenerator[bytes, None]:
                yield _sse_status_phase(chat_id=chat_id, model=model,
                                        phase="prompt")
                yield _sse_status_phase(chat_id=chat_id, model=model,
                                        phase="refine")
                yield _sse_chunk("", chat_id=chat_id, model=model,
                                 role="assistant")
                # Type the answer out as deltas instead of one burst (operator
                # "streaming the thinking pipeline doesn't work" -- the
                # fast chat path bursted; native-loop already streams). _stream_answer
                # char-chunks byte-exact + paced.
                async for _b in _stream_answer(reply, chat_id=chat_id, model=model):
                    yield _b
                yield _sse_status_phase(chat_id=chat_id, model=model,
                                        phase="chat_done", done=True)
                yield _sse_chunk("", chat_id=chat_id, model=model,
                                 finish_reason="stop")
                yield _sse_done()
            return StreamingResponse(_stream_refine_chat(),
                                     media_type="text/event-stream")
        return JSONResponse(content={
            "id": chat_id,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": reply},
                "finish_reason": "stop",
            }],
        })

    # ── OS-CONTROL ACTION FAST-PATH ──────────────────
    # A single concrete OS/window action ("Launch Forza", "Close Discord",
    # "focus VSCodium") is a DETERMINISTIC one-verb action, NOT a research
    # question. Fire that ONE verb through the broker, report the REAL
    # verdict, and STOP -- no council fan-out, no web_search, no synthesis of
    # fabricated detail. Fixes the operator's two traces: "Launch Forza" ran a
    # 4-agent web-search swarm that invented window coordinates AND kept going
    # after the launch had already succeeded; "Close Forza" narrated a fake
    # `mios-window -mode graceful` call. Runs REGARDLESS of unify-on -- the
    # whole point is to NOT unify a deterministic action onto the research
    # agent path. Verb membership is data-driven from the mios.toml launch
    # section (_OS_CONTROL_VERBS): no hardcoded English verb list here.
    if refined and refined.get("intent") == "dispatch":
        _os_tool = str(refined.get("tool") or "").strip()
        _os_args = (refined.get("args")
                    if isinstance(refined.get("args"), dict) else {})
        if (_os_tool in _FASTPATH_VERBS
                and not _force_council and not _force_delegate):
            log.info("fast-path dispatch: %s args=%s (deterministic, no fan-out)",
                     _os_tool, _os_args)
            # schedule + other non-window fast-path verbs are NOT in
            # _OS_CONTROL_ACTION_VERBS / _LAUNCH_VERBS, so _respond_os_control
            # fires them + polishes the result WITHOUT the window enumerate/diff/
            # verify machinery -- it just runs the one verb and stops.
            return await _respond_os_control(
                _os_tool, _os_args, refined,
                streaming=streaming, chat_id=chat_id, model=model,
                session_id=session_id, last_user_text=last_user_text,
                persona_system=_persona_system)
        # A dispatch intent that isn't a known fast-path verb (or a forced
        # swarm override) falls back to a normal agent turn so it still gets
        # handled by the council/planner downstream.
        log.info("refine dispatch tool=%r not a fast-path verb -> agent",
                 _os_tool)
        refined["intent"] = "agent"
        refined.pop("tool", None)
        refined.pop("args", None)

    # HYBRID KNOWLEDGE-GAP PROMOTION ("use web tools for
    # knowledge gaps EVERY TURN" + "you are a LIAR" re: fabricated GPU specs): the
    # big refine call collapses "the theoretical specs of MY hardware" to local-only
    # (web=false), so the external half was dropped/fabricated. Run a FOCUSED yes/no
    # judge (generative, NO keywords) ONLY for a local_state turn that refine did NOT
    # already flag for web -- if it needs off-machine facts, set web=true + domain
    # 'both'. That trips the fast-path skip below + the native-loop's web+local
    # prefetch, so the answer grounds local identity (system_status) AND cited web
    # specs, and token-streams. Degrade-closed (judge false/error -> pure-local).
    if (LOCAL_STATE_FASTPATH and refined and refined.get("local_state")
            and not (refined.get("web") or refined.get("news"))
            and refined.get("intent") not in ("multi_task", "chat", "dispatch")
            and not _force_council and not _force_delegate):
        try:
            if await _needs_external_knowledge(last_user_text):
                refined["web"] = True
                refined["domain_type"] = "both"
                log.info("hybrid: local_state turn needs external knowledge "
                         "-> web=true (additive grounding)")
        except Exception:  # noqa: BLE001 -- degrade-closed
            pass
    # COMPUTE PROMOTION ("MATH(AND OTHER PYTHON CAPABILITIES)...
    # natural language!!! not verbs/keywords"): a calculation request often refines to
    # intent=chat ("what is 19387*4472") and takes the trivial chat path, which has NO
    # compute step -> the 8B answers in-head, wrong. A GENERATIVE judge (by MEANING, no
    # keywords) promotes a compute-needing chat turn to the agent/native-loop path, where
    # the compute prefetch runs the math in the sandbox. Verdict stashed on refined so the
    # native-loop prefetch reuses it (no double judge). Degrade-open (judge false/error
    # -> unchanged chat path). This is what makes compute AMBIENT across answer paths.
    if (NATIVE_LOOP_MATH_HINT and NATIVE_LOOP_ENABLE and refined
            and refined.get("intent") == "chat" and "coderun" in _VERB_CATALOG
            and not _force_council and not _force_delegate):
        try:
            if await _needs_compute(last_user_text):
                refined["intent"] = "agent"
                refined["_needs_compute"] = True
                log.info("compute promotion: chat -> agent (calculation needed)")
        except Exception:  # noqa: BLE001 -- degrade-open
            pass
    # CURRENT-EVENTS / EXTERNAL-FACT PROMOTION ("news fabricated
    # without search"): granite often refines a current-events / live-fact ask to
    # intent=chat EVEN WHILE flagging it web/news/external ("what is new today", "latest
    # on X") -- an inconsistency. A chat-intent turn never reaches the native loop (which
    # holds the deterministic web prefetch, L26553 gated on web/news), so it takes the
    # trivial/planner chat path and the model emits a fabricated "here are today's
    # headlines:" roundup with NO real sources (mios_sources: NONE -- live-confirmed).
    # Promote chat -> agent (+ ensure web=true) whenever ANY model signal says this needs
    # the web -- refine web/news/domain_type=external|both OR the router's domain=web (the
    # same signals _web_flagged trusts) -- so it routes to the native loop, the web
    # prefetch fires, and the answer is GROUNDED + CITED. Model-classified, NOT a keyword
    # list. Degrade-open.
    if (NATIVE_LOOP_ENABLE and refined
            and refined.get("intent") == "chat"
            and (refined.get("web") or refined.get("news")
                 or refined.get("domain_type") in ("external", "both")
                 or _routed_domain_var.get(None) == "web")
            # NOT a needs_location turn with NO resolved location: those must reach the
            # ask-for-city guard below -- promoting them to the
            # native-loop web search makes "weather near me" fabricate a city (it answered
            # "New York" for an unlocated user). A LOCATED needs_location turn is fine to
            # web-search (the city is in the query); only the UNLOCATED one must ask.
            and not (refined.get("needs_location")
                     and not str((_client_env(body) or {}).get("location") or "").strip())
            and not _force_council and not _force_delegate):
        try:
            refined["intent"] = "agent"
            refined["web"] = True
            refined["domain_type"] = "both" if refined.get("local_state") else "web"
            # a web/current turn is time-bound: skip stale-recall inject + don't cache
            # its own time-bound answer (consistent with the temporal gate above).
            try:
                _turn_volatile_var.set(True)
            except Exception:  # noqa: BLE001
                pass
            log.info("web promotion: router domain=web on a chat turn -> intent=agent "
                     "+ web=true (anti-fabrication, grounds current-events asks)")
        except Exception:  # noqa: BLE001 -- degrade-open
            pass
    # LOCAL-STATE FAST-PATH : a "what's installed / what's
    # my state" question is local INVENTORY, not research. Answer it
    # deterministically from the live READ tools (mios_apps etc.) instead of
    # fanning out to the council/swarm that HALLUCINATED "no games" over the
    # real 11-game inventory + took 20 min. Falls through to the normal path if
    # the tools yield nothing. multi_task/chat excluded; forced-swarm respected.
    if (LOCAL_STATE_FASTPATH and refined and refined.get("local_state")
            and refined.get("intent") not in ("multi_task", "chat", "dispatch")
            # HYBRID : a local_state turn that ALSO needs web
            # knowledge must NOT take the local-only deterministic path (it has no
            # web grounding + bursts the answer). Fall through to the native loop,
            # which fires BOTH local + web prefetch and token-streams the answer.
            and not (refined.get("web") or refined.get("news"))
            and not _force_council and not _force_delegate):
        _ls_resp = await _respond_local_state(
            refined, streaming=streaming, chat_id=chat_id, model=model,
            session_id=session_id, last_user_text=last_user_text,
            persona_system=_persona_system)
        if _ls_resp is not None:
            log.info("local-state fast-path: answered deterministically")
            return _ls_resp
        log.info("local-state fast-path: no grounding -> normal path")

    # P0 LOOP-GUARD ENFORCEMENT : a depth-exhausted turn -- the
    # cross-hop X-MiOS-Hop/Via bound tripped (a re-entrant loop) OR we are already
    # MAX_DISPATCH_DEPTH deep -- MUST NOT fan out. Clearing the force flags + routing
    # straight to the SINGLE-AGENT native loop makes a re-entrant loop answer ONCE and
    # stop, instead of building a council/DAG anyway via the breadth-seed/force_council/
    # safety-net paths (which don't individually check depth). The swarm block below
    # also carries `and not _depth_exhausted()` as a backstop for the refine-None case.
    if _depth_exhausted():
        if _force_council or _force_delegate:
            log.warning("loop guard: dispatch depth %d >= %d -> SINGLE-AGENT "
                        "(no fan-out)", _dispatch_depth(), MAX_DISPATCH_DEPTH)
        _force_council = False
        _force_delegate = False
        if NATIVE_LOOP_ENABLE and refined and \
                refined.get("intent") in ("agent", "multi_task", "chat"):
            try:
                _nl = await _respond_native_loop_direct(
                    refined, streaming=streaming, chat_id=chat_id, model=model,
                    session_id=session_id, last_user_text=last_user_text,
                    persona_system=_persona_system, messages=messages,
                    request=request, tool_choice=body.get("tool_choice"))
                if _nl is not None:
                    return _nl
            except Exception as _lge:  # noqa: BLE001 -- degrade-open, fall through
                log.warning("loop-guard native loop failed: %s", _lge)

    # NATIVE TOOL-LOOP short-circuit ("simplify the pipeline
    # to work natively"): the cheap fast-paths above (trivial chat / OS-control
    # dispatch / local-state) keep their direct handling; a SUBSTANTIVE agent or
    # multi_task turn routes straight to ONE standard agentic tool-loop where the
    # model self-routes via tool choice -- collapsing the classify/route/decompose
    # /per-facet layers. GATED OFF by default (MIOS_NATIVE_LOOP); never wedges the
    # turn (falls through to the existing pipeline on any error).
    if (NATIVE_LOOP_ENABLE and refined
            and refined.get("intent") in ("agent", "multi_task")
            and not _force_council):
        try:
            _nl = await _respond_native_loop_direct(
                refined, streaming=streaming, chat_id=chat_id, model=model,
                session_id=session_id, last_user_text=last_user_text,
                persona_system=_persona_system, messages=messages, request=request,
                tool_choice=body.get("tool_choice"))
            if _nl is not None:
                log.info("native-loop: handled the turn")
                return _nl
        except Exception as _e:  # noqa: BLE001 -- never wedge; fall through
            log.warning("native-loop failed -> pipeline fallthrough: %s", _e)

    # MULTI-TASK SHORT-CIRCUIT: refine detected several independent
    # goals (>=2 tasks in the array). Write them to kanban_shadow,
    # promote task #1 as the active dispatch, and stash the queue on
    # the refined envelope so polish can prepend a "queued N tasks"
    # preamble to the final reply.
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
            # ACTION-intended compound (e.g. "list my games, research reviews,
            # LAUNCH the best"): try the verb-DAG planner FIRST so the action
            # ACTUALLY FIRES. decompose_intent can emit a deterministic
            # inventory -> agent-decides-winner -> launch_verified(#winner) DAG
            # whose launch is a REAL broker verb node -- instead of the LLM-facet
            # swarm merely narrating "launching X" ("FAILURE
            # ENTIRELY"). Use it ONLY when it returns a real WRITE/action verb
            # node; pure-research compounds fall through to the facets unchanged.
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
            # ("separate prompts per refinement step ->
            # sub-agents ... concurrent Compute"): run the independent tasks
            # as a CONCURRENT per-agent DAG THIS turn -- each task routed to
            # its target_agent, all in parallel -- and synthesise one answer,
            # instead of promoting task #0 and deferring the rest to follow-up
            # turns. The kanban_shadow queue above stays (audit/visibility).
            # Falls through to the legacy promote-and-queue path when fewer
            # than 2 tasks resolve to agents.
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
            # Promote task #0 to the active turn. Replace
            # last_user_text + the refined envelope's top-level
            # fields with task #0's, so all downstream branches
            # (router, agent dispatch, polish) operate on the
            # active task. Keep the original `tasks` array +
            # active index on the envelope so polish can render
            # the preamble.
            active = queued[0]
            last_user_text = str(active.get("refined_text")
                                 or active.get("title", "")
                                 or last_user_text)
            for k in ("refined_text", "intended_outcome",
                      "target_agent", "hint_tools", "hint_skills"):
                if active.get(k) is not None:
                    refined[k] = active[k]
            refined["intent"] = "agent"
            refined["_multi_task_queue"] = queued
            refined["_multi_task_active_idx"] = 0

    # LOCATION-REQUIRED but UNKNOWN -> ASK, never fabricate (
    # "check the weather for tomorrow" invented "San Fernando del Valle de
    # Catamarca, Argentina" because NO client location was forwarded and the swarm
    # web-searched the literal "my current location" -> random cities; one node
    # even ranted about DNS/401 telemetry). When refine flags needs_location and the
    # client shared none, ask for the city instead of fanning out to a guessing
    # swarm. A FORWARDED location flows through normally (refine puts the real city
    # in refined_text; _env_grounding resolves "near me"). Forced swarm overrides.
    if (refined and refined.get("needs_location")
            and not str((_client_env(body) or {}).get("location") or "").strip()
            and not _force_council and not _force_delegate):
        # Prefer the host-system-timezone REGION as a coarse locale BEFORE asking
        # ("where am I / what would local weather refer to" must
        # GROUND to the real system region, not punt "tell me your city" and never
        # fabricate 5 random cities). _host_timezone() is a real, always-available env
        # detail; granite ignores the soft _client_grounding prose AND this guard
        # returns before the model runs, so resolve it DETERMINISTICALLY here. Only ASK
        # when even the host timezone is unavailable.
        # No client location -> ask for the city HONESTLY via the existing helper.
        # NEVER derive a city/region from the host timezone (
        # a tz area such as America/New_York is NOT the user's location) and never
        # fan out a guessing swarm.
        _loc_reply = await _ask_for_location(last_user_text)
        # GLOBAL ASK-USER: this IS a clarification (we need the user's city). Mark it so
        # OWUI/Hermes render a native INPUT prompt + feed the typed city back as the next
        # turn ("ask user... for clarifications too"). The question
        # shown is the agent's own generated ask (no new hardcoded string). Degrade-open.
        try:
            if ASK_CLARIFY_ENABLE and "mios_clarification" not in _loc_reply:
                import json as _lcj
                _loc_reply = _loc_reply.rstrip() + "\n\n```json\n" + _lcj.dumps(
                    {"mios_clarification": {"question": _loc_reply.strip()[:200]}},
                    ensure_ascii=False) + "\n```"
        except Exception:  # noqa: BLE001
            pass
        log.info("needs_location + no client loc -> honest ask-for-city (no tz-city, no swarm)")
        _store_knowledge(query=last_user_text, answer=_loc_reply,
                         session_id=session_id, tool_history=[])
        if streaming:
            async def _stream_loc_ask() -> AsyncGenerator[bytes, None]:
                yield _sse_status_phase(chat_id=chat_id, model=model, phase="prompt")
                yield _sse_chunk("", chat_id=chat_id, model=model, role="assistant")
                yield _sse_chunk(_loc_reply, chat_id=chat_id, model=model)
                yield _sse_chunk("", chat_id=chat_id, model=model,
                                 finish_reason="stop")
                yield _sse_done()
            return StreamingResponse(_stream_loc_ask(),
                                     media_type="text/event-stream")
        return JSONResponse(content={
            "id": chat_id, "object": "chat.completion",
            "created": int(time.time()), "model": model,
            "choices": [{"index": 0,
                         "message": {"role": "assistant", "content": _loc_reply},
                         "finish_reason": "stop"}],
        })

    # MULTI-STEP -> per-agent DAG bridge ("separate
    # prompts per refinement step -> sub-agents ... concurrent Compute").
    # refine flagged this turn multi-step but didn't itemise a tasks array
    # (so the multi_task block above didn't fire). Give the planner ONE
    # chance to decompose it; if it returns a genuine MULTI-AGENT plan
    # (>=1 agent node), run that DAG concurrently this turn + synthesise.
    # Otherwise fall through to the unified Hermes + council path unchanged.
    # This is the unify-on entry point to the per-agent planner DAG.
    # The 🧩 Delegate SWARM toggle (force_delegate) forces this decomposition
    # regardless of refine's classification -- the manual override for when
    # the classifier under-fires.
    # Decompose-by-default: a substantive agent-intent ask attempts the swarm
    # decomposer even without an explicit delegate toggle / _multi_step flag.
    # _plan_swarm self-gates (returns [] when not worth splitting), so simple
    # asks fall through to council unharmed.
    # Attempt the planner for any SUBSTANTIVE query even when refine returned
    # empty/None (gemma4 reasoning intermittently yields empty content -> refined
    # falsy -> the decompose path was being gated off entirely). The planner
    # self-gates (returns [] when not worth splitting), so a non-decomposable ask
    # still falls through to council unharmed..
    _decompose_default = bool(
        SWARM_DECOMPOSE_DEFAULT
        and len((last_user_text or "").split()) >= SWARM_DECOMPOSE_MIN_WORDS
        and (not refined or refined.get("intent") in ("agent", "chat"))
        # ACTION domains are PERFORMED (verb-DAG / Hermes tool-loop), NEVER fanned
        # out to the research swarm ("send a discord message"
        # got researched into a dictionary search instead of executed). Data-driven
        # on verb permission (_is_action_domain); research/info domains unchanged.
        and not _is_action_domain(_routed_domain_var.get(None)))
    # Breadth -> decompose is the MODEL's call, not a hardcoded phrase list
    # ("THAT SEEM AWFULLY HARDCODED"): refine classifies a
    # broad/comprehensive ask as intent=multi_task (handled above via the
    # multi_task -> _agent_dag_from_tasks path) or sets _multi_step; the refine
    # prompt -- not Python keywords -- decides what is multi-faceted.
    # A browser ACTION enters the swarm path too ("fire
    # both"): the swarm researches the context on all nodes AND a pinned Hermes
    # node drives the live browser to PERFORM the action -- even for a short ask
    # ("log in to X") that wouldn't meet the decompose word-count.
    _browser_action = bool(refined and refined.get("browser_action"))
    # Deterministic browser trigger : a request naming a URL
    # together with a READ/browse intent ("open ... and quote/read/tell/summarize")
    # must hit the CDP browse path (real DOM via mios-cdp-fetch), NOT the open_url
    # fast-path (which only launches). refine often flags browser_action=false for
    # these, so force it here off the raw text.
    if not _browser_action and _BROWSER_ACTION_ALT:
        try:
            import re as _re_ba
            _ut_ba = last_user_text or ""
            if _re_ba.search(r'https?://', _ut_ba) and _re_ba.search(
                    r'\b(?:' + _BROWSER_ACTION_ALT + r')\b', _ut_ba, _re_ba.I):
                _browser_action = True
                log.info("browser_action forced: URL + read-intent -> CDP browse")
        except Exception:
            pass
    # An ACTION-domain request (a write-verb domain: agents_comms/apps_windows/
    # computer_use/...) is a NATIVE app/GUI action, NOT a web browse. Suppress
    # browser_action so it takes the action route (Hermes tool-loop orchestrates the
    # desktop action) instead of the browser/web-research path -- the root of "open
    # discord and send a message" STILL web-searching "open discord" after the
    # dispatch guard. Data-driven on verb permission (_is_action_domain); no
    # literals..
    if _browser_action and _is_action_domain(_routed_domain_var.get(None)):
        log.info("browser_action suppressed for action domain %s -> action route",
                 _routed_domain_var.get(None))
        _browser_action = False
    # A pure LOCAL-STATE query ("summarize recent activity" /
    # "check service status") must NOT enter the swarm: the swarm facet grounding
    # ALWAYS web-searches (synthetic web hints), which is exactly the garbage to
    # avoid. Route it to the unified council instead, where web is gated off and
    # _read_tool_enrich grounds it on the REAL local tools -- so every node still
    # fires, but on real system data. (A mixed multi_task that's also local, e.g.
    # detect+research+launch, still decomposes -- only PURE local-state skips.)
    _local_state = bool(refined and refined.get("local_state")
                        and refined.get("intent") != "multi_task")
    # CONCURRENT-SWARM gate ("I SAID A CONCURRENT TRUE AI
    # SWARM"): a substantive query ALWAYS fans out to every live distinct node via
    # the DAG path (each node on its OWN hardware, prefer_cpu=False) -- breadth is
    # NOT gated. What's gated by DEPTH (_is_deep) is the per-node DEEPEN loop +
    # per-facet deep multi-pass web research (the real 18-min/load cost), handled
    # in _respond_agent_dag: a casual turn fans to all nodes but each does ONE pass
    # off the shared web_search (fast, concurrent); a deep turn adds per-facet deep
    # research + deepen. So fan-out is universal, DEPTH is the dial.
    _is_deep = bool(refined and (refined.get("deep") or refined.get("deep_research")))
    log.info("decompose-gate: planner=%s local_state=%s decompose_default=%s "
             "multi_step=%s browser=%s", bool(PLANNER_ENABLED), _local_state,
             _decompose_default, bool(refined and refined.get("_multi_step")),
             _browser_action)
    # Removed `not _local_state`: refine's local_state flag is unreliable (it
    # mis-flags research comparisons), so let the PLANNER decide -- it self-gates
    # (returns [] for a genuine local-state ask -> council/local grounding) and
    # decomposes real research into distinct facets (offline-proven)..
    # ACTION-domain native execution : the routed domain is an
    # ACTION (write verb) -> PERFORM it, never research it. Decompose into an
    # EXECUTABLE verb-DAG and run it; if the planner declines (an iterative GUI nav
    # like "send a discord message to a user" is not a static DAG), fall through to
    # the single Hermes tool-loop, which orchestrates the action natively. NEVER the
    # research swarm. Data-driven on verb permission (_is_action_domain); no literals.
    _action_route = (PLANNER_ENABLED
                     and _is_action_domain(_routed_domain_var.get(None))
                     and not _browser_action)
    if _action_route:
        _act_dag = await decompose_intent(last_user_text)
        _act_nodes = (_act_dag.get("nodes") or []) if isinstance(_act_dag, dict) else []
        # EXECUTE the DAG only if it contains a real ACTION (verb/tool) node. A DAG
        # of ONLY agent nodes is a research split -- wrong for an ACTION request (it
        # produced an empty council "warning" for a discord DM action request,
        #). Fall through to the single Hermes tool-loop, which
        # calls the action verb (discord_send / GUI) directly.
        if _act_nodes and any(n.get("tool") for n in _act_nodes):
            log.info("action-domain -> verb-DAG EXECUTES (%d nodes; %s)", len(_act_nodes),
                     [n.get("tool") or ("agent:" + str(n.get("agent"))) for n in _act_nodes])
            return await _respond_agent_dag(
                _act_dag, refined, request=request, streaming=streaming,
                chat_id=chat_id, model=model, session_id=session_id,
                last_user_text=last_user_text, persona_system=_persona_system)
        log.info("action-domain: planner gave %s -> Hermes tool-loop (native, NOT research)",
                 "no DAG" if not _act_nodes else "agent-only DAG (no verb node)")
    # BREADTH signal ("research native patterns"): the MODEL's
    # own judgment that the ask warrants a multi-node fan-out -- refine's deep/
    # deep_research/multi_task/_multi_step flags or an explicit operator toggle. NO
    # hardcoded keywords. Gates both the synthetic swarm seed and the council safety-
    # net so a focused atomic ask (planner returns [] + no breadth) is NOT force-
    # swarmed, while a genuinely broad ask STILL fires on ALL live nodes.
    _breadth = bool(
        _force_delegate or _force_council
        or (refined and (refined.get("_multi_step") or refined.get("deep")
                         or refined.get("deep_research")
                         or refined.get("intent") == "multi_task")))
    if PLANNER_ENABLED and not _action_route and not _depth_exhausted() and (_force_delegate
                            or (refined and refined.get("_multi_step"))
                            or _decompose_default
                            or _browser_action):
        # Layer B (operator 'AI SWARM'): the DEDICATED swarm decomposer
        # first (reliable {agent, sub-task} assignments), then fall back to
        # the general verb-DAG planner if it produced an agent plan. Either
        # yields a concurrent per-agent DAG; otherwise fall through to the
        # unified Hermes + council path.
        # Plan + seed off the CLEAN refined query ("too
        # sparse"): the planner splits BETTER facets from refine's disambiguated,
        # date-anchored text than from the raw greeting-laden user message (which
        # produced the junk "worldwide trends today" search). Fall back to the user
        # text only when refine gave no refined_text.
        # DECOMPOSE off the RAW user text: it carries the concrete items to split
        # (e.g. "SQLite, PostgreSQL, DuckDB"); refine's refined_text can OVER-
        # condense them away ("Recommend the best database...") so the planner has
        # nothing to split -> [] -> council dups. The planner prompt extracts the
        # GENUINE facets and ignores greetings, so the raw is the right input here
        # (offline-proven: raw -> 4 distinct facets; refined_text -> []). operator
        #. Fall back to refined_text only if the raw is empty.
        _planq = (last_user_text or "").strip() or str((refined or {}).get("refined_text") or "")
        _swarm_tasks = await _plan_swarm(_planq, messages)
        # SEED for the CONCURRENT swarm ("unfired nodes"): if
        # the planner produced NO facets (a short/atomic substantive ask), seed ONE
        # task = the refined query so _agent_dag_from_tasks BACKFILLS it across EVERY
        # live node -> the whole swarm fires concurrently (each node answers on its
        # OWN hardware) instead of collapsing to a narrow council on one lane.
        # TRUST THE PLANNER'S VERDICT : only seed the synthetic
        # backfill task when a breadth signal justifies fanning out an under-split plan
        # (or the kill-switch is off). When the planner self-gated [] AND no breadth ->
        # leave _swarm_tasks empty so the DAG-build below is skipped and the turn falls
        # through to the single-agent path (no synthetic seed -> no off-topic facet
        # balloon). ADaPT/Adaptive-RAG: decompose only on evidence of need.
        if not _swarm_tasks and (_breadth or not SWARM_TRUST_ATOMIC):
            _swarm_tasks = [{"title": (_planq or "")[:72],
                             "refined_text": _planq}]
        elif not _swarm_tasks:
            log.info("swarm: planner self-gated [] + no breadth -> trust atomic verdict, "
                     "single-agent path (no synthetic seed)")
        # DIVERSIFY the backfill ("diversify the backfill facets
        # per node"): the planner routinely under-splits (e.g. 2 facets for a
        # 7-node roster), so the backfill round-robins DUPLICATE facets -> N nodes
        # do redundant work. If there are fewer facets than live nodes, have the
        # model generate ADDITIONAL DISTINCT angles so each node works its OWN facet
        # (capped at SWARM_MAX_WIDTH; self-gates to no-op for a thin ask).
        try:
            _live_n = len(await _live_agent_names())
        except Exception:  # noqa: BLE001
            _live_n = 0
        _target_facets = min(_live_n, SWARM_MAX_WIDTH) if _live_n else 0
        if _target_facets and len(_swarm_tasks) < _target_facets:
            _exist = [str(t.get("title") or t.get("refined_text") or "")
                      for t in _swarm_tasks]
            _more = await _expand_facets(_planq, _exist, _target_facets, messages)
            for _ef in _more:
                _swarm_tasks.append({"title": _ef[:72], "refined_text": _ef})
            if _more:
                log.info("facet-expand: +%d distinct facets (%d -> %d) for %d nodes",
                         len(_more), len(_exist), len(_swarm_tasks), _live_n)
        # RESEARCH turn? ("research should dispatch as many
        # 2-4GB models as possible across all lanes"). Use the EXISTING web/news/
        # deep refine signals (no hardcoded English) -- a web-grounded research
        # turn pulls in the research_only workers so the 2-4GB models
        # multiply across every lane; a plain action/chat swarm stays light.
        _is_research = bool(refined and (refined.get("web")
                            or refined.get("news") or refined.get("deep")
                            or refined.get("deep_research")))
        # Autonomous turns NEVER pull in the research_only workers (operator
        # wedge fix): a timer-fired research run would otherwise
        # multiply 2-4GB models across every lane -> OOM wedge. Force the swarm
        # DAG to the bounded (non-research-worker) node set.
        if _autonomous and _is_research:
            _is_research = False
        log.info("swarm hook: force_delegate=%s plan_swarm=%d tasks research=%s autonomous=%s",
                 _force_delegate, len(_swarm_tasks), _is_research, _autonomous)
        # Pass the LIVE roster so the swarm DAG fires on EVERY reachable node
        # ("fire on ALL NODES"); _live_agent_names is
        # TTL-cached so this is a near-free hit right after _plan_swarm.
        # Gate is >=1 (NOT >=2): even ONE good facet builds the DAG, and the
        # backfill in _agent_dag_from_tasks expands it to ALL live nodes. The
        # old >=2 gate let a 1-facet plan fall through to the hermes-only unify
        # path -> "only fired on the dGPU and nothing else".
        _mdag = (_agent_dag_from_tasks(_swarm_tasks,
                                       live_agents=await _live_agent_names(),
                                       include_research=_is_research)
                 if len(_swarm_tasks) >= 1 else None)
        if not (_mdag and len(_mdag.get("nodes") or []) >= 2):
            _gen = await decompose_intent(last_user_text)
            _gn = (_gen.get("nodes") or []) if _gen else []
            _n_agents = sum(1 for n in _gn if n.get("agent"))
            _has_action = any(
                str((_VERB_CATALOG.get(str(n.get("tool"))) or {})
                    .get("permission", "")).lower() == "write"
                for n in _gn)
            # Take the planner DAG ONLY when it's a REAL multi-agent split
            # (>=2 agents) OR an EXECUTABLE action (a WRITE verb like
            # winget_install). A thin [web_search, hermes] plan is a single task
            # with a tool, NOT a swarm -- let it fall through to the ALL-NODES
            # council so the FIRST PASS is the full swarm (
            # "just using only Hermes ... not swarm from first operations").
            # Actions still execute via the broker; research multi-splits run.
            _mdag = _gen if (_n_agents >= 2 or _has_action) else None
        # FIRE-BOTH browser action : the swarm above
        # researches the context on every node; now PIN one extra Hermes node
        # that drives the LIVE browser to actually PERFORM the action via its
        # native browser_*/CDP tools (Hermes runs its own loop, so this is the
        # real hand-off, not research). Appended AFTER the DAG is built so the
        # backfill can't reassign the browser facet to a non-browser agent. If
        # the swarm produced nothing (atomic action), the DAG is just this node.
        if _browser_action and "hermes" in (_AGENT_REGISTRY or {}):
            if not (isinstance(_mdag, dict) and isinstance(_mdag.get("nodes"), list)):
                _mdag = {"summary": (last_user_text or "")[:120], "nodes": []}
            _act = (last_user_text or "").strip()
            # Deterministic CDP prefetch ("cdp web browse in
            # hermes"): gemma4 fabricated page content instead of driving
            # browser_navigate. If the request names a URL, fetch its REAL
            # rendered text up front via ChromeDev CDP (mios-cdp-fetch -> :9222)
            # and hand it to the node so the answer is grounded in the actual
            # page, not a guess. The agent's own browser_* tools still run for
            # click/type/multi-step actions. Degrades silently if CDP is down.
            _cdp_page = ""
            try:
                import re as _re_cdp
                import subprocess as _sp_cdp
                _um = _re_cdp.search(r'https?://[^\s"\'<>]+', _act)
                if _um:
                    _u = _um.group(0).rstrip('.,);]')
                    _cr = _sp_cdp.run(["mios-cdp-fetch", _u, "4000"],
                                      capture_output=True, text=True, timeout=55)
                    if _cr.returncode == 0 and _cr.stdout.strip():
                        _pg = _loads_lenient(_cr.stdout)
                        if (_pg.get("text") or "").strip():
                            _cdp_page = (
                                "LIVE PAGE CONTENT fetched via ChromeDev CDP from "
                                "%s\nTITLE: %s\n\n%s"
                                % (_pg.get("url"), _pg.get("title"),
                                   (_pg.get("text") or "")[:4000]))
                            log.info("cdp prefetch ok: %s (%d chars)",
                                     _u, len(_pg.get("text") or ""))
            except Exception as _ce:
                log.warning("cdp prefetch failed: %s", _ce)
            if _cdp_page:
                # Real page text in hand -> render the answer DIRECTLY via the proven
                # grounded path (_format_local_state on /v1) instead of the DAG: the
                # DAG synthesis dropped the single grounded node (merged_chars=0 ->
                # hallucination,). _respond_local_state handles
                # streaming + non-streaming; falls through to the live browser node
                # only if the grounded render declines.
                _ls = await _respond_local_state(
                    refined, streaming=streaming, chat_id=chat_id, model=model,
                    session_id=session_id, last_user_text=_act,
                    persona_system=_persona_system, grounding_override=_cdp_page)
                if _ls is not None:
                    return _ls
            _mdag["nodes"].append({
                "id": "browser-action", "agent": "hermes",
                "prompt": ("Use your live browser tools -- first run "
                           "`terminal: mios-hermes-browser ensure`, then "
                           "browser_navigate / browser_click / browser_type -- to "
                           "ACTUALLY PERFORM this on the real web. Do NOT just "
                           "explain how; DO it, step by step, and report exactly "
                           "what you did and the final state (success or the "
                           "specific blocker): " + _act),
                "title": "browser action (live)", "deps": []})
            log.info("browser-action fire-both: pinned hermes browser node "
                     "(+%d research nodes)", len(_mdag["nodes"]) - 1)
        if _mdag and (_mdag.get("nodes") or []):
            _nd = _mdag["nodes"]
            log.info("swarm -> DAG (%d nodes; %s)", len(_nd),
                     [n.get("tool") or ("agent:" + str(n.get("agent")))
                      for n in _nd])
            return await _respond_agent_dag(
                _mdag, refined, request=request, streaming=streaming, chat_id=chat_id,
                model=model, session_id=session_id,
                last_user_text=last_user_text, persona_system=_persona_system)

    # 🧩 Delegate GUARANTEES a swarm: when structured decomposition declined
    # above (the local planner is inconsistent at splitting), escalate to the
    # FULL council swarm downstream (every agent, same prompt) rather than the
    # relevance-gated fan-out -- the toggle must never collapse to one agent.
    if _force_delegate:
        _force_council = True
    # SAFETY NET ("only fired on the dGPU and nothing
    # else"): a substantive agent query that produced NO swarm DAG above (the
    # planner emitted 0 facets / failed to parse) must STILL engage every live
    # node, not collapse to the hermes-only unify path. Force the full council
    # so the first pass is the whole swarm.
    # GATED on _breadth ("trust the planner verdict"): only
    # force the full council when the ask is genuinely BROAD -- a focused atomic ask
    # (planner []+no breadth) degrades to the single-agent path instead of being
    # re-force-swarmed here (which would defeat the seed gate above). Kill-switch
    # SWARM_TRUST_ATOMIC=false restores the unconditional force_council.
    if _decompose_default and not _force_council and (_breadth or not SWARM_TRUST_ATOMIC):
        log.info("swarm: no DAG built for substantive agent query "
                 "-> force_council (fan out across ALL live nodes)")
        _force_council = True

    # ACTION-DOMAIN GUARD (repeated "discord_send restricted to
    # read-only" / "YOU LIED AGAIN" FAILURE): an action-domain turn (ANY
    # [routing.domains.*] whose SSOT has a write-permission verb --
    # agents_comms/computer_use/apps_windows/packages/files/system/memory/code_shell)
    # MUST execute on the PRIMARY's write-capable tool-loop, NEVER fan out to a forced
    # council of READ-ONLY secondaries. The OWUI/desktop delegate flag set
    # _force_delegate->_force_council above, which (a) re-expanded the single action into
    # a swarm whose read-only nodes SKIP write verbs and narrate "discord_send is
    # restricted to read-only", and (b) suppressed tool_choice=required (the anti-
    # narration guard below needs `not _force_council`). Collapse to the single writer so
    # the action FIRES. Multi-step actions are decomposed by the action-route DAG planner
    # earlier (executed via the primary's writes), never by this read-only council.
    if _is_action_domain(_routed_domain_var.get(None)) and (_force_council or _force_delegate):
        log.info("action-domain: suppressing forced swarm/council "
                 "(writes need the primary write-loop, not read-only secondaries)")
        _force_council = False
        _force_delegate = False

    # Unify-on default ("Unify should be on by
    # default"). Non-chat routes through the agent path (refine -> Hermes
    # streamed -> critic -> polish) for a clean answer + streaming; the
    # dispatch/DAG fast-paths stay hardened (verb-name normalisation,
    # capped CPU polish) for when MIOS_AGENT_PIPE_UNIFY_AGENT=0.
    _unify_agent = os.environ.get(
        "MIOS_AGENT_PIPE_UNIFY_AGENT", "1") not in {"0", "false", "no"}
    # TWO CLASSIFIERS -> ONE (refactor): under
    # unify-on, refine already classified and chat + multi_task have
    # short-circuited above, so all that remains is intent=agent -> the
    # agent path. The layer-1 router only added dispatch-shape (tool+args)
    # extraction, which unify-on bypasses -- so skip the redundant second
    # classifier LLM call. (Unify-off still runs it for dispatch/DAG.)
    if _unify_agent and refined and refined.get("intent"):
        verdict = None
    else:
        # Layer-1 router: {"action": "dispatch"|"chat"|"agent", ...}.
        verdict = await classify_intent(last_user_text)
    # Carry refined hints into the verdict for downstream branches.
    if verdict and refined:
        verdict["_refined"] = refined
    # No router verdict but refine classified agent/dag -> promote
    # refine's verdict so we proxy to the right sub-agent.
    if not verdict and refined and refined.get("intent") in ("agent", "dag"):
        verdict = {"action": "agent", "reason": "refine-classified",
                   "_refined": refined}

    if verdict:
        action = verdict.get("action")

        # ── DISPATCH fast-path (skipped when unified onto agent) ──
        if action == "dispatch" and not _unify_agent:
            tool = str(verdict.get("tool", "")).strip()
            args = verdict.get("args") or {}
            if tool:
                result = await dispatch_mios_verb(
                    tool, args if isinstance(args, dict) else {},
                    session_id=session_id,
                )
                ok = bool(result.get("success"))
                # tool_call row -- write fire-and-forget.
                # Phase A.3: include taint state for the firewall.
                _row = {
                    "tool": tool,
                    "args": args if isinstance(args, dict) else {},
                    "result_preview": (result.get("output") or "")[:500],
                    "success": ok,
                    "latency_ms": int(result.get("latency_ms", 0)),
                    "tainted": bool(result.get("tainted")),
                    "taint_reason": (result.get("taint_reason") or "") or None,
                }
                if session_id:
                    _db_fire(_db_post(
                        _db_create("tool_call", _row, now_fields=("ts",)).rstrip(";")
                        + f", session = {session_id};"
                    ))
                else:
                    _db_fire(_db_post(
                        _db_create("tool_call", _row, now_fields=("ts",))
                    ))
                # Build the tool_calls envelope (OpenAI-spec-shaped
                # tool_call + tool_result wrapped in <details> so
                # gateways with markdown rendering get a collapsible
                # block + agents reading the chat history see the
                # canonical structured shape).
                envelope = {
                    "tool_call": {
                        "id": f"call_{int(time.time()*1000)}",
                        "type": "function",
                        "function": {
                            "name": tool,
                            "arguments": args if isinstance(args, dict) else {},
                        },
                    },
                    "tool_result": {
                        "success": ok,
                        "output": (result.get("output") or "")[:2000],
                        "stderr": (result.get("stderr") or "")[:2000],
                        "exit_code": int(result.get("exit_code", -1)),
                    },
                }
                # Phase B.1 + B.3 chained critic: Challenger runs
                # post-dispatch (audit trail); on a high-confidence
                # challenge / ask, the chain auto-escalates to the
                # B.2 4-persona flow; if THAT flow surfaces dissent,
                # the session gets tainted so the firewall refuses
                # the next high-privilege dispatch. Fire-and-forget
                # so the operator's reply isn't delayed.
                if DCI_ENABLED:
                    _db_fire(critic_then_maybe_flow(
                        last_user_text, envelope,
                        session_id=session_id,
                    ))
                symbol = "✅" if ok else "⚠️"
                envelope_block = (
                    f"<details type=\"tool_calls\" done=\"true\">\n"
                    f"<summary>{symbol} `{tool}`</summary>\n\n"
                    f"```json\n{json.dumps(envelope, indent=2, default=str)}\n```\n"
                    f"</details>"
                )
                # Polish the tool output into a human-facing summary
                # so the operator sees "Here are your 32 installed
                # apps: ..." above the collapsible envelope, NOT just
                # the raw JSON. Synthesise a minimal refined dict for
                # the polish call when refine didn't run (dispatch
                # path can fire without a full refine envelope when
                # the trivial-bypass kicked in).
                _refined_for_polish = refined or {
                    "intent": "dispatch",
                    "intended_outcome": f"answer the question by running {tool}",
                    "refined_text": last_user_text,
                }
                # Cap tight for the CPU polish lane: 6000 chars of (e.g.)
                # system_status JSON made the 1.7b CPU polish blow its
                # timeout -> raw JSON fallback. 1800
                # chars summarises fast on pure CPU while keeping the
                # salient fields. mios-os-control stays CPU-capable.
                tool_output = (result.get("output") or "")[:1800]
                # Inline satisfaction check writes the user_query_
                # (un)satisfied event before polish queries verdicts.
                await _inline_satisfaction_check(
                    session_id, _refined_for_polish)
                polished = ""
                if tool_output.strip():
                    polished_raw = await polish_response(
                        f"Tool `{tool}` ran successfully and returned:\n"
                        f"{tool_output}\n\n"
                        f"Write a friendly natural-language answer to the "
                        f"operator's question using this tool output.",
                        _refined_for_polish, session_id=session_id,
                        original_user_text=last_user_text,
                        persona_system=_persona_system,
                    )
                    polished = (_strip_think_tags(polished_raw)
                                if polished_raw else "")
                # Compose: polished answer ABOVE the collapsible
                # envelope (envelope is the audit trail, polished is
                # the operator-visible reply).
                if polished.strip():
                    rendered = f"{polished}\n\n{envelope_block}"
                else:
                    rendered = envelope_block
                if streaming:
                    async def _stream_dispatch() -> AsyncGenerator[bytes, None]:
                        # Phase markers: listening -> picking -> doing -> done.
                        # Technical detail (tool args, exit codes, latencies)
                        # lives in the event_log; the strip stays
                        # readable for non-technical operators.
                        yield _sse_status_phase(chat_id=chat_id, model=model,
                                                phase="prompt")
                        yield _sse_status_phase(chat_id=chat_id, model=model,
                                                phase="route")
                        yield _sse_status_phase(chat_id=chat_id, model=model,
                                                phase="tool")
                        yield _sse_chunk("", chat_id=chat_id, model=model,
                                         role="assistant")
                        async for _b in _stream_answer(rendered, chat_id=chat_id, model=model):
                            yield _b
                        yield _sse_status_phase(
                            chat_id=chat_id, model=model,
                            phase="tool_done" if ok else "tool_done_warn",
                            done=True)
                        yield _sse_chunk("", chat_id=chat_id, model=model,
                                         finish_reason="stop")
                        yield _sse_done()
                    return StreamingResponse(_stream_dispatch(),
                                             media_type="text/event-stream")
                # Non-streaming response.
                return JSONResponse(content={
                    "id": chat_id,
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "message": {"role": "assistant", "content": rendered},
                        "finish_reason": "stop",
                    }],
                })

        # ── CHAT fast-path (one-line conversational reply) ──────
        if action == "chat":
            reply = str(verdict.get("reply", "")).strip()
            if reply:
                if streaming:
                    async def _stream_chat() -> AsyncGenerator[bytes, None]:
                        yield _sse_status_phase(chat_id=chat_id, model=model,
                                                phase="prompt")
                        yield _sse_status_phase(chat_id=chat_id, model=model,
                                                phase="route")
                        yield _sse_chunk("", chat_id=chat_id, model=model,
                                         role="assistant")
                        async for _b in _stream_answer(reply, chat_id=chat_id, model=model):
                            yield _b
                        yield _sse_status_phase(chat_id=chat_id, model=model,
                                                phase="chat_done", done=True)
                        yield _sse_chunk("", chat_id=chat_id, model=model,
                                         finish_reason="stop")
                        yield _sse_done()
                    return StreamingResponse(_stream_chat(),
                                             media_type="text/event-stream")
                return JSONResponse(content={
                    "id": chat_id,
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "message": {"role": "assistant", "content": reply},
                        "finish_reason": "stop",
                    }],
                })

        # action == "agent" -> planner gets a chance to decompose
        # into a DAG of dispatch verbs (Phase A.1). If the planner
        # returns >=2 actionable nodes, run the DAG locally; if it
        # returns empty or fails, fall through to the backend proxy
        # which has Hermes's full tool-calling agent loop available.
        if action == "agent" and PLANNER_ENABLED and not _unify_agent:
            dag = await decompose_intent(last_user_text)
            if dag and (dag.get("nodes") or []):
                if streaming:
                    async def _stream_dag() -> AsyncGenerator[bytes, None]:
                        yield _sse_status_phase(chat_id=chat_id, model=model,
                                                phase="prompt")
                        yield _sse_status_phase(chat_id=chat_id, model=model,
                                                phase="route")
                        yield _sse_status_phase(chat_id=chat_id, model=model,
                                                phase="plan")
                        yield _sse_chunk("", chat_id=chat_id, model=model,
                                         role="assistant")
                        # Run the DAG via the unified CONCURRENT executor
                        # (topological levels; agent + verb nodes run in
                        # parallel per level), then render the audit
                        # envelope. Per-node "tool" pills are dropped --
                        # independent nodes now run concurrently so a
                        # per-node stream order is no longer meaningful;
                        # the collapsible envelope is the audit trail.
                        yield _sse_status_phase(chat_id=chat_id, model=model,
                                                phase="tool")
                        dag_result = {}
                        async for _k, _p in _execute_dag_emitting(
                                dag, session_id=session_id,
                                chat_id=chat_id, model=model):
                            if _k == "event":
                                yield _p
                            else:
                                dag_result = _p
                        all_ok = dag_result.get("success", False)
                        env = {
                            "dag": {
                                "summary": dag.get("summary", ""),
                                "nodes_total": dag_result.get("nodes_total", 0),
                                "nodes_executed": dag_result.get("nodes_executed", 0),
                                "success": all_ok,
                            },
                            "nodes": dag_result.get("node_results", []),
                        }
                        symbol = "✅" if all_ok else "⚠️"
                        rendered = (
                            f"<details type=\"tool_calls\" done=\"true\">\n"
                            f"<summary>{symbol} dag · {env['dag']['nodes_total']} steps</summary>\n\n"
                            f"```json\n{json.dumps(env, indent=2, default=str)}\n```\n"
                            f"</details>"
                        )
                        async for _b in _stream_answer(rendered, chat_id=chat_id, model=model):
                            yield _b
                        yield _sse_status_phase(
                            chat_id=chat_id, model=model,
                            phase="dag_done" if all_ok else "dag_done_warn",
                            done=True)
                        yield _sse_chunk("", chat_id=chat_id, model=model,
                                         finish_reason="stop")
                        yield _sse_done()
                    return StreamingResponse(_stream_dag(),
                                             media_type="text/event-stream")
                # Non-streaming DAG execution.
                dag_result = await _execute_dag_bounded(dag, session_id=session_id, request=request)
                env = {
                    "dag": {
                        "summary": dag.get("summary", ""),
                        "nodes_total": dag_result.get("nodes_total", 0),
                        "nodes_executed": dag_result.get("nodes_executed", 0),
                        "success": dag_result.get("success", False),
                    },
                    "nodes": dag_result.get("node_results", []),
                }
                symbol = "✅" if dag_result.get("success") else "⚠️"
                rendered = (
                    f"<details type=\"tool_calls\" done=\"true\">\n"
                    f"<summary>{symbol} dag · {env['dag']['nodes_total']} steps</summary>\n\n"
                    f"```json\n{json.dumps(env, indent=2, default=str)}\n```\n"
                    f"</details>"
                )
                return JSONResponse(content={
                    "id": chat_id,
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "message": {"role": "assistant", "content": rendered},
                        "finish_reason": "stop",
                    }],
                })
            # Planner returned empty / unparseable -> fall through.

        # action == "agent" (planner declined) or unrecognized -> backend.

    # ── No router verdict (router timed out / unparseable) ─────
    # Phase A.1 graceful-degrade: even with no router verdict, give
    # the planner a chance to decompose multi-step intents. If the
    # planner returns a usable DAG, run it; otherwise proceed to the
    # backend proxy. This avoids losing tool dispatch entirely when
    # the router (qwen3:1.7b on the CPU-fallback iGPU lane) takes
    # longer than its timeout budget under cold-load.
    if not verdict and PLANNER_ENABLED and not _unify_agent:
        dag = await decompose_intent(last_user_text)
        if dag and (dag.get("nodes") or []):
            # Same handling as the action=agent path: the unified
            # execute_dag runs it (concurrent levels, agent + verb nodes).
            if streaming:
                async def _stream_dag2() -> AsyncGenerator[bytes, None]:
                    yield _sse_status_phase(chat_id=chat_id, model=model,
                                            phase="prompt")
                    yield _sse_status_phase(chat_id=chat_id, model=model,
                                            phase="plan")
                    yield _sse_chunk("", chat_id=chat_id, model=model,
                                     role="assistant")
                    # Unified CONCURRENT executor (agent + verb nodes,
                    # topological levels in parallel), same as the
                    # action=agent streaming path -- no per-node loop here.
                    yield _sse_status_phase(chat_id=chat_id, model=model,
                                            phase="tool")
                    dag_result = {}
                    async for _k, _p in _execute_dag_emitting(
                            dag, session_id=session_id,
                            chat_id=chat_id, model=model):
                        if _k == "event":
                            yield _p
                        else:
                            dag_result = _p
                    all_ok = dag_result.get("success", False)
                    env = {
                        "dag": {
                            "summary": dag.get("summary", ""),
                            "nodes_total": dag_result.get("nodes_total", 0),
                            "nodes_executed": dag_result.get("nodes_executed", 0),
                            "success": all_ok,
                        },
                        "nodes": dag_result.get("node_results", []),
                    }
                    symbol = "✅" if all_ok else "⚠️"
                    rendered = (
                        f"<details type=\"tool_calls\" done=\"true\">\n"
                        f"<summary>{symbol} dag · {env['dag']['nodes_total']} steps</summary>\n\n"
                        f"```json\n{json.dumps(env, indent=2, default=str)}\n```\n"
                        f"</details>"
                    )
                    async for _b in _stream_answer(rendered, chat_id=chat_id, model=model):
                        yield _b
                    yield _sse_status_phase(
                        chat_id=chat_id, model=model,
                        phase="dag_done" if all_ok else "dag_done_warn",
                        done=True)
                    yield _sse_chunk("", chat_id=chat_id, model=model,
                                     finish_reason="stop")
                    yield _sse_done()
                return StreamingResponse(_stream_dag2(),
                                         media_type="text/event-stream")
            dag_result = await _execute_dag_bounded(dag, session_id=session_id, request=request)
            env = {
                "dag": {
                    "summary": dag.get("summary", ""),
                    "nodes_total": dag_result.get("nodes_total", 0),
                    "nodes_executed": dag_result.get("nodes_executed", 0),
                    "success": dag_result.get("success", False),
                },
                "nodes": dag_result.get("node_results", []),
            }
            symbol = "✅" if dag_result.get("success") else "⚠️"
            rendered = (
                f"<details type=\"tool_calls\" done=\"true\">\n"
                f"<summary>{symbol} dag · {env['dag']['nodes_total']} steps</summary>\n\n"
                f"```json\n{json.dumps(env, indent=2, default=str)}\n```\n"
                f"</details>"
            )
            return JSONResponse(content={
                "id": chat_id,
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": rendered},
                    "finish_reason": "stop",
                }],
            })

    # ── AGENT path / fallback -> proxy to a sub-agent ──────────
    # Phase D.5b: multi-agent routing + hint injection + polish.
    #   1. Pick target_agent from refined hints, fall back to
    #      registry default (Hermes).
    #   2. Build a hint-injected system message ("MiOS-Agent
    #      refined plan: ...") so the sub-agent gets the
    #      operator's intent + suggested tools/skills as context.
    #   3. Forward to the sub-agent's endpoint.
    #   4. Non-streaming: polish the response before returning.
    #      Streaming: emit raw stream + a final polished delta if
    #      polish succeeded (heavy on token re-emission; gated on
    #      response shape so we don't re-stream small chat replies).
    target_role = ""
    if refined:
        target_role = str(refined.get("target_agent") or "").lower()
    target_name, target_cfg = _pick_agent(target_role)
    # Cached liveness, computed ONCE here and reused for both the primary guard
    # and the fan-out below. Prune DOWN nodes so a dead engine (a down iGPU/
    # phone) isn't selected as primary OR dispatched into the council (operator
    # debug: 'mios-igpu 💤' kept appearing). Negligible cost (TTL
    # cache); degrades open (probe failure -> None -> legacy all-configured).
    try:
        _live_set = await _live_agent_names()
    except Exception:  # noqa: BLE001
        _live_set = None
    # OUTAGE: if refine routed the PRIMARY to a node that is currently down, fall
    # back to a LIVE agent (prefer the registry default, which is never
    # health_gate) so the turn never proxies to a dead primary endpoint.
    if _live_set is not None and target_name not in _live_set:
        _alt_name, _alt_cfg = _pick_agent("")     # default agent (always live)
        if _alt_name in _live_set:
            log.info("outage: primary %r down -> live %r", target_name, _alt_name)
            target_name, target_cfg = _alt_name, _alt_cfg
    target_endpoint = target_cfg.get("endpoint") or BACKEND
    # Casual MiOS-convention label for SSE strip; the literal name
    # stays in the event payload + journal for debuggability.
    target_label = f"→ {_casual_agent_label(target_name)}"
    # Multi-agent concurrent fan-out : pick a COUPLE
    # of relevant secondary agents to run alongside the primary. Empty
    # unless [dispatch].fanout_max>1 AND a registered agent's role/strengths
    # match the refined intent -> safe single-agent no-op by default.
    # research_only workers join the council ONLY on a research/deep turn
    # (runaway fix) -- same web/news/deep signal the swarm
    # path uses, recomputed here (no hardcoded English). On an
    # everyday agent turn this keeps the research workers OUT of the fan-
    # out, so a trivial prompt no longer cold-loads the whole pool at once.
    _council_research = bool(refined and (refined.get("web")
                             or refined.get("news") or refined.get("deep")
                             or refined.get("deep_research")))
    # AUTONOMOUS turn (autonomous-wedge fix): a scheduled /
    # cron-fired research run sets metadata.mios_autonomous (mios-scheduled-
    # research). Such a turn must NEVER trigger the WIDE research fan-out -- it
    # fires unattended on a timer, and a periodic research council cold-loading
    # all 2-4GB workers across every lane is exactly what wedged the VM with no
    # user present. Force include_research=False so it stays on the bounded
    # council (capped + no research workers), regardless of research intent.
    # _autonomous read once near the top of the handler (with _mflags). An
    # autonomous turn forces the bounded council (no research workers).
    if _autonomous and _council_research:
        log.info("autonomous turn: forcing bounded council (no wide research fan-out)")
        _council_research = False
    # Model-driven relevance selection (the old token-overlap
    # scorer was itself a hardcode) -> async; degrades open to council-equal-weight.
    _fanout = await _pick_fanout_agents(target_name, refined,
                                        force_council=(_force_council and not _autonomous),
                                        live_agents=_live_set,
                                        include_research=_council_research)
    # ACTION-DOMAIN -> PRIMARY-ONLY ("YOU LIED AGAIN" / discord
    # read-only failure). Even with the forced council suppressed above, the relevance-
    # gated fanout STILL recruits read-only secondaries (mios-daemon-agent / node:local-*
    # run the pipe-side READ-ONLY tool-loop -- they SKIP write verbs, narrate
    # "discord_send is restricted to read-only", and their refusals both poison the
    # synthesis AND blow the latency budget -> the 200s timeout). A write action is
    # executed by the ONE write-capable primary (Hermes), not a council. Multi-step
    # actions were already decomposed by the action-route DAG planner earlier.
    if _is_action_domain(_routed_domain_var.get(None)) and _fanout:
        log.info("action-domain: collapsing fanout to primary-only "
                 "(read-only secondaries cannot perform writes)")
        _fanout = []
    if _fanout:
        # A5: this turn REALLY fans out to >=1 secondary -> report council mode honestly.
        try:
            _council_mode_var.set("council")
        except Exception:  # noqa: BLE001
            pass
        log.info("fanout%s: primary=%s + %d secondary %s",
                 " (FORCED swarm)" if _force_council else "",
                 target_name, len(_fanout), [n for n, _ in _fanout])

    # Build the proxy body + enrich the system prefix. The FOUR enrich passes
    # are independent (latency) and run CONCURRENTLY (worst
    # case = their MAX not SUM):
    #   _rag_enrich           vector recall (in-loop for every agent)
    #   _web_research_enrich  full web toolchain: SearXNG + extract + deep crawl
    #   _read_tool_enrich     refine-hinted READ-only no-arg verbs (live state);
    #                         WRITE/launch verbs are NEVER auto-fired (binding)
    #   _recall_knowledge     prior finished Q+A (read half of store/recall)
    # CRITICAL ("no emitters at all until almost the end"):
    # this used to be a ~90s BLOCK *before* the streaming generator started, so
    # the client saw nothing until it finished, then everything dumped. It is now
    # a COROUTINE: the streaming path runs it INSIDE the generator with a LIVE
    # emit sink (each web step streams in real time); the non-streaming path just
    # awaits it. Returns (full system prefix, finalized proxy body).
    async def _finalize(emit=None):
        pb = dict(body)
        # Strip SWARM control flags (MiOS orchestration, not an OpenAI field).
        pb.pop("mios_flags", None)
        # 🧠 Force-tool: tool_choice=required -> the executor MUST emit a real
        # tool_call instead of narrating (anti-"I posted to Discord" guard).
        # Fires on the manual OWUI toggle OR auto when refine hinted a state-
        # changing (non-read) verb (slice 3) -- the structural anti-narration fix
        # the big labs use; gated by verb permission, not an action-word list.
        if _force_tool or (AUTO_FORCE_TOOL and not _force_council
                           and not _force_delegate
                           and (_hints_write_action(refined)
                                or _is_action_domain(_routed_domain_var.get(None)))):
            # action-domain turns force a real tool_call even when refine mislabels
            # them intent=chat ("send a discord message" was
            # refined as chat -> no write-hint -> the primary narrated a read-only
            # refusal instead of calling discord_send). An action domain MUST act.
            if not isinstance(pb.get("tool_choice"), dict):
                pb["tool_choice"] = "required"
        # PRIMARY force-tool opt-out (mirrors the council/secondary downgrade at
        # _sec_body): llama.cpp 200-ACCEPTS but SILENTLY IGNORES tool_choice, so
        # 'required'/named reaches :11450 un-forcing -- the force-tool guard is a
        # no-op on the BACKEND_LIGHT primary path. Downgrade required->auto when the
        # resolved primary endpoint doesn't honor it (llama.cpp still emits real
        # tool_calls under 'auto'); leave SGLang/vLLM heavy lanes that DO honor it
        # untouched. The BACKEND-light lane carries no api='llamacpp' in target_cfg,
        # so synthesize that cfg from the SSOT flag so the helper recognizes it.
        _pc = pb.get("tool_choice")
        if _pc not in ("none", "auto", None):
            _prim_cfg = ({"api": "llamacpp"}
                         if (_BACKEND_IS_LIGHT
                             and str(target_endpoint).rstrip("/")
                             == str(BACKEND).rstrip("/"))
                         else target_cfg)
            if not _endpoint_supports_tool_choice(
                    str(target_endpoint or ""), _prim_cfg,
                    _agent_offload_engine(_prim_cfg)):
                pb["tool_choice"] = "auto"
        # Universal agent contract FIRST (".md presented
        # to every agent"): the primary + every council secondary lead with
        # the overlay contract (global tools, live internet, delegation, no
        # disclaim/fabricate) BEFORE env grounding -- so a secondary never
        # falls back to "I have no internet" / stale-data invention.
        sp: list = []
        _contract = _agent_contract()
        if _contract:
            sp.append({"role": "system", "content": _contract})
        _overlay = _role_system(target_name)   # thin per-role DEVELOPER overlay (OpenAI pattern)
        if _overlay:
            sp.append({"role": "system", "content": _overlay})
        sp.append({"role": "system", "content": _env_grounding()})
        _spb = _scratchpad_render()
        if _spb:
            sp.append({"role": "system", "content": _spb})
        # Fresh-news turns SKIP knowledge recall : a prior
        # stored answer is stale by definition for "what's new today", and a weak
        # research replica was observed parroting an off-topic recalled answer.
        # web/news/deep => fetch live, don't recall.
        _fresh = bool(refined and (refined.get("web") or refined.get("news")
                      or refined.get("deep") or refined.get("deep_research")))

        async def _recall_or_skip():
            return "" if _fresh else await _recall_knowledge(last_user_text)
        # Ground the web search off the CLEAN refined query (
        # "too sparse"): the raw user text fanned out to junk ("worldwide trends
        # today"); refine's disambiguated/date-anchored text returns real stories.
        _cq = str((refined or {}).get("refined_text") or "").strip() or last_user_text
        _rag_ctx, _web_ctx, _readtool_ctx, _recall_ctx, _amem_ctx = [
            (c if isinstance(c, str) else "") for c in await asyncio.gather(
                _rag_enrich(last_user_text),
                _web_research_enrich(_cq, refined, emit=emit),
                _read_tool_enrich(refined, session_id),
                _recall_or_skip(),
                _recall_agent_memory(last_user_text),  # P1: self-edited durable facts (default-off)
                return_exceptions=True)]
        # Research context (RAG / web / read-tool) stays as SYSTEM context. But the
        # SAVED-FACTS recall (knowledge + agent-memory) must NOT sit in a system
        # message -- the model ignores recall buried there ~1/3 (the native-loop's
        # own note ~20911 documents this). Position the saved facts IMMEDIATELY
        # before the user's question with strong "you HAVE this" framing instead
        # (mirrors the native-loop fix 20913-20928) so "what do you remember about X"
        # reliably answers from the saved fact instead of "I have no stored
        # information" (Claude recall-grounding fix). NO-OP for turns with
        # no saved facts: _saved_ctx="" -> sp holds the same 3 research blocks as
        # before and the prefix below never fires -> identical message shape.
        for _ctx in (_rag_ctx, _web_ctx, _readtool_ctx):
            if _ctx:
                sp.append({"role": "system", "content": _ctx})
        _saved_ctx = "\n\n".join(c for c in (_recall_ctx, _amem_ctx) if c)
        # The refined-plan marker block (intent / intended_outcome / tool+skill
        # hints) is for the ACTING PRIMARY only -- a generic council secondary
        # PARROTS it verbatim into its answer. Secondaries
        # get the shared context + conversation, nothing to parrot.
        _hint = None
        if refined and (refined.get("hint_tools") or refined.get("hint_skills")
                        or refined.get("intended_outcome")):
            _hint = {"role": "system",
                     "content": _build_agent_hint(refined, target_name)}
        _conv = list(messages)
        if _saved_ctx and _conv:
            for _i in range(len(_conv) - 1, -1, -1):
                _m = _conv[_i]
                if isinstance(_m, dict) and _m.get("role") == "user" \
                        and isinstance(_m.get("content"), str):
                    _conv[_i] = {**_m, "content": (
                        "You ARE an assistant WITH persistent cross-session memory -- the "
                        "SAVED CONTEXT below IS your memory of this user. It is FALSE to say "
                        "you have no memory, no stored information, cannot remember, or lack "
                        "access -- NEVER say that. These are facts YOU recorded earlier; "
                        "ANSWER the question DIRECTLY AND CONFIDENTLY from them, and do NOT "
                        "call a tool to re-fetch what is already here:\n" + _saved_ctx
                        + "\n\n---\nUser's question: " + str(_m.get("content") or ""))}
                    break
        pb["messages"] = sp + ([_hint] if _hint else []) + _conv
        return sp, pb
    # Normalise header keys to lowercase so the Content-Type set
    # below replaces (not duplicates) whatever the incoming request
    # supplied. Operator-flagged trace: Hermes :8642
    # returned 400 "Duplicate 'Content-Type' header found" because
    # request.headers preserved case ("Content-Type") + setdefault
    # added a second copy ("content-type").
    headers = {k.lower(): v for k, v in request.headers.items()
               if k.lower() in ("authorization", "accept")}
    headers["content-type"] = "application/json"
    # Drop an empty / placeholder client Authorization (a keyless OpenAI
    # client like Firefox Smart Window may send a blank "Bearer" or omit the
    # key) so the backend-key fallback below applies instead of forwarding an
    # unusable header that Hermes 401s on.
    _ca = headers.get("authorization", "").strip()
    if _ca.lower() in ("", "bearer", "bearer null", "bearer none", "bearer undefined"):
        headers.pop("authorization", None)
    # The client bearer authenticates the CLIENT->PIPE hop only. Hermes
    # enforces ONE canonical API_SERVER_KEY, so forwarding any OTHER client
    # token (a desktop app's own api_key, a curl test key) 401s the whole
    # turn before a single delta streams -- the bare "⚠️ / 🤖 general only"
    # failure. Present OUR backend credential whenever
    # we have one; the fallback-only injection below covers the keyless case.
    if _BACKEND_KEY:
        headers["authorization"] = f"Bearer {_BACKEND_KEY}"

    # Detail strings: refine elapsed/intent/model, target endpoint,
    # tool_cards count, multi_task queue length. Operator should be
    # able to read the strip and tell exactly which sub-agent got
    # what plan.
    if streaming:
        # OPERATOR-BINDING: ALL sub-agent output goes inside the
        # <details type="reasoning"> dropdown; polished answer is
        # main content; <think> tags are stripped.
        #
        # Strategy: force upstream stream=false so we get the
        # COMPLETE final message (Hermes's tool-loop fully resolved,
        # tool_calls invoked + their results folded in, final
        # message.content assembled). Then run polish/wrap/strip on
        # that and emit ONE assistant content delta. We lose
        # mid-tool-call streaming visibility but gain a COMPLETE
        # final content -- the previous SSE-line parser dropped
        # tool_call envelope deltas, leaving the content cut off
        # mid-sentence ("using the standard Windows screenshot
        # command:" with nothing after). Real-time status strip
        # still streams (agent-pipe's own _sse_status_phase events
        # below).
        async def _stream_backend_inner() -> AsyncGenerator[bytes, None]:
            yield _sse_status_phase(chat_id=chat_id, model=model,
                                    phase="prompt")
            if refined:
                yield _sse_status_phase(chat_id=chat_id, model=model,
                                        phase="refine")
            yield _sse_status_phase(chat_id=chat_id, model=model,
                                    phase="route")
            yield _sse_status_phase(chat_id=chat_id, model=model,
                                    phase="agent_target")
            # Run the enrich passes INSIDE the stream with LIVE web-step emits
            # ("no emitters at all until almost the end" --
            # the enrich was a ~90s BLOCK *before* the generator started, so the
            # client saw nothing then everything dumped). Drain its emit queue and
            # yield each step (🔎 search, 🕷️ crawl, 📚 grounded) in REAL TIME, with
            # a keepalive during any silent gap. _finalize returns the prefix +
            # body once the toolchain completes.
            _eq: asyncio.Queue = asyncio.Queue()
            _fin_holder: dict = {}

            async def _run_enrich() -> None:
                try:
                    _fin_holder["v"] = await _finalize(emit=_eq.put_nowait)
                finally:
                    _eq.put_nowait(None)        # sentinel: enrich done

            _etask = asyncio.create_task(_run_enrich())
            while True:
                try:
                    _s = await asyncio.wait_for(_eq.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    yield b": keepalive\n\n"
                    continue
                if _s is None:
                    break
                yield _sse_status(chat_id=chat_id, model=model,
                                  emoji=str(_s.get("emoji", "·")),
                                  label=str(_s.get("label", "")),
                                  detail=_s.get("detail"))
            await _etask
            _sys_prefix, proxy_body = _fin_holder.get(
                "v", ([{"role": "system", "content": _env_grounding()}],
                      {**dict(body), "messages": list(messages)}))
            # Endpoint emitter: announce the PRIMARY node + its endpoint.
            yield _node_status(
                chat_id=chat_id, model=model, name=target_name,
                cfg={**(_AGENT_REGISTRY.get(target_name) or {}),
                     "endpoint": target_endpoint}, state="engage")
            client = await _get_client()
            stream_body = dict(proxy_body)
            stream_body["stream"] = True
            raw = ""
            # Stream Hermes's INLINE output (reasoning + tool steps + answer
            # are one interleaved stream -- "Hermes prints everything
            # inline",) and forward it into the dropdown
            # as CHECKPOINTED, self-contained <details done="true"> reasoning
            # blocks. Each block renders the instant it closes (a single
            # growing <details> only renders once closed -> "everything
            # dumps at the end"). The full content is accumulated for the
            # polish pass. CRITICAL: accumulate EVERY content delta and
            # REPRESENT tool_calls inline -- the previous parser dropped
            # tool_call deltas and cut content off mid-sentence, which is
            # why this path used to buffer.
            _block_buf = ""
            _last_flush = time.time()
            _ckpt_s = float(os.environ.get("MIOS_AGENT_CKPT_S", "2.0"))
            _reasoning_open = False
            # CONFIRMATION ENGINE: names of verbs the sub-agent invokes
            # inside its own tool-loop, captured from the stream. Feeds
            # the Definition-of-Done check below -- agent-pipe records no
            # tool_call row for a hermes-internal verb, so this is the
            # only signal that the turn DID act.
            _tools_called: list = []
            _summary = _HUMAN_LABELS.get("agent_target", ("🤖", ""))[0]

            def _flush_reasoning(buf: str) -> bytes:
                # KEYSTONE : stream the agent's live
                # thinking on the STANDARD delta.reasoning_content channel --
                # NOT as a <details> block inside content. OWUI renders
                # reasoning_content as its native Thinking dropdown; strict
                # OpenAI clients (Firefox Smart Window) ignore it and show
                # only the clean `content` answer. This is what stops the
                # <think> leaks, the reasoning masquerading as the answer, and
                # the empty-answer / no-emit behaviour.
                return _sse_reasoning(_sanitize_tool_text(buf),
                                      chat_id=chat_id, model=model)

            # The reasoning dropdown opens on the FIRST real reasoning delta
            # (tool steps / council merges via _flush_reasoning below). The old
            # "👂 ✨ 🧭 🤖" preamble was REMOVED -- it dumped bare
            # emojis into the dropdown ("Hermes just prints emojis"); the phase
            # pills already carry that progress signal as status events.
            # Kick the secondary fan-out agents CONCURRENTLY with the primary
            # stream ('a couple at a time'). They run
            # non-streaming + best-effort; their answers fold into polish +
            # the reasoning dropdown once the primary finishes. Dead endpoints
            # drop out harmlessly (return_exceptions on the gather below).
            # Endpoint emitters: announce EACH secondary node as it's engaged,
            # and remember its cfg so the collection loop can mark it
            # responded/silent.
            _fanout_cfg = {_n: _c for _n, _c in _fanout}
            # Live MERGED-event-queue streaming : the
            # PRIMARY is pumped in the BACKGROUND into the SAME queue the
            # secondaries stream into, so the generator drains ONE queue and
            # secondary fragments interleave LIVE even while the primary sits
            # SILENT in a tool-loop (the prior version only drained on a
            # primary delta). Per-agent buffered + checkpoint-flushed
            # (🤝 <agent>: ...) so N concurrent agents stay readable.
            _ev_q: "asyncio.Queue" = asyncio.Queue()
            _sec_bufs: dict = {}
            _sec_last: dict = {}
            _sec_hdr: set = set()   # nodes whose "🤝 <name>:" header already shown

            def _flush_sec(force: bool = False) -> list:
                out: list = []
                _now = time.time()
                for _nm in list(_sec_bufs.keys()):
                    _buf = _sec_bufs.get(_nm, "")
                    if not _buf.strip():
                        continue
                    if force or (_now - _sec_last.get(_nm, 0.0) >= _ckpt_s):
                        # Emit the "🤝 <node>:" header ONCE; later flushes for the
                        # same node append content WITHOUT re-labelling. The old
                        # code re-prefixed the label on EVERY checkpoint, so a node
                        # that streamed across N flushes spammed "🤝 <node>:" N times
                        # down the reasoning dropdown -- burying the other nodes
                        # (operator: "didnt show details for ALL nodes").
                        if _nm in _sec_hdr:
                            out.append(_flush_reasoning(_buf))
                        else:
                            out.append(_flush_reasoning(f"\n🤝 {_nm}: {_buf}"))
                            _sec_hdr.add(_nm)
                        _sec_bufs[_nm] = ""
                        _sec_last[_nm] = _now
                return out

            def _pump_sec(force: bool = False) -> list:
                # Non-blocking pull of queued secondary fragments into the
                # per-agent buffers, for the post-primary phases where the
                # main merged loop is no longer draining the queue.
                while True:
                    try:
                        ev = _ev_q.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                    if ev and ev[0] == "SF":
                        _sec_bufs[ev[1]] = _sec_bufs.get(ev[1], "") + ev[2]
                return _flush_sec(force)

            async def _primary_pump():
                # Stream the primary (Hermes) in the BACKGROUND, pushing typed
                # events onto _ev_q; a PD sentinel marks end-of-stream so the
                # merged drain loop knows the primary is finished.
                conv_gw_mode = os.environ.get("MIOS_CONV_GATEWAY_MODE", "http")
                is_queue_mode = (conv_gw_mode == "queue" and str(target_endpoint).rstrip("/") == str(BACKEND).rstrip("/"))
                try:
                    if is_queue_mode:
                        try:
                            import mios_dispatcher
                            res = await mios_dispatcher.dispatch_via_queue(stream_body, GATEWAY_QUEUE)
                            content = ""
                            if isinstance(res, dict):
                                choices = res.get("choices") or []
                                if choices:
                                    msg = choices[0].get("message") or {}
                                    content = msg.get("content") or ""
                            if content:
                                _ev_q.put_nowait(("PR", content))
                        except Exception as e:
                            log.warning("queue stream dispatch failed, falling back to HTTP: %s", e)
                            is_queue_mode = False
                    if not is_queue_mode:
                        async with client.stream(
                                "POST",
                                f"{target_endpoint}/chat/completions",
                                content=json.dumps(stream_body).encode("utf-8"),
                                headers=headers) as resp:
                            if resp.status_code != 200:
                                await resp.aread()
                                log.warning("streamed backend %s",
                                            resp.status_code)
                            else:
                                async for line in resp.aiter_lines():
                                    if not line or not line.startswith("data:"):
                                        continue
                                    data = line[5:].strip()
                                    if data == "[DONE]":
                                        break
                                    try:
                                        chunk = _loads_lenient(data)
                                    except (json.JSONDecodeError, ValueError):
                                        continue
                                    ch = chunk.get("choices") or []
                                    if not ch:
                                        continue
                                    delta = ch[0].get("delta") or {}
                                    piece = delta.get("content") or ""
                                    if piece:
                                        _ev_q.put_nowait(("PR", piece))
                                    for _tc in (delta.get("tool_calls") or []):
                                        _fn = (_tc.get("function") or {}).get("name")
                                        if _fn:
                                            _ev_q.put_nowait(("PT", _fn))
                except Exception as e:
                    log.warning("streamed backend call failed: %s", e)
                finally:
                    _ev_q.put_nowait(("PD", None))

            # Secondaries run on the lighter body (shared context, NO primary-
            # only marker block) so a generic council model cannot parrot the
            # routing plan into its answer. Built PER-LANE: a SLOW lane (iGPU /
            # phone) gets a TRIMMED prefix (_trim_sys_prefix) so its slow prefill
            # finishes in budget instead of being abandoned mid-compute.
            # P2.1 role-lens ("council not fan-out"):
            # prepend a small SECONDARY-SPECIFIC system message identifying
            # the agent's angle so the council answers from N DIVERSE lenses
            # instead of duplicating one answer N times.
            _sec_tasks = []
            for _n, _c in _fanout:
                _node_body = dict(proxy_body)
                _lens = _council_role_lens(_n, _c)
                _lens_msgs = ([{"role": "system", "content": _lens}]
                              if _lens else [])
                _node_body["messages"] = (
                    _lens_msgs
                    + _trim_sys_prefix(_sys_prefix, _agent_lane(_c))
                    + list(messages))
                # Hand each council secondary the SAME global verb surface the
                # DAG workers get so the fan-out agents
                # CALL tools (web_search/etc.) via the secondary tool-loop
                # instead of fabricating/disclaiming. Writes are gated on the
                # refined intent (mirrors the primary path) -- a read-only turn
                # keeps the secondaries read-only, avoiding parallel write storms.
                if WORKER_TOOLS_ENABLE:
                    _wtools = await _worker_tools_surface_async(
                        cap=_lane_tool_cap(_agent_lane(_c)), intent=_lens)
                    if _wtools:
                        _node_body["tools"] = _wtools
                        _node_body["num_ctx"] = WORKER_TOOL_CTX
                        _node_body["_allow_write"] = _hints_write_action(refined)
                _tc_val = _node_body.get("tool_choice")
                if _tc_val and _tc_val not in ("none", "auto") and not \
                        _endpoint_supports_tool_choice(
                            str(_c.get("endpoint") or ""), _c,
                            _agent_offload_engine(_c)):
                    # Downgrade required->auto (llama.cpp accepts auto + emits real
                    # tool_calls); dropping it made the model narrate the call.
                    _node_body["tool_choice"] = "auto"
                # context = the secondary's ROLE/specialty (why it's engaged on
                # this turn); council members all answer the same prompt, so the
                # role is the relevant per-node step context.
                yield _node_status(chat_id=chat_id, model=model, name=_n,
                                   cfg=_c, state="engage",
                                   context=str(_c.get("role", "")))
                _sec_tasks.append(asyncio.create_task(
                    _call_agent_stream(_n, _c, _node_body, headers, client,
                                       _ev_q, priority=_turn_priority)))
            _prim_task = asyncio.create_task(_primary_pump())
            # Per-secondary ✅/💤 emitted LIVE as each fan-out task FINISHES
            # ("emitters per-step compute, not all at
            # once"). Was a burst after the post-primary gather. Records each
            # result so the post-loop merge reuses it (no second emit).
            _sec_meta = list(_fanout)
            _sec_done_emitted: set = set()
            _sec_results: dict = {}

            def _finished_sec_status() -> list:
                _o: list = []
                for _ti, _t in enumerate(_sec_tasks):
                    if _t in _sec_done_emitted or not _t.done():
                        continue
                    _sec_done_emitted.add(_t)
                    _mn, _mc = _sec_meta[_ti]
                    try:
                        _rn, _rt = _t.result()
                    except Exception:
                        _rn, _rt = _mn, ""
                    _sec_results[_mn] = (_rn, _rt)
                    _o.append(_node_status(
                        chat_id=chat_id, model=model, name=_mn, cfg=_mc,
                        state="ok" if (_rt and _rt.strip()) else "down"))
                return _o

            # Drain the MERGED queue until the primary signals done. Primary
            # reasoning + tool steps and secondary fragments interleave LIVE,
            # whichever source is producing. The pending get() is KEPT across
            # idle timeouts (never cancelled) so no event -- including a piece
            # of the primary `raw` -- is ever dropped by a wait_for race.
            _primary_done = False
            _get_task = None
            while not _primary_done:
                if _get_task is None:
                    _get_task = asyncio.ensure_future(_ev_q.get())
                _done, _ = await asyncio.wait({_get_task}, timeout=2.0)
                # Stream ✅/💤 for any secondary that JUST finished -- per-step
                # live, interleaved with the primary, not a burst at the end.
                for _b in _finished_sec_status():
                    yield _b
                if not _done:
                    for _b in _flush_sec():
                        yield _b
                    yield b": keepalive\n\n"
                    continue
                ev = _get_task.result()
                _get_task = None
                _k = ev[0]
                if _k == "PR":
                    raw += ev[1]
                    _block_buf += ev[1]
                    if (_block_buf.strip()
                            and time.time() - _last_flush >= _ckpt_s):
                        yield _flush_reasoning(_block_buf)
                        _block_buf = ""
                        _last_flush = time.time()
                    for _b in _flush_sec():
                        yield _b
                elif _k == "PT":
                    _fn = ev[1]
                    _block_buf += f"\n🛠️ {_fn}\n"
                    if _fn not in _tools_called:
                        _tools_called.append(_fn)
                    yield _sse_status(chat_id=chat_id, model=model,
                                      emoji="🛠️", label="", detail=_fn)
                    for _b in _flush_sec():
                        yield _b
                elif _k == "SF":
                    _sec_bufs[ev[1]] = _sec_bufs.get(ev[1], "") + ev[2]
                    for _b in _flush_sec():
                        yield _b
                elif _k == "PD":
                    _primary_done = True
            # Flush the tail of the reasoning buffer. No </details> to close --
            # reasoning_content is a separate delta channel, not inline markup.
            if _block_buf.strip():
                yield _flush_reasoning(_block_buf)
            # CONFIRMATION ENGINE : run the
            # Definition-of-Done check NOW -- on the agent's just-finished
            # answer + the verbs it invoked -- BEFORE the heavy critic
            # re-pass. The check writes the authoritative
            # user_query_(un)satisfied verdict polish reads downstream.
            # When the turn is CONFIRMED satisfied (the agent acted and
            # delivered an answer, no recorded tool failed), the chain
            # HALTS here: the critic is SKIPPED. The critic re-litigates a
            # done answer and can flip a confirmed success into a false
            # failure -- the mios-os-control "succeeds early then reports
            # failed after a long chain" bug. Only re-critique an
            # UNCONFIRMED / unsatisfied turn, where a corrective pass is
            # actually warranted.
            _verdict = await _inline_satisfaction_check(
                session_id, refined,
                agent_tools_called=_tools_called,
                agent_answered=bool(raw.strip()))
            _confirmed = bool(
                _verdict
                and _verdict.get("kind") == "user_query_satisfied")
            if _confirmed:
                # Halt: surface the confirmation in the live dropdown so
                # the operator sees the chain stopped on success, not on a
                # timeout. Glyph-only, locale-neutral.
                yield _flush_reasoning("\n✅\n")
            else:
                # Critic->refiner (heavy agent path; fires only when the
                # turn is NOT confirmed satisfied): if the DCI critic
                # challenges this answer, revise it ONCE before polish.
                # No-op for short answers + when the critic is happy.
                # Heartbeat-wrap it: the DCI critic runs on a possibly-
                # contended lane and may re-invoke Hermes (5-40s); a bare
                # await went silent. Robust: returns
                # the original `raw` on any error.
                critic_task = asyncio.create_task(_critic_refine_agent(
                    raw, last_user_text, refined, session_id,
                    client=client, target_endpoint=target_endpoint,
                    headers=headers, base_body=proxy_body))
                while not critic_task.done():
                    try:
                        await asyncio.wait_for(
                            asyncio.shield(critic_task), timeout=2.0)
                    except asyncio.TimeoutError:
                        for _b in _pump_sec():
                            yield _b
                        yield b": keepalive\n\n"
                    except Exception:
                        break
                try:
                    raw = critic_task.result()
                except Exception:
                    pass  # keep the pre-critic raw on any failure
            # Collect the concurrent fan-out agents :
            # they ran alongside the primary, so this await adds little. Each
            # secondary's work surfaces in the reasoning dropdown and merges
            # into the polish input so the final answer SYNTHESISES all agents.
            # ANTI-LEAK (OWUI docs): the primary's content
            # streamed live to the dropdown via the reasoning_content channel
            # ALREADY; strip any <think>/<thinking>/<reasoning>-family tags from
            # the answer source so reasoning can NEVER masquerade as / leak into
            # the final response (the reasoning stays in its native dropdown).
            raw = _strip_think_tags(raw)
            raw_for_polish = raw
            # Roster of contributing agents (primary + ok secondaries) -- used
            # by the generative synthesis emit + the dropdown summary. Always
            # defined (even with no secondaries) so polish-time refs are safe.
            _roster = [(target_name, "ok")]
            if _sec_tasks:
                while not all(t.done() for t in _sec_tasks):
                    try:
                        await asyncio.wait_for(
                            asyncio.shield(asyncio.gather(
                                *_sec_tasks, return_exceptions=True)),
                            timeout=2.0)
                    except asyncio.TimeoutError:
                        for _b in _pump_sec():
                            yield _b
                        yield b": keepalive\n\n"
                    except Exception:
                        break
                # Flush tail fragments + emit ✅/💤 for any FINAL straggler
                # secondary (finished after the primary; most already streamed
                # their status live during the drain loop above).
                for _b in _pump_sec(force=True):
                    yield _b
                for _b in _finished_sec_status():
                    yield _b
                # Build the polish merge from the per-secondary results that the
                # live-status helper recorded (status already emitted -> no
                # duplicate _node_status here; their text already streamed into
                # the dropdown via the merged queue, so we fold text only).
                _merge = []
                for _mn, _mc in _sec_meta:
                    _sn, _stext = _sec_results.get(_mn, (_mn, ""))
                    if _stext and _stext.strip():
                        _merge.append(f"[{_sn} agent]:\n{_stext.strip()}")
                        _scratchpad_note(_sn, _stext, phase="council")
                        _roster.append((_mn, "ok"))
                    else:
                        _roster.append((_mn, "down"))
                # Final dropdown summary line (the per-node ✅/💤 already streamed
                # live, per-step; this is just the at-a-glance recap).
                yield _flush_reasoning(
                    "\n🛰️ swarm: " + " · ".join(
                        f"{_pretty_name(_nm)} {'✅' if _st == 'ok' else '💤'}"
                        for _nm, _st in _roster) + "\n")
                if _merge:
                    raw_for_polish = (raw + "\n\n" + "\n\n".join(_merge)).strip()
            # (Satisfaction verdict already written by the confirmation
            # engine above, BEFORE the critic gate, so polish's recent-
            # verdicts block sees THIS turn's authoritative verdict.)
            # GATE ON THE MERGED CONTENT, not the primary alone (operator
            # "BOTH ARE FAILURES"): when the primary (hermes)
            # returns empty/silent but the concurrent SECONDARIES succeeded
            # (their drafts are already folded into raw_for_polish via the
            # _merge above), the answer is RIGHT THERE -- gating on `raw`
            # alone discarded it and emitted a bare "⚠️" while the master
            # review / news synthesis sat unused in the dropdown. Gate on
            # raw_for_polish so a live secondary still produces a real answer.
            if raw_for_polish.strip():
                # Skip the (slow CPU) polish when the sub-agent's answer
                # is ALREADY clean -- no <think>-tag leakage and not
                # absurdly long. Hermes usually formats its answer well,
                # so re-writing it just burns the CPU polish lane, which
                # was timing out 45s on an already-clean answer (operator
                # "slight refactor"). Polish only messy raw.
                # Polish PREPARES the final user-facing answer from the
                # sub-agent's think blocks -- "Hermes doesn't create the
                # final answer EVER". So it ALWAYS
                # runs; it's fast now on the 4b dGPU lane. Heartbeat-
                # wrapped so the SSE stream stays alive during it.
                # Live status across the otherwise-silent ~8s synthesis pass:
                # name the agents actually being synthesised (generative, not a
                # static label) -- "emits are generative
                # live to the tasks being done".
                yield _sse_status(
                    chat_id=chat_id, model=model, emoji="🧬",
                    label=" + ".join(_pretty_name(_nm) for _nm, _st in _roster if _st == "ok"))
                polish_task = asyncio.create_task(polish_response(
                    raw_for_polish, refined, session_id=session_id,
                    original_user_text=last_user_text,
                    persona_system=_persona_system,
                    agent_tools=_tools_called))
                while not polish_task.done():
                    try:
                        await asyncio.wait_for(
                            asyncio.shield(polish_task), timeout=8.0)
                    except asyncio.TimeoutError:
                        yield b": keepalive\n\n"
                    except Exception:
                        break
                try:
                    polished = polish_task.result()
                except Exception:
                    polished = None
                # The sub-agent's FULL raw work -- its responses, prints,
                # AND reasoning -- goes into the collapsed
                # <details type="reasoning"> dropdown (operator binding:
                # 'sub-agent responses and prints and thinking is all
                # printed to thinking'). The POLISHED clean answer is the
                # main reply. <think>-family tag MARKERS are unwrapped
                # (content kept, readable) so reasoning shows in the
                # dropdown instead of bleeding inline or being discarded.
                dropdown_content = _THINK_ORPHAN_RE.sub("", raw).strip()
                # Fallback source = primary answer, OR the merged secondary
                # content when the primary was empty :
                # so a silent primary + live secondaries still yields a real
                # answer instead of "⚠️" if polish itself returns nothing.
                answer_only = (_strip_think_tags(raw).strip()
                               or _strip_think_tags(raw_for_polish).strip())
                polished_clean = (
                    _strip_think_tags(polished) if polished else ""
                )
                main = polished_clean.strip() or answer_only.strip()
                preamble = ""
                if (isinstance(refined, dict)
                        and refined.get("_multi_task_queue")):
                    preamble = _multi_task_preamble(
                        refined["_multi_task_queue"],
                        int(refined.get(
                            "_multi_task_active_idx", 0)),
                    )
                # Show the dropdown whenever the sub-agent's work is more
                # than the bare answer (reasoning/prints present, or polish
                # reshaped it). When the raw IS already the clean answer,
                # skip the dropdown (no double-render).
                # agent-pipe emits ONLY the clean polished answer. The
                # live thinking dropdown is owned by the OWUI pipe, which
                # streams the AI's actual work from the hermes-tail
                # (generative, live) -- "pure streamed
                # + generative, nothing hardcoded". No post-hoc wrap here
                # (that wrap caused the "answered twice" duplication).
                wrapped = f"{preamble}{main}"
            else:
                # Upstream returned nothing usable (HTTP error,
                # truncated, etc.). Emit a brief warning marker so
                # the operator gets visible feedback instead of an
                # empty turn. Localised by glyph alone.
                wrapped = "⚠️"
            # Attach REAL sources to the STREAMED answer :
            # harvest the answer's own inline URLs + the turn-collected sources,
            # then append a numbered **Sources:** list so the streamed reply
            # (OWUI / Discord) carries real citations, never invented names.
            try:
                _src_record_from_text(wrapped)
            except Exception:  # noqa: BLE001
                pass
            _stream_refs = _src_collected()
            _stream_refs = _filter_relevant_sources(_stream_refs, wrapped)
            if _stream_refs and "**Sources:**" not in wrapped:
                wrapped = wrapped.rstrip() + _sources_markdown(_stream_refs)
            yield _sse_chunk("", chat_id=chat_id, model=model,
                             role="assistant")
            async for _ab in _stream_answer(wrapped, chat_id=chat_id,
                                            model=model):
                yield _ab
            yield _sse_status_phase(chat_id=chat_id, model=model,
                                    phase="subagent_done", done=True)
            yield _sse_chunk("", chat_id=chat_id, model=model,
                             finish_reason="stop")
            yield _sse_done()
        # BULLET-PROOF : wrap the council stream so an
        # unhandled exception mid-iteration can NEVER wedge the SSE (leaving the
        # client hung). On error: log + close the stream cleanly (finish + done);
        # preserve cancellation. Happy path unchanged. Glyph-free, no hardcoded
        # English (the partial content already streamed is the answer).
        async def _stream_backend() -> AsyncGenerator[bytes, None]:
            try:
                async for _b in _stream_backend_inner():
                    yield _b
            except asyncio.CancelledError:
                raise
            except Exception as _e:  # noqa: BLE001
                log.warning("_stream_backend aborted mid-stream: %s", _e)
                try:
                    yield _sse_chunk("", chat_id=chat_id, model=model,
                                     finish_reason="stop")
                    yield _sse_done()
                except Exception:  # noqa: BLE001
                    pass
        return StreamingResponse(_stream_backend(),
                                 media_type="text/event-stream")
    # Non-streaming: run the enrich passes (no live emits on this path) and
    # build the proxy body -- same _finalize the streaming generator runs live.
    _sys_prefix, proxy_body = await _finalize()
    # Pin the model to the lane this request is ACTUALLY dispatched to. The front
    # door advertises a single virtual model ("MiOS AI") and sub-agents carry
    # lane-specific models (e.g. the heavy worker's "mios-heavy"); when the
    # primary resolves to the BACKEND light lane -- including the health-gate
    # fallback when the heavy worker is down -- that incoming/heavy model is NOT
    # served there, so llama-swap returns "no router for requested model". Force
    # BACKEND_MODEL so the fallback request routes. install-robustness.
    if str(target_endpoint).rstrip("/") == str(BACKEND).rstrip("/"):
        proxy_body["model"] = BACKEND_MODEL
    proxy_bytes = json.dumps(proxy_body).encode("utf-8")
    client = await _get_client()
    # Council fan-out on the NON-streaming path too (
    # "every prompt/query/request"): kick the secondaries CONCURRENTLY with
    # the primary call so a stream:false request (external OpenAI clients)
    # gets the SAME multi-agent council as the streamed OWUI path instead of
    # Hermes-only. Their answers merge into the polish input below. Best-
    # effort; CPU twins offload to :11435, dead endpoints drop to ''.
    # P2.1 role-lens (mirrors streaming path): each secondary gets a small
    # secondary-specific system message identifying its angle so the council
    # answers from N DIVERSE lenses, not duplicates one answer N times.
    # Pre-await the COMPLETE surface (verbs+recipes+skills) ONCE here -- the
    # skill projection needs an async DB read but _sec_body is sync; the local
    # is reused for every secondary.
    # Full surface awaited ONCE (priority-sorted); per-agent a weak lane gets a
    # CAPPED slice ("nothing toolless"), fast lanes the full.
    _sec_wtools = (await _worker_tools_surface_async()
                   if WORKER_TOOLS_ENABLE else [])
    _sec_allow_write = _hints_write_action(refined)

    def _sec_body(_n, _c):
        _b = dict(proxy_body)
        _lens = _council_role_lens(_n, _c)
        if _lens:
            _b["messages"] = ([{"role": "system", "content": _lens}]
                              + list(proxy_body.get("messages") or []))
        # Hand each council secondary the SAME global verb+recipe+skill surface
        # the DAG workers get so the fan-out agents CALL
        # tools (web_search/etc.) via the secondary tool-loop instead of
        # fabricating/disclaiming. Writes gated on the refined intent (mirrors
        # the primary path) -- a read-only turn keeps secondaries read-only,
        # avoiding parallel write storms.
        # Every secondary gets tools; a weak lane (iGPU/mobile) gets a CAPPED
        # slice it can grammar-constrain in budget, never
        # zero. _sec_wtools is priority-sorted, so the slice keeps read/web first.
        if _sec_wtools:
            _cap = _lane_tool_cap(_agent_lane(_c))
            _b["tools"] = _sec_wtools[:_cap] if _cap > 0 else _sec_wtools
            _b["num_ctx"] = WORKER_TOOL_CTX
            _b["_allow_write"] = _sec_allow_write
        _tc_val = _b.get("tool_choice")
        if _tc_val and _tc_val not in ("none", "auto") and not _endpoint_supports_tool_choice(
                str(_c.get("endpoint") or ""), _c, _agent_offload_engine(_c)):
            # llama.cpp REJECTS tool_choice='required' but ACCEPTS 'auto' and then
            # emits real OpenAI tool_calls (proven: gemma4/qwen3 on mios-llm-light).
            # Downgrade to 'auto' rather than DROPPING it -- dropping it made the
            # model NARRATE the call as text ("<|tool_call>...") instead of
            # executing it, so verbs never fired (stress test).
            _b["tool_choice"] = "auto"
        return _b

    _sec_tasks = [
        asyncio.create_task(
            _call_agent_complete(_n, _c, _sec_body(_n, _c), headers, client,
                                 priority=_turn_priority))
        for _n, _c in _fanout
    ]
    conv_gw_mode = os.environ.get("MIOS_CONV_GATEWAY_MODE", "http")
    is_queue_mode = (conv_gw_mode == "queue" and str(target_endpoint).rstrip("/") == str(BACKEND).rstrip("/"))

    try:
        if is_queue_mode:
            try:
                import mios_dispatcher
                res = await mios_dispatcher.dispatch_via_queue(proxy_body, GATEWAY_QUEUE)
                from mios_dispatcher import MockResponse
                r = MockResponse(res)
            except Exception as e:
                log.warning("queue dispatch failed, falling back to HTTP: %s", e)
                import mios_dispatcher
                r = await mios_dispatcher.dispatch_via_http(proxy_body, target_endpoint, headers=headers)
        else:
            import mios_dispatcher
            r = await mios_dispatcher.dispatch_via_http(proxy_body, target_endpoint, headers=headers)
        try:
            backend_json = r.json()
        except (json.JSONDecodeError, ValueError):
            for _t in _sec_tasks:
                _t.cancel()
            return JSONResponse(
                content={
                    "error": {
                        "message": "backend returned non-JSON response",
                        "type": "backend_non_json",
                        "backend_status": r.status_code,
                        "backend_preview": (r.text or "")[:500],
                    }
                },
                status_code=502,
            )
        # Drain + collect the concurrent council secondaries; merged into
        # the polish input below so the final answer SYNTHESISES all agents
        # (the non-streaming twin of the streamed 🤝 merge).
        _merge: list = []
        if _sec_tasks:
            for _res in await asyncio.gather(*_sec_tasks,
                                             return_exceptions=True):
                if (isinstance(_res, tuple) and _res[1]
                        and str(_res[1]).strip()):
                    _merge.append(f"[{_res[0]} agent]:\n{str(_res[1]).strip()}")
                    _scratchpad_note(_res[0], str(_res[1]), phase="council")
        # Polish the assistant content when refine produced an
        # intended_outcome. Skip on streaming, on empty responses,
        # and on backend errors. The raw sub-agent output is
        # preserved as a collapsed <details type="reasoning">
        # block ABOVE the polished answer -- operator directive
        # "all sub-agents tasked by MiOS-Agent have
        # their printing and patterns/responses they end up
        # printing to the user -- is all written to the OWUI
        # thinking blocks/OWUI dropdown for thoughts".
        log.info(
            "polish-gate: enabled=%s refined=%s status=%s json=%s",
            POLISH_ENABLED, bool(refined), r.status_code,
            isinstance(backend_json, dict),
        )
        if (POLISH_ENABLED and refined and r.status_code == 200
                and isinstance(backend_json, dict)):
            choices = backend_json.get("choices") or []
            if choices:
                msg = choices[0].get("message") or {}
                raw = str(msg.get("content") or "")
                log.info("polish-gate: raw_len=%d refined_outcome=%s",
                         len(raw),
                         (refined.get("intended_outcome") or "")[:60])
                # CONFIRMATION ENGINE -- same gate
                # as the streaming branch above. Capture the verbs the
                # sub-agent invoked (final-message tool_calls), run the
                # Definition-of-Done check FIRST, and SKIP the critic
                # re-pass on a confirmed-satisfied turn so a succeeded
                # verb isn't re-litigated into a false failure.
                _tools_called = [
                    (tc.get("function") or {}).get("name")
                    for tc in (msg.get("tool_calls") or [])
                    if (tc.get("function") or {}).get("name")
                ]
                _verdict = await _inline_satisfaction_check(
                    session_id, refined,
                    agent_tools_called=_tools_called,
                    agent_answered=bool(raw.strip()))
                _confirmed = bool(
                    _verdict
                    and _verdict.get("kind") == "user_query_satisfied")
                if not _confirmed:
                    raw = await _critic_refine_agent(
                        raw, last_user_text, refined, session_id,
                        client=client, target_endpoint=target_endpoint,
                        headers=headers, base_body=proxy_body)
                raw_for_polish = (
                    (raw + "\n\n" + "\n\n".join(_merge)).strip()
                    if _merge else raw)
                if raw_for_polish.strip():
                    polished = await polish_response(
                        raw_for_polish, refined, session_id=session_id,
                        original_user_text=last_user_text,
                        persona_system=_persona_system,
                        agent_tools=_tools_called)
                    # qwen3 reasoning models occasionally leak
                    # <think>...</think> blocks past /no_think; strip
                    # them from BOTH the dropdown content and the
                    # polished main content so neither carries the
                    # internal CoT through to the operator.
                    # Sub-agent FULL raw work (responses + prints +
                    # reasoning) -> collapsed dropdown; polished clean
                    # answer -> main. Mirrors the streaming branch +
                    # operator binding: all sub-agent output goes to the
                    # thinking dropdown. Tag MARKERS unwrapped so the
                    # reasoning is readable, not bleeding inline.
                    dropdown_content = _THINK_ORPHAN_RE.sub("", raw).strip()
                    answer_only = _strip_think_tags(raw)
                    polished_clean = (
                        _strip_think_tags(polished) if polished else ""
                    )
                    main = polished_clean.strip() or answer_only.strip()
                    # Multi-task: prepend the queue preamble so the
                    # operator sees "started X; queued Y, Z" before
                    # the polished answer for task #1.
                    preamble = ""
                    if (isinstance(refined, dict)
                            and refined.get("_multi_task_queue")):
                        preamble = _multi_task_preamble(
                            refined["_multi_task_queue"],
                            int(refined.get(
                                "_multi_task_active_idx", 0)),
                        )
                    # Show the dropdown whenever the sub-agent's work is
                    # more than the bare answer; else just the clean main.
                    # agent-pipe emits ONLY the clean polished answer; the
                    # OWUI pipe owns the live thinking dropdown (streamed
                    # from the hermes-tail). No post-hoc wrap (it caused
                    # the "answered twice" duplication)..
                    wrapped = f"{preamble}{main}"
                    polish_ok = bool(polished_clean.strip())
                    # Attach the REAL sources collected this turn :
                    # every council/DAG web_search recorded its result URLs in the
                    # turn-scoped collector. ALSO harvest the answer's OWN inline URLs so
                    # the metadata matches what the answer actually cites, prefer real
                    # article URLs, then append a deterministic Sources list + structured
                    # mios_sources metadata -- grounded in REAL results, never invented.
                    try:
                        _src_record_from_text(wrapped)
                    except Exception:  # noqa: BLE001
                        pass
                    _refs = _src_collected()
                    # OpenAI grounding: keep ONLY sources that support the answer
                    # (drop the off-topic bleed) before citing. web-tools hardening
                    #.
                    _refs = _filter_relevant_sources(_refs, wrapped, last_user_text)
                    if _refs and "**Sources:**" not in wrapped:
                        wrapped = wrapped.rstrip() + _sources_markdown(_refs)
                    if _refs:
                        backend_json["mios_sources"] = _sources_metadata(_refs)
                        # OpenAI url_citation annotations -- the canonical citation
                        # contract so clients render clickable web cites.
                        msg["annotations"] = _sources_annotations(_refs, wrapped)
                    msg["content"] = wrapped
                    choices[0]["message"] = msg
                    backend_json["choices"] = choices
                    _db_fire(_db_post(_db_create("event", {
                        "source": "mios-agent-pipe",
                        "kind": "polish",
                        "severity": "info" if polish_ok else "warn",
                        "summary": f"{target_name} "
                                   f"{'polished' if polish_ok else 'wrapped (polish no-op)'}",
                        "payload": {
                            "target_agent": target_name,
                            "raw_len": len(raw),
                            "polished_len": len(polished_clean),
                            "polish_ok": polish_ok,
                        },
                    }, now_fields=("ts",))))
        # W0-T3: prompt in-flight release for this (non-streaming) autonomous turn
        # now that it has completed; TTL is the backstop for paths without a clean
        # terminal point. No-op for foreground / non-autonomous turns.
        await _budget_release_inflight(_budget_turn_token)
        return JSONResponse(content=backend_json, status_code=r.status_code)
    except httpx.HTTPError as e:
        log.warning("chat/completions backend proxy failed: %s", e)
        await _budget_release_inflight(_budget_turn_token)
        return JSONResponse(
            content={"error": {"message": str(e), "type": "backend_error"}},
            status_code=502,
        )


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
    _routed_domain_var = ctx.get("_routed_domain_var")
    
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

    _swarm_nodes = await _plan_swarm(last_user_text, messages)
    if not _swarm_nodes:
        log.info("multi_task decomposition yielded 0 nodes -> falling back to full council")
        _force_council = True
        decision.mode = "agent"
        ctx["_force_council"] = True
        return await _KERNEL.dispatcher.run(decision, **ctx)

    if not SWARM_TRUST_ATOMIC and len(_swarm_nodes) == 1:
        log.info("multi_task yielded 1 node (trust_atomic=false) -> running as normal agent turn")
        refined["intent"] = "agent"
        refined["deep"] = True
        decision.mode = "agent"
        return await _KERNEL.dispatcher.run(decision, **ctx)

    _dag = _agent_dag_from_tasks(_swarm_nodes, last_user_text)
    return await _respond_agent_dag(
        _dag, refined,
        streaming=streaming, chat_id=chat_id, model=model,
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
    _routed_domain_var = ctx.get("_routed_domain_var")
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
