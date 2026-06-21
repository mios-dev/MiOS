#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_cua (WS-8 perceive->act->verify computer-use loop core). Pure stdlib, no server.py/VLM/pytest. Verifies the logical-action -> per-platform verb mapping (resolve_verb, fail-closed on unknown action/platform), observation-change/stall detection, the FAIL-SAFE verify-verdict parser (unparseable -> NOT done, never false success), the loop_status terminal decision (goal/budget/stall precedence), and the CuaTrace bookkeeping.
# AI-related: ./mios_cua.py
# AI-functions: check, main
"""Unit tests for mios_cua (WS-8)."""
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


def main():
    t_resolve_verb()
    t_observation()
    t_verify_verdict()
    t_loop_status()
    t_trace()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
