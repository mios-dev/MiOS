#!/usr/bin/env python3
# AI-hint: Offline stdlib test for mios_oscontrol (refactor R9): stubs every sibling (fastapi.responses + mios_sse/mios_jsonsalvage/m...
# AI-doc: usr/share/doc/mios/manual/agent-pipe.md
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

    m.configure(launch_verbs=frozenset({"open_app", "launch_app", "open_url"}),
                os_control_action_verbs=frozenset({"open_app", "close_window"}))

    shell = {"hwnd": 1, "title": "Program Manager", "proc": "explorer"}
    before = {"ok": True, "count": 1, "windows": [shell]}
    opened_win = {"hwnd": 42, "title": "Sample App - Home", "proc": "msrdc"}
    after_opened = {"ok": True, "count": 2, "windows": [shell, opened_win]}
    after_none = {"ok": True, "count": 1, "windows": [shell]}

    d_open = m._window_diff(before, after_opened)
    check("window_diff sees the opened window",
          [w["hwnd"] for w in d_open["opened"]] == [42] and not d_open["closed"],
          str(d_open))
    d_close = m._window_diff(after_opened, before)
    check("window_diff sees the closed window (reverse)",
          [w["hwnd"] for w in d_close["closed"]] == [42] and not d_close["opened"],
          str(d_close))
    check("window_delta_text renders the opened title",
          "Sample App - Home" in m._window_delta_text(d_open)
          and m._window_delta_text(d_open).startswith("opened:"),
          m._window_delta_text(d_open))
    check("window_delta_text reports no change when snapshots match",
          m._window_delta_text(m._window_diff(before, before))
          == "no visible window change detected")

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

    blind = {"ok": False, "count": 0, "windows": []}
    verdict_blind = m._verify_os_action(
        "open_app", {"app": "epiphany"}, fired, blind, blind,
        m._window_diff(blind, blind))
    check("blind enumeration fails action verification (fail-closed)",
          verdict_blind is False)

    close_res = {"success": True, "output": "", "exit_code": 0}
    v_close = m._verify_os_action(
        "close_window", {"title": "Sample App"}, close_res,
        after_opened, before, m._window_diff(after_opened, before))
    check("close verifies TRUE when the target window is gone", v_close is True)
    v_close_still = m._verify_os_action(
        "close_window", {"title": "Sample App"}, close_res,
        after_opened, after_opened, m._window_diff(after_opened, after_opened))
    check("close verifies FALSE when the target window is still present",
          v_close_still is False)

    tab_res = {"success": True, "output": '{"success": true, "target": "com.google.ChromeDev", "url": "https://example.com", "summary": "tab-opened-existing"}', "exit_code": 0}
    v_tab = m._verify_os_action(
        "open_url", {"url": "https://example.com"}, tab_res,
        before, after_none, m._window_diff(before, after_none))
    check("open_url verify is TRUE for already-running tab opens", v_tab is True)

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



# ==============================================================================
# Consolidated from test_mios_launch.py (T-1092)
# ==============================================================================
# AI-hint: Standalone unit test for the deterministic_action_route logic to ensure "open/launch" commands correctly strip filler phrases and map to open_app(n...
# AI-doc: usr/share/doc/mios/manual/agent-pipe.md

import os
import re
import sys

_RESULTS_launch: list = []

def _check_launch(name: str, ok: bool, detail: str = "") -> None:
    _RESULTS_launch.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))

def _load_fillers() -> list:
    """Load the REAL SSOT list the same way server.py `_load_launch_fillers` does."""
    path = os.environ.get("MIOS_TOML", "/usr/share/mios/mios.toml")
    if not os.path.exists(path):
        here = os.path.dirname(os.path.abspath(__file__))
        cand = os.path.join(here, "..", "..", "..", "share", "mios", "mios.toml")
        if os.path.exists(cand):
            path = cand
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    with open(path, "rb") as f:
        rt = (tomllib.load(f).get("routing") or {})
    return sorted(
        (str(p).lower().strip() for p in (rt.get("launch_filler_phrases") or []) if str(p).strip()),
        key=len, reverse=True)

_TRIGGERS = {"open", "launch"}

def _extract(user_text: str, fillers: list):
    t = (user_text or "").strip()
    if not t or len(t) > 80 or "?" in t:
        return None
    words = t.split()
    if len(words) < 2:
        return None
    head = words[0].lower().strip(".,:;!\"'")
    if head not in _TRIGGERS:
        return None
    rest = " ".join(words[1:]).strip()
    low = rest.lower()
    changed = True
    while changed and rest:
        changed = False
        for f in fillers:
            if f and low.endswith(f):
                rest = rest[:len(rest) - len(f)].rstrip(" ,.")
                low = rest.lower()
                changed = True
                break
    if not rest or len(rest.split()) > 3:
        return None
    if "://" in rest or re.search(r"\b(in|and|then|with|on|to)\b", low):
        return None
    return rest

def t_ssot() -> None:
    fillers = _load_fillers()
    _check_launch("fillers: SSOT list non-empty", len(fillers) > 0, f"n={len(fillers)}")
    _check_launch("fillers: longest-match-first ordering",
           fillers == sorted(fillers, key=len, reverse=True))
    _check_launch("fillers: 'for me' present (the e2e case)", "for me" in fillers)
    _check_launch("fillers: 'on my desktop' present (the e2e case)", "on my desktop" in fillers)

def t_extraction() -> None:
    fillers = _load_fillers()
    cases = {
        "open notepad": "notepad",                        # bare
        "open notepad for me": "notepad",                 # trailing courtesy stripped (was the bug)
        "open spotify on my desktop for me": "spotify",   # location+courtesy stripped (was the bug)
        "launch discord please": "discord",
        "open file explorer": "file explorer",            # 2-word app preserved
        "open file in editor": None,                      # true compound -> LLM router
        "open the calculator and minimize it": None,      # conjunction -> LLM router
        "open https://example.com": None,                 # url -> LLM router
        "what is open today": None,                       # not a launch -> None
        "open": None,                                     # bare trigger only -> None
    }
    for text, expected in cases.items():
        got = _extract(text, fillers)
        _check_launch(f"extract {text!r} -> {expected!r}", got == expected, f"got={got!r}")

def _main_launch() -> int:
    for t in (t_ssot, t_extraction):
        t()
    passed = sum(1 for _, ok, _ in _RESULTS_launch if ok)
    total = len(_RESULTS_launch)
    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


def _run_extra_launch():
    import os
    _saved_env = dict(os.environ)
    try:
        return _main_launch()
    except SystemExit as _e:
        return _e.code if _e.code is not None else 0
    finally:
        os.environ.clear()
        os.environ.update(_saved_env)



def _run_all_folded_oscontrol_suites():
    rc = _run_extra_launch()
    if rc not in (None, 0):
        import sys
        sys.exit(f"Folded test suite failed: exit code {rc}")

if __name__ == "__main__":
    _rc_main = main()
    _run_all_folded_oscontrol_suites()
    sys.exit(_rc_main)
