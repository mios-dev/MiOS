# AI-hint: WS-8 computer-use perceive->act->verify loop core (the PURE half). Unifies GUI control across the Windows host desktop (windows_desktop_* verbs) and the Linux/Wayland desktop (linux_desktop_* verbs) behind ONE logical action vocabulary (screenshot/click/type/key/find_element/click_element/list_windows) via resolve_verb(action, platform) -- fail-closed (unknown action/platform -> None, never guess a verb). Owns the loop CONTROL: step budget, stall (no-screen-change) detection, and the terminal decision (loop_status), plus parse_verify_verdict which is FAIL-SAFE (unparseable verify -> NOT done, so a goal is never falsely declared reached). server.py owns the I/O (the VLM perceive/verify call + dispatching the action verbs + capturing screenshots); this module is the deterministic, testable policy in the mios_preempt/mios_sandbox sibling style.
# AI-related: ./server.py, ./mios_sandbox.py, /usr/share/mios/mios.toml, ./test_mios_cua.py
# AI-functions: resolve_verb, observation_digest, observation_changed, parse_verify_verdict, loop_status, class CuaTrace
"""mios_cua -- unified computer-use perceive->act->verify loop (WS-8).

A VLM-grounded computer-use agent runs a closed loop: PERCEIVE (screenshot ->
the VLM locates UI / plans the next action) -> ACT (dispatch a click/type/key
verb) -> VERIFY (screenshot -> the VLM checks whether the goal state holds) ->
repeat until the goal is reached or a budget/stall guard fires. Before WS-8 the
pieces existed (the Holo1.5 VLM lane + windows_desktop_* / linux_desktop_*
verbs) but were never unified into one cross-platform loop.

This module is the PURE control layer:
  * resolve_verb()      -- ONE logical action vocabulary -> the right verb per
                           platform (Windows host vs in-VM Linux desktop),
                           fail-closed so a caller never invents a verb.
  * loop_status()       -- the terminal decision after each VERIFY: goal reached
                           / out of step budget / stalled (no screen change) /
                           keep going.
  * parse_verify_verdict() -- interpret the VLM's verify answer; FAIL-SAFE: an
                           unparseable verdict is NOT-done, so the loop can never
                           falsely declare success (it just runs to the budget).

server.py owns the I/O (the VLM call, the verb dispatch, the screenshots) +
the flag-gating; this is the deterministic, unit-testable policy.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Optional

PLATFORMS = ("windows", "linux")

# ONE logical action -> the per-platform verb. Both desktops expose a symmetric
# surface, so the loop is written ONCE against logical actions and resolved to
# the host's verbs at dispatch. (Windows host = windows_desktop_*; the in-VM
# Linux/Wayland desktop = linux_desktop_*.)
_ACTION_VERB = {
    "screenshot":    {"windows": "windows_desktop_screenshot",
                      "linux": "linux_desktop_screenshot"},
    "click":         {"windows": "windows_desktop_click",
                      "linux": "linux_desktop_click"},
    "type":          {"windows": "windows_desktop_type_text",
                      "linux": "linux_desktop_type_text"},
    "key":           {"windows": "windows_desktop_press_key",
                      "linux": "linux_desktop_press_key"},
    "find_element":  {"windows": "windows_desktop_find_element_by_name",
                      "linux": "linux_desktop_find_element_by_name"},
    "click_element": {"windows": "windows_desktop_click_element",
                      "linux": "linux_desktop_click"},
    "list_windows":  {"windows": "windows_desktop_list_elements",
                      "linux": "linux_desktop_window_list"},
}

# Terminal reasons returned by loop_status.
RUNNING = "running"
GOAL_REACHED = "goal_reached"
MAX_STEPS = "max_steps"
STALLED = "stalled"


def resolve_verb(action: str, platform: str) -> "Optional[str]":
    """Map a logical computer-use action to the platform's verb name. Fail-closed:
    an unknown action OR an unknown platform -> None, so the caller refuses to
    dispatch rather than guessing a verb that doesn't exist."""
    a = str(action or "").strip().lower()
    p = str(platform or "").strip().lower()
    return _ACTION_VERB.get(a, {}).get(p)


def observation_digest(obs: object) -> str:
    """A stable digest of one observation (a screenshot's bytes/path/hash, or the
    VLM's textual description of the screen). Used to detect a no-change stall."""
    if obs is None:
        return ""
    if isinstance(obs, (bytes, bytearray)):
        return hashlib.sha256(bytes(obs)).hexdigest()
    return hashlib.sha256(str(obs).strip().encode("utf-8", "replace")).hexdigest()


def observation_changed(prev: object, cur: object) -> bool:
    """Did the screen change after the last action? Identical observations mean
    the action had no visible effect -- a stall signal."""
    return observation_digest(prev) != observation_digest(cur)


def parse_verify_verdict(text: object) -> dict:
    """Interpret a VLM verify answer into {done: bool, reason: str}. Accepts a
    JSON object {"done": ..., "reason": ...} anywhere in the text, else the
    sentinels GOAL_REACHED / DONE=YES / NOT_DONE (case-insensitive).

    FAIL-SAFE: anything unparseable -> done=False. The loop therefore NEVER
    falsely declares the goal reached on a malformed/ambiguous verify; it simply
    keeps working until the step budget (the operator's 'never claim success you
    didn't achieve' rule, enforced structurally)."""
    s = str(text or "")
    m = re.search(r"\{[^{}]*\"done\"[^{}]*\}", s, re.DOTALL)
    if m:
        try:
            d = json.loads(m.group(0))
            return {"done": bool(d.get("done")),
                    "reason": str(d.get("reason", ""))[:300]}
        except (ValueError, TypeError):
            pass
    low = s.lower()
    if re.search(r"\bgoal[_ ]?reached\b", low) or re.search(r"\bdone\s*[:=]\s*(yes|true)\b", low):
        if "not_done" not in low and "not done" not in low:
            return {"done": True, "reason": "sentinel"}
    return {"done": False, "reason": "unparsed-or-not-done"}


def loop_status(*, step: int, max_steps: int, goal_done: bool,
                stall_count: int, max_stall: int = 2) -> str:
    """The terminal decision after each VERIFY phase. Goal-reached wins (a final
    successful act terminates cleanly); else the step budget; else a stall guard
    (max_stall consecutive acts with no screen change -> the loop is stuck, stop
    rather than burn the budget); else keep going."""
    if goal_done:
        return GOAL_REACHED
    if step >= max_steps:
        return MAX_STEPS
    if stall_count >= max_stall:
        return STALLED
    return RUNNING


class CuaTrace:
    """Append-only record of a computer-use loop for the result/audit: each step's
    (action, verb, ok, changed) + the terminal status. Pure bookkeeping."""

    __slots__ = ("platform", "goal", "steps", "status")

    def __init__(self, platform: str, goal: str) -> None:
        self.platform = str(platform)
        self.goal = str(goal)
        self.steps: "list[dict]" = []
        self.status = RUNNING

    def record(self, action: str, verb: "Optional[str]", ok: bool,
               changed: bool) -> None:
        self.steps.append({"action": str(action), "verb": verb,
                           "ok": bool(ok), "changed": bool(changed)})

    def finish(self, status: str) -> "CuaTrace":
        self.status = status
        return self

    def to_dict(self) -> dict:
        return {"platform": self.platform, "goal": self.goal[:300],
                "status": self.status, "n_steps": len(self.steps),
                "steps": self.steps, "reached": self.status == GOAL_REACHED}
