# AI-hint: OS-CONTROL fast-path responder + window enum/verify helpers extracted VERBATIM from server.py (refactor R9 wave). The deterministic one-verb action path: _respond_os_control (fire ONE app/window/URL verb through the broker, snapshot windows BEFORE, fire, snapshot AFTER, diff to learn exactly what opened/closed, VERIFY the action actually took effect, RE-ATTEMPT a write or POLL a launch until the window renders or the deadline passes, auto-center a launched window, remember the last-opened window for a follow-up standalone type, then write a SHORT generative anti-fabrication reply that never claims a success the verb output does not show). Owns the cross-desktop window enumeration (_load_oscontrol_endpoints SSOT discovery, _remote_enumerate_windows_one, _enumerate_windows with retry-on-empty), the snapshot diff (_window_key, _window_diff, _win_titles, _window_delta_text, _index_window_event RAG indexing), the launch-verification verdict (_os_target, _win_hay, _verify_os_action anti-fabrication, _launch_proc_patterns, _proc_present global pgrep), window centering (_center_windows) and the per-conversation last-opened-window memory (_LAST_OPENED_WINDOW, _record_last_opened_window). Moved byte-identically -- NO consolidation, every comment/heuristic/guard preserved (LIVE hot path). Siblings (_sse_*, dispatch_mios_verb, polish_response, _store_knowledge, loads_lenient, DCI critic) are imported directly; every server-side dep (the OS_CONTROL_* config scalars, the verb sets, the conv-key ContextVar, _get_client, _scratchpad_note, the _db_* helpers, _inline_satisfaction_check, _strip_think_tags) is dependency-INJECTED via configure() (one-way boundary -- this module NEVER imports server). server.py re-imports every moved name under its original alias (surface-parity zero-diff).
# AI-related: ./server.py, ./mios_config.py, ./mios_sse.py, ./mios_dispatch.py, ./mios_verity.py, ./mios_knowledge.py, ./mios_dci.py, ./mios_jsonsalvage.py, ./test_mios_oscontrol.py
# AI-functions: _load_oscontrol_endpoints, _remote_enumerate_windows_one, _enumerate_windows, _window_key, _window_diff, _win_titles, _window_delta_text, _index_window_event, _os_target, _win_hay, _center_windows, _launch_proc_patterns, _proc_present, _verify_os_action, _record_last_opened_window, _respond_os_control, _render_os_control_verbs, configure
"""OS-control fast-path responder + window enum/verify helpers (refactor R9).

Extracted VERBATIM from ``server.py`` -- the deterministic one-verb OS-control
action path (``_respond_os_control``) and the window-enumeration / before-after
diff / launch-verification / anti-fabrication-verdict helpers it owns. Every
function is moved byte-identically (LIVE hot path: computer-use / launch /
window-op); their consolidation is NOT in scope. ``server.py`` re-imports every
name under its original alias so the module's public surface is byte-identical.

Sibling functions (the ``_sse_*`` emitters, the broker ``dispatch_mios_verb``,
``polish_response``, ``_store_knowledge``, ``loads_lenient``, the DCI critic) are
imported directly; every server-side symbol the path touches (the ``OS_CONTROL_*``
config scalars, the ``_OS_CONTROL_ACTION_VERBS`` / ``_LAUNCH_VERBS`` verb sets, the
conv-key ContextVar, ``_get_client``, ``_scratchpad_note``, the ``_db_*`` helpers,
``_inline_satisfaction_check``, ``_strip_think_tags``) is injected via
:func:`configure` (one-way boundary -- this module never imports ``server``).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from typing import Any, AsyncGenerator, Optional

from fastapi.responses import JSONResponse, StreamingResponse

from mios_sse import _sse_status_phase, _sse_status, _sse_chunk, _sse_done
from mios_jsonsalvage import loads_lenient as _loads_lenient
from mios_dci import DCI_ENABLED, critic_then_maybe_flow
from mios_dispatch import dispatch_mios_verb
from mios_verity import polish_response
from mios_knowledge import _store_knowledge

log = logging.getLogger("mios-agent-pipe")


# -- Dependency-injection seam --------------------------------------
# The OS-control fast-path reads server.py's OS_CONTROL_* config scalars + the
# verb sets, the per-conversation conv-key ContextVar, and calls back into the
# broker-adjacent helpers (_get_client, _scratchpad_note, the _db_* row helpers,
# _inline_satisfaction_check, _strip_think_tags). server.py calls configure()
# with those AFTER every one is defined (one-way boundary: this module never
# imports server). The placeholders below carry the documented defaults so a
# standalone ``import mios_oscontrol`` still succeeds; every consumer is
# async/runtime so nothing fires before configure() runs.

# config scalars (server SSOT/env-derived; injected at import-completion)
OS_CONTROL_LAUNCH_VERIFY_S = 16.0
OS_CONTROL_LAUNCH_POLL_S = 1.5
OS_CONTROL_RETRY_ATTEMPTS = 2
OS_CONTROL_RETRY_SETTLE_S = 1.2
OS_CONTROL_REPLY_MAX_TOKENS = 200
OS_CONTROL_ENUM_RETRY = 2
OS_CONTROL_ENUM_TIMEOUT_S = 6.0
OS_CONTROL_ENUM_RETRY_SETTLE_S = 0.7
_OS_CONTROL_ACTION_VERBS: frozenset = frozenset()
_LAUNCH_VERBS: frozenset = frozenset()

# server-side refs/helpers (injected)
_conv_key_var = None
_get_client = None
_scratchpad_note = None
_db_fire = None
_db_post = None
_db_create = None
_inline_satisfaction_check = None
_strip_think_tags = None

# fast-path verb set + verb catalog (server SSOT; injected). Read by
# _render_os_control_verbs to build the per-verb refine-prompt lines. Server.py
# CALLS that render at import time, so it injects these two BEFORE that call (the
# import-time stage of its two-stage configure); the empty placeholders here let a
# standalone import + render succeed (returns "" when no verbs are registered).
_FASTPATH_VERBS: frozenset = frozenset()
_VERB_CATALOG: dict = {}


def configure(*, os_control_launch_verify_s=None, os_control_launch_poll_s=None,
              os_control_retry_attempts=None, os_control_retry_settle_s=None,
              os_control_reply_max_tokens=None, os_control_enum_retry=None,
              os_control_enum_timeout_s=None, os_control_enum_retry_settle_s=None,
              os_control_action_verbs=None, launch_verbs=None,
              conv_key_var=None, get_client=None, scratchpad_note=None,
              db_fire=None, db_post=None, db_create=None,
              inline_satisfaction_check=None, strip_think_tags=None,
              fastpath_verbs=None, verb_catalog=None) -> None:
    """Inject server.py's OS-control config scalars, the verb sets, the conv-key
    ContextVar and the runtime helpers the fast-path calls back into.

    Callable more than once with a partial set (mios_sched-style): server.py
    injects ``fastpath_verbs`` / ``verb_catalog`` EARLY (the import-time stage --
    ``_render_os_control_verbs`` is called at server import) and the remaining
    runtime deps LATE, once they are all defined."""
    g = globals()
    if os_control_launch_verify_s is not None:
        g["OS_CONTROL_LAUNCH_VERIFY_S"] = os_control_launch_verify_s
    if os_control_launch_poll_s is not None:
        g["OS_CONTROL_LAUNCH_POLL_S"] = os_control_launch_poll_s
    if os_control_retry_attempts is not None:
        g["OS_CONTROL_RETRY_ATTEMPTS"] = os_control_retry_attempts
    if os_control_retry_settle_s is not None:
        g["OS_CONTROL_RETRY_SETTLE_S"] = os_control_retry_settle_s
    if os_control_reply_max_tokens is not None:
        g["OS_CONTROL_REPLY_MAX_TOKENS"] = os_control_reply_max_tokens
    if os_control_enum_retry is not None:
        g["OS_CONTROL_ENUM_RETRY"] = os_control_enum_retry
    if os_control_enum_timeout_s is not None:
        g["OS_CONTROL_ENUM_TIMEOUT_S"] = os_control_enum_timeout_s
    if os_control_enum_retry_settle_s is not None:
        g["OS_CONTROL_ENUM_RETRY_SETTLE_S"] = os_control_enum_retry_settle_s
    if os_control_action_verbs is not None:
        g["_OS_CONTROL_ACTION_VERBS"] = os_control_action_verbs
    if launch_verbs is not None:
        g["_LAUNCH_VERBS"] = launch_verbs
    if conv_key_var is not None:
        g["_conv_key_var"] = conv_key_var
    if get_client is not None:
        g["_get_client"] = get_client
    if scratchpad_note is not None:
        g["_scratchpad_note"] = scratchpad_note
    if db_fire is not None:
        g["_db_fire"] = db_fire
    if db_post is not None:
        g["_db_post"] = db_post
    if db_create is not None:
        g["_db_create"] = db_create
    if inline_satisfaction_check is not None:
        g["_inline_satisfaction_check"] = inline_satisfaction_check
    if strip_think_tags is not None:
        g["_strip_think_tags"] = strip_think_tags
    if fastpath_verbs is not None:
        g["_FASTPATH_VERBS"] = fastpath_verbs
    if verb_catalog is not None:
        g["_VERB_CATALOG"] = verb_catalog


_OSCONTROL_ENDPOINTS_CACHE: Optional[list] = None


def _load_oscontrol_endpoints() -> list:
    """Resolve the cross-desktop window-probe endpoints from the SSOT
    (vendor /usr/share + /etc/mios + ~/.config). Returns a list of
    {"label","url"} dicts -- the local-host executor (when set) plus every
    [os_control.nodes.<name>].endpoint declared with a non-empty URL.
    Cached once per process; the lazy-load means a build without ANY
    overlay incurs zero work (returns [])."""
    global _OSCONTROL_ENDPOINTS_CACHE
    if _OSCONTROL_ENDPOINTS_CACHE is not None:
        return _OSCONTROL_ENDPOINTS_CACHE
    try:
        try:
            import tomllib  # py311+
        except ImportError:
            import tomli as tomllib  # noqa: F401  (older fedoras)
        base = os.environ.get("MIOS_TOML", "/usr/share/mios/mios.toml")
        layers = [base, "/etc/mios/mios.toml",
                  os.path.expanduser("~/.config/mios/mios.toml")]
        cfg: dict = {}
        for p in layers:
            try:
                with open(p, "rb") as f:
                    d = tomllib.load(f)
            except (OSError, Exception):  # noqa: BLE001
                continue
            sec = d.get("os_control") or {}
            if not isinstance(sec, dict):
                continue
            # Top-level executor_endpoint overlays.
            if "executor_endpoint" in sec:
                cfg.setdefault("__exec__", {}).update(
                    {"endpoint": str(sec.get("executor_endpoint") or "")})
            # Per-node overlays (sec.nodes.<name>).
            nodes = sec.get("nodes") or {}
            if isinstance(nodes, dict):
                for nname, ncfg in nodes.items():
                    if isinstance(ncfg, dict):
                        cfg.setdefault(nname, {}).update(ncfg)
        out: list = []
        if "__exec__" in cfg:
            url = (cfg["__exec__"].get("endpoint") or "").rstrip("/")
            if url:
                out.append({"label": "local-executor", "url": url})
        for nname, ncfg in cfg.items():
            if nname == "__exec__":
                continue
            url = str(ncfg.get("endpoint") or "").rstrip("/")
            if url:
                out.append({"label": nname, "url": url})
        _OSCONTROL_ENDPOINTS_CACHE = out
        return out
    except Exception as e:  # noqa: BLE001
        log.warning("oscontrol endpoint discovery failed: %s", e)
        _OSCONTROL_ENDPOINTS_CACHE = []
        return []


async def _remote_enumerate_windows_one(ep: dict,
                                        timeout_s: float = 3.5) -> list:
    """GET <url>/windows on one Windows-native executor + normalise the
    result into the [{hwnd,title,proc,pid,x,y,w,h,_source}] shape the
    rest of the verify path expects. Errors -> []."""
    url = ep.get("url") or ""
    if not url:
        return []
    label = ep.get("label") or "remote"
    try:
        client = await _get_client()
        r = await client.get(url + "/windows", timeout=timeout_s)
        if r.status_code != 200:
            return []
        d = r.json()
    except Exception as e:  # noqa: BLE001
        log.debug("remote window probe %s failed: %s", label, e)
        return []
    wins = (d or {}).get("windows") or []
    if not isinstance(wins, list):
        return []
    norm: list = []
    for w in wins:
        if not isinstance(w, dict):
            continue
        wcopy = dict(w)
        wcopy.setdefault("_source", label)
        norm.append(wcopy)
    return norm


async def _enumerate_windows() -> dict:
    """Snapshot all open top-level windows. Calls the WSL-side list_windows verb
    AND every configured cross-desktop executor in parallel ([os_control].
    executor_endpoint + every [os_control.nodes.*].endpoint), merging the
    results. Without remote endpoints this collapses to the original WSL-only
    behavior (vendor empty = no overhead). Returns {"ok", "count", "windows":[...]}
    with each window carrying a `_source` tag so the diff can attribute opens to
    a specific desktop. Never raises."""
    async def _local() -> list:
        try:
            res = await dispatch_mios_verb("list_windows", {})
            raw = (res.get("output") or "").strip()
            data = _loads_lenient(raw) if raw else {}
            wins = data.get("windows") if isinstance(data, dict) else None
            wins = wins if isinstance(wins, list) else []
            out: list = []
            for w in wins:
                if isinstance(w, dict):
                    wcopy = dict(w)
                    wcopy.setdefault("_source", "wsl")
                    out.append(wcopy)
            return out
        except Exception as e:  # noqa: BLE001
            log.debug("local window enumerate failed: %s", e)
            return []

    async def _snapshot_once() -> tuple:
        endpoints = _load_oscontrol_endpoints()
        tasks = [asyncio.create_task(_local())]
        for ep in endpoints:
            tasks.append(asyncio.create_task(_remote_enumerate_windows_one(ep)))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        merged: list = []
        any_ok = False
        for r in results:
            if isinstance(r, list):
                if r:
                    any_ok = True
                merged.extend(r)
        return any_ok, merged

    # RETRY-ON-EMPTY : an empty snapshot on a live desktop is a
    # transient broker miss, not truth -- re-enumerate so a launch-verify never goes
    # falsely BLIND (which forced the unreliable PID fallback). Each attempt is
    # wait_for-bounded; the empty case returns fast in practice, so the common path
    # (windows present on the first try) adds ZERO latency.
    any_ok, merged = False, []
    for _attempt in range(max(1, OS_CONTROL_ENUM_RETRY + 1)):
        try:
            any_ok, merged = await asyncio.wait_for(
                _snapshot_once(), timeout=OS_CONTROL_ENUM_TIMEOUT_S)
        except Exception as e:  # noqa: BLE001 -- timeout or gather failure -> empty
            log.debug("window snapshot attempt %d failed: %s", _attempt, e)
            any_ok, merged = False, []
        if merged:
            break
        if _attempt < OS_CONTROL_ENUM_RETRY:
            log.info("window enumeration empty (count:0) -> re-enumerate "
                     "(attempt %d/%d); a live desktop always has >=1 window",
                     _attempt + 1, OS_CONTROL_ENUM_RETRY)
            await asyncio.sleep(OS_CONTROL_ENUM_RETRY_SETTLE_S)
    return {"ok": any_ok, "count": len(merged), "windows": merged}


def _window_key(w: dict) -> tuple:
    """Stable identity for diffing snapshots: prefer hwnd, else (title, proc)."""
    if not isinstance(w, dict):
        return ("?", str(w))
    hw = w.get("hwnd")
    if hw not in (None, "", 0):
        return ("hwnd", str(hw))
    return ("tp", str(w.get("title", "")), str(w.get("proc", "")))


def _window_diff(before: dict, after: dict) -> dict:
    """opened = windows in AFTER not in BEFORE; closed = the reverse."""
    before = before or {}
    after = after or {}
    b = {_window_key(w): w for w in (before.get("windows") or [])}
    a = {_window_key(w): w for w in (after.get("windows") or [])}
    opened = [a[k] for k in (a.keys() - b.keys())]
    closed = [b[k] for k in (b.keys() - a.keys())]
    return {"opened": opened, "closed": closed}


def _win_titles(wins: Optional[list]) -> str:
    out = []
    for w in (wins or [])[:12]:
        if isinstance(w, dict):
            t = str(w.get("title", "")).strip() or str(w.get("proc", "")).strip()
            if t:
                out.append(t)
    return ", ".join(out)


def _window_delta_text(diff: dict) -> str:
    bits = []
    if diff.get("opened"):
        bits.append(f"opened: {_win_titles(diff['opened'])}")
    if diff.get("closed"):
        bits.append(f"closed: {_win_titles(diff['closed'])}")
    return "; ".join(bits) or "no visible window change detected"


def _index_window_event(tool: str, args: dict, before: dict, after: dict,
                        diff: dict, session_id: Optional[str]) -> None:
    """RECORD + INDEX the before/after window snapshots + delta so FUTURE
    queries recall them (RAG: embedded knowledge row via _store_knowledge) and
    same-conversation agents see them (scratchpad). Fire-and-forget; the
 "check before, diff after" grounding the operator asked for."""
    target = ""
    if isinstance(args, dict):
        target = str(args.get("app") or args.get("title")
                     or args.get("name") or args.get("url") or "").strip()
    delta = _window_delta_text(diff)
    q = (f"open desktop windows after {tool} {target}".strip()
         if target else f"open desktop windows after {tool}")
    answer = (
        f"OS-control action `{tool}` (target={target!r}).\n"
        f"Open windows BEFORE ({(before or {}).get('count', 0)}): "
        f"[{_win_titles((before or {}).get('windows'))}].\n"
        f"Open windows AFTER ({(after or {}).get('count', 0)}): "
        f"[{_win_titles((after or {}).get('windows'))}].\n"
        f"Delta: {delta}.")
    try:
        _store_knowledge(query=q, answer=answer, session_id=session_id,
                         tool_history=[{"tool": tool, "args": args}])
    except Exception as e:
        log.debug("window event index skipped: %s", e)
    _scratchpad_note("os-control", f"{tool} {target} -> {delta}",
                     lane="window", phase="action")


def _os_target(args: dict) -> str:
    if not isinstance(args, dict):
        return ""
    return str(args.get("app") or args.get("title") or args.get("name")
               or args.get("url") or "").strip().lower()


def _win_hay(w: dict) -> str:
    return (str(w.get("title", "")) + " " + str(w.get("proc", ""))).lower()


async def _center_windows(wins: list) -> list:
    """Center the given window(s) on their desktop (operator binding
    'launches are ALWAYS centered -- that should be the default MiOS AI opening
    pattern'). WSLg / flatpak windows IGNORE Win32 launch-time placement, so we
    center AFTER the window maps. Picks the LARGEST window per owning executor
    (the MAIN app window -- a launch also spawns ~11 tiny PopupHost/tooltip
    windows) and POSTs /window/center to the Windows-native executor that owns
    it (only executor-sourced windows have movable Win32 hwnds; the WSL
    list_windows hwnds are a different namespace). The executor's center is a
    non-blocking async SetWindowPos, so this never stalls the turn. Best-effort;
    returns the list of centered window titles. Never raises."""
    eps = {e.get("label"): e.get("url")
           for e in _load_oscontrol_endpoints() if e.get("url")}
    if not eps:
        return []
    # Largest qualifying window per owning executor.
    best: dict = {}
    for w in (wins or []):
        if not isinstance(w, dict):
            continue
        src = w.get("_source")
        if src not in eps:                      # only movable Win32 windows
            continue
        hw = w.get("hwnd")
        if hw in (None, "", 0):
            continue
        ww = int(w.get("w") or 0)
        hh = int(w.get("h") or 0)
        if ww < 200 or hh < 120:                # skip popups / tooltips
            continue
        area = ww * hh
        if area >= (best.get(src, {}).get("_area", -1)):
            best[src] = {"hwnd": hw, "_area": area,
                         "title": w.get("title") or w.get("proc") or ""}
    if not best:
        return []
    done: list = []
    for src, w in best.items():
        try:
            client = await _get_client()
            await client.post(eps[src] + "/window/center",
                              json={"hwnd": w["hwnd"]}, timeout=5)
            done.append(str(w["title"]))
        except Exception as e:  # noqa: BLE001
            log.debug("auto-center on %s failed: %s", src, e)
    return done


def _launch_proc_patterns(args: dict, result: dict) -> list:
    """Process-name patterns to pgrep for to confirm a launch ACTUALLY started
 ('should JUST search for PIDs globally for
    verifications'). The robust signal is the PROCESS existing -- WSLg windows
    carry content titles + proc=msrdc, never the app name, so title/count are
    unreliable. The launcher echoes the resolved ref ('launching <id>' /
    'fired <id>' / 'run <id>'); take both the reverse-DNS id AND its lowercased
    leaf (the bwrap binary, e.g. org.gnome.Epiphany -> 'epiphany'), plus the
    bare target name as a last-resort weak pattern."""
    pats: list = []
    blob = str(result.get("output") or "") + " " + str(result.get("stderr") or "")
    for m in re.finditer(r'(?:launching|fired|run|exec)\s+([A-Za-z][A-Za-z0-9._+-]{2,})', blob):
        ref = m.group(1).strip().strip('"\'')
        if "." in ref:
            leaf = ref.split(".")[-1].lower()
            if len(leaf) >= 3 and leaf not in pats:
                pats.append(leaf)
            if ref.lower() not in pats:
                pats.append(ref.lower())
        elif len(ref) >= 3 and ref.lower() not in pats:
            pats.append(ref.lower())
    t = _os_target(args)
    if t and len(t) >= 3 and t not in pats:
        pats.append(t)
    return pats


async def _proc_present(patterns: list) -> bool:
    """True if ANY pattern matches a running process command line (global
    `pgrep -if`). /proc is world-readable, so the agent uid sees EVERY user's
    process cmdlines -- including the operator's flatpak GUIs running under
    bwrap. This is the primary, generative launch-verification signal."""
    for pat in patterns:
        if not pat or len(pat) < 3:
            continue
        try:
            p = await asyncio.create_subprocess_exec(
                "pgrep", "-if", pat,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL)
            rc = await asyncio.wait_for(p.wait(), timeout=4)
            if rc == 0:
                return True
        except Exception:
            pass
    return False


def _verify_os_action(tool: str, args: dict, result: dict,
                      before: dict, after: dict, wdiff: dict) -> bool:
    """Did the OS-control action ACTUALLY take effect ('the
    pipeline VERIFIES TRUE and re-attempts')? Grounded in the window-enumeration
    diff when available; falls back to the verb's exit code when enumeration is
    BLIND (executor not wired -> count:0 both sides, can't diff)."""
    ok = bool(result.get("success"))
    target = _os_target(args)
    bc = (before or {}).get("count", 0)
    ac = (after or {}).get("count", 0)
    blind = (bc == 0 and ac == 0)
    if tool in _LAUNCH_VERBS:
        if blind:
            return ok  # can't enumerate -> trust the fire's exit code
        wins = (after or {}).get("windows") or []
        # A NEW window appeared after the launch = it worked. This is the
        # robust signal: WSLg windows report CONTENT titles ("Home", "Anime
        # North - Home", "mios@MiOS-955:~") + proc=msrdc -- NEVER the app name
        # - so a target-NAME substring match is unreliable (
        # train: epiphany/files/ptyxis ALL opened but were reported "failed"
        # because "epiphany" isn't in "Anime North - Home"). No hardcoded app
        # names: count-delta + the live window diff carry the truth.
        if ac > bc or wdiff.get("opened"):
            return True
        # ALREADY-OPEN: mios-launch's preflight focuses+centers an existing
        # instance and reports already_running -- honour that as success.
        _out = (result.get("output") or "") + " " + (result.get("stderr") or "")
        if "already_running" in _out and "true" in _out:
            return True
        if "tab-opened" in _out and '"success": true' in _out:
            return True
        # Last resort: a genuine title match (native Windows apps DO carry
        # their name, e.g. "Task Manager").
        if target and any(target in _win_hay(w) for w in wins):
            return True
        return False
    if tool == "close_window":
        if blind:
            return ok
        wins = (after or {}).get("windows") or []
        if target:
            return not any(target in _win_hay(w) for w in wins)  # gone == success
        return bool(wdiff.get("closed")) or ok
    # focus / move / resize / center / state: no window-count change expected.
    return ok


# "Last window THIS CONVERSATION opened" -- the referent for a standalone "type X
# into it" the turn AFTER a launch (operator's exact domain: typing). Keyed on the
# per-conversation scratchpad key (_conv_key_var = metadata.chat_id the OWUI pipe
# forwards) NOT the per-REQUEST session_id, which is a fresh DB row each turn and
# would never match across the conversation. A launch records its opened window
# here; a later standalone pc_type focuses it before typing so the keystrokes land
# in the window the user means, not whatever stole foreground since. Bounded
# (LRU-ish via clear); read-back still verifies the text actually landed -- this
# only improves WHICH window is targeted, it never asserts success.
_LAST_OPENED_WINDOW: dict = {}
_LAST_OPENED_WINDOW_CAP = int(os.environ.get("MIOS_LAST_WINDOW_CAP", "256") or 256)


def _record_last_opened_window(wdiff: dict) -> None:
    """Remember the first window a launch opened for THIS conversation (best-effort)."""
    _key = _conv_key_var.get()
    if not _key or not isinstance(wdiff, dict):
        return
    _titles = [str(w.get("title") or "").strip()
               for w in (wdiff.get("opened") or [])
               if isinstance(w, dict) and str(w.get("title") or "").strip()]
    if not _titles:
        return
    if len(_LAST_OPENED_WINDOW) >= _LAST_OPENED_WINDOW_CAP:
        _LAST_OPENED_WINDOW.clear()  # crude bound; conversations are ephemeral
    _LAST_OPENED_WINDOW[_key] = _titles[0]
    log.info("recorded last-opened window for conv %r -> %r", _key, _titles[0])


async def _respond_os_control(
    tool: str, args: dict, refined: Optional[dict], *,
    streaming: bool, chat_id: str, model: str,
    session_id: Optional[str], last_user_text: str,
    persona_system: str = "", emit=None,
) -> Any:
    """OS-control action fast-path. A single concrete
    app/window/URL action is a DETERMINISTIC one-verb action: fire that ONE
    verb through the broker, report the REAL verdict, and STOP. NO council
    fan-out, NO web_search, NO synthesis of fabricated detail -- the failure
    mode that ran a 4-agent web-search swarm for "Launch Forza" (inventing
    window coordinates, never stopping after the launch had already
    succeeded) and narrated a fake tool call for "Close Forza".

    The polish prompt forbids claiming a success the verb's own output does
    not show (anti-fabrication; mirrors the launch_verified / verify_launch
    'presented, not merely process-alive' Definition-of-Done rule in SOUL)."""
    _args = args if isinstance(args, dict) else {}

    # ── LIVE EMIT PUMP, decoupled from the work ("emits
    # are HELD BACK BY THE PIPELINE; should run SEPARATELY ... zero emits during
    # a launch"). When streaming, run the SAME work as a non-streaming bg task
    # whose `emit` callback PUSHES milestone status onto a queue, and drain that
    # queue LIVE here (mirrors the research _gen pump). ONE shared work body --
    # only the transport differs -- so a launch streams route -> launching ->
    # checking -> centering -> result in REAL TIME instead of a silent gap then
    # a dump. Keepalive during any quiet stretch keeps the SSE channel open.
    if streaming:
        async def _stream_os() -> AsyncGenerator[bytes, None]:
            yield _sse_status_phase(chat_id=chat_id, model=model, phase="prompt")
            yield _sse_status_phase(chat_id=chat_id, model=model, phase="route")
            _oq: asyncio.Queue = asyncio.Queue()
            _holder: dict = {}

            async def _work() -> None:
                try:
                    _holder["resp"] = await _respond_os_control(
                        tool, args, refined, streaming=False, chat_id=chat_id,
                        model=model, session_id=session_id,
                        last_user_text=last_user_text,
                        persona_system=persona_system, emit=_oq.put_nowait)
                except Exception as _e:  # noqa: BLE001
                    _holder["err"] = str(_e)
                finally:
                    _oq.put_nowait(None)

            _wtask = asyncio.create_task(_work())
            while True:
                try:
                    _s = await asyncio.wait_for(_oq.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    yield b": keepalive\n\n"
                    continue
                if _s is None:
                    break
                if isinstance(_s, dict):
                    yield _sse_status(chat_id=chat_id, model=model,
                                      emoji=str(_s.get("emoji", "·")),
                                      label=str(_s.get("label", "")),
                                      detail=_s.get("detail"))
            await _wtask
            _content = ""
            _resp = _holder.get("resp")
            try:
                _b = _loads_lenient(bytes(_resp.body).decode("utf-8"))
                _content = _b["choices"][0]["message"]["content"]
            except Exception:  # noqa: BLE001
                _content = "The OS-control action completed."
            yield _sse_chunk("", chat_id=chat_id, model=model, role="assistant")
            yield _sse_chunk(_content, chat_id=chat_id, model=model)
            yield _sse_status_phase(chat_id=chat_id, model=model,
                                    phase="tool_done", done=True)
            yield _sse_chunk("", chat_id=chat_id, model=model,
                             finish_reason="stop")
            yield _sse_done()
        return StreamingResponse(_stream_os(), media_type="text/event-stream")

    # Milestone emitter -- no-op unless a streaming pump passed an `emit` sink.
    def _emit(emoji: str, label: str, detail=None) -> None:
        if emit:
            try:
                emit({"emoji": emoji, "label": label, "detail": detail})
            except Exception:  # noqa: BLE001
                pass

    # CONTEXT-AWARE FOCUS for a standalone type (operator's exact domain): a bare
    # "now type X into it" the turn after a launch has NO same-turn window to
    # focus -- the "it" referent is the window THIS session most recently opened.
    # Focus it before pc_type so the keystrokes land there, not whatever stole
    # foreground since (the cross-turn analogue of the compound type-chain's
    # focus-before-type). Best-effort + degrade-open: no remembered window, or a
    # focus miss (window since closed), just types into the current foreground;
    # pc_type's STRICT read-back still verifies the text actually landed. ONLY the
    # standalone route enters _respond_os_control with tool=pc_type (the compound
    # chain dispatches pc_type directly), so this never double-focuses.
    if tool == "pc_type":
        _ckey = _conv_key_var.get()
        _lw = _LAST_OPENED_WINDOW.get(_ckey) if _ckey else None
        if _lw:
            try:
                await dispatch_mios_verb("focus_window", {"title": _lw},
                                         session_id=session_id)
                await asyncio.sleep(0.35)
                log.info("standalone pc_type: context-focused this "
                         "conversation's last-opened window %r before typing", _lw)
            except Exception:  # noqa: BLE001 -- best-effort
                pass
    # FIRE -> VERIFY -> RE-ATTEMPT ("iGPU does MiOS OS
    # control ... the rest of the pipeline VERIFIES TRUE and attempts to
    # re-attempt"). For a WRITE OS-control verb: snapshot ALL open windows
    # BEFORE, fire the action, snapshot AFTER, diff to learn exactly what
    # opened/closed, and CONFIRM via the diff (launch -> target window now
    # present; close -> target gone). If the enumeration does NOT confirm it
    # took effect, RE-ATTEMPT up to OS_CONTROL_RETRY_ATTEMPTS. The before/after
    # diff is real once the executor is wired (else blind count:0 -> trust the
    # exit code, no retry-spin). A launch already present short-circuits (no
    # double-launch). The final snapshot+delta is indexed to RAG.
    _action = tool in _OS_CONTROL_ACTION_VERBS
    _is_launch = tool in _LAUNCH_VERBS
    _before = _after = None
    _wdiff: dict = {}
    result: dict = {}
    _verified = False
    _tries = 0
    if _action and _is_launch:
        # LAUNCH: fire ONCE (the launch is detached + fire-and-forget), then
        # POLL the window enumeration until the window renders or the deadline
        # passes. Re-DISPATCHING a launch on a miss would spawn DUPLICATE
        # instances (train: 3 gedit instances; epiphany/
        # nautilus/ptyxis all opened ~5-10s later but were reported "no
        # window"). Polling (re-enumerate only, no re-launch) fixes both.
        _emit("🚀", f"opening {_os_target(_args) or tool}")
        _before = await _enumerate_windows()
        result = await dispatch_mios_verb(tool, _args, session_id=session_id)
        _deadline = time.monotonic() + OS_CONTROL_LAUNCH_VERIFY_S
        _proc_pats = _launch_proc_patterns(_args, result)
        while True:
            _tries += 1
            _emit("🔍", "checking it opened")
            _after = await _enumerate_windows()
            _wdiff = _window_diff(_before, _after)
            # A GUI launch is VERIFIED by a real WINDOW -- a new window opened,
            # or a visible window matching the target ("this
            # is how i know nothing is verified" -- Discord PTB spawned 6 procs
            # with MainWindowHandle=0 and ZERO top-level windows, started
            # minimized to the tray, yet a pgrep PID check flipped the verdict to
            # "launched". A live process with NO window is NOT "opened"). So
            # _proc_present is demoted to a BLIND-ONLY fallback: when the window
            # enumeration can see nothing at all (executor not wired -> count:0
            # both sides), THEN fall back to the global-PID check / exit code
            # (operator's earlier "search PIDs globally"). When we CAN enumerate
            # windows, process-presence does NOT override the absence of one.
            _win_verdict = _verify_os_action(
                tool, _args, result, _before, _after, _wdiff)
            _enum_blind = ((_before or {}).get("count", 0) == 0
                           and (_after or {}).get("count", 0) == 0)
            _verified = (_win_verdict
                         or (_enum_blind and await _proc_present(_proc_pats)))
            if _verified or time.monotonic() >= _deadline:
                break
            log.info("os-control %s not yet confirmed (poll %d) -> wait %.1fs",
                     tool, _tries, OS_CONTROL_LAUNCH_POLL_S)
            await asyncio.sleep(OS_CONTROL_LAUNCH_POLL_S)
        # CENTER the freshly-launched window (operator binding: 'launches are
        # ALWAYS centered -- the default MiOS opening pattern'). Done HERE, after
        # the verify loop has identified what opened, so we center the REAL main
        # window (mapped + full-size) rather than an early popup. Server-side so
        # it covers EVERY fast-path launch + reuses the diff already computed.
        if _wdiff.get("opened"):
            _emit("🎯", "centering it")
            _ctr = await _center_windows(_wdiff["opened"])
            if _ctr:
                log.info("auto-centered launched window(s): %s", ", ".join(_ctr))
        # Remember what this launch opened so a FOLLOW-UP turn's standalone
        # "type X into it" can focus the right window before typing.
        _record_last_opened_window(_wdiff)
    else:
        _emit("🪟", (f"{tool.replace('_window', '').replace('_', ' ').strip()} "
                     f"{_os_target(_args)}").strip())
        _attempts = max(1, OS_CONTROL_RETRY_ATTEMPTS) if _action else 1
        for _i in range(_attempts):
            _tries = _i + 1
            _before = await _enumerate_windows() if _action else None
            result = await dispatch_mios_verb(tool, _args, session_id=session_id)
            _after = await _enumerate_windows() if _action else None
            _wdiff = _window_diff(_before, _after) if _action else {}
            _verified = (_verify_os_action(tool, _args, result, _before, _after, _wdiff)
                         if _action else bool(result.get("success")))
            if _verified or not _action:
                break
            if _i < _attempts - 1:
                log.info("os-control %s NOT verified (try %d/%d) -> re-attempt",
                         tool, _tries, _attempts)
                await asyncio.sleep(OS_CONTROL_RETRY_SETTLE_S)
    ok = bool(result.get("success"))
    # Effective verdict for the operator-facing symbol: a launch that fired
    # (exit 0) but did NOT verify (no window) is NOT a confirmed success.
    _eff_ok = _verified if _action else ok
    # ...BUT a launch whose COMMAND fired (exit 0) with no window yet is
    # LAUNCHING, not failed -- normal for Steam/Store games that load over
    # 30-60s, well past the verify window ("play a game").
    # Distinct from a fire that errored (genuine failure -> stays ⚠️).
    _launch_pending = bool(_is_launch and ok and not _verified)
    # SMART FOCUS ("detect if running -> focus to the
    # foreground -> not available? -> find and launch to the foreground"):
    # focus_window only raises an ALREADY-OPEN window. If the target isn't
    # running (focus found no matching window), LAUNCH it -- the launcher brings
    # the new window to the foreground -- so "focus X" means "ensure X is open +
    # frontmost", never a dead-end "X isn't running" punt.
    _focus_launched = False
    if tool == "focus_window" and not _eff_ok:
        _t = str(_args.get("title") or _args.get("app")
                 or _args.get("name") or "").strip()
        if _t:
            log.info("smart-focus: '%s' not running -> launch to foreground", _t)
            _before = await _enumerate_windows()
            result = await dispatch_mios_verb("open_app", {"name": _t},
                                              session_id=session_id)
            _after = await _enumerate_windows()
            _wdiff = _window_diff(_before, _after)
            _verified = _verify_os_action("open_app", {"app": _t}, result,
                                          _before, _after, _wdiff)
            ok = bool(result.get("success"))
            _eff_ok = _verified
            _focus_launched = True
    # (Compound-launch TYPE-CHAIN hack removed: the agent now relies on 
    # native AIOS routing to compose open_app and pc_type sequentially.)
    if _action:
        _index_window_event(tool, _args, _before, _after, _wdiff, session_id)
    _row = {
        "tool": tool,
        "args": _args,
        "result_preview": (result.get("output") or "")[:500],
        "success": ok,
        "latency_ms": int(result.get("latency_ms", 0)),
        "tainted": bool(result.get("tainted")),
        "taint_reason": (result.get("taint_reason") or "") or None,
    }
    if session_id:
        _db_fire(_db_post(
            _db_create("tool_call", _row, now_fields=("ts",)).rstrip(";")
            + f", session = {session_id};"))
    else:
        _db_fire(_db_post(_db_create("tool_call", _row, now_fields=("ts",))))
    envelope = {
        "tool_call": {
            "id": f"call_{int(time.time()*1000)}",
            "type": "function",
            "function": {"name": tool, "arguments": _args},
        },
        "tool_result": {
            "success": ok,
            "output": (result.get("output") or "")[:2000],
            "stderr": (result.get("stderr") or "")[:2000],
            "exit_code": int(result.get("exit_code", -1)),
        },
    }
    if _action:
        # Grounding diff: what the enumeration shows ACTUALLY changed + the
        # verify/re-attempt verdict.
        envelope["window_change"] = {
            "verified": bool(_verified),
            "attempts": _tries,
            "before_count": (_before or {}).get("count", 0),
            "after_count": (_after or {}).get("count", 0),
            "opened": [str(w.get("title") or w.get("proc") or "")
                       for w in _wdiff.get("opened", []) if isinstance(w, dict)],
            "closed": [str(w.get("title") or w.get("proc") or "")
                       for w in _wdiff.get("closed", []) if isinstance(w, dict)],
        }
    # (type_chain removed)
    if DCI_ENABLED:
        _db_fire(critic_then_maybe_flow(last_user_text, envelope,
                                        session_id=session_id))
    symbol = ("✅" if _eff_ok else ("🚀" if _launch_pending else "⚠️"))
    envelope_block = (
        f"<details type=\"tool_calls\" done=\"true\">\n"
        f"<summary>{symbol} `{tool}`</summary>\n\n"
        f"```json\n{json.dumps(envelope, indent=2, default=str)}\n```\n"
        f"</details>")
    _refined_for_polish = refined or {
        "intent": "dispatch",
        "intended_outcome": f"perform the {tool} action the operator asked for",
        "refined_text": last_user_text,
    }
    # Inline satisfaction event before polish reads verdicts.
    await _inline_satisfaction_check(session_id, _refined_for_polish)
    _out = (result.get("output") or "").strip()
    _err = (result.get("stderr") or "").strip()
    _polish_src = (
        f"exit_code={int(result.get('exit_code', -1))}\n"
        f"stdout:\n{_out[:1500]}\n"
        + (f"stderr:\n{_err[:600]}\n" if _err else ""))
    if _action:
        _polish_src += (
            f"window_enumeration: before={(_before or {}).get('count', 0)} open, "
            f"after={(_after or {}).get('count', 0)} open; "
            f"{_window_delta_text(_wdiff)}\n"
            f"verified={bool(_verified)} after {_tries} attempt(s)\n")
        if _focus_launched:
            _polish_src += ("smart_focus: the window was NOT already open, so it "
                            "was LAUNCHED to the foreground (report that it "
                            "wasn't running and you opened it).\n")
        if _launch_pending:
            _polish_src += ("launch_fired_pending: the launch COMMAND SUCCEEDED "
                            "(the app/game was told to start) but its window has "
                            "NOT appeared within the short verify window -- this "
                            "is NORMAL for Steam/Store GAMES, which load over "
                            "30-60s. Report this as STARTING / LAUNCHING (e.g. "
                            "'<app> is launching via Steam -- it may take a moment "
                            "to appear'), which is NOT a failure.\n")
    # (type_chain reporting removed)
    # OS-control replies are SHORT + GENERATIVE ("completely
    # generative in its replies too" + "JUST reply SUCCESS and DETAILS and
    # FOLLOW-UPS, nothing much more"). So: model-written (no template), but a
    # tight prompt + low token cap -> fast (vs the 16s full-length polish). The
    # `verified`/window/proc facts in _polish_src are the ground truth.
    _emit(symbol, "writing the result")
    polished_raw = await polish_response(
        "The OS-control verb `" + tool + "` ran (result below). Reply in 1-3 "
        "short sentences with exactly: (1) SUCCESS or failure -- grounded in "
        "`verified` (verified=True means it took effect; if False after the "
        "retries, say it did NOT and do not claim success -- EXCEPT when "
        "`launch_fired_pending` is present, which means the launch DID fire and "
        "the app/game is still LOADING: report it as STARTING/LAUNCHING, NOT a "
        "failure); (2) the key DETAILS "
        "(what opened/closed/was focused, the app/window name); (3) one or two "
        "natural FOLLOW-UPS the operator might want next (e.g. focus it, move "
        "it, close it, open another). No preamble, no invented coordinates, no "
        "fabricated confirmation -- nothing beyond success + details + "
        "follow-ups.\n\n" + _polish_src,
        _refined_for_polish, session_id=session_id,
        original_user_text=last_user_text, persona_system=persona_system,
        max_tokens=OS_CONTROL_REPLY_MAX_TOKENS)
    polished = _strip_think_tags(polished_raw) if polished_raw else ""
    rendered = (f"{polished}\n\n{envelope_block}"
                if polished.strip() else envelope_block)
    # Streaming is handled by the live-emit pump at the TOP of this function (it
    # runs THIS body as a non-streaming bg task + drains the milestone emits in
    # real time). Reaching here means streaming=False -> return the rendered
    # envelope (polished answer + tool_calls block) as a plain JSON completion.
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


def _render_os_control_verbs() -> str:
    """One line per fast-path verb (name(sig) -- desc) for the refine prompt, so
    the micro maps a single concrete action to the right catalog verb WITHOUT a
    hardcoded keyword map. Covers OS-control + other deterministic single-action
    verbs (scheduling). Empty string when none are registered."""
    lines = []
    for name in sorted(_FASTPATH_VERBS):
        cfg = _VERB_CATALOG.get(name) or {}
        sig = cfg.get("sig", "")
        desc = (cfg.get("desc", "") or "").strip().replace("\n", " ")[:150]
        lines.append(f"  {name}({sig}) -- {desc}")
    return "\n".join(lines)
