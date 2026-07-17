# AI-hint: Verb->bash DISPATCH chokepoint extracted VERBATIM from server.py (refactor R7 wave). The launcher chokepoint every MiOS verb passes through: _template_to_cmd (renders an SSOT [verbs.*].cmd template into the broker bash line -- {arg}/{arg!}/{arg=default}/{arg?FLAG}/{arg*} placeholder forms), _build_dispatch_cmd (the per-verb guard registry -- launch_app/window_op/os_recipe/pkg/pc_*/text_*/powershell_run branches; maps verb+args -> the bash command the broker runs; NEVER rename a verb key), and the taint->firewall->HITL->broker launcher proper: dispatch_mios_verb (public entry: alias-resolve, HITL block + ask-to-run pending, web_search recency/date anchor, single-flight dedup), _dispatch_bounded (WS-A7 conflict/parallel-limit + web_search SearXNG bulkhead) and _dispatch_mios_verb_inner (PDP/quota/firewall-taint/HITL/enum gates, then mios-sandbox-wrapped broker socket I/O over the CAPTURE_JSON: protocol). SECURITY-CRITICAL: every gate is NAME-KEYED (verb keys, permission tiers, _HIGH_PRIVILEGE_VERBS / _LAUNCH_VERBS membership) -- nothing renamed. dispatch_mios_verb is re-injected into mios_skills/mios_hitlflow/mios_planner. _classify_verb_taint/_session_is_tainted (mios_firewall), _hitl_block_reason/_hitl_arbiter_verdict/_match_user_cfg/_dispatch_pdp_reason/_dispatch_quota_reason (mios_policy), _action_hash/_pending_hash/_hitl_record_pending/_hitl_gate (mios_hitlflow), _loads_lenient (mios_jsonsalvage) and mios_sandbox are imported DIRECTLY from their sibling modules; every other server-side symbol (the verb catalog, the broker socket path, the DB-event helpers, the dispatch ContextVars, the sandbox-profile resolver, _arg_with_synonyms / _resolve_verb_key / _validate_enum_args / _trace_span / _TOOL_CONFLICT / the dedup state) is dependency-INJECTED via configure() (one-way boundary -- this module NEVER imports server). server.py re-imports every moved name verbatim under its original alias (surface-parity zero-diff).
# AI-related: ./server.py, ./mios_config.py, ./mios_sandbox.py, ./mios_secset.py, ./mios_toolconflict.py, ./mios_firewall.py, ./mios_policy.py, ./mios_hitlflow.py, ./mios_jsonsalvage.py, ./test_mios_dispatch.py
# AI-functions: _arg_with_synonyms, _validate_enum_args, _dispatch_sandbox_profile, _sandbox_wrap_cmd, _template_to_cmd, _build_dispatch_cmd, dispatch_mios_verb, _dispatch_bounded, _dispatch_mios_verb_inner, dispatch_router, dispatch_verb, configure
"""Verb->bash dispatch chokepoint -- the taint->firewall->HITL->broker launcher.

Extracted verbatim from ``server.py`` (refactor R7). Holds the SSOT command-
template renderer (``_template_to_cmd``), the per-verb dispatch-command builder
(``_build_dispatch_cmd`` -- the launch_app / window_op / os_recipe / pkg / pc_* /
text_* / powershell_run guard registry) and the launcher proper
(``dispatch_mios_verb`` / ``_dispatch_bounded`` / ``_dispatch_mios_verb_inner``).
``server.py`` re-imports every name under its original alias so the module's
public surface is byte-identical.

The moved bodies are UNCHANGED. ``_classify_verb_taint`` / ``_session_is_tainted``
(mios_firewall), ``_hitl_block_reason`` / ``_HITL_ARBITER_URL`` /
``_hitl_arbiter_verdict`` / ``_match_user_cfg`` / ``_dispatch_quota_reason`` /
``_dispatch_pdp_reason`` (mios_policy), ``_action_hash`` / ``_pending_hash`` /
``_hitl_record_pending`` / ``_hitl_gate`` (mios_hitlflow) and ``_loads_lenient``
(mios_jsonsalvage) are imported directly from their sibling modules; ``mios_sandbox``
is imported as a module. Every other server-side symbol they touch (the verb
catalog, the broker socket path, the DB-event helpers, the dispatch ContextVars,
the sandbox-profile resolver and the dedup state) is injected via
:func:`configure` (one-way boundary -- this module never imports ``server``).

SECURITY-CRITICAL: every gate here is NAME-KEYED (verb keys, the permission tier
in mios_policy, the ``_HIGH_PRIVILEGE_VERBS`` / ``_LAUNCH_VERBS`` set membership).
Nothing is renamed.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import random
import re
import shlex
import socket as _socket
import time
import uuid
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse

import mios_sandbox
import mios_ruleof2          # the Rule-of-Two architectural gate (pure evaluator)
import mios_argval
from mios_argval import _arg_with_synonyms, _validate_enum_args
from mios_template import _template_to_cmd
import mios_quarantine       # the CaMeL dual-context quarantine gate (stricter superset)
import mios_hitl             # the unified HITL verdict resolver (mios_hitl.decide)
from mios_jsonsalvage import loads_lenient as _loads_lenient
import mios_scratchpad
# Security gates imported DIRECTLY from their sibling modules (NAME-KEYED -- nothing
# renamed). These modules are themselves DI-configured by server.py; importing the
# function objects here binds the SAME configured callables server.py uses.
from mios_firewall import _classify_verb_taint, _session_is_tainted, _is_external_url
from mios_policy import (
    _hitl_block_reason,
    _HITL_ARBITER_URL,
    _hitl_arbiter_verdict,
    _match_user_cfg,
    _dispatch_quota_reason,
    _dispatch_pdp_reason,
)
from mios_hitlflow import (
    _action_hash,
    _pending_hash,
    _hitl_record_pending,
    _hitl_gate,
)

log = logging.getLogger("mios-agent-pipe")


# -- Dependency-injection seam --------------------------------------
# The dispatch chokepoint reads server.py's verb catalog, config scalars, the
# broker socket path, the dispatch ContextVars and calls back into the DB-event /
# sandbox-profile / enum-validate / trace / conflict-gate helpers. server.py calls
# configure() with those AFTER every one is defined (one-way boundary: this module
# never imports server). The placeholders below carry the documented defaults so a
# standalone ``import mios_dispatch`` still succeeds; every consumer is async/runtime
# so nothing fires before configure() runs.

# config scalars (server SSOT/env-derived; injected at import-completion). The
# sandbox knobs back the native _sandbox_wrap_cmd helper below; their placeholder
# defaults are degrade-open (no enforcement / nothing self-confined) until server
# injects the real SSOT-derived values -- they do NOT restate any server literal.
WEB_DISPATCH_JITTER_S = 0.15
DISPATCH_DEDUP = True
NATIVE_LOOP_DATE_IN_QUERY = True
LAUNCHER_SOCK = "/run/mios-launcher/launcher.sock"
SANDBOX_ENFORCE = False
_SANDBOX_SELF_CONFINED: tuple = ()
# F2/T-033 Rule-of-Two architectural gate mode (SSOT [security].rule_of_two_mode):
# off (default -- the evaluator is NOT consulted, byte-identical) | audit | enforce.
# Placeholder default OFF until server injects the SSOT/env-derived value.
RULE_OF_TWO_MODE = "off"
# F2 CaMeL dual-context QUARANTINE gate mode (SSOT [security].quarantine_mode):
# off (default -- the evaluator is NOT consulted, byte-identical) | audit | enforce.
# The STRICTER superset of Rule-of-Two: gates the tainted + (sensitive OR state-change)
# case. Placeholder default OFF until server injects the SSOT/env-derived value.
QUARANTINE_MODE = "off"

# mutable catalogs / sets / state / ContextVars / sync primitives (injected BY
# REFERENCE -- server assigns each exactly once and never rebinds, so the shared
# object stays live + context propagation works).
_VERB_CATALOG: dict = {}
_VERB_ARG_SYNONYMS: dict = {}
_HIGH_PRIVILEGE_VERBS: frozenset = frozenset()
_LAUNCH_VERBS: frozenset = frozenset()
_dispatch_inflight: dict = {}
_web_sem = None
_TOOL_CONFLICT = None
_conv_key_var = None
_recency_ctx_var = None
_proposal_var = None
_dispatch_agent_var = None
# Rule-of-Two approval downgrade: the ask-to-run turn var carrying the action_hash the
# user EXPLICITLY approved this turn (shared with the [ai] gate; None until injected).
_hitl_approved_var = None
_AGENT_REGISTRY: dict = {}

# server-side helpers (injected). _arg_with_synonyms / _validate_enum_args /
# _dispatch_sandbox_profile / _sandbox_wrap_cmd now LIVE in this module (their sole
# consumer is the dispatch chokepoint), so they are no longer injected.
_resolve_verb_key = None
_current_date_str = None
_trace_span = None
_db_fire = None
_db_post = None
_db_create = None
_letta_dispatch_handler = None


def _emit_dispatch_dedup_event(tool: str, args: dict,
                               session_id: "Optional[str]") -> None:
    """Audit the single-flight collapse as the same `action_repeat_dedup`
    event the DAG cross-level guard emits -- one observability shape for both
    dedup paths (MiOS spec). Uses the module's injected event-DB writers."""
    try:
        _db_fire(_db_post(_db_create("event", {
            "source": "mios-agent-pipe",
            "kind": "action_repeat_dedup",
            "severity": "info",
            "summary": f"single-flight collapse: {tool}",
            "payload": {"tool": tool, "mode": "concurrent_single_flight"},
        }, now_fields=("ts",))))
    except Exception:
        pass


def _record_dispatch_tool_call_row(tool: str, result: dict,
                                   session_id: "Optional[str]") -> None:
    """Persist a /v1/dispatch verb execution as a session-linked ``tool_call`` row
    -- the SAME shape the chat dispatch fast-path and the DAG executor write -- so a
    verb run through the dispatch HTTP front (mios-mcp-server's ``tools/call`` lands
    here) is VISIBLE to same-session provenance-taint propagation.

    ``_session_is_tainted`` decides the Semantic Firewall block by reading prior
    ``tool_call`` rows with ``tainted = true``; the chat + DAG paths each record their
    executions, but the dispatch path did not -- so a tainting verb dispatched here
    left no row, the taint was never seen, and a downstream high-privilege verb in the
    SAME session went un-gated. The taint markers come straight off the verb result
    (``_classify_verb_taint`` set them inside the dispatch chokepoint): no new schema,
    no new taint logic, just the missing persistence.

    Best-effort / degrade-open: the verb has ALREADY executed by the time this runs,
    so an absent DB writer or a write failure is swallowed (the audit row is not
    load-bearing for the verb's own result)."""
    try:
        _row = {
            "tool": str(result.get("tool") or tool or ""),
            "args": result.get("args") if isinstance(result.get("args"), dict) else {},
            "result_preview": (result.get("output") or "")[:500],
            "success": bool(result.get("success")),
            "latency_ms": int(result.get("latency_ms", 0) or 0),
            "tainted": bool(result.get("tainted")),
            "taint_reason": (result.get("taint_reason") or "") or None,
        }
        sql = _db_create("tool_call", _row, now_fields=("ts",))
        if session_id:
            sql = sql.rstrip().rstrip(";") + f", session = {session_id};"
        _db_fire(_db_post(sql))
    except Exception:  # noqa: BLE001 -- degrade-open: verb already ran; audit is best-effort
        pass


def configure(*, verb_catalog=None, verb_arg_synonyms=None,
              high_privilege_verbs=None, launch_verbs=None,
              web_dispatch_jitter_s=None, dispatch_dedup=None,
              native_loop_date_in_query=None, launcher_sock=None,
              sandbox_enforce=None, sandbox_self_confined=None,
              rule_of_two_mode=None, quarantine_mode=None,
              dispatch_inflight=None, web_sem=None, tool_conflict=None,
              conv_key_var=None, recency_ctx_var=None, proposal_var=None,
              dispatch_agent_var=None, hitl_approved_var=None,
              resolve_verb_key=None, current_date_str=None,
              emit_dispatch_dedup_event=None,
              trace_span=None, db_fire=None, db_post=None,
              db_create=None, letta_dispatch_handler=None,
              agent_registry=None) -> None:
    """Inject server.py's verb catalog + arg-synonym map, config scalars (incl. the
    sandbox enforce knob + self-confined set), broker socket path, dispatch
    ContextVars + state and the runtime helpers the dispatch chokepoint calls back
    into. Partial injection supported (each guarded by `is not None`) so the
    late-bound native_loop_date_in_query can land in a second call."""
    global WEB_DISPATCH_JITTER_S, DISPATCH_DEDUP, NATIVE_LOOP_DATE_IN_QUERY
    global LAUNCHER_SOCK, SANDBOX_ENFORCE, _SANDBOX_SELF_CONFINED, RULE_OF_TWO_MODE
    global QUARANTINE_MODE
    global _VERB_CATALOG, _VERB_ARG_SYNONYMS, _HIGH_PRIVILEGE_VERBS, _LAUNCH_VERBS
    global _dispatch_inflight, _web_sem, _TOOL_CONFLICT
    global _conv_key_var, _recency_ctx_var, _proposal_var, _dispatch_agent_var
    global _hitl_approved_var, _AGENT_REGISTRY
    global _resolve_verb_key, _current_date_str
    global _emit_dispatch_dedup_event, _trace_span, _db_fire, _db_post, _db_create
    global _letta_dispatch_handler
    if agent_registry is not None:
        _AGENT_REGISTRY = agent_registry
    if verb_catalog is not None:
        _VERB_CATALOG = verb_catalog
        mios_argval.configure(verb_catalog=verb_catalog)
    if letta_dispatch_handler is not None:
        _letta_dispatch_handler = letta_dispatch_handler
    if verb_arg_synonyms is not None:
        _VERB_ARG_SYNONYMS = verb_arg_synonyms
        mios_argval.configure(verb_arg_synonyms=verb_arg_synonyms)
    if high_privilege_verbs is not None:
        _HIGH_PRIVILEGE_VERBS = high_privilege_verbs
    if launch_verbs is not None:
        _LAUNCH_VERBS = launch_verbs
    if web_dispatch_jitter_s is not None:
        WEB_DISPATCH_JITTER_S = web_dispatch_jitter_s
    if dispatch_dedup is not None:
        DISPATCH_DEDUP = dispatch_dedup
    if native_loop_date_in_query is not None:
        NATIVE_LOOP_DATE_IN_QUERY = native_loop_date_in_query
    if launcher_sock is not None:
        LAUNCHER_SOCK = launcher_sock
    if sandbox_enforce is not None:
        SANDBOX_ENFORCE = sandbox_enforce
    if sandbox_self_confined is not None:
        _SANDBOX_SELF_CONFINED = sandbox_self_confined
    if rule_of_two_mode is not None:
        RULE_OF_TWO_MODE = rule_of_two_mode
    if quarantine_mode is not None:
        QUARANTINE_MODE = quarantine_mode
    if dispatch_inflight is not None:
        _dispatch_inflight = dispatch_inflight
    if web_sem is not None:
        _web_sem = web_sem
    if tool_conflict is not None:
        _TOOL_CONFLICT = tool_conflict
    if conv_key_var is not None:
        _conv_key_var = conv_key_var
    if recency_ctx_var is not None:
        _recency_ctx_var = recency_ctx_var
    if proposal_var is not None:
        _proposal_var = proposal_var
    if dispatch_agent_var is not None:
        _dispatch_agent_var = dispatch_agent_var
    if hitl_approved_var is not None:
        _hitl_approved_var = hitl_approved_var
    if resolve_verb_key is not None:
        _resolve_verb_key = resolve_verb_key
    if current_date_str is not None:
        _current_date_str = current_date_str
    if emit_dispatch_dedup_event is not None:
        _emit_dispatch_dedup_event = emit_dispatch_dedup_event
    if trace_span is not None:
        _trace_span = trace_span
    if db_fire is not None:
        _db_fire = db_fire
    if db_post is not None:
        _db_post = db_post
    if db_create is not None:
        _db_create = db_create


# ── Verb-arg + enum validation + sandbox-profile helpers ───────────
# Moved here from server.py: the dispatch chokepoint is their SOLE consumer
# (_template_to_cmd / _build_dispatch_cmd resolve args via _arg_with_synonyms;
# _dispatch_mios_verb_inner gates on _validate_enum_args then resolves +
# opt-in-wraps the broker cmd via _dispatch_sandbox_profile / _sandbox_wrap_cmd).
# They read the injected verb catalog / arg-synonym map / sandbox knobs above.
# (Functions _arg_with_synonyms and _validate_enum_args are imported from mios_argval above)


def _dispatch_sandbox_profile(tool: str) -> "mios_sandbox.SandboxProfile":
    """Resolve the WS-A13 confinement profile for `tool`: its [verbs.*].permission
    tier, with an optional [verbs.*].sandbox_profile explicit override. Fail-closed
    in mios_sandbox (unknown tier/override -> strict)."""
    vcfg = _VERB_CATALOG.get(tool) or {}
    return mios_sandbox.resolve_profile(
        str(vcfg.get("permission", "read")).lower(),
        explicit=vcfg.get("sandbox_profile"))


def _sandbox_wrap_cmd(tool: str, cmd: str,
                      profile: "mios_sandbox.SandboxProfile",
                      session_id: Optional[str] = None) -> "tuple":
    """Return (cmd, workspace_or_None). When SANDBOX_ENFORCE is on AND `tool` OPTS
    IN to confinement (an explicit [verbs.*].sandbox_profile) AND the resolved
    profile is confined AND the cmd does not already self-confine, prefix it with
    mios-sandbox-exec (--level enforce, +--net iff the tier allows egress) bound to
    a fresh per-dispatch workspace. Otherwise the cmd is returned unchanged. The
    OPT-IN gate (explicit override, not tier alone) is what keeps OS-control/launch
    verbs -- which bwrap would break -- from ever being wrapped here."""
    import subprocess
    cephfs_enable = os.environ.get("MIOS_CEPHFS_ENABLE", "false").lower() in ("true", "1", "yes", "on")
    if cephfs_enable:
        sess_id = session_id or uuid.uuid4().hex[:8]
        sess_id = "".join(c for c in sess_id if c.isalnum() or c in "-_")[:32]
        uid = os.getuid() if hasattr(os, "getuid") else 1000
        runtime_dir = f"/run/user/{uid}/session-{sess_id}"
        try:
            subprocess.run(["systemd-run", "--user", "--scope", "-p", f"RuntimeDirectory=session-{sess_id}", "true"], capture_output=True, check=False)
        except Exception:
            try:
                os.makedirs(runtime_dir, exist_ok=True)
                os.chmod(runtime_dir, 0o700)
            except Exception:
                pass
        cmd = f"XDG_RUNTIME_DIR={runtime_dir} " + cmd

    opted_in = bool((_VERB_CATALOG.get(tool) or {}).get("sandbox_profile"))
    if not (SANDBOX_ENFORCE and opted_in and profile.confined):
        return cmd, None
    if any(w in cmd for w in _SANDBOX_SELF_CONFINED):
        return cmd, None
    ws = mios_sandbox.workspace_path(tool, uuid.uuid4().hex)
    prefix = mios_sandbox.sandbox_exec_prefix(profile, workspace=ws)
    if not prefix:
        return cmd, None
    return " ".join(shlex.quote(p) for p in prefix) + " " + cmd, ws


# ── Dispatch (broker socket bridge) ────────────────────────────────



def normalize_container_exec(script: str) -> str:
    # 1. Map docker -> podman (case-insensitively, using word boundaries)
    script = re.sub(r'\bdocker(\.exe)?\b', 'podman', script, flags=re.IGNORECASE)
    
    # 2. Map code-server / mios-code-server -> mios-agents
    script = re.sub(r'\b(mios-)?code-server\b', 'mios-agents', script, flags=re.IGNORECASE)
    
    # 3. Strip interactive -t / -it / -ti / --tty flags from podman exec/docker exec
    def clean_flags(match):
        flag_str = match.group(2)
        if flag_str.startswith('--'):
            if 'tty' in flag_str.lower():
                return match.group(1) + ' exec'
            return match.group(0)
        cleaned = re.sub(r'[tT]', '', flag_str)
        if cleaned == '-':
            return match.group(1) + ' exec'
        return match.group(1) + ' exec ' + cleaned

    script = re.sub(r'\b(podman)\s+exec\s+(\-[a-zA-Z]+|\-\-tty\b)', clean_flags, script, flags=re.IGNORECASE)
    
    # 4. Strip bare shell execution at the end of podman exec to prevent hangs.
    # Replace bare shell (bash, sh, zsh, /bin/bash, etc.) with a safe 'true' command.
    script = re.sub(
        r'\b(podman\s+exec\s+(?:-[a-zA-Z\d\-]+(?:\s+[^\s]+)?\s+)*[\w\-\.]+)\s+(bash|sh|zsh|/bin/bash|/bin/sh|/bin/zsh)(\s+-[a-zA-Z\d\-]+)*\s*$',
        r'\1 true',
        script,
        flags=re.IGNORECASE | re.MULTILINE
    )
    return script


def _build_dispatch_cmd(tool: str, args: dict) -> Optional[str]:
    """Map verb name + args -> the bash command line the launcher
    broker executes. Kept in lockstep with the OWUI pipe's
    _dispatch_mios_verb. Returns None for unknown verbs."""
    if tool in ("powershell_run", "run_code", "code_mode"):
        for key in ("script", "code"):
            if key in args and isinstance(args[key], str):
                args[key] = normalize_container_exec(args[key])
    # SSOT command template takes precedence (P3): a verb with a `cmd` in
    # mios.toml renders via the catalog; verbs without one fall through to the
    # code branches below. Incremental migration -> zero regression.
    # SKIP verbs with pre-processing guards (basename extraction, probe-name
    # reject, position routing, dimension validation): they render templates
    # explicitly AFTER validation in their own branch.
    _GUARDED_VERBS = {"launch_app", "window_op"}
    _tmpl = (_VERB_CATALOG.get(tool) or {}).get("cmd")
    if _tmpl and tool not in _GUARDED_VERBS:
        _rendered = _template_to_cmd(tool, _tmpl, args)
        if _rendered:
            return _rendered
    if tool == "launch_app":
        name = _arg_with_synonyms(tool, "name", args).strip()
        if name and ("/" in name or "\\" in name):
            base = os.path.basename(name.rstrip("/\\")) or name
            for suf in (".exe", ".desktop", ".lnk"):
                if base.lower().endswith(suf):
                    base = base[: -len(suf)]
                    break
            name = base
        if not name:
            return None
        norm = name.lower().replace("-", "_").rstrip("s")
        if norm in _VERB_CATALOG or norm.rstrip("_") in {
            v.replace("-", "_").rstrip("s") for v in _VERB_CATALOG
        }:
            return None
        _clean = dict(args, name=name)
        extra_args = args.get("args") or []
        _cat = _VERB_CATALOG.get("launch_app") or {}
        if extra_args:
            _tmpl = _cat.get("cmd_args") or _cat.get("cmd")
        else:
            _tmpl = _cat.get("cmd")
        if _tmpl:
            return _template_to_cmd("launch_app", _tmpl, _clean)
        return None
    if tool == "window_op":
        op = str(args.get("op", "focus")).lower()
        _cat = _VERB_CATALOG.get("window_op") or {}
        if op == "focus":
            pos = str(args.get("position", "default")).lower()
            if pos in ("as-is", "default", ""):
                _tmpl = _cat.get("cmd")
            else:
                _tmpl = _cat.get("cmd_positioned")
        elif op == "move-pixel":
            _tmpl = _cat.get("cmd_pixel")
        elif op == "resize":
            w = int(args.get("width", 0))
            h = int(args.get("height", 0))
            if w <= 0 or h <= 0:
                return None
            _tmpl = _cat.get("cmd_resize")
        else:
            _tmpl = _cat.get("cmd")
        if _tmpl:
            return _template_to_cmd("window_op", _tmpl, args)
        return None
    if tool == "os_recipe":
        name = _arg_with_synonyms(tool, "name", args).strip()
        if not name:
            return None
        params = args.get("params") or {}
        if not isinstance(params, dict):
            params = {}
        # Splice key=value pairs after the recipe name; mios-os-recipe
        # quote-escapes each substituted value before splicing into
        # the recipe template.
        kv_args = " ".join(
            f"{shlex.quote(str(k))}={shlex.quote(str(v))}"
            for k, v in params.items()
        )
        target_os = str(args.get("os") or "").strip().lower()
        # HOST-DEFAULT (policy A): host-describing recipes report
        # the MACHINE's state -- on this WSL-on-Windows deployment the operator means the
        # WINDOWS HOST, not the Linux VM. With no explicit os=, default these to 'windows'
        # IF the host is reachable (full-path interop present, since appendWindowsPath=false
        # keeps bare powershell.exe off PATH); else leave to mios-os-recipe's detect (linux).
        # service-status stays linux (systemctl is VM-specific). Fixes "show my network/disk"
        # describing the VM instead of the operator's actual machine.
        if (not target_os
                and name in {"show-network", "disk-usage", "list-drives", "show-process"}
                and os.path.exists("/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe")):
            target_os = "windows"
        os_flag = f"--os {shlex.quote(target_os)} " if target_os in ("linux", "windows") else ""
        return f"mios-os-recipe --json {os_flag}{shlex.quote(name)} {kv_args}".strip()
    # ── pkg (unified package verb -- collapses 13 winget_* / flatpak_*
    # verbs into one). Routes by (action, backend) to the existing
    # winget / flatpak shims. backend="auto" picks winget when id looks
    # like Publisher.AppId, flatpak otherwise -- the LLM is encouraged
    # to be explicit. Operator-flagged "consolidate
    # redundant" -- legacy winget_*/flatpak_* verbs kept tier='rare'
    # for in-flight chains; this is the canonical path.
    if tool == "pkg":
        action = str(args.get("action") or "").strip().lower()
        backend = str(args.get("backend") or "auto").strip().lower()
        pid = _arg_with_synonyms(tool, "id", args).strip()
        query = _arg_with_synonyms(tool, "query", args).strip()
        if backend == "auto":
            # winget if id contains a dot AND no slash (Publisher.AppId
            # vs flatpak's org.foo.Bar/x86_64/stable). Bias toward
            # flatpak when only running on the Linux surface (no .exe
            # context). Default winget for unambiguous installs.
            ref = pid or query
            backend = "flatpak" if ("/" in ref or ref.startswith("org.")) else "winget"
        if backend not in ("winget", "flatpak"):
            return None
        # Route to the underlying verb name + delegate to its branch
        # below (no logic duplication).
        legacy = {
            "search":     f"{backend}_search",
            "list":       f"{backend}_list",
            "show":       f"{backend}_show",
            "install":    f"{backend}_install",
            "upgrade":    f"{backend}_upgrade",
            "uninstall":  f"{backend}_uninstall",
            "preflight":  "flatpak_preflight",  # winget has no analog
        }.get(action)
        if not legacy:
            return None
        # Re-shape args to match the legacy verb's expected keys.
        forwarded = dict(args)
        if action == "search" and query:
            forwarded["query"] = query
        if pid:
            forwarded["id"] = pid
        return _build_dispatch_cmd(legacy, forwarded)
    # ── Package management (Phase D.4 -- winget + flatpak surfaces) ──
    # Both shims emit JSON envelopes by default; agent-pipe surfaces
    # the JSON straight back to the gateway. WRITE verbs (install /
    # upgrade / uninstall) are firewall-gated.
    # ALL winget_* + flatpak_* verbs migrated to SSOT [verbs.*].cmd templates
    # (P3). The two upgrade verbs + flatpak_install took the HELPER-CONTRACT
    # path: the conditional logic lives in the helper, not dispatch --
    #   * mios-winget/mios-flatpak `upgrade`: no-arg / "all" / --all = all.
    #   * mios-flatpak `install <id> [scope]`: the helper's _resolve_scope owns
    #     the system/user -> --system/--user mapping + default-scope fallback
    #     (the old dispatch's scope branch + its dead --system/--user matches
    #     are gone; the scope enum is validated pre-dispatch, so only
    #     system/user/empty reach the helper, which resolves them).
    # open_url / mios_find / mios_apps / everything_search / flatpak_preflight
    # are migrated to SSOT [verbs.*].cmd templates (P3); they dispatch via the
    # catalog-template check at the top of this function (incl. the {arg?FLAG}
    # optional-flag form for --filter / -ext / the optional browser arg).
    # web_search migrated to the SSOT [verbs.web_search].cmd template (P3):
    # "mios-web-search -n {limit=5} --fanout {fanout=$MIOS_WEB_FANOUT:2} {query}".
    # The {fanout=$MIOS_WEB_FANOUT:2} ENV-default form preserves the old
    # os.environ.get("MIOS_WEB_FANOUT","2") fallback + the per-call `fanout`
    # override; the helper does the query fan-out (K concurrent sub-queries +
    # RRF merge) + grounds on REAL fetched data so the model never fabricates.
    # discord_send migrated to the SSOT [verbs.discord_send].cmd template (P3):
    # "mios-discord-send {content}{channel?--channel}". It stays a REAL dispatched
    # verb -> a real tool_call -> truthful result (the model can't narrate a fake
    # "posted to Discord"); the command literal + token/default-channel handling
    # live in the mios-discord-send helper, not here.
    # Discovery verbs knowledge_search / directory_lookup / fs_search migrated
    # to SSOT [verbs.*].cmd templates (P3); they dispatch via the catalog-
    # template check at the top of this function (optional-flag form for
    # --collection / --root / --ext / --kind / -ext / -path / -type, with the
    # int-default {top_k=5}/{limit=20}). The catalog path also resolves the
    # declared aliases (q/text, name/filename/term) the old raw args.get(...)
    # ignored. NB: fs_search.type enum is f/d/l but mios-locate only acts on
    # f/d and ignores any other -type, so the template emitting `-type l`
    # (which the old branch dropped) is harmless -- identical net behavior.
    # app_search / tool_search stay as code: their `if not query: return None`
    # guard is input validation the minimal template syntax can't express
    # (an empty query would otherwise dispatch a degenerate search).
    # System-category verbs (system_logs, process_list, container_status,
    # container_restart, service_status, service_restart) migrated to SSOT
    # [verbs.*].cmd templates (P3). They delegate to the mios-sysview /
    # mios-restart / mios-os-recipe helpers, which already OWN the journalctl /
    # ps / podman literals AND arg normalisation -- mios-sysview lowercases
    # level/sort + defaults lines/limit itself -- so the old dispatch-side
    # .lower()/int-coercion were redundant; the catalog path also resolves the
    # declared aliases (service/unit/container/from/window/n) the old raw
    # args.get(...) ignored.
    # NOTE: disk-usage is intentionally NOT a verb -- it is a [recipes.disk-usage]
    # recipe (command in mios.toml SSOT) reached via os_recipe(name="disk-usage").
    # no command literals baked in code; capabilities live
    # as native tools/skills/recipes.
    # ── PC-input verbs (Phase A.1 -- needed for DAG chains like
    # open_app -> focus_window -> pc_type -> pc_key Ctrl+S) ──
    # pc_type migrated to SSOT [verbs.pc_type].cmd ("mios-pc-control type {text}");
    # the catalog path also resolves its content/input aliases. pc_key (combo
    # "+" -> key-combo conditional) + pc_click (int coords + button enum-clamp)
    # stay as code.
    if tool == "pc_key":
        key = str(args.get("key", "")).strip()
        # Modifier combos -> key-combo; single keys -> key.
        if "+" in key:
            return f"mios-pc-control key-combo {shlex.quote(key)}"
        return f"mios-pc-control key {shlex.quote(key)}"
    if tool == "pc_click":
        x = int(args.get("x", 0))
        y = int(args.get("y", 0))
        button = str(args.get("button", "left")).lower()
        if button not in ("left", "right", "middle"):
            button = "left"
        return f"mios-pc-control click {x} {y} {button}"
    # ── Native text-editor verbs (replaces pc_type+pc_key save chain) ──
    # Bodies may contain shell metacharacters + multiline content;
    # stage them in /tmp via the broker-side mktemp + base64 so the
    # bash command line stays sane and broker output parsing isn't
    # tripped by literal newlines in the args.
    # text_view migrated to SSOT [verbs.text_view].cmd (P3):
    # "mios-text-edit view {path}{start?--start}{end?--end}". The optional-flag
    # form maps the old `is not None` checks exactly (start=0 still emits
    # --start 0) and is safer than the old int(start) -- an empty start string
    # crashed the old branch, the template emits nothing. Its base64-staging
    # siblings (text_create / text_insert / text_str_replace) stay as code.
    if tool == "text_create":
        path = shlex.quote(str(args.get("path", "")))
        body_b64 = base64.b64encode(
            str(args.get("content", "")).encode("utf-8")).decode()
        # Pipe content via stdin (-) -- avoids the argv length limit
        # and any quoting weirdness with newlines / embedded quotes.
        return (
            f"echo {shlex.quote(body_b64)} | base64 -d "
            f"| mios-text-edit create {path} --content -"
        )
    if tool == "text_str_replace":
        path = shlex.quote(str(args.get("path", "")))
        old_b64 = base64.b64encode(
            str(args.get("old", "")).encode("utf-8")).decode()
        new_b64 = base64.b64encode(
            str(args.get("new", "")).encode("utf-8")).decode()
        # Stage both blocks as files via two echo+base64 hops so
        # mios-text-edit's @-file args read them cleanly.
        return (
            "_old=$(mktemp); _new=$(mktemp); "
            f"echo {shlex.quote(old_b64)} | base64 -d > $_old; "
            f"echo {shlex.quote(new_b64)} | base64 -d > $_new; "
            f"mios-text-edit str_replace {path} --old @$_old --new @$_new; "
            "_rc=$?; rm -f $_old $_new; exit $_rc"
        )
    if tool == "text_insert":
        path = shlex.quote(str(args.get("path", "")))
        line = int(args.get("line", 0))
        body_b64 = base64.b64encode(
            str(args.get("content", "")).encode("utf-8")).decode()
        return (
            f"echo {shlex.quote(body_b64)} | base64 -d "
            f"| mios-text-edit insert {path} --line {line} --content -"
        )
    # ── Native PowerShell execution (Windows-side bash analogue) ──
    if tool == "powershell_run":
        script = str(args.get("script", ""))
        if not script.strip():
            return None
        script = normalize_container_exec(script)
        timeout = int(args.get("timeout", 30))
        work_dir = str(args.get("work_dir", "")).strip()
        elevate = bool(args.get("elevate", False))
        script_b64 = base64.b64encode(script.encode("utf-8")).decode()
        cmd = (
            f"echo {shlex.quote(script_b64)} | base64 -d "
            f"| mios-powershell --timeout {timeout} --json"
        )
        if work_dir:
            cmd += f" --work-dir {shlex.quote(work_dir)}"
        if elevate:
            cmd += " --elevate"
        cmd += " -"
        return cmd
    return None


async def _dispatch_bounded(
    tool: str, args: dict, *,
    session_id: Optional[str] = None,
) -> dict:
    """Bulkhead layer. web_search dispatches share a global concurrency
    semaphore so a council/DAG fan-out -- each call itself expanding into
    MIOS_WEB_FANOUT concurrent sub-queries -- can't stampede the local
    SearXNG; excess calls QUEUE here, with a small pre-acquire jitter to
    stagger simultaneous starts. All other verbs pass straight through.

    WS-A7: additionally, every dispatch is wrapped in the Tool-Manager conflict
    gate, which serializes verbs that declare a parallel_limit (per-verb
    concurrency cap) or a conflict_group (named mutual-exclusion set, e.g. the
    single-foreground-window UI verbs). The gate is a no-op for verbs that
    declare neither (the overwhelming majority), so this adds ~zero overhead to
    the common path while making stateful verbs fan-out-safe."""
    _t = re.sub(r"\(.*?\)\s*$", "", str(tool or "").strip()).strip().strip("`'\"")
    # WS-A7 conflict/parallel-limit serialization (outermost so it composes with
    # the web_search SearXNG bulkhead below). Degrade-open: unconstrained -> no-op.
    # WS-A8: a "dispatch" span times the verb under the current request trace.
    async with _trace_span("dispatch", verb=_t), _TOOL_CONFLICT.guard(_t):
        if _t == "web_search":
            if WEB_DISPATCH_JITTER_S > 0:
                await asyncio.sleep(random.uniform(0, WEB_DISPATCH_JITTER_S))
            async with _web_sem:
                return await _dispatch_mios_verb_inner(
                    tool, args, session_id=session_id)
        return await _dispatch_mios_verb_inner(tool, args, session_id=session_id)


async def dispatch_mios_verb(
    tool: str, args: dict, *,
    session_id: Optional[str] = None,
) -> dict:
    try:
        from mios_pipe.routing.chat import _replay_active, _replay_tool_queue, _record_active, _in_exec_tool_calls, _conv_key_var
        in_exec = _in_exec_tool_calls.get() if (_in_exec_tool_calls is not None and hasattr(_in_exec_tool_calls, "get")) else False
    except ImportError:
        in_exec = False
        _replay_active = None
        _record_active = None
        _conv_key_var = None

    tool_resolved = _resolve_verb_key(str(tool))

    if not in_exec and _replay_active is not None and _replay_active.get():
        q = _replay_tool_queue.get()
        if q:
            row = q.pop(0)
            meta = row.get("meta") or {}
            out = meta.get("output") or ""
            success = bool(meta.get("success", True))
            log.info("Replayed tool call (direct dispatch): %s -> %s", tool_resolved, str(out)[:200])
            return {"success": success, "output": out}
        else:
            log.warning("No recorded tool response in queue for direct dispatch: %s", tool_resolved)
            return {"success": False, "output": f"(error: no recorded tool response found in replay log for {tool_resolved})"}

    res = await _dispatch_mios_verb_live(tool, args, session_id=session_id)

    if not in_exec and _record_active is not None and _record_active.get():
        try:
            sess_id = session_id or (_conv_key_var.get() if (_conv_key_var is not None and hasattr(_conv_key_var, "get")) else "default")
            import uuid
            out_content = res.get("output") or res.get("result") or ""
            success = bool(res.get("success", True))
            
            row = {
                "id": f"session:tool:{uuid.uuid4().hex[:24]}",
                "kind": "tool_io",
                "owui_chat_id": sess_id,
                "meta": {
                    "tool": tool_resolved,
                    "args": args if isinstance(args, dict) else {},
                    "output": str(out_content),
                    "success": success
                }
            }
            if _db_create is not None:
                sql = _db_create("session", row, now_fields=("ts",), passport_sign=False)
                if _db_fire is not None and _db_post is not None:
                    _db_fire(_db_post(sql))
            log.info("Recorded tool call (direct dispatch) in session: %s", tool_resolved)
        except Exception as e:
            log.warning("Failed to record tool call (direct dispatch) in session: %s", e)

    return res

async def _dispatch_mios_verb_live(
    tool: str, args: dict, *,
    session_id: Optional[str] = None,
) -> dict:
    """Public dispatch entry point, wrapping the bulkhead with a conversation-
    scoped concurrent SINGLE-FLIGHT guard (anti-swarm-duplication; see
    _dispatch_inflight). Concurrent identical (verb, resolved-args) dispatches
    in the same conversation collapse to ONE broker execution + share the
    result, so a side effect never fires N times across a fan-out. In-flight
    only -> sequential repeats re-run fresh."""
    # P1 PA-Tool: a tool_call may arrive under a model_name alias (the model only ever
    # sees the alias). Resolve to the canonical verb key HERE -- the single dispatch
    # chokepoint -- so every downstream lookup (cmd template, permission, firewall, dedup,
    # HITL) keys off the real verb. Idempotent for plain keys.
    tool = _resolve_verb_key(str(tool))
    # Strict-schema safety : a strict OpenAI tool schema makes
    # optional params nullable+required, so a model emits `null` to "skip" one. Drop
    # null args here so the cmd-template default ({arg=default}) applies -- never pass
    # null through as a real value. No-op for non-strict callers (no nulls present).
    if isinstance(args, dict):
        args = {k: v for k, v in args.items() if v is not None}

    # T-037: Per-Agent Access Control check
    aname = (_dispatch_agent_var.get() or "").strip() if _dispatch_agent_var else ""
    if aname:
        acfg = _AGENT_REGISTRY.get(aname) or {} if _AGENT_REGISTRY else {}
        privilege_group = acfg.get("privilege_group") or "routine"
        
        vcfg = _VERB_CATALOG.get(tool) or {} if _VERB_CATALOG else {}
        verb_tier = vcfg.get("tier") or "routine"
        
        if verb_tier == "destructive" and privilege_group == "routine":
            verdict = "hitl"
            _acl_hitl_reason = f"ACL block: agent '{aname}' lacks privilege to run destructive verb '{tool}' without HITL approval."
            
            if _db_fire is not None and _db_post is not None and _db_create is not None:
                try:
                    _db_fire(_db_post(_db_create("event", {
                        "source": "agent-pipe",
                        "kind": "acl_decision",
                        "severity": "info",
                        "summary": f"ACL decision for {aname} calling {tool}: hitl",
                        "payload": {
                            "agent": aname,
                            "verb": tool,
                            "verdict": "hitl"
                        }
                    }, now_fields=("ts",))))
                except Exception:
                    pass

            try:
                _ah = _pending_hash(tool, args or {})
                _scope = _conv_key_var.get() or session_id
                _hitl_record_pending(tool, args or {}, _ah, _scope)
                if not isinstance(_proposal_var.get(), dict):
                    _proposal_var.set({"tool": tool, "args": args or {},
                                       "action_hash": _ah, "reason": _acl_hitl_reason})
            except Exception:
                pass
                
            return {"success": False, "output": "", "stderr": _acl_hitl_reason,
                    "exit_code": 126, "hitl_blocked": True}
        else:
            if _db_fire is not None and _db_post is not None and _db_create is not None:
                try:
                    _db_fire(_db_post(_db_create("event", {
                        "source": "agent-pipe",
                        "kind": "acl_decision",
                        "severity": "info",
                        "summary": f"ACL decision for {aname} calling {tool}: allow",
                        "payload": {
                            "agent": aname,
                            "verb": tool,
                            "verdict": "allow"
                        }
                    }, now_fields=("ts",))))
                except Exception:
                    pass

    # #62 HITL gate (off by default -> the helper early-returns, ~zero overhead).
    # In block mode a high-risk verb is REFUSED here (never executed) pending human
    # approval; audit mode logs + proceeds. Keys off the resolved verb above.
    _hitl_reason = _hitl_block_reason(tool, args)
    if _hitl_reason is None and _HITL_ARBITER_URL:
        _hitl_reason = await _hitl_arbiter_verdict(tool, args)  # #62 out-of-process arbiter
    if _hitl_reason is not None:
        # ASK-TO-RUN : record the blocked action as a PENDING
        # proposal + stash it so the final answer can OFFER "reply yes to run it" instead
        # of silently no-op'ing or fabricating. Keyed by action_hash (idempotent pending
        # slot, research §5); the user's next-turn approval (model-classified) re-dispatches
        # exactly this. Stash only the FIRST proposal of the turn. Degrade-open.
        try:
            _ah = _pending_hash(tool, args or {})   # NULL-free (pg TEXT-safe)
            # scope the pending by the STABLE conversation key (metadata.chat_id), not
            # the per-turn session row -- so next turn's approval can find it.
            _scope = _conv_key_var.get() or session_id
            _hitl_record_pending(tool, args or {}, _ah, _scope)
            if not isinstance(_proposal_var.get(), dict):
                _proposal_var.set({"tool": tool, "args": args or {},
                                   "action_hash": _ah, "reason": _hitl_reason})
        except Exception:  # noqa: BLE001
            pass
        return {"success": False, "output": "", "stderr": _hitl_reason,
                "exit_code": 126, "hitl_blocked": True}
    # Deterministic recency/breadth for web_search on a time-sensitive turn (see
    # _recency_ctx_var): FILL IN time_range/fanout the model omitted so a "what's
    # trending" turn always gets fresh, multi-facet coverage instead of an untimed
    # single-facet search. Only fills MISSING keys -> an explicit model value wins.
    if tool == "web_search" and isinstance(args, dict):
        _rc = _recency_ctx_var.get()
        if _rc:
            # DATE ANCHOR: when the turn is model-classified time-sensitive (recency ctx
            # set), fold the resolved current date (YYYY-MM) into the query so
            # "recent/this week/latest" resolves to the PRESENT, not a training-era year.
            # This is the single choke-point BOTH the prefetch AND the model's own in-loop
            # web_search calls pass through. Touches ONLY the query string (no keyword
            # branch); idempotent (skip if already present); SSOT-gated; degrade-open.
            if NATIVE_LOOP_DATE_IN_QUERY:
                try:
                    _q = str(args.get("query") or "").strip()
                    _ds = _current_date_str()
                    _ym = _ds[:7]
                    if _q and _ds not in _q and _ym not in _q:
                        args["query"] = _q + " " + _ym
                except Exception:  # noqa: BLE001 -- degrade-open
                    pass
            if not str(args.get("time_range") or "").strip() and _rc.get("time_range"):
                args["time_range"] = _rc["time_range"]
            try:
                if int(args.get("fanout") or 0) < int(_rc.get("fanout") or 0):
                    args["fanout"] = int(_rc["fanout"])
            except (TypeError, ValueError):
                args["fanout"] = int(_rc.get("fanout") or 0) or args.get("fanout")
    if not DISPATCH_DEDUP:
        return await _dispatch_bounded(tool, args, session_id=session_id)
    _a = args if isinstance(args, dict) else {}
    key = f"{_conv_key_var.get()}\x00{_action_hash(str(tool), _a)}"
    fut = _dispatch_inflight.get(key)
    if fut is not None:
        # An identical dispatch is already in flight in this conversation --
        # await it and reuse its result instead of firing the verb again.
        try:
            shared = await asyncio.shield(fut)
        except Exception:
            shared = None
        if isinstance(shared, dict):
            _emit_dispatch_dedup_event(str(tool), _a, session_id)
            dd = dict(shared)
            dd["deduped"] = True
            return dd
        # Shared result unusable -> fall through and run normally.
    loop = asyncio.get_running_loop()
    fut = loop.create_future()
    # Synchronous claim (no await between get + set) so a concurrent task
    # either sees no future and becomes the leader, or sees this one and
    # follows -- never two leaders for the same key.
    _dispatch_inflight[key] = fut
    try:
        res = await _dispatch_bounded(tool, args, session_id=session_id)
        if not fut.done():
            fut.set_result(res)
        return res
    except Exception as e:
        if not fut.done():
            fut.set_result({
                "success": False, "tool": tool,
                "args": _a, "output": "",
                "stderr": f"dispatch error: {e}", "exit_code": -1,
                "latency_ms": 0,
            })
        raise
    finally:
        _dispatch_inflight.pop(key, None)


def _emit_ro2_event(tool: str, args: dict, session_id: "Optional[str]",
                    verdict: "mios_ruleof2.RuleOfTwoVerdict", *, blocked: bool) -> None:
    """Audit a Rule-of-Two all-three decision -- one structured observability shape for
    both the audit-mode log line and the enforce-mode block. Carries the property
    breakdown (which of A/B/C, the count, the mode) so the decision is reconstructable.
    Best-effort / degrade-open: an absent DB writer or a write failure is swallowed."""
    try:
        _db_fire(_db_post(_db_create("event", {
            "source": "agent-pipe",
            "kind": "rule_of_two_block" if blocked else "rule_of_two_audit",
            "severity": "high" if blocked else "warn",
            "summary": (f"rule-of-two {'BLOCK' if blocked else 'audit'}: {tool} holds "
                        f"all 3 (untrusted-input + sensitive-access + state-change)"),
            "payload": {
                "tool": tool, "args": args,
                "rule_of_two": verdict.to_dict(),
                "agent": (_dispatch_agent_var.get() if _dispatch_agent_var else "") or "",
            },
        }, now_fields=("ts",))))
    except Exception:  # noqa: BLE001 -- audit is best-effort; never breaks dispatch
        pass


async def _rule_of_two_gate(tool: str, args: dict, *,
                            session_id: "Optional[str]" = None) -> "Optional[dict]":
    """The Rule-of-Two architectural gate (F2/T-033, CaMeL-class), composed at the
    dispatch chokepoint. Returns a block_result dict to REFUSE the dispatch (enforce
    mode, a confirmed all-three kill-chain not yet human-approved) or None to PROCEED.

    Composes EXISTING signals -- it re-derives nothing: A (untrusted-input) is the
    provenance-taint chain (``_session_is_tainted``); B (sensitive-access) + C
    (state-change) are derived from the SSOT verb metadata INSIDE the pure
    ``mios_ruleof2.evaluate`` (the [verbs.*].sensitive flag + the permission tier).
    Placed AFTER the existing taint/HITL gates -- each of those returns early on its
    own block -- so Rule-of-Two only ADDS a refusal (the stricter gate wins).

      off     -> not consulted (the call-site guards on the mode -> byte-identical).
      audit   -> structured non-blocking audit line, then proceed (observe before enforce).
      enforce -> route the all-three posture through the SINGLE ``mios_hitl.decide``
                 resolver; an explicit same-turn ask-to-run approval downgrades the
                 block so the human who approved THIS exact action can run it.

    Degrade-open: ANY error -> None (fall back to the existing firewall/HITL behaviour;
    never crash, never newly block-everything). A CONFIRMED all-three under enforce
    gates (fail toward safety)."""
    try:
        mode = mios_ruleof2.normalize_mode(RULE_OF_TWO_MODE)
        if mode == mios_ruleof2.MODE_OFF:
            return None
        vmeta = _VERB_CATALOG.get(tool) or {}
        # A: the EXISTING provenance-taint signal (mios_firewall owns it; no re-derive).
        a_tainted = False
        if session_id:
            a_tainted, _chain = await _session_is_tainted(session_id)
        verdict = mios_ruleof2.evaluate(
            session_tainted=a_tainted,
            permission_tier=vmeta.get("permission"),
            sensitive=vmeta.get("sensitive"),
            mode=mode)
        if not verdict.all_three:
            return None  # <=2 of {A,B,C} -> the invariant holds -> proceed
        if mode == mios_ruleof2.MODE_AUDIT:
            _emit_ro2_event(tool, args, session_id, verdict, blocked=False)
            return None  # non-blocking: observe before enforce
        # enforce: a 3-property chain. Resolve via the single HITL verdict so it
        # composes with the other gates' approval semantics; an explicit same-turn
        # approval (ask-to-run set this action's hash) downgrades the block.
        approved = False
        try:
            if _hitl_approved_var is not None:
                _appr = _hitl_approved_var.get()
                approved = bool(_appr) and _appr == _pending_hash(tool, args or {})
        except Exception:  # noqa: BLE001
            approved = False
        if mios_hitl.decide(ro2_block=True, approved=approved) != mios_hitl.BLOCK:
            return None  # approved -> downgraded -> proceed
        # fail-safe BLOCK: record a pending_action (approvable out-of-band via
        # /v1/hitl/approve) + refuse before the broker, in the hitl_pending shape the
        # agent tool-loop already handles (a failure + a human-readable next step).
        _ah = _pending_hash(tool, args or {})
        try:
            _hitl_record_pending(tool, args or {}, _ah, session_id)
        except Exception:  # noqa: BLE001 -- recording is best-effort; the block still holds
            pass
        _emit_ro2_event(tool, args, session_id, verdict, blocked=True)
        _res = mios_hitl.block_result(tool, args, _ah)
        _res["rule_of_two_blocked"] = True
        return _res
    except Exception:  # noqa: BLE001 -- degrade-open: any error -> existing gate behaviour
        return None


def _emit_quarantine_event(tool: str, args: dict, session_id: "Optional[str]",
                           verdict: "mios_quarantine.QuarantineVerdict", *,
                           blocked: bool) -> None:
    """Audit a CaMeL quarantine decision (the boundary BIT: tainted AND privileged) --
    one structured observability shape for both the audit-mode log line and the
    enforce-mode block. Carries the axis breakdown (A + whether B / C, the mode) so the
    decision is reconstructable. Best-effort / degrade-open: an absent DB writer or a
    write failure is swallowed."""
    try:
        _db_fire(_db_post(_db_create("event", {
            "source": "agent-pipe",
            "kind": "quarantine_block" if blocked else "quarantine_audit",
            "severity": "high" if blocked else "warn",
            "summary": (f"quarantine {'BLOCK' if blocked else 'audit'}: {tool} -- "
                        f"untrusted content drives a privileged "
                        f"(sensitive-read OR state-change) action"),
            "payload": {
                "tool": tool, "args": args,
                "quarantine": verdict.to_dict(),
                "agent": (_dispatch_agent_var.get() if _dispatch_agent_var else "") or "",
            },
        }, now_fields=("ts",))))
    except Exception:  # noqa: BLE001 -- audit is best-effort; never breaks dispatch
        pass


async def _quarantine_gate(tool: str, args: dict, *,
                           session_id: "Optional[str]" = None) -> "Optional[dict]":
    """The CaMeL dual-context QUARANTINE gate (F2, the deeper half of T-033), composed
    at the dispatch chokepoint AFTER the Rule-of-Two gate so it only ADDS a refusal
    (stricter-wins). Returns a block_result dict to REFUSE the dispatch (enforce mode, a
    confirmed tainted+privileged action not yet human-approved) or None to PROCEED.

    Composes EXISTING signals -- it re-derives nothing: A (untrusted-input) is the
    provenance-taint chain (``_session_is_tainted``); B (sensitive-access) + C
    (state-change) come from the SSOT verb metadata INSIDE the pure
    ``mios_quarantine.evaluate`` (the [verbs.*].sensitive flag + the permission tier).
    The boundary BITES on tainted AND (sensitive OR state-change) -- the STRICTER
    superset of Rule-of-Two's all-three, for when you want full CaMeL isolation.

      off     -> not consulted (the call-site guards on the mode -> byte-identical).
      audit   -> structured non-blocking audit line, then proceed (observe before enforce).
      enforce -> route the bite posture through the SINGLE ``mios_hitl.decide`` resolver
                 (quarantine_block=True); an explicit same-turn ask-to-run approval
                 downgrades the block so the human who approved THIS exact action runs it.

    SOUNDNESS: this sits at the SAME single chokepoint as the firewall / HITL /
    Rule-of-Two gates and only ADDS a refusal -- there is no second action path that
    bypasses it, and stricter-wins composition means enabling it can only make the
    posture stricter, never weaker.

    Degrade-open: ANY error -> None (fall back to the existing firewall/HITL/Rule-of-Two
    behaviour; never crash, never newly block-everything). A CONFIRMED bite under enforce
    gates (fail toward safety)."""
    try:
        mode = mios_quarantine.normalize_mode(QUARANTINE_MODE)
        if mode == mios_quarantine.MODE_OFF:
            return None
        vmeta = _VERB_CATALOG.get(tool) or {}
        # A: the EXISTING provenance-taint signal (mios_firewall owns it; no re-derive).
        a_tainted = False
        if session_id:
            a_tainted, _chain = await _session_is_tainted(session_id)
            # T-033: Also check if tainted content is in the scratchpad (current context)
            if not a_tainted and mios_scratchpad.SQLITE_VEC_ENABLE:
                scratchpad_dir = os.environ.get("MIOS_CONV_MEMORY_SCRATCHPAD_DIR", "/tmp")
                if mios_scratchpad.has_tainted(session_id, scratchpad_dir):
                    a_tainted = True
        
        # T-033: Determine if the verb is privileged/side-effecting:
        # It reads sensitive data (sensitive=True) OR changes state (is_state_change=True)
        # OR is open_url to non-allowlisted domain.
        sensitive = bool(vmeta.get("sensitive"))
        is_side_effecting = mios_ruleof2.is_state_change(vmeta.get("permission"))
        if tool == "open_url" and _is_external_url(str((args or {}).get("url", ""))):
            is_side_effecting = True
            
        verdict = mios_quarantine.evaluate(
            session_tainted=a_tainted,
            permission_tier="write" if is_side_effecting else vmeta.get("permission"),
            sensitive=sensitive,
            mode=mode)
        if not verdict.bites:
            return None  # untainted OR non-privileged -> nothing to quarantine -> proceed
        if mode == mios_quarantine.MODE_AUDIT:
            _emit_quarantine_event(tool, args, session_id, verdict, blocked=False)
            return None  # non-blocking: observe before enforce
        # enforce: untrusted content drives a privileged action. Resolve via the single
        # HITL verdict so it composes with the other gates' approval semantics; an
        # explicit same-turn approval (ask-to-run set this action's hash) downgrades it.
        approved = False
        try:
            if _hitl_approved_var is not None:
                _appr = _hitl_approved_var.get()
                approved = bool(_appr) and _appr == _pending_hash(tool, args or {})
        except Exception:  # noqa: BLE001
            approved = False
        if mios_hitl.decide(quarantine_block=True, approved=approved) != mios_hitl.BLOCK:
            return None  # approved -> downgraded -> proceed
        # fail-safe BLOCK: record a pending_action (approvable out-of-band via
        # /v1/hitl/approve) + refuse before the broker, in the hitl_pending shape the
        # agent tool-loop already handles (a failure + a human-readable next step).
        _ah = _pending_hash(tool, args or {})
        try:
            _hitl_record_pending(tool, args or {}, _ah, session_id)
        except Exception:  # noqa: BLE001 -- recording is best-effort; the block still holds
            pass
        _emit_quarantine_event(tool, args, session_id, verdict, blocked=True)
        _res = mios_hitl.block_result(tool, args, _ah)
        _res["quarantine_blocked"] = True
        return _res
    except Exception:  # noqa: BLE001 -- degrade-open: any error -> existing gate behaviour
        return None


async def _dispatch_mios_verb_inner(
    tool: str, args: dict, *,
    session_id: Optional[str] = None,
) -> dict:
    res = await _dispatch_mios_verb_inner_raw(tool, args, session_id=session_id)
    # T-033: Log: event(kind="firewall_decision", verdict=allow|block|hitl)
    try:
        verdict = "allow"
        if res.get("firewall_blocked") or "firewall_block" in str(res.get("stderr") or ""):
            verdict = "block"
        elif res.get("hitl_blocked") or res.get("quarantine_blocked") or "hitl" in str(res.get("stderr") or "") or "quarantine" in str(res.get("stderr") or ""):
            verdict = "hitl"
        elif "quota_block" in str(res.get("stderr") or "") or "pdp_block" in str(res.get("stderr") or ""):
            verdict = "block"
            
        if _db_fire is not None and _db_post is not None and _db_create is not None:
            _db_fire(_db_post(_db_create("event", {
                "source": "agent-pipe",
                "kind": "firewall_decision",
                "severity": "high" if verdict != "allow" else "info",
                "summary": f"firewall decision: {tool} -> {verdict}",
                "payload": {
                    "tool": tool,
                    "args": args,
                    "verdict": verdict,
                    "session_id": session_id,
                }
            }, now_fields=("ts",))))
    except Exception:
        pass
    return res


async def _dispatch_mios_verb_inner_raw(
    tool: str, args: dict, *,
    session_id: Optional[str] = None,
) -> dict:
    """Run a single MiOS verb via the launcher broker (unix socket
    /run/mios-launcher/launcher.sock). Returns a structured dict:
    {success, tool, args, output, stderr, exit_code, latency_ms,
     tainted, taint_reason}. Uses the broker's CAPTURE_JSON: protocol
    so stdout/stderr split cleanly.

    Phase A.3: Semantic Firewall stub -- when a high-privilege verb
    is dispatched and the session has ANY upstream tainted tool_call,
    the dispatch is REFUSED (not even sent to the broker) and an
    event row is emitted (kind=firewall_block, severity=high).
    Taint of the dispatched verb itself is computed from
    _classify_verb_taint AND inherited from session state."""
    # Normalise the verb name: capable models (qwen3.5:4b) format tool
    # names as function calls -> "system_status()", which then misses
    # the catalog. Strip a trailing "(...)" and
    # surrounding whitespace/quotes so the catalog lookup is robust to
    # however a model phrased the name.
    tool = re.sub(r"\(.*?\)\s*$", "", str(tool or "").strip()).strip().strip("`'\"")
    if _letta_dispatch_handler:
        _res = await _letta_dispatch_handler(tool, args, session_id)
        if _res is not None:
            return _res
    # ── WS-A9 dispatch-time PDP capability gate (before the firewall/HITL/enum
    # checks): re-evaluate the caller's per-agent + per-user policy at the single
    # chokepoint so a verb absent from the filtered surface can't still run. DENY
    # -> refuse deterministically + emit a pdp_block audit event. Degrade-open. ──
    _pdp_deny = _dispatch_pdp_reason(tool)
    if _pdp_deny is not None:
        _db_fire(_db_post(_db_create("event", {
            "source": "agent-pipe",
            "kind": "pdp_block",
            "severity": "high",
            "summary": _pdp_deny[:200],
            "payload": {"tool": tool, "args": args,
                        "agent": _dispatch_agent_var.get() or ""},
        }, now_fields=("ts",))))
        return {
            "success": False, "tool": tool, "args": args, "output": "",
            "stderr": f"pdp_block: {_pdp_deny}",
            "exit_code": 126, "latency_ms": 0,
            "pdp_blocked": True,
        }
    # ── WS-6 per-user quota / rate-limit gate (after PDP). INERT unless the
    # caller's [users.*] config sets rpm_limit/daily_budget; degrade-open. ──
    _q_deny = _dispatch_quota_reason(tool)
    if _q_deny is not None:
        _db_fire(_db_post(_db_create("event", {
            "source": "agent-pipe",
            "kind": "quota_block",
            "severity": "warn",
            "summary": _q_deny[:200],
            "payload": {"tool": tool, "user": (_match_user_cfg()[0] or "")},
        }, now_fields=("ts",))))
        return {
            "success": False, "tool": tool, "args": args, "output": "",
            "stderr": f"quota_block: {_q_deny}",
            "exit_code": 429, "latency_ms": 0,
            "quota_blocked": True,
        }
    # ── Firewall pre-check for high-privilege verbs ──
    if tool in _HIGH_PRIVILEGE_VERBS and session_id:
        is_tainted, chain = await _session_is_tainted(session_id)
        if is_tainted:
            _db_fire(_db_post(_db_create("event", {
                "source": "agent-pipe",
                "kind": "firewall_block",
                "severity": "high",
                "summary": f"refused {tool} (tainted session)",
                "payload": {
                    "tool": tool, "args": args,
                    "taint_chain": chain,
                },
            }, now_fields=("ts",))))
            return {
                "success": False, "tool": tool, "args": args,
                "output": "",
                "stderr": f"firewall_block: {tool} refused -- "
                          f"upstream taint: {chain}",
                "exit_code": -1, "latency_ms": 0,
                "tainted": True,
                "taint_reason": f"firewall_block:{chain[:200]}",
            }

    # ── [ai] RISK-TIER HITL gate at the INNER universal chokepoint ──
    # The public dispatch_mios_verb entry runs this same [ai] gate, but every DIRECT
    # _dispatch_mios_verb_inner caller (e.g. the computer-use perceive->act loop)
    # reaches the broker WITHOUT passing it -- a silent bypass of the blocking gate.
    # Re-applying the SAME reconciled decision here (mios_hitl.decide, via
    # _hitl_block_reason + the out-of-process arbiter) makes the inner the single
    # coherent HITL enforcement point: no caller can dispatch a tier-gated verb
    # un-blocked. Idempotent on the public path (already decided there, incl. the
    # ask-to-run approval bypass); fail-safe -- refuse on a block reason.
    _ai_hitl = _hitl_block_reason(tool, args)
    if _ai_hitl is None and _HITL_ARBITER_URL:
        _ai_hitl = await _hitl_arbiter_verdict(tool, args)
    if _ai_hitl is not None:
        return {
            "success": False, "tool": tool, "args": args, "output": "",
            "stderr": _ai_hitl, "exit_code": 126, "latency_ms": 0,
            "hitl_blocked": True,
        }

    # ── WS-6 runtime HITL approval gate ([hitl] verb-scope; after the taint
    # firewall, before exec). log mode -> emits + proceeds (None); gate mode ->
    # blocks unapproved scoped verbs with a hitl_pending result. Degrade-open: a gate
    # error proceeds. Shares the mios_hitl.decide resolver with the [ai] gate above.
    _hitl_block = await _hitl_gate(tool, args, session_id)
    if _hitl_block is not None:
        return _hitl_block

    # ── F2/T-033 Rule-of-Two architectural gate (CaMeL-class; after the taint/HITL
    # gates so it only ADDS a refusal -- stricter-wins). The DETERMINISTIC kill-chain
    # invariant: a dispatch may hold at most TWO of {untrusted-input (the provenance-
    # taint chain), sensitive-access (SSOT [verbs.*].sensitive), state-change (SSOT
    # permission tier)} without human review. INERT unless [security].rule_of_two_mode
    # is audit/enforce: the mode guard keeps default-off BYTE-IDENTICAL (the evaluator
    # is not consulted, no taint read, no event). Degrade-open inside the gate. ──
    if RULE_OF_TWO_MODE != mios_ruleof2.MODE_OFF:
        _ro2_block = await _rule_of_two_gate(tool, args, session_id=session_id)
        if _ro2_block is not None:
            return _ro2_block

    # ── F2 CaMeL dual-context QUARANTINE gate (the deeper half of T-033; after the
    # taint/HITL/Rule-of-Two gates so it only ADDS a refusal -- stricter-wins). The
    # CaMeL boundary: untrusted/attacker-controllable content (a TAINTED session) must
    # not autonomously drive a PRIVILEGED action -- one that READS sensitive data (SSOT
    # [verbs.*].sensitive) OR CHANGES state (SSOT permission tier). Where Rule-of-Two
    # gates only the all-three chain, quarantine-enforce ADDITIONALLY gates the
    # tainted + (sensitive OR state-change) case -- the STRICTER posture for full CaMeL
    # isolation. INERT unless [security].quarantine_mode is audit/enforce: the mode guard
    # keeps default-off BYTE-IDENTICAL (the evaluator is not consulted, no taint read, no
    # event). Same single chokepoint -> no bypass. Degrade-open inside the gate. ──
    if QUARANTINE_MODE != mios_quarantine.MODE_OFF:
        _q_block = await _quarantine_gate(tool, args, session_id=session_id)
        if _q_block is not None:
            return _q_block

    # Tool-Manager enum validation (ref AIOS C 3.7): reject out-of-enum
    # args BEFORE the broker. The structured error feeds the planner's
    # reflection pass, which re-issues the step with a valid value.
    _enum_err = _validate_enum_args(tool, args)
    if _enum_err is not None:
        return {
            "success": False, "tool": tool, "args": args,
            "output": "", "stderr": _enum_err,
            "exit_code": -1, "latency_ms": 0,
        }
    cmd = _build_dispatch_cmd(tool, args)
    if cmd is None:
        # Distinguish "no such verb" from "verb known but args rejected"
        # so the planner can see WHICH layer failed + re-plan. Operator-
        # flagged "launch_app(path=...) -> unknown verb"
        # error was misleading -- the verb existed but the dispatcher
        # rejected because (a) `name` wasn't populated via any alias
        # (now also accepts `path`), or (b) the proposed target name
        # equals a known verb (defensive check).
        if tool in _VERB_CATALOG:
            v = _VERB_CATALOG[tool]
            required = [n for n, c in (v.get("params") or {}).items()
                        if isinstance(c, dict) and "default" not in c]
            stderr = (
                f"verb {tool!r} known but dispatch rejected: "
                f"args={list(args.keys())} required={required} "
                f"(check arg names; paths get auto-basenamed; "
                f"name equal to a known verb is refused as a defensive "
                f"check against planner emitting the probe tool name as "
                f"the launch target)"
            )
        else:
            stderr = (
                f"unknown verb {tool!r} (not in [verbs.*] catalog "
                f"of mios.toml; visible verbs: "
                f"{sorted(_VERB_CATALOG.keys())[:10]}...)"
            )
        return {
            "success": False, "tool": tool, "args": args,
            "output": "", "stderr": stderr,
            "exit_code": -1, "latency_ms": 0,
        }
    if not os.path.exists(LAUNCHER_SOCK):
        return {
            "success": False, "tool": tool, "args": args,
            "output": "", "stderr": f"broker socket missing at {LAUNCHER_SOCK}",
            "exit_code": -1, "latency_ms": 0,
        }
    # ── WS-A13 risk-tier sandbox: resolve this verb's confinement profile (recorded
    # on the result for audit) + OPT-IN wrap the broker cmd through mios-sandbox-exec.
    # Default-off / opt-in-per-verb => cmd is unchanged unless a verb declares
    # [verbs.*].sandbox_profile AND MIOS_SANDBOX_ENFORCE is on (degrade-open: any
    # resolve error falls back to the strictest profile + the unwrapped cmd).
    try:
        _sbx_profile = _dispatch_sandbox_profile(tool)
        cmd, _sbx_ws = _sandbox_wrap_cmd(tool, cmd, _sbx_profile, session_id=session_id)
    except Exception:  # noqa: BLE001
        _sbx_profile, _sbx_ws = mios_sandbox.resolve_profile(""), None
    t0 = time.time()
    try:
        def _broker_io() -> str:
            s = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
            # 60s broker timeout: flatpak cold-launches (epiphany / chromedev
            # via WSLg compositor + portal handshake) routinely take 25-45s
            # to first paint. Prior 20s cap fired Broken Pipe on the broker
            # side, surfaced as "broker: empty response" to the agent.
            # Operator-flagged. Tunable via env.
            s.settimeout(float(os.environ.get("MIOS_BROKER_TIMEOUT_S", "60")))
            chunks: list[bytes] = []
            try:
                s.connect(LAUNCHER_SOCK)
                s.sendall(("CAPTURE_JSON: " + cmd + "\n").encode())
                while True:
                    buf = s.recv(65536)
                    if not buf:
                        break
                    chunks.append(buf)
            except _socket.timeout:
                pass
            finally:
                s.close()
            return b"".join(chunks).decode("utf-8", errors="replace").strip()
        # Run the BLOCKING broker socket I/O in a worker thread so the event loop
        # stays free to serve RE-ENTRANT callbacks during the dispatch. Verbs like
        # tool_search / a2a_delegate / handoff shell to a thin client that calls
        # BACK into this same agent-pipe over HTTP; with a blocking socket here the
        # loop was stalled and those callbacks deadlocked ("agent-pipe unreachable:
        # timed out"). to_thread also lets independent verb dispatches overlap.
        raw = await asyncio.to_thread(_broker_io)
        try:
            j = _loads_lenient(raw) if raw else {}
        except json.JSONDecodeError:
            j = {}
        latency_ms = int((time.time() - t0) * 1000)
        if not j:
            return {
                "success": False, "tool": tool, "args": args,
                "output": "", "stderr": raw or "broker: empty response",
                "exit_code": -1, "latency_ms": latency_ms,
            }
        exit_code = int(j.get("exit_code", -1))
        # Compute taint for this verb's OWN execution (e.g. open_url
        # to an external host marks the result as tainted).
        v_tainted, v_reason = _classify_verb_taint(tool, args)
        _out = (j.get("stdout") or "")[:6000]
        _err = (j.get("stderr") or "")[:2000]
        # Launch verbs emit noisy resolve/fallback PROGRESS to stderr (wine
        # attempts, per-candidate misses, "trying Windows") even when the launch
        # ULTIMATELY SUCCEEDS via a fallback (e.g. native interop). The small
        # agent model misread that progress as failure and NARRATED "couldn't
        # find it" though the window opened ("LIAR"). On a
        # SUCCESSFUL launch surface the clean stdout verdict and demote the
        # progress noise so the agent reports the success it actually achieved.
        if tool in _LAUNCH_VERBS and exit_code == 0:
            if not _out.strip():
                _tgt = args.get("name") or args.get("app") or args.get("url") or tool
                _out = f"Launched {_tgt} (verified)."
            _err = ""
        return {
            "success": exit_code == 0,
            "tool": tool, "args": args,
            "output": _out,
            "stderr": _err,
            "exit_code": exit_code,
            "latency_ms": latency_ms,
            "tainted": v_tainted,
            "taint_reason": v_reason,
            "sandbox": _sbx_profile.to_dict(),  # WS-A13 resolved confinement posture
        }
    except OSError as e:
        return {
            "success": False, "tool": tool, "args": args,
            "output": "", "stderr": f"broker: {e}",
            "exit_code": -1,
            "latency_ms": int((time.time() - t0) * 1000),
            "tainted": False,
            "taint_reason": "",
        }


# -- @app -> APIRouter migration (refactor R13 batch 3: single-verb dispatch) -----
# The single-verb dispatch endpoint (/v1/dispatch) -- the HTTP front of THIS module's
# dispatch_mios_verb chokepoint (mios-mcp-server's tools/call lands here) -- moved off
# server.py's @app onto this co-located dispatch_router (the same routes->APIRouter
# pattern the /a2a wave established). server.py imports dispatch_router + dispatch_verb
# (re-imported there so its importable `provided` surface is unchanged) and mounts the
# router via app.include_router(dispatch_router); the served path/method is identical
# (the live-app route gate proves it). The body moved VERBATIM and calls the
# module-resident dispatch_mios_verb DIRECTLY (no sys.modules hop). One-way boundary:
# this module never imports server. APIRouter()/method decorators are structural.
dispatch_router = APIRouter()


@dispatch_router.post("/v1/dispatch")
async def dispatch_verb(body: dict) -> JSONResponse:
    """Dispatch a single MiOS verb. Body: {tool, args, session_id?}.
    Returns the same {success, output, stderr, exit_code, latency_ms,
    tainted, taint_reason} envelope as the DAG executor. Used by
    mios-mcp-server for MCP `tools/call`."""
    tool = str(body.get("tool", "")).strip()
    args = body.get("args") or {}
    if not isinstance(args, dict):
        args = {}
    session_id = body.get("session_id")
    result = await dispatch_mios_verb(tool, args, session_id=session_id)
    # A9/F2 security: persist the executed verb as a session-linked tool_call row so
    # same-session provenance-taint (_session_is_tainted) sees verbs run through this
    # HTTP front. The chat + DAG paths already record their executions; this closes
    # the dispatch-path taint-blind hole. Best-effort -- never blocks the reply.
    _record_dispatch_tool_call_row(tool, result, session_id)
    return JSONResponse(result)
