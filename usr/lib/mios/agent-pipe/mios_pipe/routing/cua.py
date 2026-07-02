# AI-hint: WS-8 computer-use perceive->act->verify loop core (the PURE half). Unifies GUI control across the Windows host desktop (windows_desktop_* verbs) and the Linux/Wayland desktop (linux_desktop_* verbs) behind ONE logical action vocabulary (screenshot/click/type/key/find_element/click_element/list_windows) via resolve_verb(action, platform) -- fail-closed (unknown action/platform -> None, never guess a verb). Owns the loop CONTROL: step budget, stall (no-screen-change) detection, and the terminal decision (loop_status), plus parse_verify_verdict which is FAIL-SAFE (unparseable verify -> NOT done, so a goal is never falsely declared reached). This module ALSO owns the I/O half (moved verbatim from server.py): _cua_loop drives the live perceive->act->verify loop, _cua_screenshot_uri/_cua_extract_png capture+locate a screenshot PNG, and _cua_vlm_json makes the VLM call -- all reading server-owned chokepoints (the verb-dispatch _dispatch_mios_verb_inner, the shared httpx _get_client, the _vision_backend_failed gate) + config constants (VISION_MODEL/VISION_ENDPOINT/CUA_MAX_STEPS/_BACKEND_KEY) injected via configure(); server.py keeps only the thin @app wrapper. Deterministic policy + injected I/O in the mios_preempt/mios_sandbox sibling style.
# AI-related: ./server.py, ./mios_sandbox.py, ./mios_dispatch.py, ./mios_vision.py, /usr/share/mios/mios.toml, ./test_mios_cua.py
# AI-functions: resolve_verb, observation_digest, observation_changed, parse_verify_verdict, loop_status, class CuaTrace, configure, v1_computer_use_logic, cua_router, v1_computer_use, _cua_extract_png, _cua_screenshot_uri, _cua_vlm_json, _cua_loop
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

import asyncio
import hashlib
import json
import logging
import re
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

# Self-import: the moved I/O half (appended below) was written in server.py and
# references this module's pure-core names qualified as ``mios_cua.<name>``
# (resolve_verb / observation_digest / CuaTrace / PLATFORMS / loop_status / ...).
# Keeping the bodies byte-identical, a self-reference binds those calls to this
# (fully-initialised by call time) module. Safe: ``mios_cua`` is already in
# sys.modules while this module executes, and every consumer is a runtime call.
import mios_cua  # noqa: E402

log = logging.getLogger("mios-agent-pipe")


# -- Dependency-injection seam --------------------------------------
# The /v1/computer-use route (v1_computer_use_logic) reads the CUA_ENABLE gate flag
# and calls the perceive->act->verify loop _cua_loop -- which now lives IN this
# module (appended below). The loop + its screenshot/VLM helpers read server-owned
# chokepoints (the verb-dispatch _dispatch_mios_verb_inner, the shared httpx
# _get_client, the _vision_backend_failed gate) and config constants
# (VISION_MODEL / VISION_ENDPOINT / CUA_MAX_STEPS / _BACKEND_KEY) -- those stay
# OWNED by server.py (every config const is in the importable-surface golden) and
# are injected here via configure() AFTER each is defined (one-way boundary: this
# module never imports server). The None placeholders keep a standalone
# ``import mios_cua`` working for the pure-core unit tests; every consumer is a
# runtime call, so nothing fires before configure() runs.
CUA_ENABLE = None
_dispatch_mios_verb_inner = None
_get_client = None
_vision_backend_failed = None
_BACKEND_KEY = None
VISION_MODEL = None
VISION_ENDPOINT = None
CUA_MAX_STEPS = None
_HIDPI_SCALE_FACTOR = 1.0


def configure(*, cua_enable=None, dispatch_mios_verb_inner=None, get_client=None,
              vision_backend_failed=None, backend_key=None, vision_model=None,
              vision_endpoint=None, cua_max_steps=None, hidpi_scale_factor=None) -> None:
    """Inject the computer-use route + I/O-loop deps under their EXACT original
    names: the CUA_ENABLE gate flag, the verb-dispatch chokepoint
    (_dispatch_mios_verb_inner), the shared httpx client (_get_client), the vision
    backend-failure gate (_vision_backend_failed), and the config constants the
    loop reads (_BACKEND_KEY / VISION_MODEL / VISION_ENDPOINT / CUA_MAX_STEPS).
    Each field is gated on ``is not None`` (an empty backend key or a False flag is
    a legitimate value), so an unset keyword leaves the prior binding. The loop
    (_cua_loop) is module-local now, so it is NOT injected back."""
    global CUA_ENABLE, _dispatch_mios_verb_inner, _get_client, _vision_backend_failed
    global _BACKEND_KEY, VISION_MODEL, VISION_ENDPOINT, CUA_MAX_STEPS, _HIDPI_SCALE_FACTOR
    if cua_enable is not None:
        CUA_ENABLE = cua_enable
    if dispatch_mios_verb_inner is not None:
        _dispatch_mios_verb_inner = dispatch_mios_verb_inner
    if get_client is not None:
        _get_client = get_client
    if vision_backend_failed is not None:
        _vision_backend_failed = vision_backend_failed
    if backend_key is not None:
        _BACKEND_KEY = backend_key
    if vision_model is not None:
        VISION_MODEL = vision_model
    if vision_endpoint is not None:
        VISION_ENDPOINT = vision_endpoint
    if cua_max_steps is not None:
        CUA_MAX_STEPS = cua_max_steps
    if hidpi_scale_factor is not None:
        _HIDPI_SCALE_FACTOR = hidpi_scale_factor


_W_TENSOR = 1000
_H_TENSOR = 1000
_W_ORIG = 1920
_H_ORIG = 1080
_LAST_SCREENSHOT_PATH = None


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


async def v1_computer_use_logic(request: Request) -> JSONResponse:
    """WS-8 perceive->act->verify computer-use. Body: {goal, platform?
    (windows|linux), max_steps?}. Runs the closed VLM loop and returns the trace
    {status, reached, steps[...]}. DEFAULT-OFF (MIOS_CUA_ENABLE): returns a clear
    disabled notice until the operator opts in AND a GPU VLM is loaded. Never
    claims a goal it did not verify (fail-safe in mios_cua)."""
    if not CUA_ENABLE:
        return JSONResponse({"object": "mios.computer_use",
                             "enabled": False,
                             "detail": "computer-use loop is disabled "
                                       "([dispatch].cua_enable / MIOS_CUA_ENABLE); "
                                       "enable it and load a GPU VLM to use it."},
                            status_code=200)
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = {}
    goal = str((body or {}).get("goal") or "").strip()
    if not goal:
        return JSONResponse({"object": "mios.computer_use",
                             "error": "missing 'goal'"}, status_code=400)
    try:
        trace = await _cua_loop(goal,
                                platform=str((body or {}).get("platform") or "windows"),
                                max_steps=(body or {}).get("max_steps"),
                                session_id=(body or {}).get("session_id"))
        return JSONResponse({"object": "mios.computer_use", "enabled": True, **trace})
    except Exception as e:  # noqa: BLE001 -- never 500 the surface
        return JSONResponse({"object": "mios.computer_use", "error": str(e)},
                            status_code=200)


# -- @app -> APIRouter migration (refactor R13): the /v1/computer-use route ---------
# The WS-8 perceive->act->verify route moved off server.py's @app onto this co-located
# router (cohesive with the CUA loop core + logic it gates). server.py imports
# cua_router + the handler NAME and mounts it via app.include_router(cua_router); the
# name is re-imported there so server's importable `provided` surface is unchanged and
# the served path/method set is byte-identical (the live-app route gate proves it). The
# body calls the module-resident v1_computer_use_logic DIRECTLY (same module -- no
# sys.modules hop). One-way boundary: this module never imports server (its CUA gate +
# deps arrive via configure()). APIRouter()/method decorators are structural, not config.
cua_router = APIRouter()


@cua_router.post("/v1/computer-use")
async def v1_computer_use(request: Request) -> JSONResponse:
    """WS-8 perceive->act->verify computer-use route. Calls v1_computer_use_logic
    (same module)."""
    return await v1_computer_use_logic(request)


def _cua_extract_png(result: dict) -> "Optional[str]":
    """Pull a screenshot PNG path out of a screenshot verb's result. The
    *_desktop_screenshot verbs write a PNG + name it in stdout; degrade-open ->
    None when no path is found."""
    out = str((result or {}).get("output") or "")
    m = re.search(r"(/[^\s\"']+\.png|[A-Za-z]:[\\/][^\s\"']+\.png)", out)
    return m.group(1) if m else None


async def _cua_screenshot_uri(platform: str, session_id: "Optional[str]") -> "tuple":
    """Take a screenshot via the platform's verb, read the PNG, return
    (data_uri, raw_observation). Degrade-open -> (None, ""). The data URI is what
    the VLM 'sees'; the raw observation digest drives stall detection."""
    verb = mios_cua.resolve_verb("screenshot", platform)
    if not verb:
        return None, ""
    res = await _dispatch_mios_verb_inner(verb, {}, session_id=session_id)
    path = _cua_extract_png(res)
    if not path:
        return None, str((res or {}).get("output") or "")
    try:
        import base64
        import subprocess
        import struct
        with open(path, "rb") as fh:
            raw = fh.read()
            
        global _LAST_SCREENSHOT_PATH, _W_TENSOR, _H_TENSOR, _W_ORIG, _H_ORIG
        _LAST_SCREENSHOT_PATH = path
        
        try:
            # Call mios-smart-resize CLI via subprocess
            p = subprocess.Popen(
                ["/usr/libexec/mios/mios-smart-resize"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            out_bytes, err_bytes = p.communicate(input=raw)
            if p.returncode == 0:
                raw = out_bytes
                meta = json.loads(err_bytes.decode("utf-8").strip())
                _W_TENSOR = meta.get("W_tensor", _W_TENSOR)
                _H_TENSOR = meta.get("H_tensor", _H_TENSOR)
                _W_ORIG = meta.get("W_orig", _W_ORIG)
                _H_ORIG = meta.get("H_orig", _H_ORIG)
        except Exception:
            # Fallback to direct struct PNG header parsing
            try:
                if len(raw) >= 24 and raw[12:16] == b"IHDR":
                    _W_ORIG, _H_ORIG = struct.unpack(">II", raw[16:24])
            except Exception:
                pass
                
        return "data:image/png;base64," + base64.b64encode(raw).decode(), \
            mios_cua.observation_digest(raw)
    except Exception:  # noqa: BLE001 -- degrade-open: no image -> VLM stop
        return None, path


async def _cua_vlm_json(system: str, user_text: str,
                        image_uri: "Optional[str]") -> dict:
    """One VLM call returning the model's parsed JSON object (a plan or a verify
    verdict). Degrade-open -> {} on any backend/parse failure (the caller's
    fail-safe handles an empty verdict as NOT-done)."""
    if not (image_uri and (VISION_MODEL or "").strip()):
        return {}
    content = [{"type": "text", "text": user_text},
               {"type": "image_url", "image_url": {"url": image_uri}}]
    vbody = {"model": VISION_MODEL, "stream": False,
             "messages": [{"role": "system", "content": system},
                          {"role": "user", "content": content}]}
    headers = {"content-type": "application/json"}
    if _BACKEND_KEY:
        headers["authorization"] = f"Bearer {_BACKEND_KEY}"
    try:
        client = await _get_client()
        r = await client.post(f"{VISION_ENDPOINT}/v1/chat/completions",
                              content=json.dumps(vbody).encode("utf-8"),
                              headers=headers)
        if _vision_backend_failed(r.status_code, r.text):
            return {}
        txt = str(((r.json().get("choices") or [{}])[0].get("message") or {})
                  .get("content") or "")
        m = re.search(r"\{.*\}", txt, re.DOTALL)
        return json.loads(m.group(0)) if m else {}
    except Exception:  # noqa: BLE001 -- degrade-open
        return {}


def bounds_contain(bounds, x, y):
    if not bounds:
        return False
    if isinstance(bounds, (list, tuple)) and len(bounds) == 4:
        b0, b1, b2, b3 = bounds
        if b2 > b0 and b3 > b1:
            return b0 <= x <= b2 and b1 <= y <= b3
        else:
            return b0 <= x <= (b0 + b2) and b1 <= y <= (b1 + b3)
    if isinstance(bounds, dict):
        left = bounds.get("left") or bounds.get("x")
        top = bounds.get("top") or bounds.get("y")
        right = bounds.get("right")
        bottom = bounds.get("bottom")
        width = bounds.get("width") or bounds.get("w")
        height = bounds.get("height") or bounds.get("h")
        if left is not None and top is not None:
            if right is not None and bottom is not None:
                return left <= x <= right and top <= y <= bottom
            if width is not None and height is not None:
                return left <= x <= (left + width) and top <= y <= (top + height)
    return False


async def wait_for_stable_element(platform: str, session_id: Optional[str] = None):
    prev_digest = None
    verb = mios_cua.resolve_verb("list_windows", platform)
    if not verb:
        return
    for _ in range(10):
        res = await _dispatch_mios_verb_inner(verb, {}, session_id=session_id)
        out = res.get("output", "")
        cur_digest = hashlib.sha256(out.encode("utf-8", "replace")).hexdigest()
        if prev_digest and cur_digest == prev_digest:
            break
        prev_digest = cur_digest
        await asyncio.sleep(0.3)


async def _execute_click_hierarchy(verb: str, args: dict, platform: str, session_id: Optional[str] = None) -> dict:
    # Scale coordinates
    x_raw = float(args.get("x", 0))
    y_raw = float(args.get("y", 0))
    
    scale_factor = _HIDPI_SCALE_FACTOR or 1.0
    model_name = (VISION_MODEL or "").lower()
    is_qwen3 = "qwen3" in model_name or "qwen-3" in model_name
    
    if is_qwen3:
        x_scaled = round((x_raw / 1000.0) * _W_ORIG * scale_factor)
        y_scaled = round((y_raw / 1000.0) * _H_ORIG * scale_factor)
    else:
        x_scaled = round((x_raw / _W_TENSOR) * _W_ORIG * scale_factor)
        y_scaled = round((y_raw / _H_TENSOR) * _H_ORIG * scale_factor)
        
    args_scaled = dict(args)
    args_scaled["x"] = x_scaled
    args_scaled["y"] = y_scaled
    
    # Try Tier 2: Accessibility Tree (UIA/AT-SPI) click
    list_verb = mios_cua.resolve_verb("list_windows", platform)
    if list_verb:
        res_list = await _dispatch_mios_verb_inner(list_verb, {}, session_id=session_id)
        elements = []
        try:
            data = json.loads(res_list.get("output", ""))
            if isinstance(data, dict):
                elements = data.get("elements") or data.get("data") or []
            elif isinstance(data, list):
                elements = data
        except Exception:
            pass
            
        matching_elements = []
        for el in elements:
            if isinstance(el, dict):
                bounds = el.get("bounds")
                if bounds_contain(bounds, x_scaled, y_scaled):
                    matching_elements.append(el)
                    
        if matching_elements:
            target_el = matching_elements[-1]
            el_name = target_el.get("name") or target_el.get("automation_id")
            if el_name:
                click_el_verb = mios_cua.resolve_verb("click_element", platform)
                if click_el_verb:
                    res_click = await _dispatch_mios_verb_inner(
                        click_el_verb, {"name": el_name}, session_id=session_id)
                    if res_click.get("success"):
                        return res_click
                        
    # Tier 3: Vision grounding coordinate click fallback
    return await _dispatch_mios_verb_inner(verb, args_scaled, session_id=session_id)


async def _cua_loop(goal: str, platform: str = "windows",
                    max_steps: "Optional[int]" = None,
                    session_id: "Optional[str]" = None) -> dict:
    """Run the perceive->act->verify loop until the VLM verifies the goal or a
    budget/stall guard fires. Returns mios_cua.CuaTrace.to_dict(). VLM-gated +
    degrade-open: no vision model / no screenshot -> an honest non-reached stop
    (it never fabricates success)."""
    platform = (platform or "windows").strip().lower()
    if platform not in mios_cua.PLATFORMS:
        platform = "windows"
    budget = int(max_steps or CUA_MAX_STEPS)
    trace = mios_cua.CuaTrace(platform, goal)
    plan_sys = (f"You drive the {platform} desktop to accomplish a GOAL. Look at "
                "the screenshot. Reply ONLY with a JSON object: either "
                '{"action":"click|type|key|click_element","args":{...},"why":"..."} '
                'for the NEXT single step, or {"done":true} if the GOAL is already '
                "satisfied on screen. Use pixel coords for click {x,y}; text for "
                'type {text}; a key name for key {key}; an element name for '
                "click_element {name}. One step at a time.")
    verify_sys = (f"You verify a {platform} desktop GOAL. Look at the screenshot and "
                  'reply ONLY JSON {"done":true|false,"reason":"..."} -- done=true '
                  "ONLY if the GOAL is clearly satisfied on screen right now.")
    prev_obs, stall = None, 0
    step = 0
    while True:
        step += 1
        uri, obs = await _cua_screenshot_uri(platform, session_id)
        if uri is None:                         # cannot perceive -> honest stop
            trace.record("screenshot", mios_cua.resolve_verb("screenshot", platform),
                         False, False)
            return trace.finish(mios_cua.STALLED).to_dict()
        plan = await _cua_vlm_json(plan_sys, f"GOAL: {goal}", uri)
        if plan.get("done"):                    # VLM says already satisfied -> verify
            v = mios_cua.parse_verify_verdict(json.dumps(
                await _cua_vlm_json(verify_sys, f"GOAL: {goal}", uri)))
            trace.record("verify", None, True, False)
            return trace.finish(mios_cua.GOAL_REACHED if v["done"]
                                else mios_cua.MAX_STEPS).to_dict()
        action = str(plan.get("action") or "").strip().lower()
        verb = mios_cua.resolve_verb(action, platform)
        if not verb:                            # no plan / bad action
            stall += 1
        elif action == "click":
            # Retry logic up to 3 times
            retries = 0
            click_success = False
            res = {}
            obs2 = obs
            uri2 = uri
            changed = False
            
            while retries < 3:
                res = await _execute_click_hierarchy(verb, dict(plan.get("args") or {}), platform, session_id)
                
                # Wait-for-stable-element polling
                await wait_for_stable_element(platform, session_id)
                
                # Capture screenshot to verify change
                uri2, obs2 = await _cua_screenshot_uri(platform, session_id)
                changed = mios_cua.observation_changed(obs, obs2)
                
                if res.get("success") and changed:
                    click_success = True
                    break
                    
                # Click failed or no state change -> retry with re-grounding!
                retries += 1
                if retries < 3:
                    plan = await _cua_vlm_json(plan_sys, f"GOAL: {goal}", uri2 or uri)
                    if plan.get("done") or str(plan.get("action") or "").strip().lower() != "click":
                        break
                        
            if not click_success and retries >= 3:
                raise RuntimeError("HITL escalation: 3 click retries exhausted without state change")
                
            stall = 0 if changed else stall + 1
            trace.record(action, verb, bool((res or {}).get("success")), changed)
            v = mios_cua.parse_verify_verdict(json.dumps(
                await _cua_vlm_json(verify_sys, f"GOAL: {goal}", uri2 or uri)))
            status = mios_cua.loop_status(step=step, max_steps=budget,
                                          goal_done=v["done"], stall_count=stall)
            if status != mios_cua.RUNNING:
                return trace.finish(status).to_dict()
            prev_obs = obs2
            continue
        else:
            res = await _dispatch_mios_verb_inner(
                verb, dict(plan.get("args") or {}), session_id=session_id)
            # VERIFY: re-perceive, detect a no-change stall, ask the VLM the verdict.
            uri2, obs2 = await _cua_screenshot_uri(platform, session_id)
            changed = mios_cua.observation_changed(obs, obs2)
            stall = 0 if changed else stall + 1
            trace.record(action, verb, bool((res or {}).get("success")), changed)
            v = mios_cua.parse_verify_verdict(json.dumps(
                await _cua_vlm_json(verify_sys, f"GOAL: {goal}", uri2 or uri)))
            status = mios_cua.loop_status(step=step, max_steps=budget,
                                          goal_done=v["done"], stall_count=stall)
            if status != mios_cua.RUNNING:
                return trace.finish(status).to_dict()
            prev_obs = obs2
            continue
        status = mios_cua.loop_status(step=step, max_steps=budget,
                                      goal_done=False, stall_count=stall)
        if status != mios_cua.RUNNING:
            return trace.finish(status).to_dict()
        prev_obs = obs
