# AI-hint: NATIVE single-agent tool-loop responders extracted VERBATIM from server.py
#   (strangler-fig refactor). _respond_native_loop_direct is the mios-heavy + full MiOS
#   tool-surface agentic loop -- deterministic remember/identity fast-paths, capability +
#   env + recency + computation + route-by-source system grounding, concurrent
#   memory/knowledge/RAG recall, the stable-prefix tool surface + dispatch_to_nodes
#   fan-out tool, the LIVE-emit streaming pump, the web/compute/local-state/file-search
#   PREFETCH grounding, the secondary tool-loop, heavy->light bullet-proof failover,
#   think-tag empty-recovery, polish, the relay ladder, the anti-fabricated-citation
#   guard, and deterministic **Sources:** capture -- every comment/heuristic/guard moved
#   byte-identically. _respond_local_state is the deterministic local-READ fast-path with
#   its own live-emit pump + native-loop recovery. Sibling helpers (mios_sse, mios_verity
#   polish, mios_secondary_loop, mios_jsonsalvage) are imported directly; every
#   server-side dep is dependency-INJECTED via configure() (one-way boundary -- this
#   module NEVER imports server). server.py re-imports both names under their original
#   aliases so the importable surface is byte-identical.
# AI-related: ./server.py, ./mios_config.py, ./mios_turn.py, ./mios_sse.py, ./mios_verity.py, ./mios_secondary_loop.py, ./mios_jsonsalvage.py, ./test_mios_native_loop.py
# AI-functions: _respond_native_loop_direct, _respond_local_state, _formulate_compute_snippet, _formulate_web_query, _format_local_state, configure
"""NATIVE single-agent tool-loop responders (strangler-fig refactor).

Extracted VERBATIM from ``server.py``. ``_respond_native_loop_direct`` runs the
mios-heavy + full-tool-surface agentic loop (prefetch grounding -> secondary tool
loop -> failover -> polish -> relay ladder -> sources); ``_respond_local_state`` is
the deterministic local-READ fast-path. Both keep every heuristic/guard/comment
byte-identical. Sibling leaf helpers are imported directly; every server-side symbol
is injected via :func:`configure` (one-way boundary -- this module never imports
``server``). ``server.py`` re-imports both responders under their original aliases so
the importable surface stays byte-identical.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
import logging
from typing import Any, AsyncGenerator, Optional

import httpx
from fastapi.responses import JSONResponse, StreamingResponse

from mios_jsonsalvage import loads_lenient as _loads_lenient
from mios_secondary_loop import _v1_secondary_tool_loop
from mios_verity import polish_response
from mios_sse import (
    _sse_chunk, _sse_done, _sse_reasoning, _sse_status, _sse_status_phase,
    _stream_answer,
)
# SSOT model/endpoint scalars the moved web/compute formulators + local-state
# responder read are imported DIRECTLY from mios_config (the SSOT) rather than
# injected -- they are never reassigned in server.py, so import == inject-by-value
# with no DI seam growth (one-way boundary: mios_config never imports this module).
from mios_config import (
    PLANNER_ENDPOINT, PLANNER_TIMEOUT_S, POLISH_ENDPOINT, POLISH_MAX_TOKENS,
    POLISH_MODEL, POLISH_TIMEOUT_S, ROUTER_MODEL,
)
# The shared think-tag stripper lives in mios_turn (its SSOT home); imported here
# directly for _format_local_state's final clean-up (no cycle -- mios_turn imports
# no siblings).
from mios_turn import _strip_think_tags
# The web-enrich verb SET (which role:"tool" outputs count as fetched ground
# truth) lives in toolexec's SSOT; referenced through the module so a runtime
# reconfigure() is reflected (no duplicated literal set -- Law 7).
from mios_pipe.routing import toolexec as _toolexec

log = logging.getLogger("mios-agent-pipe")


# ── Anti-fabrication guards (FAB-01 fabricated execution / FAB-02 fabricated
# grounding). Extracted to module scope so each stage is unit-testable WITHOUT
# standing up the pipe. The SSOT flag + thresholds are bridged from mios.toml
# [verity] via MIOS_ANTIFAB_* (userenv.sh -> system-sync-env.sh -> install.env);
# env is the live source and the get() fallbacks are the degrade-OPEN defaults
# used only before the bridge runs (they mirror the SSOT defaults). Same idiom as
# the chat-sibling flag. -------------------------------------------------------
_ANTIFAB_ENABLE = os.environ.get(
    "MIOS_ANTIFAB_ENABLE", "true").strip().lower() not in {"false", "0", "no", "off"}


def _antifab_min_entities() -> int:
    """Minimum candidate entities a section must carry before its grounding is
    judged; below this the signal is too thin to trust -> degrade-open. SSOT:
    [verity].antifab_min_entities -> MIOS_ANTIFAB_MIN_ENTITIES (live)."""
    try:
        return int(os.environ.get("MIOS_ANTIFAB_MIN_ENTITIES", "").strip() or 3)
    except ValueError:  # malformed override -> fall back to the degrade-open default
        return 3


def _antifab_ground_min() -> float:
    """Minimum grounded fraction a judged section must clear to survive; below it
    the section's named entities are mostly absent from every fetched source ->
    fabricated. SSOT: [verity].antifab_ground_min -> MIOS_ANTIFAB_GROUND_MIN."""
    try:
        return float(os.environ.get("MIOS_ANTIFAB_GROUND_MIN", "").strip() or 0.34)
    except ValueError:
        return 0.34


# Executor-evidence shapes. The '🤝 <verb> output:' sentinel is emitted ONLY into
# the reasoning stream by the tool executor -- it is never concatenated into a
# model-synthesized answer -- and the {"success":true,...,"tool":"..."} form is a
# tool-run success claim. A synthesized answer that WRITES either is reprinting an
# execution it did not produce (FAB-01). The 🤝 glyph appears ONLY on the
# executor's evidence line, so matching any 🤝-line that mentions 'output' (the
# real 'output:' AND a mimicked-but-varied 'output (truncated for brevity):') and
# consuming its block to the next blank line is safe and total in synthesized prose.
_RE_EVIDENCE_SENTINEL = re.compile(r'🤝[^\n]*output.*?(?=\n\n|\Z)', re.DOTALL)
_RE_SUCCESS_JSON = re.compile(
    r'\{[^{}]*"success"\s*:\s*true[^{}]*"tool"\s*:\s*"[^"]+"[^{}]*\}', re.DOTALL)


def _strip_synth_evidence(ans: str) -> str:
    """FAB-01 (synthesized answer): strip EVERY executor-evidence block. Verb
    membership is irrelevant -- a synthesized answer is prose, so any sentinel or
    success-JSON block is model-authored (e.g. a duplicate invented 'apps' block
    for an already-fired verb). Lossless for real answers: the sentinel never
    legitimately reaches synthesized prose."""
    _san = _RE_EVIDENCE_SENTINEL.sub("", ans)
    _san = _RE_SUCCESS_JSON.sub("", _san)
    return _san


def _real_tool_output(m2) -> dict:
    """verb-name -> REAL captured output, from the secondary loop's role:"tool"
    messages (the in-scope ground truth for what each verb actually returned)."""
    return {str(_mm.get("name")): str(_mm.get("content") or "")
            for _mm in (m2 or [])
            if isinstance(_mm, dict) and _mm.get("role") == "tool"}


def _keep_matching_success_json(ans: str, real_out: dict) -> str:
    """FAB-01 (raw-evidence path): the answer IS surfaced executor evidence, so a
    success-JSON block is legitimate ONLY if it byte-matches the real captured
    output for its verb in `real_out`; a non-matching one is fabricated -> drop.
    The sentinel form never appears on this path."""
    def _keep(_m):
        _blk = _m.group(0)
        _mv = re.search(r'"tool"\s*:\s*"([^"]+)"', _blk)
        _vn = _mv.group(1) if _mv else ""
        return _blk if (_vn and _blk.strip() in str(real_out.get(_vn) or "")) else ""
    return _RE_SUCCESS_JSON.sub(_keep, ans)


def _guard_fabricated_execution(ans, *, surfaced_raw_evidence, m2, enable):
    """FAB-01 guard body (extracted). SYNTHESIZED answer -> strip all evidence
    blocks; RAW-evidence answer -> keep only success-JSON matching real tool
    output. Degrade-OPEN: disabled / empty / error -> return `ans` byte-identical."""
    if not (ans and enable):
        return ans
    try:
        if not surfaced_raw_evidence:
            _san = _strip_synth_evidence(ans)
            if _san != ans:
                log.warning("native-loop: stripped executor-evidence block(s) from "
                            "synthesized answer (anti-fab)")
                return _san.strip()
            return ans
        _san = _keep_matching_success_json(ans, _real_tool_output(m2))
        if _san != ans:
            log.warning("native-loop: dropped success-JSON block not matching "
                        "captured tool output (anti-fab)")
            return _san.strip()
        return ans
    except Exception:  # noqa: BLE001 -- degrade-open
        return ans


def _norm(s: str) -> str:
    """Casefold + reduce to word chars for a language-neutral substring test."""
    return re.sub(r"\W+", " ", str(s or ""), flags=re.UNICODE).casefold()


def _entity_tokens(text: str) -> set:
    """Structural, UNICODE-aware candidate entities (Law 7: NO English word list).
    Bare registrable domains/hosts, digit-bearing tokens (years / versions /
    counts), and proper-noun-shaped word tokens (unicode upper-initial or all-caps).
    A caseless script (e.g. CJK) yields few/none -> callers see too-few entities
    and degrade-open rather than strip."""
    text = str(text or "")
    ents = set()
    for _m in re.findall(r"\b[\w-]+(?:\.[\w-]+)+\b", text):          # domains / hosts
        if re.search(r"\.[^\W\d_]{2,}$", _m, re.UNICODE):
            ents.add(_m)
    for _m in re.findall(r"\b\w*\d[\w.]*\b", text):                   # digit-bearing
        ents.add(_m)
    for _w in re.findall(r"[^\W\d_][\w'’-]*", text, re.UNICODE):      # word tokens
        if _w[:1].isupper() or _w.isupper():                         # proper-noun-ish
            ents.add(_w)
    return ents


def _ground_sections(ans, corpus, min_entities, ground_min):
    """FAB-02 per-SECTION grounding. Split the answer structurally (blank lines +
    markdown heading boundaries) and drop ONLY a section that carries at least
    `min_entities` candidate entities AND whose grounded fraction (entities whose
    normalized form is a substring of the normalized fetched `corpus`) is below
    `ground_min`. A section with too few entities is always kept (degrade-open,
    covers caseless scripts). Returns (kept_text, stripped_any)."""
    _nc = _norm(corpus)
    if not _nc.strip():
        return ans, False                       # no ground truth -> cannot verify
    _sections = re.split(r"(?m)\n\s*\n|^(?=[ \t]*#{1,6}\s)", ans)
    _kept, _stripped = [], False
    for _sec in _sections:
        if not _sec or not _sec.strip():
            continue
        _ents = _entity_tokens(_sec)
        if len(_ents) < min_entities:
            _kept.append(_sec.strip())          # too little signal -> keep
            continue
        _grounded = 0
        for _e in _ents:
            _ne = _norm(_e).strip()
            if _ne and _ne in _nc:
                _grounded += 1
        if (_grounded / len(_ents)) < ground_min:
            _stripped = True                    # mostly-ungrounded -> fabricated
            continue
        _kept.append(_sec.strip())
    if not _stripped:
        return ans, False
    return "\n\n".join(_kept).strip(), True


def _guard_entity_grounding(ans, corpus, *, gate, enable, min_entities, ground_min,
                            note):
    """FAB-02 guard body (extracted). Degrade-OPEN: disabled / ungated / empty
    corpus / nothing stripped / error -> return `ans` unchanged. When it strips a
    fabricated section it keeps the grounded sections and appends `note` (a
    user-facing honest line -- output prose, NOT a decision gate)."""
    if not (ans and enable and gate):
        return ans
    try:
        _out, _stripped = _ground_sections(ans, corpus, min_entities, ground_min)
        if _stripped and _out.strip():
            log.warning("native-loop: stripped ungrounded section(s) from web/news "
                        "answer (anti-fab per-section grounding)")
            return _out.rstrip() + "\n\n" + note
        return ans
    except Exception:  # noqa: BLE001 -- degrade-open
        return ans


# -- Dependency-injection seam ----------------------------------------
# These responders read server.py's config scalars + routing table, the live
# verb catalog, three request-scoped ContextVars, and call back into a large set
# of server-side helpers (grounding, recall, prefetch, source, store, usage, the
# worker-tools surface + its rebindable core-cache). server.py calls configure()
# with those AFTER every one is defined (one-way boundary: this module never
# imports server). The placeholders below let a standalone import succeed; every
# consumer is async/runtime so nothing fires before configure() runs. NOTE: the
# worker-tools CORE cache is REBOUND by server at request time, so it is injected as
# a live getter (``_worker_tools_core_cache()``) rather than by value.

dispatch_mios_verb = None
_usage_estimate = None
_identity_answer = None
_agent_contract = None
_capability_grounding = None
_env_grounding = None
_recall_agent_memory = None
_recall_knowledge = None
_rag_enrich = None
_tool_pref_block = None
_current_date_str = None
_worker_tools_surface_async = None
_read_tool_enrich = None
_needs_compute = None
_src_record = None
_src_collected = None
_src_record_from_text = None
_endpoint_supports_parallel_tools = None
_filter_relevant_sources = None
_sources_markdown = None
_sources_annotations = None
_sources_metadata = None
_store_knowledge = None
_iter_answer_chunks = None
_write_skill_md_fire = None
# Server-owned prompt const + the polish (url, payload) builder shared with
# mios_verity (verity imports it via configure too) -- both INJECTED (one-way
# boundary): _LOCAL_STATE_SYSTEM is a server string, _polish_post stays in
# server.py because moving it would cycle (this module imports mios_verity, which
# also consumes _polish_post).
_LOCAL_STATE_SYSTEM = ""
_polish_post = None
_VERB_CATALOG = None
_routed_domain_var = None
_orch_ctx_var = None
_recency_ctx_var = None
_worker_tools_core_cache = None

BACKEND = ""
BACKEND_MODEL = ""
_BACKEND_KEY = None
_BACKEND_HOSTPORT = ""
REFINE_ENDPOINT = ""
REFINE_MODEL = ""
STABLE_PREFIX = False
STABLE_PREFIX_HINT = False
STABLE_PREFIX_TAIL = 0
NATIVE_LOOP_TOOL_CAP = 0
NATIVE_LOOP_TIMEOUT_S = 300.0
NATIVE_LOOP_CAPABILITY_GROUNDING = True
NATIVE_LOOP_PERSISTENCE = False
_NATIVE_LOOP_PERSISTENCE_PROSE = ""
NATIVE_LOOP_BREADTH_GUIDANCE = False
_NATIVE_LOOP_BREADTH_PROSE = ""
NATIVE_LOOP_REFLECTION = False
_NATIVE_LOOP_REFLECTION_PROSE = ""
NATIVE_LOOP_RECENCY_RANGE = "day"
NATIVE_LOOP_RECENCY_FANOUT = 5
NATIVE_LOOP_RECENCY_DEFAULTS = True
NATIVE_LOOP_MATH_HINT = True
NATIVE_LOOP_DATE_ANCHOR = True
NATIVE_LOOP_QUERY_REFORMULATE = True
NATIVE_LOOP_STREAM_TOKENS = True
NATIVE_LOOP_STREAM_CHUNK = 0
NATIVE_LOOP_STREAM_DELAY_MS = 0
_ROUTING_DOMAINS = {}
_DEBUG_ENABLE = False


_INJECTED = frozenset((
    "_DEBUG_ENABLE",
    "dispatch_mios_verb", "_usage_estimate", "_identity_answer", "_agent_contract",
    "_capability_grounding", "_env_grounding", "_recall_agent_memory", "_recall_knowledge",
    "_rag_enrich", "_tool_pref_block", "_current_date_str", "_worker_tools_surface_async",
    "_read_tool_enrich", "_needs_compute",
    "_src_record", "_src_collected", "_src_record_from_text",
    "_endpoint_supports_parallel_tools", "_filter_relevant_sources", "_sources_markdown",
    "_sources_annotations", "_sources_metadata", "_store_knowledge", "_iter_answer_chunks",
    "_write_skill_md_fire", "_LOCAL_STATE_SYSTEM", "_polish_post",
    "_VERB_CATALOG", "_routed_domain_var",
    "_orch_ctx_var", "_recency_ctx_var", "_worker_tools_core_cache", "BACKEND",
    "BACKEND_MODEL", "_BACKEND_KEY", "_BACKEND_HOSTPORT", "REFINE_ENDPOINT",
    "REFINE_MODEL", "STABLE_PREFIX", "STABLE_PREFIX_HINT", "STABLE_PREFIX_TAIL",
    "NATIVE_LOOP_TOOL_CAP", "NATIVE_LOOP_TIMEOUT_S", "NATIVE_LOOP_CAPABILITY_GROUNDING",
    "NATIVE_LOOP_PERSISTENCE", "_NATIVE_LOOP_PERSISTENCE_PROSE",
    "NATIVE_LOOP_BREADTH_GUIDANCE", "_NATIVE_LOOP_BREADTH_PROSE", "NATIVE_LOOP_REFLECTION",
    "_NATIVE_LOOP_REFLECTION_PROSE", "NATIVE_LOOP_RECENCY_RANGE",
    "NATIVE_LOOP_RECENCY_FANOUT", "NATIVE_LOOP_RECENCY_DEFAULTS", "NATIVE_LOOP_MATH_HINT",
    "NATIVE_LOOP_DATE_ANCHOR", "NATIVE_LOOP_QUERY_REFORMULATE",
    "NATIVE_LOOP_STREAM_TOKENS", "NATIVE_LOOP_STREAM_CHUNK", "NATIVE_LOOP_STREAM_DELAY_MS",
    "_ROUTING_DOMAINS",
))


def configure(**deps) -> None:
    """Inject server-side deps under their EXACT original names (one-way boundary).

    Called once from ``server.py`` after every injected symbol is defined. Each
    keyword equals the module global it sets; ``_worker_tools_core_cache`` is a live
    zero-arg getter for server's rebindable ``_WORKER_TOOLS_CORE_CACHE`` cache.
    """
    g = globals()
    for _k, _v in deps.items():
        if _k in _INJECTED:
            g[_k] = _v


async def _respond_native_loop_direct(
    refined: Optional[dict], *, streaming: bool, chat_id: str, model: str,
    session_id: Optional[str], last_user_text: str, persona_system: str,
    messages: list, request=None, emit=None, tool_choice=None,
    force_delegate=None, target_agents=None, **kwargs
) -> Any:
    """Native agentic tool-loop: mios-heavy + the full MiOS tool surface, one
    standard call->tool_calls->execute->repeat loop, then polish. The model routes
    itself via tool choice -- no bespoke classify/route/decompose layers."""
    # Deterministic memory-SAVE : an 8B mis-handles "remember X"
    # -- it called save_document / tried to RUN the named app instead of saving the
    # fact. The save-a-fact pattern is unambiguous, so fire the `remember` verb
    # directly + confirm, bypassing the model's mis-interpretation. (Read-back stays
    # the model's job via `recall`.) The one routing exception the native loop keeps,
    # because the model demonstrably cannot be trusted with this exact phrasing.
    _rmemo = re.match(
        r"\s*(?:please\s+)?(?:remember|note|keep in mind|don'?t forget)"
        r"(?:\s+that)?\s+(.+)", last_user_text or "", re.IGNORECASE)
    if _rmemo and len(_rmemo.group(1).strip()) > 2 and "remember" in (_VERB_CATALOG or {}):
        _fact = re.split(r",?\s*\b(?:then|and then)\b", _rmemo.group(1),
                         maxsplit=1)[0].strip().rstrip(".")
        _ok = False
        try:
            _rr = await dispatch_mios_verb("remember", {"fact": _fact},
                                           session_id=session_id)
            _ok = isinstance(_rr, dict) and _rr.get("success")
        except Exception:  # noqa: BLE001
            _ok = False
        _memans = (f"Got it -- I'll remember that {_fact}." if _ok
                   else f"I tried to save \"{_fact[:80]}\" to memory but it didn't confirm.")
        log.info("native-loop: deterministic remember (ok=%s)", _ok)
        if streaming:
            async def _stream_memo() -> AsyncGenerator[bytes, None]:
                yield _sse_chunk("", chat_id=chat_id, model=model, role="assistant")
                yield _sse_chunk(_memans, chat_id=chat_id, model=model)
                yield _sse_chunk("", chat_id=chat_id, model=model, finish_reason="stop")
                yield _sse_done()
            return StreamingResponse(_stream_memo(), media_type="text/event-stream")
        return JSONResponse(content={
            "id": chat_id, "object": "chat.completion", "created": int(time.time()),
            "model": model,
            "choices": [{"index": 0,
                         "message": {"role": "assistant", "content": _memans},
                         "finish_reason": "stop"}],
            "usage": _usage_estimate(last_user_text, _memans)})
    # Deterministic IDENTITY/CAPABILITY answer : "who are you
    # / what can you do" made the 14B confabulate ("Zabbix agent", "Mio's Pizza")
    # and vary run-to-run. Like the remember handler above, answer this narrow,
    # unambiguous class deterministically from the LIVE catalog so the reply is
    # accurate, consistent, and correct even on a Day-0 (no-history) image. Tight
    # gate (anchored phrasing + short message) so it never hijacks a real task.
    _idq = re.match(
        r"\s*(?:hey|hi|hello|yo|ok|okay|so)?[,\s]*"
        r"(?:can you\s+|could you\s+|please\s+)?"
        r"(?:who\s+(?:are|r)\s+(?:you|u)|what\s+(?:are|r)\s+(?:you|u)|"
        r"what\s+can\s+(?:you|u)\s+do|what\s+do\s+(?:you|u)\s+do|"
        r"introduce\s+yourself|tell\s+me\s+about\s+yourself|"
        r"what\s+are\s+your\s+(?:capabilities|abilities|features|functions)|"
        r"what(?:'s| is)\s+your\s+(?:purpose|function|job|role))\b",
        last_user_text or "", re.IGNORECASE)
    if NATIVE_LOOP_CAPABILITY_GROUNDING and _idq and len(last_user_text or "") <= 80:
        _idans = _identity_answer()
        if _idans:
            log.info("native-loop: deterministic identity answer")
            if streaming:
                async def _stream_id() -> AsyncGenerator[bytes, None]:
                    yield _sse_chunk("", chat_id=chat_id, model=model, role="assistant")
                    yield _sse_chunk(_idans, chat_id=chat_id, model=model)
                    yield _sse_chunk("", chat_id=chat_id, model=model, finish_reason="stop")
                    yield _sse_done()
                return StreamingResponse(_stream_id(), media_type="text/event-stream")
            return JSONResponse(content={
                "id": chat_id, "object": "chat.completion", "created": int(time.time()),
                "model": model,
                "choices": [{"index": 0,
                             "message": {"role": "assistant", "content": _idans},
                             "finish_reason": "stop"}],
                "usage": _usage_estimate(last_user_text, _idans)})
    _sys = "\n\n".join(p for p in (
        _agent_contract(),
        (_capability_grounding(_VERB_CATALOG) if NATIVE_LOOP_CAPABILITY_GROUNDING else ""),
        _env_grounding(), persona_system) if p and p.strip())
    if NATIVE_LOOP_PERSISTENCE:
        _sys += "\n\n" + _NATIVE_LOOP_PERSISTENCE_PROSE
    if NATIVE_LOOP_BREADTH_GUIDANCE:
        _sys += "\n\n" + _NATIVE_LOOP_BREADTH_PROSE
    if NATIVE_LOOP_REFLECTION:
        _sys += "\n\n" + _NATIVE_LOOP_REFLECTION_PROSE
    # Recency steering from refine's MODEL-classified time-sensitivity :
    # refine sets `news` true for current-events/trending/latest asks (model-classified, NOT
    # a keyword list). The data showed the model produces a real DATED report when it sets
    # web_search time_range='day' and a thin hedge when it doesn't -- so when refine flags the
    # turn time-sensitive, inject a SPECIFIC strong instruction to pull the recency lever.
    # Degrade-open: no flag -> no line (a timeless query is never forced to filter by date).
    if refined and refined.get("news"):
        _sys += ("\n\nRECENCY (this request is time-sensitive): set web_search's "
                 "time_range to '" + (NATIVE_LOOP_RECENCY_RANGE or "day")
                 + "' (broaden to 'week' if a day is too sparse) and category='news' "
                 "for breaking headlines, so results are current dated stories, not "
                 "evergreen pages. For a multi-facet 'what's trending' ask, set "
                 "web_search's fanout parameter to " + str(NATIVE_LOOP_RECENCY_FANOUT)
                 + " or more: one call then expands into that many facet sub-queries "
                 "and RRF-merges them, returning a rich multi-topic set from a single "
                 "call. Then ORGANIZE the results into clearly-labelled sections, ONE "
                 "per distinct trend present in the results, and report them as a "
                 "factual dated digest. Report every distinct trend you actually "
                 "found -- if you gathered five, present five. If a facet returned no "
                 "results, say so plainly; do not pad, and do not invent items to look "
                 "fuller. Do not ask the user to narrow what you can research "
                 "yourself.")
    # COMPUTATION steer ("MATH(AND OTHER PYTHON CAPABILITIES)"):
    # route any non-trivial calculation to the sandboxed Python executor rather than
    # letting the 8B compute in-head (unreliable). Unconditional capability guidance --
    # the MODEL decides when a step is non-trivial -- gated only by the SSOT flag + the
    # structural presence of the verb in _VERB_CATALOG; NO "if math in q" branch.
    if NATIVE_LOOP_MATH_HINT and ("coderun" in _VERB_CATALOG
                                  or "code_mode" in _VERB_CATALOG):
        # Frame the model's OWN limitation + the CAPABILITY (research-backed: naming the
        # weakness raises correct tool use), NOT a hardcoded verb name -- the model maps
        # this to its always-present sandbox code/Python tool from natural-language
        # understanding ("natural language!!! not verbs/keywords").
        _sys += ("\n\nCOMPUTATION: you cannot reliably do arithmetic, numeric, "
                 "statistical, date/time, unit-conversion, or symbolic math in your head "
                 "-- it is error-prone. For ANY such calculation, run it with your "
                 "sandboxed code / Python execution tool and report the tool's result "
                 "instead of computing it yourself.")
    # Tool-selection hint : refine identifies the relevant
    # verb(s) for clear patterns ("remember X" -> remember; "what apps" -> mios_apps);
    # an 8B over the full surface sometimes mis-picks a semantic neighbour (pkg for
    # mios_apps, save_document for remember). Inject refine's hint_tools as a STRONG
    # preference so the model lands on the right verb -- a nudge, not a hardcoded route.
    _hint_tools = [str(h).strip() for h in ((refined or {}).get("hint_tools") or [])
                   if isinstance(h, str) and str(h).strip()]
    # ROUTE-BY-SOURCE local steer (operator "never web-search local machine state").
    # `web` is the ONLY external [routing.domains] domain; everything else (files,
    # system, apps_windows, packages, memory, computer_use, code_shell) targets THIS
    # machine. When the turn routed to a LOCAL domain, prefer that domain's OWN verbs
    # and tell the model NOT to web-search -- fixes a live miss where "find the
    # mios.toml file on this system" (domain=files) fired web_search instead of
    # find_file_fast. SSOT: verbs come straight from [routing.domains]; degrade-open
    # when no domain was routed (_rdom_nl None -> not treated as local).
    _rdom_nl = _routed_domain_var.get(None)
    _local_domain_nl = bool(_rdom_nl) and _rdom_nl != "web"
    _local_query_nl = bool(refined and refined.get("local_state")) or _local_domain_nl
    if _local_domain_nl and _ROUTING_DOMAINS:
        _dverbs = [str(v) for v in ((_ROUTING_DOMAINS.get(_rdom_nl) or {}).get("verbs") or [])
                   if str(v).strip()]
        _seen_h: set = set()
        _merged_h: list = []
        for _h in _dverbs + _hint_tools:  # domain verbs lead, refine's hints follow
            if _h not in _seen_h:
                _seen_h.add(_h)
                _merged_h.append(_h)
        _hint_tools = _merged_h
        _sys += ("\n\nSOURCE = THIS MACHINE (the request routed to the local '"
                 + _rdom_nl + "' domain). You do NOT know this machine's actual file "
                 "paths, file contents, or live state from memory -- any specific "
                 "path, filename, value, or result you state WITHOUT first calling a "
                 "local tool is a FABRICATION. You MUST call the appropriate local "
                 "tool below to get the real answer, and do NOT web_search this "
                 "machine's own files / state / apps.")
    if _hint_tools:
        _sys += ("\n\nTOOL PREFERENCE for THIS request: if a tool is needed, strongly "
                 "prefer these (refine selected them for this query): "
                 + ", ".join(_hint_tools[:6]) + ".")
    log.info("native-loop start: intent=%s news=%s web=%s hint_tools=%s",
             (refined or {}).get("intent"),
             bool(refined and refined.get("news")),
             bool(refined and refined.get("web")), _hint_tools[:6])
    # Context recall (P4 context-propagation): the native loop's
    # system prompt was contract+env only -- it lacked the agent-memory / knowledge /
    # RAG recall the swarm path injects, so "what is my favorite editor?" surfaced
    # nothing despite a saved fact. Inject all three concurrently (each self-gates on
    # relevance + degrades to "" on miss/error).
    _recall_text = ""
    try:
        _mem, _kn, _rag = await asyncio.gather(
            _recall_agent_memory(last_user_text),
            _recall_knowledge(last_user_text),
            _rag_enrich(last_user_text),
            return_exceptions=True)
        _recall_text = "\n\n".join(
            b for b in (_mem, _kn, _rag) if isinstance(b, str) and b.strip())
    except Exception:  # noqa: BLE001
        pass
    _user_msgs = [m for m in (messages or [])
                  if isinstance(m, dict) and m.get("role") != "system"]
    # P0 stable-prefix : the cosine 'prefer these tools' relevance
    # signal rides the user-adjacent TEXT (not the tools[] order) so tools[] stays
    # byte-stable for RadixAttention. "" when STABLE_PREFIX is off (legacy intent-orders
    # tools[] instead).
    _pref = (await _tool_pref_block(last_user_text)
             if (STABLE_PREFIX and STABLE_PREFIX_HINT) else "")
    # Carry the REFINED plan (operator binding: every hop runs on refine's clean ACTIONABLE
    # rewrite, never raw user text -- see project_mios_refined_query_carry). Feeding the model
    # the refined intent (not the verbose instruction) also stops it ECHOING the literal ask
    # and hedging "no '<verbatim instruction>' content available" (judge panel: the
    # hedge quotes the user's exact wording -> reframing to the actionable intent removes that
    # anchor). Degrade-open: empty when refine produced no distinct rewrite.
    _plan_bits = []
    _rt = str((refined or {}).get("refined_text") or "").strip()
    _io = str((refined or {}).get("intended_outcome") or "").strip()
    if _rt and _rt.lower() != (last_user_text or "").strip().lower():
        _plan_bits.append("Refined request: " + _rt)
    if _io:
        _plan_bits.append("Intended outcome: " + _io)
    _plan_block = ("PLAN for this turn -- work to THIS refined intent, treat it as fully "
                   "answerable, and do not anchor on the user's literal wording:\n"
                   + "\n".join(_plan_bits) + "\n\n") if _plan_bits else ""
    # CURRENT-DATE anchor, placed beside the PLAN block in the model's attention window
    # (the soft _env_grounding prose up in _sys is demonstrably overridden by an 8B on
    # strong-prior topics -> training-era 2024 dates). Grounds the orchestrator's OWN
    # context from the forwarded OWUI client env (server-clock fallback), NOT the user
    # message -- same sanctioned pattern as the PLAN/recall blocks. Gated; degrade-open.
    _date_block = ""
    if NATIVE_LOOP_DATE_ANCHOR:
        _date_block = ("CURRENT_DATE: " + _current_date_str() + ". This is the "
                       "authoritative date for resolving any relative time reference "
                       "('today', 'this week', 'recent', 'latest', 'current'). NEVER "
                       "resolve such references from training data or from dates found in "
                       "retrieved text; use THIS date, and do not state a year absent from "
                       "CURRENT_DATE or from the live search results.\n\n")
    # Position recalled context + the tool-preference hint IMMEDIATELY BEFORE the user's
    # question (not buried in the long system prompt) so the model reliably attends to them
    # instead of tool-hunting (recall was 2/3 with the memory in
    # _sys -- the model ignored it). Keeps the system+tools prefix byte-stable.
    if (_recall_text or _pref or _plan_block or _date_block) and _user_msgs:
        _last = _user_msgs[-1]
        _ctx = _date_block + _plan_block
        if _recall_text:
            _ctx += ("You ARE an assistant WITH persistent cross-session memory -- the "
                     "SAVED CONTEXT below IS your memory of this user. It is FALSE to say "
                     "you have no memory, no stored information, cannot remember, or lack "
                     "access -- NEVER say that. These are facts YOU recorded earlier; "
                     "ANSWER the question DIRECTLY AND CONFIDENTLY from them, and do NOT "
                     "call a tool to re-fetch what is already provided here:\n"
                     + _recall_text + "\n\n")
        if _pref:
            _ctx += _pref + "\n\n"
        _user_msgs = _user_msgs[:-1] + [{
            "role": _last.get("role", "user"),
            "content": _ctx + "---\nUser's question: " + str(_last.get("content") or "")}]
    _msgs = ([{"role": "system", "content": _sys}] if _sys else []) + _user_msgs
    # P0: under STABLE_PREFIX, request the full stable core + a short cosine tail (cap =
    # core size + tail budget) so the byte-stable core block is never truncated; legacy
    # = the intent-capped out[:cap].
    _eff_cap = (len(_worker_tools_core_cache() or []) + STABLE_PREFIX_TAIL
                if STABLE_PREFIX else NATIVE_LOOP_TOOL_CAP)
    _tools = await _worker_tools_surface_async(cap=_eff_cap, intent=last_user_text)
    # Fan-out-as-a-tool (federated swarm; agents-as-tools): the
    # orchestrator can dispatch INDEPENDENT sub-tasks across all hardware nodes when a
    # task is broad/parallelizable. The swarm fires behind this tool + returns ONE
    # synthesized result; the DESCRIPTION carries the decision criteria + width rules
    # so the model self-selects (Anthropic effort-scaling). Only the orchestrator gets
    # this tool -> the fanned workers can't recurse.
    _tools = list(_tools) + [{
        "type": "function",
        "function": {
            "name": "dispatch_to_nodes",
            "description": (
                "Fan out INDEPENDENT sub-tasks across all compute nodes "
                "(dGPU/iGPU/CPU/mobile/code/doc) as concurrent sub-agents, then get "
                "ONE synthesized result. Call ONLY when BOTH hold: (1) the request "
                "has 3+ distinct facets/sources/files researchable in parallel "
                "(compare several named items; survey several topics; check several "
                "files), and (2) no sub-task needs another's output. Do NOT call for: "
                "1-2 item asks, sequential/dependent steps (step 2 needs step 1), "
                "shared-state edits, or anything you can finish in under ~30 seconds "
                "with the other tools directly. Width: 1-2 facets -> don't call, use "
                "web_search/tools yourself; 3-5 facets -> 3-5 tasks; 6+ -> cap at 8 "
                "and group under themes. Each task MUST be a single self-contained "
                "objective with NO data dependency on the others -- the synthesizer "
                "merges the results."),
            "parameters": {
                "type": "object",
                "properties": {
                    "tasks": {
                        "type": "array",
                        "description": "Independent self-contained sub-tasks, one per node.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "objective": {"type": "string", "description": "The generative task for this node."},
                                "output_format": {"type": "string", "description": "What this node should return."},
                                "tool_guidance": {"type": "string", "description": "Which tools/sources this node should prefer."},
                                "boundaries": {"type": "string", "description": "What this node should NOT do (anti-overlap)."},
                                "local_state": {"type": "boolean", "description": "true if this facet reads THIS machine's live state."},
                                "web": {"type": "boolean", "description": "true if this facet needs web research."},
                            },
                            "required": ["objective"],
                        },
                    },
                },
                "required": ["tasks"],
            },
        },
    }]
    # P0: under STABLE_PREFIX, move dispatch_to_nodes (appended last) into the STABLE
    # region -- right after the core block, BEFORE the variable cosine tail -- so the
    # [core + dispatch_to_nodes] prefix stays byte-identical + RadixAttention-cached;
    # only the trailing tail varies. (Legacy: it stays last, as today.)
    if STABLE_PREFIX and len(_tools) >= 2:
        _ncore = len(_worker_tools_core_cache() or [])
        if 0 <= _ncore < len(_tools) - 1:
            _disp = _tools[-1]
            _tools = _tools[:_ncore] + [_disp] + _tools[_ncore:-1]
    # Publish the orchestrator turn-context so the dispatch_to_nodes handler can fire
    # the swarm with full context (request-scoped contextvar; see _orch_ctx_var).
    _orch_ctx_var.set({
        "refined": refined, "chat_id": chat_id, "model": model,
        "session_id": session_id, "last_user_text": last_user_text,
        "persona_system": persona_system, "request": request})
    # Time-sensitive turn -> publish recency/breadth defaults so dispatch_mios_verb fills
    # web_search's time_range/fanout when the model omits them (deterministic coverage; the
    # prose steering alone held only ~half the time). Gated on refine's MODEL-classified
    # `news` flag -> no keyword list; the model can still override per call.
    if NATIVE_LOOP_RECENCY_DEFAULTS and refined and refined.get("news"):
        _recency_ctx_var.set({"time_range": NATIVE_LOOP_RECENCY_RANGE,
                              "fanout": NATIVE_LOOP_RECENCY_FANOUT})
    # Content-Type REQUIRED by llama-swap to identify the model (see tool-loop note);
    # this _hdrs feeds the final-completion (_pb) + light-lane fallback posts below.
    _hdrs: dict = {"Content-Type": "application/json"}
    if (_BACKEND_KEY
            and BACKEND.split("://")[-1].split("/")[0] == _BACKEND_HOSTPORT):
        _hdrs["Authorization"] = f"Bearer {_BACKEND_KEY}"
    # ── LIVE-EMIT PUMP ("nothing emits or streams thinking"):
    # the native loop ran its tool loop with a NO-OP status callback and streamed
    # ONLY the final answer -- so the front-ends (OWUI + Hermes) showed no live
    # thinking + no 🛰️/✅ emitters (the regression vs the council path). Mirror
    # _respond_local_state: the TOP-LEVEL streaming call runs the WHOLE turn as a bg
    # task whose `emit` pushes the tool-loop activity (reasoning_content) + status
    # pills onto a queue, drained LIVE here, THEN streams the synthesized answer.
    # The bg task calls back streaming=False+emit so the loop runs exactly ONCE
    # (this branch is skipped when emit is set / non-streaming).
    if streaming and emit is None:
        async def _stream_native() -> AsyncGenerator[bytes, None]:
            yield _sse_status_phase(chat_id=chat_id, model=model, phase="prompt")
            yield _sse_status_phase(chat_id=chat_id, model=model, phase="route")
            _q: asyncio.Queue = asyncio.Queue()
            _holder: dict = {}

            async def _work() -> None:
                try:
                    _holder["resp"] = await _respond_native_loop_direct(
                        refined, streaming=False, chat_id=chat_id, model=model,
                        session_id=session_id, last_user_text=last_user_text,
                        persona_system=persona_system, messages=messages,
                        request=request, emit=_q.put_nowait, tool_choice=tool_choice)
                except Exception as _e:  # noqa: BLE001
                    _holder["err"] = str(_e)
                finally:
                    _q.put_nowait(None)

            _wtask = asyncio.create_task(_work())
            yield _sse_chunk("", chat_id=chat_id, model=model, role="assistant")
            # Accumulate the REAL final-answer tokens the bg work streams onto the
            # queue so we can (a) forward them live + (b) know not to re-type a
            # simulated copy at the end ("streaming PROPERLY").
            _streamed_parts: list = []
            while True:
                try:
                    _s = await asyncio.wait_for(_q.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    yield b": keepalive\n\n"
                    continue
                if _s is None:
                    break
                if isinstance(_s, dict):
                    if _s.get("reasoning"):
                        yield _sse_reasoning(str(_s["reasoning"]),
                                             chat_id=chat_id, model=model)
                    elif _s.get("content") is not None:
                        # LIVE final-answer tokens: the bg final completion streams
                        # real content deltas (+ the **Sources:** block) onto the
                        # queue; forward them as true OpenAI content deltas instead
                        # of dropping them and re-typing a simulated copy at the end.
                        _piece = str(_s["content"])
                        if _piece:
                            _streamed_parts.append(_piece)
                            yield _sse_chunk(_piece, chat_id=chat_id, model=model)
                    elif _s.get("label"):
                        yield _sse_status(chat_id=chat_id, model=model,
                                          emoji=str(_s.get("emoji", "·")),
                                          label=str(_s["label"]),
                                          detail=_s.get("detail"))
            await _wtask
            _resp = _holder.get("resp")
            _content = ""
            try:
                _b = _loads_lenient(bytes(_resp.body).decode("utf-8"))
                _content = (_b["choices"][0]["message"]["content"] or "").strip()
            except Exception:  # noqa: BLE001
                _content = ""
            yield _sse_status_phase(chat_id=chat_id, model=model,
                                    phase="subagent_done", done=True)
            _streamed = "".join(_streamed_parts)
            if _content and not _streamed.strip():
                # NOTHING streamed live (e.g. a relay-ladder answer, or the final
                # completion returned non-stream) -> simulated token re-type of the
                # full answer (legacy path; tunable / off via SSOT). When tokens DID
                # stream live above (the normal case), the answer + **Sources:** are
                # already on the wire -- re-typing would DOUBLE them, so skip it.
                if NATIVE_LOOP_STREAM_TOKENS and NATIVE_LOOP_STREAM_CHUNK > 0:
                    _delay = max(0.0, NATIVE_LOOP_STREAM_DELAY_MS / 1000.0)
                    for _piece in _iter_answer_chunks(_content, NATIVE_LOOP_STREAM_CHUNK):
                        yield _sse_chunk(_piece, chat_id=chat_id, model=model)
                        if _delay:
                            await asyncio.sleep(_delay)
                else:
                    yield _sse_chunk(_content, chat_id=chat_id, model=model)
            yield _sse_chunk("", chat_id=chat_id, model=model, finish_reason="stop")
            yield _sse_done()
        return StreamingResponse(_stream_native(), media_type="text/event-stream")
    _raw = ""
    _fired: list = []
    async with httpx.AsyncClient(timeout=httpx.Timeout(NATIVE_LOOP_TIMEOUT_S),
                                 headers={"Content-Type": "application/json"}) as _c:
        # The tool-loop: the model calls verbs until satisfied (reuses the proven
        # rescue/nudge/runaway-guard). allow_write=True -> real OS-control actions.
        # Route the tool-loop activity into the LIVE emit stream (operator
        # "nothing emits or streams thinking"): the push callback gets
        # status fragments (tool names, glyphs, rescue/nudge markers) as the loop
        # runs -- surface them as reasoning_content so the think dropdown shows the
        # agent working LIVE. No emit (non-streaming, no pump) -> the old no-op.
        if _DEBUG_ENABLE:
            _push = (lambda s: emit({"content": str(s)})) if emit else (lambda s: None)
        else:
            _push = (lambda s: emit({"reasoning": str(s)})) if emit else (lambda s: None)
        # Research turns (refine flagged web/news): a small local model often ANSWERS
        # FROM MEMORY instead of calling web_search -> fabricated "trending news"
        #, and the light lane REJECTS tool_choice forcing so we
        # cannot force the call. PRE-FETCH web_search deterministically here and inject
        # the LIVE results, so the model synthesizes from real data, never training
        # memory. Gated on refine's web/news flags (non-research turns like "open
        # notepad" are untouched); degrade-open (any failure just skips the prefetch).
        # NOT for a LOCAL-source turn (_local_query_nl: local_state, or routed to a
        # non-`web` domain) -- web-priming a "find my file" / "what's my CPU" query is
        # the route-by-source violation that made a local file-find web_search.
        _refs: list = []   # (title, url-or-path) SOURCES this turn -> saved References
        # FETCHED-corpus ground truth for FAB-02 per-section grounding: the LIVE
        # text the pipe actually retrieved this turn. Hoisted to function scope,
        # appended as each fetch lands; stays "" for non-web turns -> the grounding
        # guard degrades-open.
        _fetched_corpus = ""
        # LOCAL-STATE prefetch FIRST (additive hybrid,): a
        # local_state turn reaches the native loop ONLY because it ALSO has a web
        # knowledge gap (pure-local goes to the deterministic fast-path). Ground THIS
        # machine's real identity/state UP FRONT so (a) the answer states identity
        # from live tool output, not memory, and (b) the web query below can target
        # the CONCRETE components the tools just identified. Degrade-open.
        _lse = ""
        if refined and refined.get("local_state"):
            try:
                _lse = await _read_tool_enrich(refined, session_id)
                if _lse and _lse.strip():
                    _push(" 🖥️")
                    _msgs.append({"role": "system", "content": _lse[:6000]})
            except Exception as _e:  # noqa: BLE001 -- degrade-open
                log.debug("native-loop local-state prefetch skipped: %s", _e)
                _lse = ""
        # ADDITIVE web grounding ("use web tools for knowledge
        # gaps EVERY TURN"): fire whenever refine flags a web/news gap -- INCLUDING a
        # local_state HYBRID turn ("the theoretical specs of MY GPU"). Was hard-gated
        # by `not _local_query_nl`, which dropped the web half of every hybrid query.
        # For a HYBRID turn FORMULATE the search query from the locally-identified
        # hardware (so it searches "NVIDIA RTX 4090 ... specs", not a dictionary
        # lookup of the word "theoretical"). Pure-local has web=false -> never searches.
        if (refined and (refined.get("web") or refined.get("news"))):
            try:
                _wq = last_user_text
                if NATIVE_LOOP_QUERY_REFORMULATE:
                    # Reformulate on EVERY web/news turn, not just hybrid: hybrid passes
                    # the identified hardware as grounding; pure-web/news passes '' and
                    # _formulate_web_query takes its generative pure-web path (entity
                    # extraction + date anchor). Kills the verbose-imperative "give"
                    # dictionary anchor. Degrade-open (returns raw text on any error).
                    _wq = await _formulate_web_query(last_user_text, _lse or "")
                elif _lse and _lse.strip():
                    _wq = await _formulate_web_query(last_user_text, _lse)
                _wsr = await dispatch_mios_verb(
                    "web_search", {"query": _wq}, session_id=session_id)
                _wtext = (str(_wsr.get("result") or _wsr.get("output")
                              or _wsr.get("results") or _wsr)
                          if isinstance(_wsr, dict) else str(_wsr or ""))
                if _wtext.strip():
                    _push(" 🔎")
                    _fetched_corpus += "\n" + _wtext   # FAB-02 ground truth
                    _msgs.append({"role": "system", "content":
                     "LIVE web_search results for the user's request (current and "
                     "real). Answer from THESE results; do NOT use training-memory "
                     "facts or invent any headlines, titles, dates, or figures not "
                     "present here. Cite sources inline as [n]; the system appends the "
                     "numbered Sources list with the real URLs -- do NOT write your own "
                     "'Source: <name>' lines or homepage URLs (those are fabrications). "
                     "If you have no source for a claim, omit the citation:\n"
                     + _wtext[:6000]})
                    # CAPTURE the source URLs so References are SAVED on the answer
                    # ("doesn't save references for web links").
                    # A small model cites sources only by NAME ("per Wikipedia") and
                    # drops the URL; we append a deterministic Sources list below from
                    # the REAL web_search result so the links are always preserved.
                    try:
                        _wj = _loads_lenient(_wtext) if isinstance(_wtext, str) else _wtext
                        _wres = (_wj.get("results") if isinstance(_wj, dict) else None) or []
                        for _rr in _wres[:6]:
                            _u = str((_rr or {}).get("url") or "").strip()
                            _t = str((_rr or {}).get("title") or "").strip()
                            if _u.startswith("http"):
                                _refs.append((_t, _u))
                        _src_record(_wres)   # unify into the turn-scoped collector
                    except Exception:  # noqa: BLE001 -- best-effort ref capture
                        pass
            except Exception as _e:  # noqa: BLE001 -- degrade-open, never block the turn
                log.debug("native-loop web prefetch skipped: %s", _e)
        # COMPUTE prefetch ("MATH(AND OTHER PYTHON CAPABILITIES)...
        # natural language!!! not verbs/keywords"): an 8B mis-computes arithmetic/numeric/
        # date/symbolic math in its head AND -- like the web case above -- won't reliably
        # call the (now ambient/core) sandbox code tool. So the PIPE does the math, exactly
        # like the web prefetch: a GENERATIVE judge (_needs_compute, by MEANING not
        # keywords) decides if a calculation is needed; if so the micro-LLM EXTRACTS it as
        # a Python snippet, we run it in the coderun sandbox, and inject the VERIFIED
        # result as authoritative grounding. No keyword gate, no required verb from the
        # user. Gated by NATIVE_LOOP_MATH_HINT; degrade-open (any failure just skips).
        if NATIVE_LOOP_MATH_HINT and "coderun" in _VERB_CATALOG:
            try:
                # Reuse the promotion's verdict if it already judged (chat->agent),
                # else judge now (a turn that was already intent=agent). No double call.
                _nc = (refined or {}).get("_needs_compute")
                if _nc is None:
                    _nc = await _needs_compute(last_user_text)
                if _nc:
                    _code = await _formulate_compute_snippet(last_user_text)
                    if _code and _code.strip():
                        _cres = await dispatch_mios_verb(
                            "coderun", {"code": _code, "lang": "python"},
                            session_id=session_id)
                        # coderun returns {output: '{"ok":true,"stdout":"..."}'} -- PARSE
                        # out the bare stdout so the model gets the clean RESULT, not the
                        # wrapper JSON (which it mis-reads, then recomputes in-head wrong).
                        _out = ((_cres.get("output") or _cres.get("result")
                                 or _cres.get("stdout") or "")
                                if isinstance(_cres, dict) else "")
                        try:
                            _oj = _loads_lenient(_out) if isinstance(_out, str) else _out
                            _ctext = (str((_oj or {}).get("stdout")
                                          or (_oj or {}).get("output") or "").strip()
                                      if isinstance(_oj, dict) else str(_out).strip())
                        except Exception:  # noqa: BLE001
                            _ctext = str(_out).strip()
                        if _ctext:
                            _push(" 🧮")
                            log.info("native-loop: compute prefetch -> %s",
                                     _ctext[:80].replace("\n", " "))
                            _msgs.append({"role": "system", "content":
                             "VERIFIED COMPUTATION (AUTHORITATIVE -- this OVERRIDES your "
                             "mental math). The user's calculation was executed in a Python "
                             "sandbox; the exact, correct result is:\n\n    " + _ctext[:600]
                             + "\n\nState THIS as the answer. Do NOT recompute it, do NOT "
                             "show step-by-step in-head arithmetic, and do NOT contradict "
                             "this value -- your mental arithmetic is unreliable and this "
                             "sandbox result is correct."})
            except Exception as _e:  # noqa: BLE001 -- degrade-open, never block the turn
                log.debug("native-loop compute prefetch skipped: %s", _e)
        # LOCAL FILE-SEARCH prefetch (symmetric to the web prefetch). SAME failure
        # mode, local edition: a small non-tool_choice model answers "find my file"
        # from MEMORY -> a fabricated path (live miss: "find mios.toml" -> 0 tool-calls
        # -> guessed C:\Users\<YourUsername>\.mios\...). For a files-domain turn,
        # extract a filename-like token and DETERMINISTICALLY run the real file-search
        # verbs (everything_search=Windows index, fs_search=Linux) -- the pipeline does
        # the call the model skips -- then inject the REAL hits. Degrade-open: no
        # filename token / no hit / error -> skip (the model still has the tools).
        if _rdom_nl == "files":
            _mfn = (re.search(r"['\"]([^'\"]+\.[A-Za-z0-9]{1,8})['\"]", last_user_text)
                    or re.search(r"\b([\w.+-]+\.[A-Za-z0-9]{1,8})\b", last_user_text))
            _fn = _mfn.group(1).strip() if _mfn else None
            if _fn:
                _hits = []
                for _sv in ("everything_search", "fs_search"):
                    if _sv not in _VERB_CATALOG:
                        continue
                    try:
                        _sr = await dispatch_mios_verb(_sv, {"query": _fn},
                                                       session_id=session_id)
                        _st = (str(_sr.get("output") or _sr.get("result") or _sr)
                               if isinstance(_sr, dict) else str(_sr or "")).strip()
                        if _st and _st not in ("{}", "null", "[]", '""'):
                            _hits.append(_sv + " -> " + _st[:1500])
                    except Exception:  # noqa: BLE001 -- degrade-open
                        pass
                if _hits:
                    _push(" 📁")
                    _msgs.append({"role": "system", "content":
                        "LIVE local file-search results for '" + _fn + "' on THIS "
                        "machine (real paths from the file index). Report the ACTUAL "
                        "full path(s) found below; do NOT invent or template a path "
                        "(no '<YourUsername>' placeholders):\n" + "\n".join(_hits)})
        _m2 = await _v1_secondary_tool_loop(
            _c, BACKEND, BACKEND_MODEL, _hdrs, _msgs, _tools,
            NATIVE_LOOP_TIMEOUT_S, _push, allow_write=True, tool_choice=tool_choice)
        # parallel_tool_calls symmetric with the tool-loop's per-turn requests (audit
        # P4): the final completion previously omitted it, so an OpenAI-
        # compatible heavy model could fall back to its OWN default on the shaping call
        # while the loop ran sequential. Gate on the same SSOT capability check.
        _pb = {"model": BACKEND_MODEL, "messages": _m2, "stream": False,
               "parallel_tool_calls": _endpoint_supports_parallel_tools(BACKEND),
               "chat_template_kwargs": {"enable_thinking": False}}
        _live_streamed = False
        if emit is not None:
            _pb["stream"] = True

        try:
            if emit is not None:
                _raw_parts = []
                async with _c.stream("POST", f"{BACKEND}/chat/completions",
                                     content=json.dumps(_pb).encode("utf-8"),
                                     headers=_hdrs, timeout=NATIVE_LOOP_TIMEOUT_S) as _r:
                    if _r.status_code != 200:
                        log.warning("native-loop final non-200: %s %s", _r.status_code, await _r.aread())
                    else:
                        async for line in _r.aiter_lines():
                            if not line or not line.startswith("data:"): continue
                            data = line[5:].strip()
                            if data == "[DONE]": break
                            try: chunk = _loads_lenient(data)
                            except Exception: continue
                            ch = chunk.get("choices") or []
                            if not ch: continue
                            delta = ch[0].get("delta") or {}
                            _content = delta.get("content") or ""
                            _reasoning = delta.get("reasoning_content") or ""
                            if _reasoning: emit({"reasoning": _reasoning})
                            if _content:
                                _raw_parts.append(_content)
                                emit({"content": _content})
                _raw = "".join(_raw_parts)
                _live_streamed = bool(_raw.strip())
            else:
                _r = await _c.post(f"{BACKEND}/chat/completions",
                                   content=json.dumps(_pb).encode("utf-8"),
                                   headers=_hdrs, timeout=NATIVE_LOOP_TIMEOUT_S)
                _ch = (_r.json().get("choices") or [])
                _raw = str((_ch[0].get("message") if _ch else {}).get("content") or "")
        except Exception as _e:  # noqa: BLE001
            log.warning("native-loop final completion failed: %s", _e)
            _raw = ""
        # BULLET-PROOF FAILOVER : the HEAVY lane can be
        # DOWN/crashed (the SGLang q35 incident) -- a heavy-completion failure must
        # NOT dead-end the turn. When it yielded nothing, fall back to the LIGHT
        # lane (the refine endpoint = mios-llm-light) for the final completion so the
        # user still gets a GENERATED answer (degraded but present, not empty).
        # Only fires on heavy-lane failure -> zero behavior change in the normal
        # case; fully degrade-open (any error -> fall through to the relay ladder).
        if not _raw.strip() and REFINE_ENDPOINT and REFINE_ENDPOINT != BACKEND:
            try:
                _fb = {"model": REFINE_MODEL, "messages": _m2, "stream": False,
                       "chat_template_kwargs": {"enable_thinking": False}}
                _fr = await _c.post(f"{REFINE_ENDPOINT}/v1/chat/completions",
                                    content=json.dumps(_fb).encode("utf-8"),
                                    timeout=NATIVE_LOOP_TIMEOUT_S)
                _fch = (_fr.json().get("choices") or [])
                _raw = str((_fch[0].get("message") if _fch else {}).get("content") or "")
                if _raw.strip():
                    log.info("native-loop: heavy lane empty -> light-lane fallback answered")
            except Exception as _e2:  # noqa: BLE001
                log.warning("native-loop light-lane fallback failed: %s", _e2)
        for _mm in _m2:
            for _tc in (_mm.get("tool_calls") or []):
                _fn = (_tc.get("function") or {}).get("name")
                if _fn:
                    _fired.append(_fn)
    # Strip model reasoning. NATIVE empty-recovery (no injected English, no extra POST):
    # if removing <think>...</think> EMPTIES the answer, the model put the answer INSIDE
    # the think tags (it ignored enable_thinking:false) -> UNWRAP the tags instead of
    # deleting their contents, so a real answer is never discarded as "empty".
    _stripped = re.sub(r"(?is)<think>.*?</think>", "", _raw).strip()
    if not _stripped and _raw.strip():
        _stripped = re.sub(r"(?is)</?think>", "", _raw).strip()
    _raw = _stripped
    _ans = _raw
    # PROVENANCE flag for the FAB-01 guard: True ONLY when `_ans` is surfaced RAW
    # executor evidence (the relay-ladder fallback below), which must be preserved
    # verbatim. False on every model-SYNTHESIZED path -> the evidence-strip applies.
    _surfaced_raw_evidence = False
    # POLISH: heavy critic / style-correction over the final answer. Skipped when
    # the answer is ALREADY clean or if we streamed live (cannot rewrite past).
    if not getattr(locals(), "_live_streamed", False):
        try:
            _p = await polish_response(
                _raw, refined, session_id=session_id,
                original_user_text=last_user_text, persona_system=persona_system,
                agent_tools=_fired)
            if _p:
                _ans = _p
        except Exception as _e:  # noqa: BLE001
            log.debug("native-loop polish skipped: %s", _e)
    if not _ans or not _ans.strip():
        # RELAY LADDER ("HARDCODED!!!" -- never a canned dead-end):
        # (1) relay the model's own raw synthesis if polish emptied it; (2) else surface
        # the REAL tool evidence the loop already gathered (data only, no English framing);
        # (3) else leave it empty -- NO canned failure phrase, NO topic list.
        if _raw and _raw.strip():
            log.info("native-loop: relaying raw synthesis (polish empty)")
            _ans = _raw.strip()
        else:
            _snips = []
            for _mm in _m2:
                if isinstance(_mm, dict) and _mm.get("role") == "tool":
                    _ct = str(_mm.get("content") or "").strip()
                    if _ct:
                        _snips.append(_ct[:600])
                    if len(_snips) >= 3:
                        break
            _ans = "\n\n".join(_snips).strip()
            _surfaced_raw_evidence = bool(_ans)   # RAW executor evidence -> preserve verbatim
            # (3b) STILL empty but we injected saved-context recall this turn ->
            # surface it deterministically. granite sometimes emits NOTHING for a
            # memory ask (its "I have no memory" reflex -> 0 content + 0 tool-calls),
            # which previously left the user with a BLANK turn even though their own
            # saved facts were right here. Never return blank when recall is present
            # (Claude; same relay-ladder spirit -- real data, no canned phrase).
            # ALSO override a non-blank PUNT/DENIAL. granite-8b frequently
            # emits "I don't have any information about your X / could you tell me?"
            # DESPITE the saved fact being injected right here (it violates even the
            # "It is FALSE to say you don't have it" directive). A confident recall hit
            # (>=MIN_SCORE, self-gated on relevance) that the model DENIED is exactly the
            # case to surface the fact deterministically instead of shipping the denial.
            if (not _ans or _is_punt(_ans)) and _recall_text and _recall_text.strip():
                # Surface the saved FACTS cleanly: drop the model-facing framing
                # headers/instructions, the [score] markers, and the "this fact:"
                # filler so the user sees facts, not scaffolding (degrade to raw if
                # over-stripped).
                _facts = re.sub(
                    r"(?im)^\s*(Durable facts|Relevant knowledge|Recent web|Context from|Saved).*$",
                    "", _recall_text)
                _facts = re.sub(
                    r"(?im)^.*(do NOT call a tool|may be OUTDATED|answer FROM IT|fetch with a tool|these saved facts|verify).*$",
                    "", _facts)
                _facts = re.sub(r"\[\d(?:\.\d+)?\]\s*", "", _facts)
                _facts = re.sub(r"(?i)\bthis fact:\s*", "", _facts)
                _facts = "\n".join(l.rstrip() for l in _facts.splitlines() if l.strip())
                _ans = ("From your saved memory:\n" + _facts
                        if _facts.strip() else _recall_text.strip())
                log.info("native-loop: surfaced injected recall (raw+polish+tools empty)")
            else:
                log.info("native-loop: %s", "surfaced tool evidence (raw+polish empty)"
                         if _ans else "no answer/raw/evidence (empty)")
    # ANTI-FABRICATED-EXECUTION guard (operator P0; sibling of the chat short-circuit
    # guard). Keys on CONTENT PROVENANCE, not verb membership: on a model-SYNTHESIZED
    # answer any '🤝 <verb> output:' / {"success":true,"tool":...} block is
    # model-authored (the real evidence streams to the reasoning pane), so ALL such
    # blocks are stripped -- this kills FAB-01's duplicate fabricated block even for an
    # already-FIRED verb, and subsumes the skill/recipe false-positive. On the
    # RAW-evidence path a success-JSON block is kept only if it byte-matches the real
    # captured output in _m2. Flag-gated (_ANTIFAB_ENABLE, SSOT); degrade-open.
    _ans = _guard_fabricated_execution(
        _ans, surfaced_raw_evidence=_surfaced_raw_evidence, m2=_m2,
        enable=_ANTIFAB_ENABLE)
    # ANTI-FABRICATED-CITATION guard (operator no-farce): on a web/news turn, a
    # cited URL that is NOT among the sources actually FETCHED this turn was invented --
    # granite confidently emits e.g. "ai.googleblog.com/2024/..." as "this week's news"
    # from TRAINING data, ignoring the real fetched sources (the swarm safety net already
    # routed here, yet the model still fabricates a plausible stale story + fake URL). The
    # fetched-source set is ground truth; an off-list URL means the specifics are
    # untrustworthy, so replace the answer with an honest note -- the REAL **Sources:** are
    # appended just below. Gated to router=web so a non-web answer that legitimately names
    # a URL from knowledge is untouched; degrade-open keeps the model answer on any error.
    if _routed_domain_var.get(None) == "web":
        try:
            _real_norm = {re.sub(r"[/\s.]+$", "", str(_s.get("url") or ""))
                          for _s in (_src_collected() or []) if isinstance(_s, dict)}
            _ans_urls = re.findall(r"https?://[^\s)\]\"'<>]+", _ans or "")
            _fab = [_u for _u in _ans_urls
                    if re.sub(r"[/\s.]+$", "", _u) not in _real_norm]
            # Also catch prose-only fabrication: a web/news turn that fetched ZERO
            # sources yet produced a sourced-looking REPORT (a markdown table of
            # "articles") -- e.g. gibberish misrouted to news -> invented outlets. No
            # ground truth exists, so it is fabricated. Structural (table), not keyword.
            _has_report_table = bool(re.search(r"(?m)^\s*\|.*\|.*\|", _ans or ""))
            if (_fab and _real_norm) or (not _real_norm and _has_report_table):
                log.warning("native-loop: web answer fabricated (%d off-list URL(s), %d fetched "
                            "source(s), report_table=%s) -> honest note", len(_fab), len(_real_norm), _has_report_table)
                _ans = ("I couldn't extract a specific, verified story from this week's live "
                        "sources (several major news sites block automated reading). Here are "
                        "the current sources I found -- open one for the latest:")
        except Exception:  # noqa: BLE001 -- degrade-open, keep the model answer
            pass
    # ANTI-FABRICATED-CITATION guard, PART 2 -- per-SECTION entity grounding
    # (FAB-02): the URL check above only catches an off-list http URL; a partial
    # fabrication (real fetched sources + an invented section that cites an outlet
    # BY NAME, no URL) slips it. Complete the fetched corpus with the web-enrich
    # tool outputs + real source titles/urls, then strip ONLY a section whose named
    # entities are mostly absent from that corpus -- keeping the grounded half + the
    # real Sources. Gated on the web/news signal (covers a news turn that never set
    # domain==web) AND _ANTIFAB_ENABLE; degrade-open on empty corpus / caseless
    # script / too-few entities. Thresholds from [verity] SSOT (no literals).
    try:
        for _mm in _m2:
            if (isinstance(_mm, dict) and _mm.get("role") == "tool"
                    and str(_mm.get("name")) in _toolexec._WEB_ENRICH_VERBS):
                _fetched_corpus += "\n" + str(_mm.get("content") or "")
        for _s in (_src_collected() or []):
            if isinstance(_s, dict):
                _fetched_corpus += ("\n" + str(_s.get("title") or "")
                                    + " " + str(_s.get("url") or ""))
    except Exception:  # noqa: BLE001 -- degrade-open (corpus stays partial/empty)
        pass
    _fab02_gate = bool((refined or {}).get("web") or (refined or {}).get("news")
                       or _routed_domain_var.get(None) == "web")
    _ans = _guard_entity_grounding(
        _ans, _fetched_corpus, gate=_fab02_gate, enable=_ANTIFAB_ENABLE,
        min_entities=_antifab_min_entities(), ground_min=_antifab_ground_min(),
        note="*(Some content above could not be verified against the fetched "
             "sources and was omitted.)*")
    # SAVE REFERENCES ("doesn't save references for web links"):
    # a small model cites web sources by NAME and drops the URL, so the answer loses
    # its links. Append a deterministic **Sources:** list from the REAL web_search
    # results captured this turn -- ONLY when the answer doesn't already carry URLs --
    # so the references are SAVED on the answer AND persisted by _store_knowledge
    # below. Degrade-open (no refs / answer already has links -> unchanged).
    # Unify with the turn-scoped central collector (prefetch + in-loop web_search via
    # _exec_tool_calls); fall back to the local prefetch capture if the collector is off.
    try:   # harvest the answer's OWN inline citations so metadata matches the text
        _src_record_from_text(_ans)
    except Exception:  # noqa: BLE001
        pass
    _refs = _src_collected() or _refs
    # OpenAI grounding: keep ONLY sources that support the answer -- drop the
    # off-topic bleed (a Fedora answer must not cite 'Shaolin monks') before any
    # citation surface. web-tools hardening.
    _refs = _filter_relevant_sources(_refs, _ans, last_user_text)
    if _refs and _ans and _ans.strip() and "**Sources:**" not in _ans:
        _append = _sources_markdown(_refs)
        if _append:
            _ans = _ans.rstrip() + _append
            if _live_streamed and emit is not None:
                emit({"content": _append})
            log.info("native-loop: appended %d real source(s)", len(_refs))
    try:
        _store_knowledge(query=last_user_text, answer=_ans,
                         session_id=session_id, tool_history=[])
    except Exception:  # noqa: BLE001
        log.warning("Failed to store knowledge", exc_info=True)
    log.info("native-loop: %d tool-calls fired %s, %dB answer",
             len(_fired), _fired[:8], len(_ans))
    if streaming:
        async def _stream_native() -> AsyncGenerator[bytes, None]:
            yield _sse_chunk("", chat_id=chat_id, model=model, role="assistant")
            async for _b in _stream_answer(_ans, chat_id=chat_id, model=model):
                yield _b
            yield _sse_chunk("", chat_id=chat_id, model=model,
                             finish_reason="stop")
            yield _sse_done()
        return StreamingResponse(_stream_native(),
                                 media_type="text/event-stream")
    return JSONResponse(content={
        "id": chat_id, "object": "chat.completion",
        "created": int(time.time()), "model": model,
        "choices": [{"index": 0,
                     "message": {"role": "assistant", "content": _ans,
                                 # OpenAI url_citation annotations (canonical
                                 # citation contract). web-tools hardening.
                                 "annotations": _sources_annotations(_refs, _ans)},
                     "finish_reason": "stop"}],
        "usage": _usage_estimate(last_user_text, _ans),
        "mios_sources": _sources_metadata(_refs) if _refs else [],
    })


async def _respond_local_state(
    refined: Optional[dict], *, streaming: bool, chat_id: str, model: str,
    session_id: Optional[str], last_user_text: str, persona_system: str = "",
    emit=None, grounding_override: Optional[str] = None,
) -> Any:
    """Deterministic local-state answer: run the local READ tools, enumerate
    faithfully, STOP. Returns a Response, or None to fall through to the normal
    council path (no grounding / format failure -- non-streaming only)."""
    # ── LIVE EMIT PUMP (emits run SEPARATELY to the
    # pipeline). The READ tools (mios_apps games-scan can take tens of seconds)
    # were a SILENT gap. Run the SAME body as a non-streaming bg task whose
    # `emit` pushes milestone status + the grounding reasoning onto a queue,
    # drained LIVE here. NOTE: when streaming we COMMIT to a local answer (no
    # council fallthrough on empty grounding) -- a local-state query that finds
    # nothing gets an honest "couldn't find it" instead of a web-search the
    # operator confirmed returns garbage for machine-state questions.
    if streaming:
        async def _stream_ls() -> AsyncGenerator[bytes, None]:
            yield _sse_status_phase(chat_id=chat_id, model=model, phase="prompt")
            yield _sse_status_phase(chat_id=chat_id, model=model, phase="route")
            _lq: asyncio.Queue = asyncio.Queue()
            _holder: dict = {}

            async def _work() -> None:
                try:
                    _holder["resp"] = await _respond_local_state(
                        refined, streaming=False, chat_id=chat_id, model=model,
                        session_id=session_id, last_user_text=last_user_text,
                        persona_system=persona_system, emit=_lq.put_nowait,
                        grounding_override=grounding_override)
                except Exception as _e:  # noqa: BLE001
                    _holder["err"] = str(_e)
                finally:
                    _lq.put_nowait(None)

            _wtask = asyncio.create_task(_work())
            yield _sse_chunk("", chat_id=chat_id, model=model, role="assistant")
            while True:
                try:
                    _s = await asyncio.wait_for(_lq.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    yield b": keepalive\n\n"
                    continue
                if _s is None:
                    break
                if isinstance(_s, dict):
                    if _s.get("reasoning"):
                        yield _sse_reasoning(str(_s["reasoning"]),
                                             chat_id=chat_id, model=model)
                    elif _s.get("label"):
                        yield _sse_status(chat_id=chat_id, model=model,
                                          emoji=str(_s.get("emoji", "·")),
                                          label=str(_s["label"]),
                                          detail=_s.get("detail"))
            await _wtask
            _resp = _holder.get("resp")
            _content = ""
            try:
                _b = _loads_lenient(bytes(_resp.body).decode("utf-8"))
                _content = (_b["choices"][0]["message"]["content"] or "").strip()
            except Exception:  # noqa: BLE001
                _content = ""
            if _content:
                # The local-state fast-path produced a real answer -> stream it + finish.
                yield _sse_chunk(_content, chat_id=chat_id, model=model)
                yield _sse_status_phase(chat_id=chat_id, model=model,
                                        phase="subagent_done", done=True)
                yield _sse_chunk("", chat_id=chat_id, model=model,
                                 finish_reason="stop")
                yield _sse_done()
                return
            # RECOVERY ("research today's global trending" was routed to
            # local-state + dead-ended on a HARDCODED string). The local-state fast-path
            # ERRORED or found NOTHING -> the query was not machine-state (refine mis-set
            # local_state). RELAY the native loop's LIVE stream: it self-routes (web_search
            # etc.) and GENERATES the whole answer -- including any "I couldn't find that"
            # in the model's own words. NO hardcoded dead-end, NO topic list. Recovers ANY
            # misroute, and streams live (no keepalive gap / answer dump).
            _rf = dict(refined or {})
            _rf["local_state"] = False
            _nl = await _respond_native_loop_direct(
                _rf, streaming=True, chat_id=chat_id, model=model,
                session_id=session_id, last_user_text=last_user_text,
                persona_system=persona_system,
                messages=[{"role": "user", "content": last_user_text}],
                request=None)
            async for _chunk in _nl.body_iterator:
                yield _chunk
        return StreamingResponse(_stream_ls(), media_type="text/event-stream")

    def _emit(emoji: str, label: str, detail=None) -> None:
        if emit:
            try:
                emit({"emoji": emoji, "label": label, "detail": detail})
            except Exception:  # noqa: BLE001
                log.warning("Failed to emit state", exc_info=True)

    _emit("🌐" if grounding_override else "📂",
          "reading the page" if grounding_override else "checking this machine")
    grounding = grounding_override or await _read_tool_enrich(refined, session_id)
    if not grounding or not grounding.strip():
        return None
    if emit:
        try:
            if _DEBUG_ENABLE:
                emit({"content": grounding[:6000]})
            else:
                emit({"reasoning": grounding[:6000]})
        except Exception:  # noqa: BLE001
            log.warning("Failed to emit reasoning/content", exc_info=True)
    _emit("✍️", "writing the answer")
    answer = await _format_local_state(last_user_text, grounding, persona_system)
    if not answer:
        return None
    # P5.7 + knowledge: capture the local-state deterministic Q+A so it surfaces
    # via RAG recall on the next similar query AND lands as a SKILL.md episodic
    # memory. Identical fire-and-forget posture to the polish_response hook.
    _store_knowledge(query=last_user_text, answer=answer,
                     session_id=session_id, tool_history=[])
    _write_skill_md_fire(query=last_user_text, answer=answer,
                         tool_history=[], session_id=session_id)
    # Streaming is handled by the live-emit pump at the TOP of this function
    # (runs THIS body as a non-streaming bg task + drains milestone/reasoning
    # emits live). Reaching here means streaming=False -> plain JSON completion.
    return JSONResponse(content={
        "id": chat_id, "object": "chat.completion", "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0,
                     "message": {"role": "assistant", "content": answer},
                     "finish_reason": "stop"}],
        "usage": _usage_estimate(last_user_text, answer),  # Tier-0 OpenAI conformance
    })


# ── Extracted from server.py (strangler-fig wave): the micro-LLM web/compute
# query formulators + the local-state faithful-enumeration responder. All three
# were EXCLUSIVELY injected into + called by this module; moved here verbatim so
# server.py drops their DI seam. They read PLANNER_*/POLISH_*/ROUTER_MODEL from
# mios_config + _strip_think_tags from mios_turn (direct imports above); the
# server-owned _LOCAL_STATE_SYSTEM prompt + the shared _polish_post builder stay
# injected via configure().
async def _formulate_compute_snippet(user_text: str) -> str:
    """Have the micro-LLM EXTRACT the calculation the user is asking for as a short,
    self-contained Python 3 snippet that PRINTS the result (mirrors _formulate_web_query).
    The snippet runs PIPE-SIDE in the coderun sandbox so the answer is COMPUTED, not
    guessed. Code-only output; '' on empty/error -> degrade-open (no compute prefetch)."""
    if not (user_text or "").strip():
        return ""
    sys = ("Write a short, self-contained Python 3 snippet that computes the answer to "
           "the user's request and PRINTS it (use print(...) and the math/datetime "
           "modules as needed; NO input(), NO network, NO file I/O). Output the CODE "
           "ONLY -- no markdown fences, no prose. If no calculation is needed, output "
           "nothing.")
    payload = {
        "model": ROUTER_MODEL,
        "messages": [{"role": "system", "content": sys},
                     {"role": "user", "content": user_text[:1000]}],
        "chat_template_kwargs": {"enable_thinking": False},
        "temperature": 0.0, "max_tokens": 300, "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=PLANNER_TIMEOUT_S) as s:
            r = await s.post(f"{PLANNER_ENDPOINT}/v1/chat/completions", json=payload,
                             headers={"Content-Type": "application/json"})
        if r.status_code != 200:
            return ""
        code = ((r.json().get("choices") or [{}])[0].get("message", {})
                .get("content") or "").strip()
        # Strip an accidental ```/```python fence pair so only runnable code remains.
        code = re.sub(r"^```[A-Za-z0-9_]*\n?", "", code)
        code = re.sub(r"\n?```\s*$", "", code).strip()
        return code[:2000]
    except Exception as e:  # noqa: BLE001 -- degrade-open (-> no compute prefetch)
        log.debug("compute-snippet formulation failed (-> none): %s", e)
        return ""


async def _formulate_web_query(user_text: str, local_grounding: str) -> str:
    """For a HYBRID local+web turn, rewrite a vague SELF-referential question ("the
    theoretical specs of MY GPU") into a CONCRETE web query naming the components the
    local tools just IDENTIFIED -- so web_search finds the actual GPU/CPU spec pages,
    not dictionary definitions of "theoretical". Model-formulated (no templates);
    degrade-open to the raw user text on any error/empty (search still runs)."""
    if not (user_text or "").strip():
        return user_text
    _has_local = bool((local_grounding or "").strip())
    # PURE-WEB/NEWS turn (no local hardware to name): reformulate the verbose imperative
    # request into a clean entity+recency query so "Give me a briefing on X this week"
    # -> "X latest developments <YYYY-MM>" instead of the leading word "give" anchoring a
    # dictionary hit. The MODEL decides what framing to drop (generative; NO stopword
    # list in code). Gated by NATIVE_LOOP_QUERY_REFORMULATE; degrade-open to raw text.
    if not _has_local and not NATIVE_LOOP_QUERY_REFORMULATE:
        return user_text
    _date = _current_date_str()
    if _has_local:
        sys = ("Write ONE concise web-search query (the query text ONLY -- no quotes, no "
               "preamble) that finds the EXTERNAL facts needed to answer the user's "
               "question about THIS machine. The machine's REAL components are in the "
               "context. Name the SPECIFIC make/model (the exact GPU and/or CPU) plus the "
               "property asked about. Never write 'this system' or 'my' -- use the "
               "concrete component names from the context.")
        msg = ("User question: " + user_text[:500]
               + "\n\nThis machine's components (from local tools):\n"
               + local_grounding[:1500])
    else:
        sys = ("Rewrite the user's request into ONE concise web-search query (the query "
               "text ONLY -- no quotes, no preamble) containing just the SALIENT ENTITIES "
               "and TOPIC. Drop conversational and imperative framing and bare quantity "
               "words. If the request asks for current / recent / latest / this-week "
               "information, append the recency anchor '" + _date + "' (the current date) "
               "so results are present-dated, not training-era. Never invent specifics; "
               "just produce the clean query.")
        msg = (user_text or "")[:500]
    payload = {
        "model": ROUTER_MODEL,
        "messages": [{"role": "system", "content": sys},
                     {"role": "user", "content": msg}],
        "chat_template_kwargs": {"enable_thinking": False},
        "temperature": 0.0, "max_tokens": 60, "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=PLANNER_TIMEOUT_S) as s:
            r = await s.post(f"{PLANNER_ENDPOINT}/v1/chat/completions", json=payload,
                             headers={"Content-Type": "application/json"})
        if r.status_code != 200:
            return user_text
        q = ((r.json().get("choices") or [{}])[0].get("message", {})
             .get("content") or "").strip()
        import re
        q = re.sub(r'(?s)<think>.*?</think>', '', q).strip().strip('"').strip()
        return q[:200] if q else user_text
    except Exception as e:  # noqa: BLE001 -- degrade-open (-> raw query)
        log.debug("web-query formulation failed (-> raw query): %s", e)
        return user_text


async def _format_local_state(question: str, grounding: str,
                              persona_system: str = "") -> Optional[str]:
    """One faithful-enumeration pass over the live local-state tool output."""
    if not grounding or not grounding.strip():
        return None
    system = _LOCAL_STATE_SYSTEM + "\n" + _env_grounding()
    if persona_system and persona_system.strip():
        system += ("\n\nSTYLE/PERSONA (voice / tone / length / language ONLY; "
                   "never add content):\n" + persona_system.strip()[:1500])
    user_msg = (f"User question (reply in this language):\n{question}\n\n"
                f"LIVE TOOL OUTPUT (authoritative ground truth for THIS "
                f"machine):\n{grounding[:30000]}")
    _url, payload = _polish_post(
        POLISH_ENDPOINT, POLISH_MODEL,
        [{"role": "system", "content": system},
         {"role": "user", "content": user_msg}],
        max(POLISH_MAX_TOKENS, 1200))
    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=POLISH_TIMEOUT_S) as s:
            r = await s.post(_url, json=payload,
                             headers={"Content-Type": "application/json"})
            if r.status_code != 200:
                log.warning("local-state format: backend %s: %s", r.status_code, r.text[:200])
                return None
            body = r.json()
    except Exception as e:  # noqa: BLE001 -- best-effort, caller falls through
        log.warning("local-state format failed: %s", e)
        return None
    log.info("local-state format: %.1fs", time.time() - t0)
    msg = body.get("message")
    if not isinstance(msg, dict):
        msg = ((body.get("choices") or [{}])[0].get("message")) or {}
    return _strip_think_tags((msg.get("content") or "").strip()) or None
