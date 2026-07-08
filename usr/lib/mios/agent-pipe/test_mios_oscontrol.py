#!/usr/bin/env python3
# AI-hint: Offline stdlib test for mios_oscontrol (refactor R9): stubs every sibling (fastapi.responses + mios_sse/mios_jsonsalvage/mios_dci/mios_dispatch/mios_verity/mios_knowledge) in sys.modules so mios_oscontrol imports with no network/DB, then drives the window enum/verify path on a synthetic before/after window set -- asserts _window_diff identifies the opened/closed windows, _window_delta_text renders them, and _verify_os_action's anti-fabrication verdict is TRUE when a launch produced a NEW window but FALSE when the launch fired yet no window appeared (the failure mode the fast-path exists to stop). Pure assert-script.
# AI-related: ./mios_oscontrol.py, ./server.py
# AI-functions: main
"""Stub-and-import test for the OS-control window verify + anti-fabrication verdict."""

import sys
import types

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def _install_stubs():
    """Minimal stand-ins for every module mios_oscontrol imports at top level so
    it loads with no 3rd-party deps, network or DB. The pure verify helpers under
    test never call into any of them."""
    fastapi = sys.modules.setdefault("fastapi", types.ModuleType("fastapi"))
    responses = types.ModuleType("fastapi.responses")
    for _c in ("JSONResponse", "StreamingResponse"):
        setattr(responses, _c, type(_c, (), {"__init__": lambda self, *a, **k: None}))
    fastapi.responses = responses
    sys.modules.setdefault("fastapi.responses", responses)

    sse = types.ModuleType("mios_sse")
    for _n in ("_sse_status_phase", "_sse_status", "_sse_chunk", "_sse_done"):
        setattr(sse, _n, lambda *a, **k: b"")
    sys.modules["mios_sse"] = sse

    js = types.ModuleType("mios_jsonsalvage")
    js.loads_lenient = lambda s: {}
    sys.modules["mios_jsonsalvage"] = js

    dci = types.ModuleType("mios_dci")
    dci.DCI_ENABLED = False
    dci.critic_then_maybe_flow = lambda *a, **k: None
    sys.modules["mios_dci"] = dci

    disp = types.ModuleType("mios_dispatch")
    async def _dispatch(*a, **k):
        return {"success": True, "output": "", "exit_code": 0}
    disp.dispatch_mios_verb = _dispatch
    sys.modules["mios_dispatch"] = disp

    verity = types.ModuleType("mios_verity")
    async def _polish(*a, **k):
        return ""
    verity.polish_response = _polish
    sys.modules["mios_verity"] = verity

    know = types.ModuleType("mios_knowledge")
    know._store_knowledge = lambda *a, **k: None
    sys.modules["mios_knowledge"] = know


def main():
    _install_stubs()
    import mios_oscontrol as m

    # Wire the verb sets the verdict reads (server injects these at startup).
    m.configure(launch_verbs=frozenset({"open_app", "launch_app", "open_url"}),
                os_control_action_verbs=frozenset({"open_app", "close_window"}))

    # ── synthetic before/after window snapshots ──────────────────────
    shell = {"hwnd": 1, "title": "Program Manager", "proc": "explorer"}
    before = {"ok": True, "count": 1, "windows": [shell]}
    # A launch opened a brand-new window (different hwnd) -- the robust signal.
    opened_win = {"hwnd": 42, "title": "Anime North - Home", "proc": "msrdc"}
    after_opened = {"ok": True, "count": 2, "windows": [shell, opened_win]}
    # A launch that fired but produced NO new window (the fabrication trap).
    after_none = {"ok": True, "count": 1, "windows": [shell]}

    # ── window-delta verify (_window_diff / _window_delta_text) ──────
    d_open = m._window_diff(before, after_opened)
    check("window_diff sees the opened window",
          [w["hwnd"] for w in d_open["opened"]] == [42] and not d_open["closed"],
          str(d_open))
    d_close = m._window_diff(after_opened, before)
    check("window_diff sees the closed window (reverse)",
          [w["hwnd"] for w in d_close["closed"]] == [42] and not d_close["opened"],
          str(d_close))
    check("window_delta_text renders the opened title",
          "Anime North - Home" in m._window_delta_text(d_open)
          and m._window_delta_text(d_open).startswith("opened:"),
          m._window_delta_text(d_open))
    check("window_delta_text reports no change when snapshots match",
          m._window_delta_text(m._window_diff(before, before))
          == "no visible window change detected")

    # ── anti-fabrication launch verdict (_verify_os_action) ──────────
    fired = {"success": True, "output": "launching org.gnome.Epiphany", "exit_code": 0}
    verdict_ok = m._verify_os_action(
        "open_app", {"app": "epiphany"}, fired, before, after_opened, d_open)
    check("launch with a NEW window verifies TRUE (count-delta, name-agnostic)",
          verdict_ok is True)

    d_none = m._window_diff(before, after_none)
    verdict_none = m._verify_os_action(
        "open_app", {"app": "epiphany"}, fired, before, after_none, d_none)
    check("launch that fired but opened NO window verifies FALSE (anti-fabrication)",
          verdict_none is False,
          "exit-0 fire must NOT be claimed a success without a window")

    # BLIND enumeration (count:0 both sides) -> trust the fire's exit code.
    blind = {"ok": False, "count": 0, "windows": []}
    verdict_blind = m._verify_os_action(
        "open_app", {"app": "epiphany"}, fired, blind, blind,
        m._window_diff(blind, blind))
    check("blind enumeration falls back to the exit code (success)",
          verdict_blind is True)

    # close_window: target gone from AFTER == success.
    close_res = {"success": True, "output": "", "exit_code": 0}
    v_close = m._verify_os_action(
        "close_window", {"title": "Anime North"}, close_res,
        after_opened, before, m._window_diff(after_opened, before))
    check("close verifies TRUE when the target window is gone", v_close is True)
    v_close_still = m._verify_os_action(
        "close_window", {"title": "Anime North"}, close_res,
        after_opened, after_opened, m._window_diff(after_opened, after_opened))
    check("close verifies FALSE when the target window is still present",
          v_close_still is False)

    # open_url: tab reuse verification check (T-116)
    tab_res = {"success": True, "output": '{"success": true, "target": "com.google.ChromeDev", "url": "https://example.com", "summary": "tab-opened-existing"}', "exit_code": 0}
    v_tab = m._verify_os_action(
        "open_url", {"url": "https://example.com"}, tab_res,
        before, after_none, m._window_diff(before, after_none))
    check("open_url verify is TRUE for already-running tab opens", v_tab is True)

    # ── fast-path verb rendering (_render_os_control_verbs) ──────────
    # server injects _FASTPATH_VERBS + _VERB_CATALOG at import time; the render is
    # one sorted "  name(sig) -- desc" line per verb, desc newline-collapsed + clipped.
    m.configure(
        fastpath_verbs=frozenset({"open_app", "schedule"}),
        verb_catalog={
            "open_app": {"sig": "app", "desc": "Launch an app"},
            "schedule": {"sig": "when, task", "desc": "Schedule a task\nlater"},
        })
    rendered = m._render_os_control_verbs()
    lines = rendered.split("\n")
    check("render emits one line per fast-path verb", len(lines) == 2, rendered)
    check("render sorts verbs (open_app before schedule)",
          lines[0] == "  open_app(app) -- Launch an app", lines[0])
    check("render collapses newlines in the desc",
          lines[1] == "  schedule(when, task) -- Schedule a task later", lines[1])
    m.configure(fastpath_verbs=frozenset())
    check("render is empty when no verbs are registered",
          m._render_os_control_verbs() == "",
          "expected '' for empty _FASTPATH_VERBS")

    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
