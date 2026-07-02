#!/usr/bin/env /usr/lib/mios/agents/.venv/bin/python3
# AI-hint: Verification test suite for mios_cua hierarchy routing, verify-after-action, and coordinate scaling.
# AI-related: /usr/lib/mios/agent-pipe/test_mios_cua_hierarchy.py, /usr/lib/mios/agent-pipe/mios_pipe/routing/cua.py

import sys
import os
import json
import asyncio
import contextvars
import mios_cua

_fails = 0

def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))

def test_coordinate_scaling():
    # Set mock dimensions
    mios_cua._W_ORIG = 1920
    mios_cua._H_ORIG = 1080
    mios_cua._W_TENSOR = 1280
    mios_cua._H_TENSOR = 720
    mios_cua._HIDPI_SCALE_FACTOR = 1.0
    
    # Qwen3-VL model (normalized 0-1000)
    mios_cua.configure(vision_model="qwen3-vl")
    
    # Mock dispatch logic
    captured = {}
    async def _mock_dispatch(verb, args, session_id=None):
        captured["verb"] = verb
        captured["args"] = args
        return {"success": True, "output": "clicked"}
        
    mios_cua._dispatch_mios_verb_inner = _mock_dispatch
    
    # We call _execute_click_hierarchy directly to isolate coordinate scaling
    asyncio.run(mios_cua._execute_click_hierarchy("windows_desktop_click", {"x": 512, "y": 384}, "windows"))
    
    check("qwen3 scaling: x coord", captured["args"]["x"] == 983)
    check("qwen3 scaling: y coord", captured["args"]["y"] == 415)
    
    # Qwen2.5-VL model (absolute pixels relative to tensor size)
    mios_cua.configure(vision_model="qwen2.5-vl")
    asyncio.run(mios_cua._execute_click_hierarchy("windows_desktop_click", {"x": 512, "y": 384}, "windows"))
    
    # 512 / 1280 * 1920 = 768
    # 384 / 720 * 1080 = 576
    check("qwen2.5 scaling: x coord", captured["args"]["x"] == 768)
    check("qwen2.5 scaling: y coord", captured["args"]["y"] == 576)

def test_a11y_hierarchy_routing():
    # Setup UIA tree mock
    mios_cua._W_ORIG = 1920
    mios_cua._H_ORIG = 1080
    mios_cua._HIDPI_SCALE_FACTOR = 1.0
    mios_cua.configure(vision_model="qwen3-vl")
    
    captured_dispatches = []
    
    # Elements returned by windows_desktop_list_elements
    elements_json = json.dumps({
        "elements": [
            {"name": "SaveButton", "bounds": [900, 400, 1000, 450]}
        ]
    })
    
    async def _mock_dispatch(verb, args, session_id=None):
        captured_dispatches.append((verb, args))
        if verb == "windows_desktop_list_elements":
            return {"success": True, "output": elements_json}
        if verb == "windows_desktop_click_element":
            return {"success": True, "output": "clicked element"}
        return {"success": True, "output": "clicked fallback"}
        
    mios_cua._dispatch_mios_verb_inner = _mock_dispatch
    
    # Click at (512, 384) which scales to (983, 415). Bounding box [900, 400, 1000, 450] contains (983, 415)!
    res = asyncio.run(mios_cua._execute_click_hierarchy("windows_desktop_click", {"x": 512, "y": 384}, "windows"))
    
    verbs = [d[0] for d in captured_dispatches]
    check("hierarchy: tried elements list", "windows_desktop_list_elements" in verbs)
    check("hierarchy: clicked element directly", "windows_desktop_click_element" in verbs)
    check("hierarchy: did NOT fall back to vision coordinate click", "windows_desktop_click" not in verbs)
    
    # Now try coordinates outside the button -> should fall back to vision
    captured_dispatches.clear()
    res = asyncio.run(mios_cua._execute_click_hierarchy("windows_desktop_click", {"x": 100, "y": 100}, "windows"))
    verbs = [d[0] for d in captured_dispatches]
    check("hierarchy fallback: tried elements list", "windows_desktop_list_elements" in verbs)
    check("hierarchy fallback: fell back to vision coordinate click", "windows_desktop_click" in verbs)
    check("hierarchy fallback: did NOT click element directly", "windows_desktop_click_element" not in verbs)

def test_verify_retry_and_escalation():
    # Setup loop mocks
    mios_cua.configure(vision_model="qwen3-vl", cua_enable=True)
    
    # Mock screenshot returns
    obs_counter = 0
    async def _mock_screenshot(platform, session_id=None):
        nonlocal obs_counter
        obs_counter += 1
        return "data:image/png;base64,stub", f"obs-{obs_counter}"
        
    mios_cua._cua_screenshot_uri = _mock_screenshot
    
    # VLM mock
    vlm_calls = 0
    async def _mock_vlm(system, user_text, image_uri):
        nonlocal vlm_calls
        vlm_calls += 1
        if "verify" in system:
            return {"done": False, "reason": "not done"}
        return {"action": "click", "args": {"x": 500, "y": 500}}
        
    mios_cua._cua_vlm_json = _mock_vlm
    
    # Mock dispatch that returns success but screenshot doesn't change
    # Wait, we need changed = False to trigger retry.
    # To mock changed = False, the observation digest returned must be identical.
    # So we should modify _mock_screenshot to return the SAME observation!
    async def _mock_screenshot_static(platform, session_id=None):
        return "data:image/png;base64,stub", "obs-static"
        
    mios_cua._cua_screenshot_uri = _mock_screenshot_static
    
    # Mock dispatch
    async def _mock_dispatch(verb, args, session_id=None):
        return {"success": True, "output": "done"}
        
    mios_cua._dispatch_mios_verb_inner = _mock_dispatch
    
    # Stub wait_for_stable_element to avoid waiting
    async def _mock_void(*a, **k): pass
    mios_cua.wait_for_stable_element = _mock_void
    
    # Run loop, expecting escalation
    try:
        asyncio.run(mios_cua._cua_loop("test goal", platform="windows", max_steps=5))
        escalated = False
    except RuntimeError as e:
        escalated = "HITL escalation" in str(e)
        
    check("retry loop: escalated to HITL after 3 failed retries", escalated)

def main():
    test_coordinate_scaling()
    test_a11y_hierarchy_routing()
    test_verify_retry_and_escalation()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0

if __name__ == "__main__":
    sys.exit(main())
