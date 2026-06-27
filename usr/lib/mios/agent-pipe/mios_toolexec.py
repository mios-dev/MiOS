# AI-hint: Tool-call EXECUTION primitive extracted verbatim from server.py (refactor R4 wave). The universal pipe-side tool-loop's hands: _exec_tool_calls (executes an OpenAI tool_calls[] list via the broker -- skill/recipe/MCP/code_mode/dispatch_to_nodes/verb branches, permission+firewall+taint gated) and the LOAD-BEARING narrated-tool-call RESCUE corpus (_rescue_tool_calls + _norm_tool_call + the _RESCUE_* regexes) that promotes a model's NARRATED call (Qwen <function=> XML, ```json fence, <tool_call>{json}</tool_call>, OpenAI {"function":...} blob) back into real tool_calls[] so the loop still fires it -- the model-agnostic structural fix for the #1 agentic-loop failure. Plus _cap_verb_result/_verb_result_cap (ACI head-tail result capping) and _format_tool_error. Config scalars + the verb/recipe/high-priv/web-enrich catalogs + the orch-ctx ContextVar + every server-side helper (dispatch_mios_verb, _mcp_call_tool, _record_mcp_tool_call, the DAG/swarm fan-out helpers, _resolve_verb_key, _session_is_tainted, the DB-event helpers, _src_record, _allowed_tool_names, the dispatch-depth guards) are dependency-INJECTED via configure() (one-way boundary -- mios_toolexec NEVER imports server). _loads_lenient/_aci_normalize/execute_skill are imported directly from their sibling modules. server.py re-imports every moved name verbatim under its original alias (surface-parity zero-diff).
# AI-related: ./server.py, ./mios_config.py, ./mios_jsonsalvage.py, ./mios_aci.py, ./mios_skills.py, ./test_mios_toolexec.py
# AI-functions: _norm_tool_call, _rescue_tool_calls, _allowed_tool_names, _verb_result_cap, _cap_verb_result, _format_tool_error, _exec_tool_calls, configure
"""Tool-call execution primitive + narrated-tool-call rescue corpus.

Extracted verbatim from ``server.py``. Holds the universal pipe-side tool
executor (``_exec_tool_calls``), the hard-won narrated-tool-call salvage
(``_rescue_tool_calls`` / ``_norm_tool_call`` + the ``_RESCUE_*`` regexes), the
ACI result capping (``_cap_verb_result`` / ``_verb_result_cap``) and the broker
error shaper (``_format_tool_error``). ``server.py`` re-imports every name under
its original alias so the module's public surface is byte-identical.

The moved bodies are unchanged. ``_loads_lenient`` (mios_jsonsalvage),
``_aci_normalize`` (mios_aci) and ``execute_skill`` (mios_skills) are imported
directly from their sibling modules; every other server-side symbol they touch
(the verb/recipe/security catalogs, the orchestrator-context ContextVar, the
config scalars and the DB / dispatch / swarm helpers) is injected via
:func:`configure` (one-way module boundary -- this module never imports
``server``).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Optional

from mios_jsonsalvage import loads_lenient as _loads_lenient
from mios_aci import normalize_output as _aci_normalize
from mios_skills import execute_skill

log = logging.getLogger("mios-agent-pipe")


# -- Dependency-injection seam --------------------------------------
# The executor + rescue helpers read server.py's config scalars, the verb /
# recipe / security catalogs, the orchestrator-context ContextVar, and call back
# into the broker dispatch + DB-event + swarm fan-out helpers. server.py calls
# configure() with those AFTER every one is defined (one-way boundary: this
# module never imports server). The placeholders below carry the documented
# defaults so a standalone ``import mios_toolexec`` still succeeds; every
# consumer is async/runtime so nothing fires before configure() runs.

# config scalars (server SSOT/env-derived; injected at import-completion)
READ_TOOL_ENRICH_CHARS = 1500
READ_TOOL_ENRICH_TIMEOUT = 12.0
ACI_MAX_LINES = 160
ACI_HEAD_FRAC = 0.6
CODE_MODE_ENABLE = False
CODE_MODE_HEAVY_ONLY = False
MAX_DISPATCH_DEPTH = 2

# mutable catalogs / ContextVar (injected BY REFERENCE -- server assigns each
# exactly once and never rebinds, so the shared object stays live)
_VERB_CATALOG: dict = {}
_RECIPE_CATALOG: dict = {}
_HIGH_PRIVILEGE_VERBS: set = set()
_WEB_ENRICH_VERBS = {"web_search", "web_extract", "crawl"}
_orch_ctx_var = None

# server-side helpers (injected)
dispatch_mios_verb = None
_mcp_call_tool = None
_record_mcp_tool_call = None
_plan_swarm = None
_live_agent_names = None
_agent_dag_from_tasks = None
_respond_agent_dag = None
_depth_exhausted = None
_dispatch_depth = None
_enter_dispatch_hop = None
_resolve_verb_key = None
_session_is_tainted = None
_db_fire = None
_db_post = None
_db_create = None
_src_record = None


def configure(*, read_tool_enrich_chars=None, read_tool_enrich_timeout=None,
              aci_max_lines=None, aci_head_frac=None, code_mode_enable=None,
              code_mode_heavy_only=None, max_dispatch_depth=None,
              verb_catalog=None, recipe_catalog=None, high_privilege_verbs=None,
              web_enrich_verbs=None, orch_ctx_var=None,
              dispatch_mios_verb=None, mcp_call_tool=None,
              record_mcp_tool_call=None, plan_swarm=None, live_agent_names=None,
              agent_dag_from_tasks=None, respond_agent_dag=None,
              depth_exhausted=None, dispatch_depth=None, enter_dispatch_hop=None,
              resolve_verb_key=None, session_is_tainted=None, db_fire=None,
              db_post=None, db_create=None, src_record=None,
              classify_verb_taint=None,
              sanitize_tool_text=None) -> None:
    """Inject server.py's config scalars, catalogs, ContextVar and runtime
    helpers the executor + rescue corpus call back into."""
    global READ_TOOL_ENRICH_CHARS, READ_TOOL_ENRICH_TIMEOUT
    global ACI_MAX_LINES, ACI_HEAD_FRAC, CODE_MODE_ENABLE, CODE_MODE_HEAVY_ONLY
    global MAX_DISPATCH_DEPTH
    global _VERB_CATALOG, _RECIPE_CATALOG, _HIGH_PRIVILEGE_VERBS
    global _WEB_ENRICH_VERBS, _orch_ctx_var
    global _mcp_call_tool, _record_mcp_tool_call
    global _plan_swarm, _live_agent_names, _agent_dag_from_tasks
    global _respond_agent_dag, _depth_exhausted, _dispatch_depth
    global _enter_dispatch_hop, _resolve_verb_key, _session_is_tainted
    global _db_fire, _db_post, _db_create, _src_record
    global _classify_verb_taint, _sanitize_tool_text
    if read_tool_enrich_chars is not None:
        READ_TOOL_ENRICH_CHARS = read_tool_enrich_chars
    if read_tool_enrich_timeout is not None:
        READ_TOOL_ENRICH_TIMEOUT = read_tool_enrich_timeout
    if aci_max_lines is not None:
        ACI_MAX_LINES = aci_max_lines
    if aci_head_frac is not None:
        ACI_HEAD_FRAC = aci_head_frac
    if code_mode_enable is not None:
        CODE_MODE_ENABLE = code_mode_enable
    if code_mode_heavy_only is not None:
        CODE_MODE_HEAVY_ONLY = code_mode_heavy_only
    if max_dispatch_depth is not None:
        MAX_DISPATCH_DEPTH = max_dispatch_depth
    if verb_catalog is not None:
        _VERB_CATALOG = verb_catalog
    if recipe_catalog is not None:
        _RECIPE_CATALOG = recipe_catalog
    if high_privilege_verbs is not None:
        _HIGH_PRIVILEGE_VERBS = high_privilege_verbs
    if web_enrich_verbs is not None:
        _WEB_ENRICH_VERBS = web_enrich_verbs
    if orch_ctx_var is not None:
        _orch_ctx_var = orch_ctx_var
    if dispatch_mios_verb is not None:
        globals()["dispatch_mios_verb"] = dispatch_mios_verb
    if mcp_call_tool is not None:
        _mcp_call_tool = mcp_call_tool
    if record_mcp_tool_call is not None:
        _record_mcp_tool_call = record_mcp_tool_call
    if classify_verb_taint is not None:
        _classify_verb_taint = classify_verb_taint
    if sanitize_tool_text is not None:
        _sanitize_tool_text = sanitize_tool_text
    if plan_swarm is not None:
        _plan_swarm = plan_swarm
    if live_agent_names is not None:
        _live_agent_names = live_agent_names
    if agent_dag_from_tasks is not None:
        _agent_dag_from_tasks = agent_dag_from_tasks
    if respond_agent_dag is not None:
        _respond_agent_dag = respond_agent_dag
    if depth_exhausted is not None:
        _depth_exhausted = depth_exhausted
    if dispatch_depth is not None:
        _dispatch_depth = dispatch_depth
    if enter_dispatch_hop is not None:
        _enter_dispatch_hop = enter_dispatch_hop
    if resolve_verb_key is not None:
        _resolve_verb_key = resolve_verb_key
    if session_is_tainted is not None:
        _session_is_tainted = session_is_tainted
    if db_fire is not None:
        _db_fire = db_fire
    if db_post is not None:
        _db_post = db_post
    if db_create is not None:
        _db_create = db_create
    if src_record is not None:
        _src_record = src_record


_RESCUE_XML_RE = re.compile(
    r"<function=([a-zA-Z0-9_.\-]+)\s*>\s*"
    r"((?:<parameter=[a-zA-Z0-9_.\-]+>.*?</parameter>\s*)*)"
    r"</function>",
    re.DOTALL)
_RESCUE_PARAM_RE = re.compile(
    r"<parameter=([a-zA-Z0-9_.\-]+)>(.*?)</parameter>", re.DOTALL)
_RESCUE_FENCE_RE = re.compile(
    r"```(?:json|tool_call|tool)?\s*(\{.*?\}|\[.*?\])\s*```",
    re.DOTALL | re.IGNORECASE)
# Qwen/Hermes <tool_call>{json}</tool_call> markup. A model on a backend WITHOUT
# the matching SGLang --tool-call-parser emits its call as this CONTENT block
# instead of OpenAI tool_calls ("DIDN'T USE WEB TOOLS":
# the SGLang research nodes narrated web_search this way -> inert text). Backstop
# the server-side parser so a narrated <tool_call> is still promoted + executed.
_RESCUE_TOOLCALL_RE = re.compile(
    r"<tool_call>\s*(\{.*?\}|\[.*?\])\s*</tool_call>", re.DOTALL | re.IGNORECASE)


def _norm_tool_call(name: str, args, idx: int) -> dict:
    """One OpenAI-spec tool_call dict; `arguments` canonicalised to a JSON
    STRING (the OpenAI egress contract -- Claude `input` / Gemini `args` arrive
    as objects, OpenAI `arguments` as a string; we normalise to the string)."""
    if isinstance(args, str):
        try:
            args = _loads_lenient(args)
        except Exception:  # noqa: BLE001 -- leave malformed for the executor
            args = {}
    if not isinstance(args, dict):
        args = {}
    return {"id": f"rescue{idx}",
            "type": "function",
            "function": {"name": name,
                         "arguments": json.dumps(args, ensure_ascii=False)}}


def _allowed_tool_names(tools: "Optional[list]") -> set:
    """Names the model may legitimately call: the OFFERED tools (OpenAI `tools=`
    shape) when present, else the full verb catalog. Gates the rescue parser so
    only REAL tool names are promoted out of narrated content."""
    names: set = set()
    for t in (tools or []):
        if isinstance(t, dict):
            fn = t.get("function") if isinstance(t.get("function"), dict) else t
            n = str((fn or {}).get("name") or "").strip()
            if n:
                names.add(n)
    return names or set(_VERB_CATALOG.keys())


def _rescue_tool_calls(content: str, tools: "Optional[list]" = None) -> list:
    """Promote a NARRATED tool call in `content` into OpenAI tool_calls[].
    Parses (a) Qwen <function=NAME><parameter=K>V</parameter></function> XML,
    and (b) JSON objects -- bare or in a ```fence -- of shape
    {"name","arguments"|"args"|"parameters"}, OpenAI {"function":{"name",
    "arguments"}}, or {"tool","args"}. Returns [] when nothing matches a known
    tool. GUARD: only names in _allowed_tool_names are promoted."""
    text = content or ""
    if "{" not in text and "<function=" not in text:
        return []
    allowed = _allowed_tool_names(tools)
    if not allowed:
        return []
    out: list = []
    # (a) Qwen XML function markup.
    for m in _RESCUE_XML_RE.finditer(text):
        name = m.group(1).strip()
        if name in allowed:
            args = {k: v.strip()
                    for k, v in _RESCUE_PARAM_RE.findall(m.group(2) or "")}
            out.append(_norm_tool_call(name, args, len(out)))
    if out:
        return out
    # (b) JSON candidates: <tool_call>{json}</tool_call> blocks first (the Qwen/
    # Hermes format an un-parsed SGLang lane emits as content), then ```fenced
    # blocks, then a whole-content object.
    candidates = list(_RESCUE_TOOLCALL_RE.findall(text))
    candidates += list(_RESCUE_FENCE_RE.findall(text))
    _stripped = text.strip()
    if _stripped[:1] in "{[":
        candidates.append(_stripped)
    for cand in candidates:
        try:
            obj = _loads_lenient(cand)
        except Exception:  # noqa: BLE001
            continue
        for item in (obj if isinstance(obj, list) else [obj]):
            if not isinstance(item, dict):
                continue
            fn = item.get("function") if isinstance(item.get("function"), dict) else None
            if fn:
                name = str(fn.get("name") or "").strip()
                args = fn.get("arguments")
            else:
                name = str(item.get("name") or item.get("tool")
                           or item.get("tool_name") or "").strip()
                args = next((item[k] for k in ("arguments", "args", "parameters", "input")
                             if item.get(k) is not None), None)
            if name and name in allowed:
                out.append(_norm_tool_call(name, args, len(out)))
        if out:
            return out
    return out


def _verb_result_cap(verb: str) -> int:
    """Chars to keep from a verb's result before feeding it to the agent. A verb
    may declare a larger `max_result_chars` in mios.toml (inventory/discovery
    verbs return long lists) -- else the default READ_TOOL_ENRICH_CHARS. Data-
 driven SSOT, no per-verb literals in code."""
    cap = int((_VERB_CATALOG.get(verb) or {}).get("max_result_chars") or 0)
    return cap if cap > 0 else READ_TOOL_ENRICH_CHARS


def _cap_verb_result(verb: str, out: str) -> str:
    """Cap a verb result to its char budget, FLAGGING truncation loudly.

    A bare mid-record slice (the old `out[:cap]`) invites the model to FABRICATE
 the omitted tail -- "what's open" invented window PIDs/
    titles + a whole process list PAST a cut-off list_windows/process_list,
    because the slice looked like a complete (just short) list. This marker +
    the grounding instruction make the model report ONLY the complete entries
    shown and say the list continues, instead of completing it from imagination.
    Returns `out` unchanged when within budget."""
    cap = _verb_result_cap(verb)
    # WS-5 ACI: head-TAIL truncation (keep start + end, elide the middle) so a
    # command's tail error/exit/result survives, not just the head. The marker
    # keeps the anti-fabrication framing. Returns `out`
    # unchanged when within budget.
    return _aci_normalize(out, max_chars=cap, max_lines=ACI_MAX_LINES,
                          head_frac=ACI_HEAD_FRAC, label=verb)


def _format_tool_error(res: Any) -> Optional[dict]:
    if isinstance(res, dict):
        if "error" in res and isinstance(res["error"], dict) and "message" in res["error"]:
            return res
        has_error = False
        err_msg = ""
        if res.get("success") is False:
            has_error = True
            err_msg = res.get("error") or res.get("stderr") or "verb execution failed"
        elif res.get("ok") is False:
            has_error = True
            err_msg = res.get("error") or res.get("stderr") or "verb execution failed"
        elif "error" in res and res["error"]:
            has_error = True
            err_msg = str(res["error"])
        if has_error:
            return {
                "error": {
                    "message": err_msg,
                    "type": "invalid_request_error",
                    "code": "tool_execution_failed"
                }
            }
    return None


async def _exec_tool_calls(tcs: list, push, allow_write: bool = False) -> tuple:
    """Execute the verbs in an OpenAI tool_calls[] list via the broker and return
    (tool_result_messages, ran_any). Shared by every pipe-side sub-agent tool-loop
 (ollama + /v1) so the OpenAI loop is ONE mechanism ('full
    loop ... to OpenAI Standards'). tool_call_id is preserved for OpenAI-spec
    linkage; the result is also keyed by `name` (some models match by name).

    allow_write: when False (the PRIMARY's pipe-side pre-resolution) only
    permission=read verbs auto-execute -- the primary's OWN loop performs writes.
    When True (a WORKER/agent loop) write/launch verbs execute too: the MiOS
    agents ACT -- the no-live-launch binding is CLAUDE's alone, not the agents'
. The broker's conversation-scoped single-flight dedup
    collapses duplicate actions across the parallel swarm, so a write fires once."""
    tool_msgs: list = []
    ran_read = False
    # P6: the orchestrator turn context carries session_id -- used to (a) persist MCP
    # taint rows and (b) firewall-gate high-privilege verbs once the session is tainted.
    _sess = (_orch_ctx_var.get() or {}).get("session_id")
    for tc in tcs:
        fn = tc.get("function") or {}
        vname = str(fn.get("name") or "").strip()
        tmsg = {"role": "tool"}
        if tc.get("id"):
            tmsg["tool_call_id"] = tc["id"]   # OpenAI-spec linkage
        if vname:
            tmsg["name"] = vname
        # Args canonicalised once (OpenAI `arguments` arrives as a JSON string;
        # Claude/Gemini as an object) so every routing branch gets a dict.
        args = fn.get("arguments")
        if isinstance(args, str):
            try:
                args = _loads_lenient(args)
            except Exception:  # noqa: BLE001
                args = {}
        if not isinstance(args, dict):
            args = {}
        # ── (a) SKILL tool: mios_skill__<name> -> execute_skill ──
        # Mirrors the MCP relay routing (mios_skill__* -> /skills/run). Skill
        # rows carry NO "read" permission marker, so a skill is treated as
        # NON-read -> gated on allow_write (a worker/agent loop). The skill
        # engine maps its body steps 1:1 to dispatch_mios_verb, so the broker's
        # own permission + dedup + firewall still apply per underlying verb.
        if vname.startswith("mios_skill__"):
            real = vname[len("mios_skill__"):]
            if not allow_write:
                tmsg["content"] = (
                    f"(skipped skill {real or '?'}: writes disabled this turn)")
                tool_msgs.append(tmsg)
                continue
            ran_read = True
            push(f" 🔧 skill:{real}")
            try:
                res = await asyncio.wait_for(
                    execute_skill(real, args),
                    timeout=READ_TOOL_ENRICH_TIMEOUT * 2)
            except Exception as e:  # noqa: BLE001
                res = {"error": str(e)}
            out = (json.dumps(res, ensure_ascii=False)
                   if isinstance(res, (dict, list)) else str(res))
            tmsg["content"] = out[:READ_TOOL_ENRICH_CHARS]
            tool_msgs.append(tmsg)
            continue
        # ── (b) RECIPE tool: mios_recipe__<name> -> os_recipe verb ──
        # Mirrors the MCP relay routing (mios_recipe__* -> os_recipe with
        # {name, params}). Permission comes from _RECIPE_CATALOG (default
        # non-read when unknown); non-read recipes (open/launch/lock) gate on
        # allow_write so the no-launch rule still binds a read-only turn.
        if vname.startswith("mios_recipe__"):
            real = vname[len("mios_recipe__"):]
            rcfg = _RECIPE_CATALOG.get(real) or {}
            r_perm = str(rcfg.get("permission", "")).lower()
            if r_perm != "read" and not allow_write:
                tmsg["content"] = (
                    f"(skipped recipe {real or '?'}: not a read-only tool)")
                tool_msgs.append(tmsg)
                continue
            ran_read = True
            push(f" 🔧 recipe:{real}")
            try:
                res = await asyncio.wait_for(
                    dispatch_mios_verb("os_recipe",
                                       {"name": real, "params": args}),
                    timeout=READ_TOOL_ENRICH_TIMEOUT * 2)
            except Exception as e:  # noqa: BLE001
                res = {"error": str(e)}
            out = (json.dumps(res, ensure_ascii=False)
                   if isinstance(res, (dict, list)) else str(res))
            tmsg["content"] = _cap_verb_result("os_recipe", out)
            tool_msgs.append(tmsg)
            continue
        # ── (b2) MCP tool: mcp.<server>.<tool> -> external MCP server ──
        # No MiOS permission marker -> treated NON-read, gated on allow_write
        # (a worker/agent loop), mirroring the skill branch (operator P0).
        if vname.startswith("mcp."):
            if not allow_write:
                tmsg["content"] = (
                    f"(skipped MCP tool {vname}: writes disabled this turn)")
                tool_msgs.append(tmsg)
                continue
            ran_read = True
            push(f" 🔧 {vname}")
            try:
                res = await asyncio.wait_for(
                    _mcp_call_tool(vname, args),
                    timeout=READ_TOOL_ENRICH_TIMEOUT * 2)
            except Exception as e:  # noqa: BLE001
                res = {"error": str(e)}
            out = (json.dumps(res, ensure_ascii=False)
                   if isinstance(res, (dict, list)) else str(res))
            tmsg["content"] = out[:READ_TOOL_ENRICH_CHARS]
            # P6: persist this MCP call's taint (an untrusted_web server taints the
            # session) so the firewall gates downstream high-priv verbs. No-op for a
            # non-taint server (the helper only writes taint sources).
            _ok = not (isinstance(res, dict) and res.get("error"))
            _record_mcp_tool_call(vname, args, _ok, out, _sess)
            tool_msgs.append(tmsg)
            continue

        # ── (b3) CODE MODE: code_mode -> the podman coderun-sandbox (WS-2) ──
        # The agent writes CODE that calls a local tool API instead of emitting
        # verbs one at a time. NON-read (executes model code) -> gated on
        # allow_write (a worker/agent loop) AND on the DEFAULT-OFF SSOT flag
        # ([code_mode].enable). Degrade CLOSED -- the one place we refuse rather
        # than fall through, since running model code is the sensitive path. The
        # actual sandbox exec + broker proxy live in mios-coderun-codemode; this
        # just routes the call through the broker like any write verb so the
        # permission/firewall/dedup/HITL gates still apply.
        if vname == "code_mode":
            if not allow_write:
                tmsg["content"] = (
                    "(skipped code_mode: writes disabled this turn)")
                tool_msgs.append(tmsg)
                continue
            if not CODE_MODE_ENABLE:
                tmsg["content"] = (
                    "(skipped code_mode: disabled -- set [code_mode].enable)")
                tool_msgs.append(tmsg)
                continue
            if CODE_MODE_HEAVY_ONLY and not (_orch_ctx_var.get() or {}):
                tmsg["content"] = (
                    "(skipped code_mode: heavy-lane-only -- a light worker may not author "
                    "code; the heavy orchestrator handles code_mode)")
                tool_msgs.append(tmsg)
                continue
            ran_read = True
            push(" 🧮 code_mode")
            try:
                res = await asyncio.wait_for(
                    dispatch_mios_verb(vname, args),
                    timeout=READ_TOOL_ENRICH_TIMEOUT * 4)
            except Exception as e:  # noqa: BLE001
                res = {"error": str(e)}
            out = (json.dumps(res, ensure_ascii=False)
                   if isinstance(res, (dict, list)) else str(res))
            tmsg["content"] = _cap_verb_result("code_mode", out)
            tool_msgs.append(tmsg)
            continue
        # ── (b4) FAN-OUT: dispatch_to_nodes -> the multi-node SWARM behind a tool
        # (federated swarm; agents-as-tools pattern). The
        # orchestrator (native loop) calls this for BROAD/parallelizable work; the
        # existing _agent_dag_from_tasks + _respond_agent_dag swarm fires across all
        # live nodes and ONE synthesized result re-enters the loop as a tool_result
        # (compression-on-return). Inert outside the native loop (orchestrator ctx
        # unset) + the fanned workers never carry this tool, so no recursion.
        if vname == "dispatch_to_nodes":
            if not allow_write:
                tmsg["content"] = "(skipped dispatch_to_nodes: writes disabled)"
                tool_msgs.append(tmsg)
                continue
            _octx = _orch_ctx_var.get() or {}
            if not _octx:
                tmsg["content"] = "(dispatch_to_nodes unavailable here)"
                tool_msgs.append(tmsg)
                continue
            ran_read = True
            _raw_tasks = args.get("tasks") if isinstance(args.get("tasks"), list) else []
            _norm = []
            for _t in _raw_tasks:
                if not isinstance(_t, dict):
                    continue
                _obj = str(_t.get("objective") or _t.get("refined_text")
                           or _t.get("task") or "").strip()
                if not _obj:
                    continue
                _brief = _obj
                if _t.get("output_format"):
                    _brief += "\n\nReturn: " + str(_t["output_format"])
                if _t.get("tool_guidance"):
                    _brief += "\nPrefer tools: " + str(_t["tool_guidance"])
                if _t.get("boundaries"):
                    _brief += "\nDo NOT: " + str(_t["boundaries"])
                _norm.append({
                    "target_agent": str(_t.get("node") or _t.get("target_agent") or ""),
                    "refined_text": _brief,
                    "title": (str(_t.get("title") or _obj))[:72],
                    "local_state": bool(_t.get("local_state")),
                    "web": bool(_t.get("web"))})
            # W0-T3 hard recursion bound: this tool IS the fan-out hop. If the
            # context is already at the depth limit, refuse to spawn another
            # swarm (degrade CLOSED -- the loop continues single-agent) so an
            # agents-as-tools chain can't recurse into a swarm-of-swarms.
            if _depth_exhausted():
                log.info("dispatch_to_nodes: depth %d >= %d -> refusing nested "
                         "swarm (degrade-closed)", _dispatch_depth(), MAX_DISPATCH_DEPTH)
                tmsg["content"] = ("(dispatch_to_nodes: maximum fan-out depth "
                                   "reached; continue with the current agent)")
                tool_msgs.append(tmsg)
                continue
            push(f" 🛰️ dispatch_to_nodes ({len(_norm)})")
            try:
                # Enter a fan-out hop: child tasks (the swarm nodes spawned below)
                # inherit this incremented depth, so any node that tries to fan out
                # AGAIN sees >= the bound and degrades to single-agent.
                _enter_dispatch_hop()
                if not _norm:
                    _norm = await _plan_swarm(_octx.get("last_user_text") or "", None)
                _live = await _live_agent_names()
                _dag = _agent_dag_from_tasks(_norm, live_agents=_live,
                                             include_research=True)
                _sresp = await _respond_agent_dag(
                    _dag, _octx.get("refined"), streaming=False,
                    chat_id=str(_octx.get("chat_id") or ""),
                    model=str(_octx.get("model") or ""),
                    session_id=_octx.get("session_id"),
                    last_user_text=str(_octx.get("last_user_text") or ""),
                    persona_system=str(_octx.get("persona_system") or ""),
                    request=_octx.get("request"))
                _stext = ""
                if _sresp is not None:
                    try:
                        _sb = _loads_lenient(bytes(_sresp.body).decode("utf-8"))
                        _stext = _sb["choices"][0]["message"]["content"]
                    except Exception:  # noqa: BLE001
                        _stext = ""
                tmsg["content"] = _stext or "(the node swarm returned no result)"
            except Exception as _e:  # noqa: BLE001
                tmsg["content"] = f"(dispatch_to_nodes failed: {str(_e)[:160]})"
            tool_msgs.append(tmsg)
            continue
        # ── (c) VERB tool: bare verb name OR P1 model_name alias -> dispatch ──
        # Resolve the alias to the canonical key so the permission gate keys off the
        # REAL verb (a renamed write verb must gate as write, not fall through unknown).
        # The model-facing `vname` is kept for the tool_result `name` + UX line.
        _key = _resolve_verb_key(vname)
        v = _VERB_CATALOG.get(_key)
        # read verbs always auto-execute; write/launch only when allow_write (an
        # agent loop -- agents act). Unknown verb -> skip with an adaptive note.
        if not v or (str(v.get("permission", "")).lower() != "read"
                     and not allow_write):
            tmsg["content"] = f"(skipped {vname or '?'}: not a read-only tool)"
            tool_msgs.append(tmsg)
            continue
        # P6 Semantic Firewall: once the session is tainted (e.g. Playwright loaded
        # untrusted web content), REFUSE high-privilege / exfil verbs -- this is the
        # enforcement half of the lethal-trifecta break. Only the high-priv set pays the
        # taint DB read (cheap); read/normal verbs are unaffected. Degrade-open on error.
        if _key in _HIGH_PRIVILEGE_VERBS and _sess:
            try:
                _tainted, _chain = await _session_is_tainted(_sess)
            except Exception:  # noqa: BLE001
                _tainted, _chain = False, ""
            if _tainted:
                _db_fire(_db_post(_db_create("event", {
                    "source": "mios-agent-pipe", "kind": "firewall_block",
                    "severity": "high",
                    "summary": f"{_key} refused -- session tainted ({_chain[:120]})",
                    "payload": {"tool": _key, "taint_chain": _chain[:200]},
                }, now_fields=("ts",))))
                tmsg["content"] = (
                    f"(firewall_block: {vname} refused -- this session is tainted by "
                    f"untrusted content [{_chain[:120]}]; a high-privilege verb cannot "
                    f"run until the chain is cleared)")
                tool_msgs.append(tmsg)
                continue
        ran_read = True
        push(f" 🔧 {vname}")
        try:
            res = await asyncio.wait_for(
                dispatch_mios_verb(_key, args),
                timeout=READ_TOOL_ENRICH_TIMEOUT * 2)
        except Exception as e:  # noqa: BLE001
            res = {"error": str(e)}
        # CENTRAL SOURCE CAPTURE : this is the ONE chokepoint
        # every web_search/extract passes through -- native loop, council secondary,
        # and DAG worker. Harvest the REAL result URLs into the turn-scoped collector
        # BEFORE truncation so the final answer attaches real Sources + metadata on
        # every path (not the model inventing names). Degrade-open; no-op off-turn.
        if _key in _WEB_ENRICH_VERBS:
            try:
                _rj = res
                if isinstance(res, dict) and isinstance(res.get("output"), str):
                    _rj = _loads_lenient(res["output"])
                if isinstance(_rj, dict):
                    _src_record(_rj.get("results") or [])
            except Exception:  # noqa: BLE001 -- never break the tool loop
                pass
        # Check for failure in the result (either dict or string)
        _res_dict = None
        if isinstance(res, dict):
            _res_dict = res
        elif isinstance(res, str):
            try:
                _parsed = _loads_lenient(res)
                if isinstance(_parsed, dict):
                    _res_dict = _parsed
            except Exception:
                pass

        if _res_dict:
            _err = _format_tool_error(_res_dict)
            if _err:
                res = _err

        out = (json.dumps(res, ensure_ascii=False)
               if isinstance(res, (dict, list)) else str(res))
        tmsg["content"] = _cap_verb_result(_key, out)
        tool_msgs.append(tmsg)
    return tool_msgs, ran_read


# MCP taint-recorder deps (injected via configure()): the firewall taint classifier
# + the text scrubber. server-side fns, one-way boundary (no import of server).
_classify_verb_taint = None
_sanitize_tool_text = None


def _record_mcp_tool_call(tool: str, args: dict, success: bool, output: str,
                          session_id: "Optional[str]") -> None:
    """P6: persist an MCP tool_call as a session-linked row so the Semantic Firewall sees
    its taint. MCP tools dispatch via _exec_tool_calls branch (b2) -> _mcp_call_tool,
    BYPASSING the broker (_dispatch_bounded) that records native-verb taint -- so without
    this an untrusted_web MCP server (Playwright) would never taint the session and the
    firewall would never gate the downstream exfil verbs (lethal trifecta left open)."""
    t_tainted, t_reason = _classify_verb_taint(
        tool, args if isinstance(args, dict) else {})
    if not t_tainted:
        return                                  # only record taint sources (cheap)
    _row = {
        "tool": tool,
        "args": args if isinstance(args, dict) else {},
        "result_preview": _sanitize_tool_text(output or "")[:500],
        "success": bool(success),
        "latency_ms": 0,
        "tainted": True,
        "taint_reason": (t_reason or "") or None,
    }
    sql = _db_create("tool_call", _row, now_fields=("ts",))
    if session_id:
        sql = sql.rstrip().rstrip(";") + f", session = {session_id};"
    _db_fire(_db_post(sql))
