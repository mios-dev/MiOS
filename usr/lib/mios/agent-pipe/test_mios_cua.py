#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_cua (WS-8 perceive->act->verify computer-use loop core). Pure stdlib, no server.py/VLM/pytest. Verifies the logical-action -> per-platform verb mapping (resolve_verb, fail-closed on unknown action/platform), observation-change/stall detection, the FAIL-SAFE verify-verdict parser (unparseable -> NOT done, never false success), the loop_status terminal decision (goal/budget/stall precedence), and the CuaTrace bookkeeping.
# AI-related: ./mios_cua.py
# AI-functions: check, main
"""Unit tests for mios_cua (WS-8)."""
import asyncio
import json
import sys

import mios_cua as cua

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_resolve_verb():
    check("resolve: click on windows", cua.resolve_verb("click", "windows") == "windows_desktop_click")
    check("resolve: click on linux", cua.resolve_verb("click", "linux") == "linux_desktop_click")
    check("resolve: screenshot symmetric",
          cua.resolve_verb("screenshot", "windows") == "windows_desktop_screenshot"
          and cua.resolve_verb("screenshot", "linux") == "linux_desktop_screenshot")
    check("resolve: type/key/find map", all([
        cua.resolve_verb("type", "windows") == "windows_desktop_type_text",
        cua.resolve_verb("key", "linux") == "linux_desktop_press_key",
        cua.resolve_verb("find_element", "windows") == "windows_desktop_find_element_by_name",
    ]))
    # fail-closed
    check("resolve: unknown action -> None", cua.resolve_verb("teleport", "windows") is None)
    check("resolve: unknown platform -> None", cua.resolve_verb("click", "macos") is None)
    check("resolve: blank -> None", cua.resolve_verb("", "") is None)
    # every action maps for BOTH platforms (no half-defined action)
    for a in cua._ACTION_VERB:
        check(f"resolve: {a} defined for both platforms",
              cua.resolve_verb(a, "windows") and cua.resolve_verb(a, "linux"))


def t_observation():
    check("obs: same text -> no change", cua.observation_changed("screen A", "screen A") is False)
    check("obs: different text -> change", cua.observation_changed("screen A", "screen B") is True)
    check("obs: bytes digest stable",
          cua.observation_digest(b"abc") == cua.observation_digest(b"abc"))
    check("obs: None -> empty digest", cua.observation_digest(None) == "")


def t_verify_verdict():
    check("verify: json done=true", cua.parse_verify_verdict('{"done": true, "reason": "ok"}')["done"] is True)
    check("verify: json done=false", cua.parse_verify_verdict('{"done": false}')["done"] is False)
    check("verify: prose with embedded json",
          cua.parse_verify_verdict('I checked. {"done": true, "reason": "window open"} done.')["done"] is True)
    check("verify: GOAL_REACHED sentinel", cua.parse_verify_verdict("GOAL_REACHED")["done"] is True)
    check("verify: done=yes sentinel", cua.parse_verify_verdict("status done: yes")["done"] is True)
    # FAIL-SAFE: unparseable / ambiguous -> NOT done (never false success)
    check("verify: garbage -> NOT done (fail-safe)", cua.parse_verify_verdict("uhhh maybe?")["done"] is False)
    check("verify: empty -> NOT done", cua.parse_verify_verdict("")["done"] is False)
    check("verify: NOT_DONE wins over stray 'done'",
          cua.parse_verify_verdict("the task is NOT_DONE yet, done soon")["done"] is False)


def t_loop_status():
    # goal wins even at the budget edge
    check("status: goal reached wins",
          cua.loop_status(step=9, max_steps=10, goal_done=True, stall_count=5) == cua.GOAL_REACHED)
    check("status: budget exhausted",
          cua.loop_status(step=10, max_steps=10, goal_done=False, stall_count=0) == cua.MAX_STEPS)
    check("status: stalled",
          cua.loop_status(step=3, max_steps=10, goal_done=False, stall_count=2) == cua.STALLED)
    check("status: still running",
          cua.loop_status(step=2, max_steps=10, goal_done=False, stall_count=1) == cua.RUNNING)
    check("status: goal beats budget AND stall",
          cua.loop_status(step=10, max_steps=10, goal_done=True, stall_count=9) == cua.GOAL_REACHED)


def t_trace():
    tr = cua.CuaTrace("linux", "open settings and toggle wifi")
    tr.record("screenshot", "linux_desktop_screenshot", True, True)
    tr.record("click", "linux_desktop_click", True, True)
    tr.record("click", "linux_desktop_click", True, False)  # no change -> stall-ish
    tr.finish(cua.GOAL_REACHED)
    d = tr.to_dict()
    check("trace: counts steps", d["n_steps"] == 3)
    check("trace: reached flag", d["reached"] is True and d["status"] == cua.GOAL_REACHED)
    check("trace: platform/goal carried", d["platform"] == "linux" and d["goal"].startswith("open settings"))
    # a non-reached terminal status -> reached False (no false success)
    tr2 = cua.CuaTrace("windows", "x").finish(cua.MAX_STEPS)
    check("trace: budget exhaust -> not reached", tr2.to_dict()["reached"] is False)


# ── /v1/computer-use route LOGIC (moved verbatim from server.py) ─────────
class _FakeReq:
    """Request stand-in: async json() returns the payload (or raises to test the
    bad-body degrade path)."""
    def __init__(self, obj, raise_json=False):
        self._obj = obj
        self._raise = raise_json

    async def json(self):
        if self._raise:
            raise ValueError("bad json")
        return self._obj


def _cbody(resp):
    """Decode a (real fastapi) JSONResponse rendered body into a dict."""
    return json.loads(bytes(resp.body).decode("utf-8"))


async def _fake_loop_ok(goal, platform="windows", max_steps=None, session_id=None):
    """Stand-in _cua_loop: a reached trace (the shape CuaTrace.to_dict() yields)."""
    return {"platform": platform, "goal": goal, "status": cua.GOAL_REACHED,
            "n_steps": 1, "steps": [], "reached": True}


async def _fake_loop_boom(*a, **k):
    raise RuntimeError("boom")


def t_computer_use():
    # DEFAULT-OFF gate: disabled -> the honest disabled notice (200, enabled False);
    # the loop is never invoked. _cua_loop is module-local now (the I/O half moved
    # home), so the fake is injected by rebinding the module global directly rather
    # than via configure() (the old cua_loop= param was de-entangled away).
    cua.configure(cua_enable=False)
    cua._cua_loop = _fake_loop_boom
    r = asyncio.run(cua.v1_computer_use_logic(_FakeReq({"goal": "x"})))
    b = _cbody(r)
    check("cua route: disabled -> honest notice, loop not run",
          b.get("enabled") is False and getattr(r, "status_code", None) == 200
          and "error" not in b)

    # ENABLED + missing goal -> 400 (no loop run).
    cua.configure(cua_enable=True)
    cua._cua_loop = _fake_loop_ok
    r = asyncio.run(cua.v1_computer_use_logic(_FakeReq({"goal": "   "})))
    b = _cbody(r)
    check("cua route: enabled + blank goal -> 400 missing goal",
          getattr(r, "status_code", None) == 400 and "goal" in (b.get("error") or ""))

    # ENABLED + goal -> runs the (injected) loop, enabled True + trace merged.
    r = asyncio.run(cua.v1_computer_use_logic(
        _FakeReq({"goal": "open settings", "platform": "linux"})))
    b = _cbody(r)
    check("cua route: enabled + goal -> loop trace merged (enabled True)",
          b.get("enabled") is True and b.get("status") == cua.GOAL_REACHED
          and b.get("reached") is True and b.get("platform") == "linux")

    # loop raises -> degrade to {error} at 200 (never 500 the surface).
    cua._cua_loop = _fake_loop_boom
    r = asyncio.run(cua.v1_computer_use_logic(_FakeReq({"goal": "x"})))
    b = _cbody(r)
    check("cua route: loop error -> 200 honest error (no 500)",
          getattr(r, "status_code", None) == 200 and "boom" in (b.get("error") or ""))


# ── computer-use I/O half (moved verbatim from server.py) ────────────────
def t_extract_png():
    # PNG path harvested out of a screenshot verb's stdout (linux + windows forms).
    check("extract_png: linux path",
          cua._cua_extract_png({"output": "saved to /tmp/shot.png ok"}) == "/tmp/shot.png")
    check("extract_png: windows path",
          cua._cua_extract_png({"output": r"wrote C:\Users\m\a.png done"}) == r"C:\Users\m\a.png")
    # no png / empty / None -> None (degrade-open, never guess a path)
    check("extract_png: no png -> None", cua._cua_extract_png({"output": "nothing here"}) is None)
    check("extract_png: empty+None -> None",
          cua._cua_extract_png({}) is None and cua._cua_extract_png(None) is None)


async def _fake_dispatch_nopng(verb, args, session_id=None):
    """Injected verb-dispatch stand-in: a screenshot that wrote no path."""
    return {"output": "screenshot taken but no path here", "success": True}


def t_screenshot_uri_injected():
    # The moved I/O helper reads the INJECTED verb-dispatch chokepoint. A dispatch
    # result carrying no PNG path degrades open -> (None, output).
    cua.configure(dispatch_mios_verb_inner=_fake_dispatch_nopng)
    uri, obs = asyncio.run(cua._cua_screenshot_uri("windows", None))
    check("screenshot_uri: no png in result -> (None, output)",
          uri is None and "no path here" in obs)
    # unknown platform -> resolve_verb None -> (None, '') BEFORE any dispatch fires.
    uri2, obs2 = asyncio.run(cua._cua_screenshot_uri("macos", None))
    check("screenshot_uri: unknown platform -> (None, '')", uri2 is None and obs2 == "")


def main():
    t_resolve_verb()
    t_observation()
    t_verify_verdict()
    t_loop_status()
    t_trace()
    t_computer_use()
    t_extract_png()
    t_screenshot_uri_injected()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
