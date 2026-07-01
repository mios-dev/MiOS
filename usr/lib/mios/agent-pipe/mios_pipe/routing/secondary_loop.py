# AI-hint: Sub-agent TOOL LOOP for both endpoint shapes, extracted verbatim from server.py (refactor R4 + a later move-home wave). Holds the symmetric pair _v1_secondary_tool_loop (the pipe-side READ-ONLY OpenAI /chat/completions tool-loop for a /v1 sub-agent) and _ollama_secondary_tool_loop (the same READ-ONLY loop for a RAW ollama node that can't self-loop): POST non-streaming -> read message.tool_calls, RESCUE a narrated call, EXECUTE read verbs via the broker, append role:tool, re-call up to SECONDARY_TOOL_MAX_ITERS or until SATISFIED. Plus their LOAD-BEARING loop guards now owned HERE: the anti-disclaimer _TOOL_NUDGE + _looks_like_disclaimer/_DISCLAIM_MARKERS, the no-progress signature _tool_call_sig, the failure verdict _tmsgs_indicate_failure, the closed-loop _REPLAN_NUDGE, and _daemon_diagnose (a fresh monitor-LLM pass over a FAILED step so the bounded retry is GUIDED not blind). _exec_tool_calls + _rescue_tool_calls (mios_toolexec) and loads_lenient (mios_jsonsalvage) are imported directly from those siblings; the remaining server-side symbols (config scalars SECONDARY_TOOL_MAX_ITERS/SECONDARY_REPLAN_MAX, the _DAEMON_DIAGNOSE_* constants, and the helpers _apply_outbound_auth/_endpoint_supports_parallel_tools) are dependency-INJECTED via configure() (one-way boundary -- this module NEVER imports server). server.py re-imports every moved name verbatim under its original alias (surface-parity zero-diff).
# AI-related: ./server.py, ./mios_toolexec.py, ./mios_jsonsalvage.py, ./mios_agent_call.py, ./mios_config.py, ./test_mios_secondary_loop.py
# AI-functions: _daemon_diagnose, _v1_secondary_tool_loop, _ollama_secondary_tool_loop, _looks_like_disclaimer, _tool_call_sig, _tmsgs_indicate_failure, configure
"""Sub-agent tool-loop (both endpoint shapes) + its anti-disclaimer / closed-loop guards.

Extracted verbatim from ``server.py``. Holds the symmetric pair
``_v1_secondary_tool_loop`` (the universal pipe-side OpenAI tool-loop a /v1
sub-agent runs through) and ``_ollama_secondary_tool_loop`` (the same loop for a
RAW ollama node that cannot self-loop), plus the load-bearing loop guards they
share: the anti-disclaimer ``_TOOL_NUDGE`` + ``_looks_like_disclaimer``, the
no-progress signature ``_tool_call_sig``, the failure verdict
``_tmsgs_indicate_failure``, the closed-loop ``_REPLAN_NUDGE`` and the
``_daemon_diagnose`` monitor pass. ``server.py`` re-imports every name under its
original alias so the module's public surface is byte-identical.

The moved bodies are unchanged. ``_exec_tool_calls`` / ``_rescue_tool_calls``
(mios_toolexec) and ``loads_lenient`` (mios_jsonsalvage) are imported directly
from those siblings; the remaining server-side symbols the loops touch (the
config scalars, the ``_DAEMON_DIAGNOSE_*`` constants and the helpers
``_apply_outbound_auth`` / ``_endpoint_supports_parallel_tools``) are injected
via :func:`configure` (one-way module boundary -- this module never imports
``server``).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from mios_toolexec import _exec_tool_calls, _rescue_tool_calls
from mios_jsonsalvage import loads_lenient as _loads_lenient

log = logging.getLogger("mios-agent-pipe")


# -- Loop guards moved home (verbatim) ------------------------------
# _tool_call_sig / _looks_like_disclaimer / _tmsgs_indicate_failure live with the
# loops that consume them (both _v1_* and _ollama_* call them). They were
# dependency-injected before this move-home wave; now defined at module level so
# the configure() seam carries one less redundant param. server.py re-imports
# each under its original name (surface-parity zero-diff).
def _tool_call_sig(tc: dict) -> str:
    """Stable (name + sorted-args) signature of a tool_call, for the loop's
    no-progress / runaway guard: if a round re-emits ONLY calls already made,
    the loop breaks instead of repeating forever (universal-loop slice 3)."""
    fn = tc.get("function") or {}
    name = str(fn.get("name") or "")
    args = fn.get("arguments")
    if isinstance(args, str):
        try:
            args = _loads_lenient(args)
        except Exception:  # noqa: BLE001
            pass
    try:
        a = json.dumps(args, sort_keys=True, ensure_ascii=False, default=str)
    except Exception:  # noqa: BLE001
        a = str(args)
    return name + "\0" + a


# A secondary that NARRATES a refusal/disclaimer with NO tool_calls (and nothing
# rescuable) defeats the tool-loop: ollama /api/chat honours no tool_choice, so
# we can't force a call up front. Detect the "I can't / no data / use my tools"
# shape and inject ONE explicit nudge to call the tool, then re-call once -- the
# ollama-lane equivalent of tool_choice=required (research
# replicas replied "I am not available... use my search tools" / "no news in the
# provided context" instead of calling web_search).
_DISCLAIM_MARKERS = (
    "not available", "no data", "no information", "no specific",
    "provided context", "i cannot", "i can't", "unable to", "i do not have",
    "i don't have", "use my search", "use your search", "knowledge is current",
    "as of my knowledge", "no relevant", "could not find", "couldn't find",
    "no news", "try a different", "would you like me to",
)


def _looks_like_disclaimer(text: str) -> bool:
    t = (text or "").strip().lower()
    return bool(t) and any(m in t for m in _DISCLAIM_MARKERS)


def _tmsgs_indicate_failure(tmsgs: list) -> bool:
    """True if any tool-result message in this batch reports a genuine FAILURE (broker
    success=False, or a read-back/verification failure marker). A valid-but-EMPTY read
    result is NOT a failure (its dispatch succeeded) -> we never re-engage on empty
    results, only on real execution/verification failures. Bounds a supervisory
    tool-loop re-engage; does not judge answer content."""
    for _m in (tmsgs or []):
        _c = str((_m or {}).get("content") or "")
        if not _c:
            continue
        try:
            _d = _loads_lenient(_c)
            if isinstance(_d, dict) and _d.get("success") is False:
                return True
        except Exception:  # noqa: BLE001 -- not JSON, fall through to text markers
            pass
        if re.search(r'"success"\s*:\s*false|not[ _]verified|text_not_delivered'
                     r'|text_mismatch|dispatch error|no_verifiable_target', _c, re.I):
            return True
    return False


# -- Dependency-injection seam --------------------------------------
# The loop + its guards read server.py's config scalars and the
# _DAEMON_DIAGNOSE_* constants, and call back into server-side helpers.
# server.py calls configure() with those AFTER every one is defined (one-way
# boundary: this module never imports server). The placeholders below carry the
# documented defaults so a standalone ``import mios_secondary_loop`` still
# succeeds; every consumer is async/runtime so nothing fires before configure().

# config scalars (server SSOT/env-derived; injected at import-completion)
SECONDARY_TOOL_MAX_ITERS = 3
SECONDARY_REPLAN_MAX = 1

# _daemon_diagnose constants (server SSOT/env-derived; injected)
_DAEMON_DIAGNOSE_MODEL = ""
_DAEMON_DIAGNOSE_ENDPOINT = ""
_DAEMON_DIAGNOSE_ENABLE = True

# server-side helpers (injected). The loop guards _looks_like_disclaimer /
# _tool_call_sig / _tmsgs_indicate_failure now live at module level (moved home),
# so only these two remain dependency-injected.
_apply_outbound_auth = None
_endpoint_supports_parallel_tools = None
_db_read = None
_db_create = None
_db_fire = None
_db_post = None


def configure(*, secondary_tool_max_iters=None, secondary_replan_max=None,
              daemon_diagnose_model=None, daemon_diagnose_endpoint=None,
              daemon_diagnose_enable=None,
              apply_outbound_auth=None,
              endpoint_supports_parallel_tools=None,
              db_read=None, db_create=None, db_fire=None, db_post=None) -> None:
    """Inject server.py's config scalars, the _DAEMON_DIAGNOSE_* constants and
    the runtime helpers the tool-loops + their guards call back into."""
    global SECONDARY_TOOL_MAX_ITERS, SECONDARY_REPLAN_MAX
    global _DAEMON_DIAGNOSE_MODEL, _DAEMON_DIAGNOSE_ENDPOINT
    global _DAEMON_DIAGNOSE_ENABLE
    global _apply_outbound_auth, _endpoint_supports_parallel_tools
    global _db_read, _db_create, _db_fire, _db_post
    if secondary_tool_max_iters is not None:
        SECONDARY_TOOL_MAX_ITERS = secondary_tool_max_iters
    if secondary_replan_max is not None:
        SECONDARY_REPLAN_MAX = secondary_replan_max
    if daemon_diagnose_model is not None:
        _DAEMON_DIAGNOSE_MODEL = daemon_diagnose_model
    if daemon_diagnose_endpoint is not None:
        _DAEMON_DIAGNOSE_ENDPOINT = daemon_diagnose_endpoint
    if daemon_diagnose_enable is not None:
        _DAEMON_DIAGNOSE_ENABLE = daemon_diagnose_enable
    if apply_outbound_auth is not None:
        _apply_outbound_auth = apply_outbound_auth
    if endpoint_supports_parallel_tools is not None:
        _endpoint_supports_parallel_tools = endpoint_supports_parallel_tools
    if db_read is not None:
        _db_read = db_read
    if db_create is not None:
        _db_create = db_create
    if db_fire is not None:
        _db_fire = db_fire
    if db_post is not None:
        _db_post = db_post


_TOOL_NUDGE = (
    "You DID NOT call a tool. You are NOT knowledge-frozen and you DO have live "
    "tools (e.g. web_search) — do not disclaim, do not say 'no data' or 'use my "
    "tools'. CALL the relevant tool NOW to fetch what you need, then answer from "
    "the real results."
)


_REPLAN_NUDGE = (
    "One of your previous tool results reported a FAILURE or an UNVERIFIED outcome "
    "(the action did not actually take effect). Re-attempt that step now with a tool "
    "call. If it genuinely cannot succeed, say so plainly -- NEVER report success for "
    "an action that did not complete.")


async def _daemon_diagnose(client, failed_summary: str, goal: str) -> str:
    """DAEMON-DIAGNOSE ("the daemon monitors the pipeline and reports
    back"): a FRESH monitor-LLM pass over a FAILED step -- WHY it likely failed + a
    DIFFERENT concrete action to try -- so the closed-loop retry is GUIDED, not a blind
    re-run. A SECOND perspective (not the model that just gave up). Short + bounded +
    degrade-open: any error/empty/disabled -> '' (caller falls back to the generic nudge)."""
    if not _DAEMON_DIAGNOSE_ENABLE:
        return ""
    try:
        _prompt = (
            "You are the MiOS pipeline MONITOR. A step just FAILED.\n"
            f"User goal: {(goal or '')[:400]}\n"
            f"Failed step result: {(failed_summary or '')[:600]}\n"
            "In 1-2 sentences: WHY did it likely fail, and what DIFFERENT, concrete tool "
            "action should be tried next to fulfil the goal? Be specific and actionable. "
            "If it genuinely cannot succeed, say so plainly.")
        _body = {"model": _DAEMON_DIAGNOSE_MODEL,
                 "messages": [{"role": "user", "content": _prompt}],
                 "stream": False, "max_tokens": 220,
                 "chat_template_kwargs": {"enable_thinking": False}}
        _r = await client.post(
            f"{_DAEMON_DIAGNOSE_ENDPOINT}/chat/completions",
            content=json.dumps(_body).encode("utf-8"),
            headers={"Content-Type": "application/json"}, timeout=30)
        if _r.status_code != 200:
            return ""
        _ch = (_r.json().get("choices") or [])
        return str((_ch[0].get("message") if _ch else {})
                   .get("content") or "").strip()[:500]
    except Exception:  # noqa: BLE001 -- degrade-open, never block the retry
        return ""


async def _v1_secondary_tool_loop(client, ep: str, model: str, headers: dict,
                                  messages: list, tools: list, timeout,
                                  push, allow_write: bool = False, tool_choice=None,
                                  session_id: Optional[str] = None) -> list:
    """Pipe-side READ-ONLY OpenAI tool-loop for a /v1 sub-agent (opencode :8633,
    hermes, daemon-agent, any node bound to a /v1 endpoint). Symmetric sibling of
    _ollama_secondary_tool_loop for the OpenAI /chat/completions shape: POST
    (non-streaming) -> read message.tool_calls (RESCUING a narrated call from
    content when the field is empty -- the opencode ```json webfetch``` lie) ->
    execute the read verbs via the broker -> append role:tool -> re-call, up to
    SECONDARY_TOOL_MAX_ITERS or until the agent stops calling tools (SATISFIED).
    A self-looping agent returns no tool_calls -> ONE pass, no-op. Returns the
    augmented messages ready for the final (streamed or complete) answer.
    Endpoint-agnostic: `ep` comes from the agent's binding map, no port literals
 here ('any agent/model on any node/endpoint, no
    hardcodes')."""
    import sys
    msgs = list(messages)
    
    # Check reflexion gate
    agent_cfg = {}
    if "mios_config" in sys.modules:
        try:
            agent_cfg = sys.modules["mios_config"]._toml_section("agent") or {}
        except Exception:
            pass
    reflexion_enable = str(agent_cfg.get("reflexion_enable", "true")).strip().lower() not in {"false", "0", "no", "off"}

    # Load superstep checkpoint
    start_iter = 0
    if session_id and _db_read:
        try:
            ckpt_sql = f"SELECT id, meta FROM session WHERE owui_chat_id = '{session_id}' AND kind = 'checkpoint' ORDER BY ts DESC LIMIT 1"
            ckpt_rows = await _db_read(ckpt_sql, pg_sql=ckpt_sql)
            if ckpt_rows and ckpt_rows[0].get("meta"):
                meta = ckpt_rows[0]["meta"]
                if isinstance(meta, str):
                    meta = json.loads(meta)
                msgs = meta.get("messages") or msgs
                start_iter = int(meta.get("superstep_idx") or 0) + 1
                log.info("Resuming ReAct loop from superstep %d (checkpoint %s)", start_iter, ckpt_rows[0]["id"])
        except Exception as _ckpt_err:
            log.warning("Failed to load ReAct checkpoint: %s", _ckpt_err)

    _seen: set = set()   # tool-call signatures already made -> loop guard
    _nudged = False      # one-shot anti-disclaimer nudge already injected?
    _replan = 0          # supervisory closed-loop re-engages used (bounded)
    _last_failed = False # did the previous tool batch report a genuine failure?
    _hdrs = dict(headers or {})
    # llama-swap (mios-llm-light proxy) REQUIRES Content-Type: application/json to
    # parse the body and extract the model id -- absent it, it 404s
    # {"error":"no model id could be identified"} (verified). httpx with
    # content=bytes does NOT auto-set it, and callers pass header dicts that omit it,
    # so the WHOLE tool-loop silently 404'd (0 tool-calls -> empty/recall-fallback).
    # Set it unconditionally here so EVERY tool-loop caller (native, opencode, hermes,
    # daemon) is covered regardless of which client/headers they pass. Idempotent.
    _hdrs.setdefault("Content-Type", "application/json")
    # WS-FED/G2: outbound credential -- the shared backend key for a local lane,
    # or this agent's OWN per-endpoint header for a remote/federated /v1 endpoint
    # (a forwarded client bearer would 401 the node, so set the right one here).
    _apply_outbound_auth(_hdrs, ep)
    for _ in range(start_iter, max(1, SECONDARY_TOOL_MAX_ITERS)):
        # parallel_tool_calls (OpenAI default True): a SMALL local model handed a
        # multi-step request ("open notepad AND type hello") emits MALFORMED parallel
        # tool calls (the fn name/wrapper drops, leaving raw "arguments": {...} in
        # content -> the call never fires), so default to False (one well-formed call
        # per turn; the loop sequences anyway). A CAPABLE lane (heavy SGLang/Qwen, per
        # _endpoint_supports_parallel_tools SSOT) gets the OpenAI-standard True -> it
        # batches INDEPENDENT calls into one turn (fewer round-trips) and still
        # sequences dependent steps. /16.
        nb = {"model": model, "messages": msgs, "tools": tools, "stream": False,
              "parallel_tool_calls": _endpoint_supports_parallel_tools(ep)}
        if tool_choice and _ == 0:
            nb["tool_choice"] = tool_choice
        try:
            r = await client.post(
                f"{ep}/chat/completions",
                content=json.dumps(nb).encode("utf-8"),
                headers=_hdrs, timeout=timeout)
            if r.status_code != 200:
                log.warning("v1 tool-loop non-200: status=%s model=%s url=%s body=%s",
                            r.status_code, model, f"{ep}/chat/completions", r.text[:240])
                break
            ch = (r.json().get("choices") or [])
            msg = (ch[0].get("message") if ch else {}) or {}
        except Exception as e:  # noqa: BLE001 -- best-effort
            log.debug("v1 secondary tool-loop call failed: %s", e)
            break
        tcs = msg.get("tool_calls") or []
        if not tcs:
            _rescued = _rescue_tool_calls(msg.get("content") or "", tools)
            if _rescued:
                push(" 🛟")
                tcs = _rescued
                _c = msg.get("content") or ""
                _c = re.sub(r"<tool_call>.*?</tool_call>", "", _c, flags=re.DOTALL | re.IGNORECASE)
                _c = re.sub(r"```(?:json)?\s*\{.*?\}\s*```", "", _c, flags=re.DOTALL | re.IGNORECASE)
                _c = re.sub(r"<function=.*?</function>", "", _c, flags=re.DOTALL | re.IGNORECASE)
                msg["content"] = _c.strip()
        if not tcs:
            # disclaimer with no tool call -> nudge ONCE then re-loop
            if not _nudged and _looks_like_disclaimer(msg.get("content") or ""):
                _nudged = True
                push(" 🪤")
                msgs.append({"role": "assistant",
                             "content": msg.get("content") or ""})
                msgs.append({"role": "user", "content": _TOOL_NUDGE})
                continue
            # CLOSED LOOP (operator "loop anything not fully fulfilled"): the model
            # stopped calling tools, but if a verb THIS loop reported a FAILURE it never
            # fixed, the turn is UNFULFILLED -> re-engage ONCE (bounded) with a fix-it
            # nudge so it retries the failed step instead of declaring done on a failure.
            # Verdict = the broker result; SECONDARY_REPLAN_MAX bounds it (no infinite loop).
            if _last_failed and _replan < SECONDARY_REPLAN_MAX:
                _replan += 1
                _last_failed = False
                push(f" 🔁{_replan}")
                log.info("tool-loop CLOSED-LOOP re-engage #%d: prior verb FAILED and the "
                         "model gave up -> fix-it nudge (bounded %d)",
                         _replan, SECONDARY_REPLAN_MAX)
                # DAEMON-DIAGNOSE: a fresh monitor LLM explains WHY the step failed +
                # proposes a DIFFERENT concrete action, so the retry is GUIDED, not a
                # blind re-ask. Pulls the goal (original user msg) + the last failed tool
                # result. Degrade-open -> generic nudge if the monitor returns nothing.
                _goal = next((str(_o.get("content") or "") for _o in (messages or [])
                              if isinstance(_o, dict) and _o.get("role") == "user"), "")
                _failsum = next((str(_o.get("content") or "") for _o in reversed(msgs)
                                 if isinstance(_o, dict) and _o.get("role") == "tool"
                                 and str(_o.get("content") or "").strip()), "")
                _diag = await _daemon_diagnose(client, _failsum, _goal)
                if _diag:
                    push(" 🩺")
                    log.info("daemon-diagnose: %s", _diag[:140])
                msgs.append({"role": "assistant",
                             "content": msg.get("content") or ""})
                msgs.append({"role": "user", "content": (
                    _REPLAN_NUDGE + ("\n\nMONITOR DIAGNOSIS (a second perspective): "
                                     + _diag if _diag else ""))})
                continue
            break
        _sigs = [_tool_call_sig(_tc) for _tc in tcs]
        if _sigs and all(_s in _seen for _s in _sigs):
            break   # loop guard: no NEW tool calls this round -> stop (runaway)
        _seen.update(_sigs)
        msgs.append({"role": "assistant",
                     "content": msg.get("content") or "", "tool_calls": tcs})
        _tmsgs, ran_read = await _exec_tool_calls(tcs, push, allow_write=allow_write)
        msgs.extend(_tmsgs)
        _last_failed = _tmsgs_indicate_failure(_tmsgs)
        
        # On tool error: add Reflexion step
        if _last_failed and reflexion_enable:
            reflection_prompt = (
                "SYSTEM REFLEXION: One or more tool calls failed. "
                "Analyze the error, reflect on why it failed, and provide a revised tool call "
                "or correct the approach in your next response."
            )
            msgs.append({"role": "user", "content": reflection_prompt})
            
            # Log the reflexion event in DB
            if _db_create and _db_fire and _db_post:
                try:
                    sql = _db_create("event", {
                        "source": "mios-agent-pipe",
                        "kind": "reflexion_retry",
                        "severity": "warning",
                        "summary": f"Tool call failed -> triggering Reflexion step for model {model}",
                        "session_id": session_id,
                        "act_type": "challenge"
                    }, now_fields=("ts",))
                    _db_fire(_db_post(sql))
                except Exception as _ev_err:
                    log.warning("Failed to log reflexion event: %s", _ev_err)

        # Save superstep checkpoint
        if session_id and _db_create and _db_fire and _db_post:
            superstep_id = f"superstep_{_}"
            checkpoint_key = f"{session_id}:{superstep_id}"
            try:
                ckpt_meta = {
                    "messages": msgs,
                    "superstep_idx": _,
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
                log.info("Saved ReAct superstep checkpoint %s", checkpoint_key)
            except Exception as _ckpt_save_err:
                log.warning("Failed to save ReAct checkpoint %s: %s", checkpoint_key, _ckpt_save_err)

        if not ran_read:
            break
    else:
        # Loop exhausted its iteration budget without the model finishing (audit P5
        #): surface the bound. The OpenAI Agents SDK raises
        # MaxTurnsExceeded; MiOS degrades-open for a gateway but LOGS so a slow /
        # looping turn is diagnosable rather than silently truncated.
        log.warning("secondary tool-loop hit MAX_ITERS=%d -> returning PARTIAL "
                    "(model kept requesting tools without a final answer)",
                    max(1, SECONDARY_TOOL_MAX_ITERS))
        msgs.append({"role": "user", "content": "SYSTEM ALERT: You have exhausted the maximum number of tool calls for this turn. Do NOT make any more tool calls. Summarize the information you have gathered and provide a final answer to the user now."})
    return msgs


async def _ollama_secondary_tool_loop(client, base: str, model: str,
                                      messages: list, tools: list, timeout,
                                      push, num_ctx: "Optional[int]" = None,
                                      allow_write: bool = False) -> list:
    """Pipe-side READ-ONLY tool-loop for a RAW ollama secondary (operator
 sub-agents run their OWN live tool-loops). The /v1 agents
    (Hermes/opencode) already loop internally; a raw ollama node can't, so the
    PIPE runs the loop: ollama /api/chat with `tools` returns message.tool_calls;
    we EXECUTE the permission=read ones (all web tools + system-state reads) via
    dispatch_mios_verb, append the results, and re-call -- up to
    SECONDARY_TOOL_MAX_ITERS. WRITE/LAUNCH verbs are NEVER run here (binding
    no-live-launch rule). The conv-scoped single-flight dedup collapses identical
    calls across the fan-out; the per-lane semaphore caps concurrency. Returns
    `messages` augmented with the assistant tool-call turn(s) + tool results,
    ready for the final streamed answer; best-effort (returns what it has)."""
    msgs = list(messages)
    _seen: set = set()   # tool-call signatures already made -> loop guard
    _nudged = False      # one-shot anti-disclaimer nudge already injected?
    _replan = 0          # supervisory closed-loop re-engages used (bounded)
    _last_failed = False # did the previous tool batch report a genuine failure?
    for _ in range(max(1, SECONDARY_TOOL_MAX_ITERS)):
        payload = {"model": model, "messages": msgs, "tools": tools, "stream": False}
        try:
            r = await client.post(
                f"{base}/v1/chat/completions",
                content=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}, timeout=timeout)
            if r.status_code != 200:
                break
            choices = r.json().get("choices") or []
            msg = (choices[0].get("message") if choices else {}) or {}
        except Exception as e:  # noqa: BLE001 -- best-effort
            log.debug("secondary tool-loop call failed: %s", e)
            break
        tcs = msg.get("tool_calls") or []
        if not tcs:
            # RESCUE: the model may have NARRATED the call in content instead of
            # emitting tool_calls[] (the narrate-instead-of-call "lie"). Promote
            # it so the loop still executes the action (universal-loop item #1).
            _rescued = _rescue_tool_calls(msg.get("content") or "", tools)
            if _rescued:
                push(" 🛟")
                tcs = _rescued
                _c = msg.get("content") or ""
                _c = re.sub(r"<tool_call>.*?</tool_call>", "", _c, flags=re.DOTALL | re.IGNORECASE)
                _c = re.sub(r"```(?:json)?\s*\{.*?\}\s*```", "", _c, flags=re.DOTALL | re.IGNORECASE)
                _c = re.sub(r"<function=.*?</function>", "", _c, flags=re.DOTALL | re.IGNORECASE)
                msg["content"] = _c.strip()
        if not tcs:
            # No tool call AND it disclaimed/punted -> nudge ONCE to actually
            # call the tool, then re-loop (ollama has no tool_choice=required).
            if not _nudged and _looks_like_disclaimer(msg.get("content") or ""):
                _nudged = True
                push(" 🪤")
                msgs.append({"role": "assistant",
                             "content": msg.get("content") or ""})
                msgs.append({"role": "user", "content": _TOOL_NUDGE})
                continue
            # CLOSED LOOP (operator "loop anything not fully fulfilled"): the model
            # stopped calling tools, but if a verb THIS loop reported a FAILURE it never
            # fixed, the turn is UNFULFILLED -> re-engage ONCE (bounded) with a fix-it
            # nudge so it retries the failed step instead of declaring done on a failure.
            # Verdict = the broker result; SECONDARY_REPLAN_MAX bounds it (no infinite loop).
            if _last_failed and _replan < SECONDARY_REPLAN_MAX:
                _replan += 1
                _last_failed = False
                push(f" 🔁{_replan}")
                log.info("tool-loop CLOSED-LOOP re-engage #%d: prior verb FAILED and the "
                         "model gave up -> fix-it nudge (bounded %d)",
                         _replan, SECONDARY_REPLAN_MAX)
                # DAEMON-DIAGNOSE: a fresh monitor LLM explains WHY the step failed +
                # proposes a DIFFERENT concrete action, so the retry is GUIDED, not a
                # blind re-ask. Pulls the goal (original user msg) + the last failed tool
                # result. Degrade-open -> generic nudge if the monitor returns nothing.
                _goal = next((str(_o.get("content") or "") for _o in (messages or [])
                              if isinstance(_o, dict) and _o.get("role") == "user"), "")
                _failsum = next((str(_o.get("content") or "") for _o in reversed(msgs)
                                 if isinstance(_o, dict) and _o.get("role") == "tool"
                                 and str(_o.get("content") or "").strip()), "")
                _diag = await _daemon_diagnose(client, _failsum, _goal)
                if _diag:
                    push(" 🩺")
                    log.info("daemon-diagnose: %s", _diag[:140])
                msgs.append({"role": "assistant",
                             "content": msg.get("content") or ""})
                msgs.append({"role": "user", "content": (
                    _REPLAN_NUDGE + ("\n\nMONITOR DIAGNOSIS (a second perspective): "
                                     + _diag if _diag else ""))})
                continue
            break
        _sigs = [_tool_call_sig(_tc) for _tc in tcs]
        if _sigs and all(_s in _seen for _s in _sigs):
            break   # loop guard: no NEW tool calls this round -> stop (runaway)
        _seen.update(_sigs)
        msgs.append({"role": "assistant",
                     "content": msg.get("content") or "", "tool_calls": tcs})
        _tmsgs, ran_read = await _exec_tool_calls(tcs, push, allow_write=allow_write)
        msgs.extend(_tmsgs)
        _last_failed = _tmsgs_indicate_failure(_tmsgs)
        if not ran_read:
            break
    else:
        # Loop exhausted its iteration budget without the model finishing (audit P5
        #): surface the bound. The OpenAI Agents SDK raises
        # MaxTurnsExceeded; MiOS degrades-open for a gateway but LOGS so a slow /
        # looping turn is diagnosable rather than silently truncated.
        log.warning("secondary tool-loop hit MAX_ITERS=%d -> returning PARTIAL "
                    "(model kept requesting tools without a final answer)",
                    max(1, SECONDARY_TOOL_MAX_ITERS))
        msgs.append({"role": "user", "content": "SYSTEM ALERT: You have exhausted the maximum number of tool calls for this turn. Do NOT make any more tool calls. Summarize the information you have gathered and provide a final answer to the user now."})
    return msgs
