<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-8 computer-use perceive->act->verify loop core (the PURE half). Unifies GUI control across the Windows host desktop (windows_desktop_* verbs) and the Linux/Wayland desktop (linux_desktop_* verbs) behind ONE logical action vocabulary (screenshot/click/type/key/find_element/click_element/list_windows) via resolve_verb(action, platform) -- fail-closed (unknown action/platform -> None, never guess a verb). Owns the loop CONTROL: step budget, stall (no-screen-change) detection, and the terminal decision (loop_status), plus parse_verify_verdict which is FAIL-SAFE (unparseable verify -> NOT done, so a goal is never falsely declared reached). This module ALSO owns the I/O half (moved verbatim from server.py): _cua_loop drives the live perceive->act->verify loop, _cua_screenshot_uri/_cua_extract_png capture+locate a screenshot PNG, and _cua_vlm_json makes the VLM call -- all reading server-owned chokepoints (the verb-dispatch _dispatch_mios_verb_inner, the shared httpx _get_client, the _vision_backend_failed gate) + config constants (VISION_MODEL/VISION_ENDPOINT/CUA_MAX_STEPS/_BACKEND_KEY) injected via configure(); server.py keeps only the thin @app wrapper. Deterministic policy + injected I/O in the mios_preempt/mios_sandbox sibling style.
AI-related: ./server.py, ./mios_sandbox.py, ./mios_dispatch.py, ./mios_vision.py, /usr/share/mios/mios.toml, ./test_mios_cua.py
AI-functions: resolve_verb, observation_digest, observation_changed, parse_verify_verdict, loop_status, class CuaTrace, configure, v1_computer_use_logic, cua_router, v1_computer_use, _cua_extract_png, _cua_screenshot_uri, _cua_vlm_json, _cua_loop

<!-- mios-src:8056c1b149be from usr/lib/mios/agent-pipe/mios_pipe/routing/cua.py:1-3 -->

