<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_cua -- unified computer-use perceive->act->verify loop...

mios_cua -- unified computer-use perceive->act->verify loop (WS-8).

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

<!-- mios-src:84a46ce41022 from usr/lib/mios/agent-pipe/mios_pipe/routing/cua.py:3-25 -->

### Inject the computer-use route + I/O-loop deps under their...

Inject the computer-use route + I/O-loop deps under their EXACT original
    names: the CUA_ENABLE gate flag, the verb-dispatch chokepoint
    (_dispatch_mios_verb_inner), the shared httpx client (_get_client), the vision
    backend-failure gate (_vision_backend_failed), and the config constants the
    loop reads (_BACKEND_KEY / VISION_MODEL / VISION_ENDPOINT / CUA_MAX_STEPS).
    Each field is gated on ``is not None`` (an empty backend key or a False flag is
    a legitimate value), so an unset keyword leaves the prior binding. The loop
    (_cua_loop) is module-local now, so it is NOT injected back.

<!-- mios-src:d0e4fa859cbc from usr/lib/mios/agent-pipe/mios_pipe/routing/cua.py:57-64 -->

### Interpret a VLM verify answer into {done: bool, reason...

Interpret a VLM verify answer into {done: bool, reason: str}. Accepts a
    JSON object {"done": ..., "reason": ...} anywhere in the text, else the
    sentinels GOAL_REACHED / DONE=YES / NOT_DONE (case-insensitive).

    FAIL-SAFE: anything unparseable -> done=False. The loop therefore NEVER
    falsely declares the goal reached on a malformed/ambiguous verify; it simply
    keeps working until the step budget (the operator's 'never claim success you
    didn't achieve' rule, enforced structurally).

<!-- mios-src:6e46b0debac6 from usr/lib/mios/agent-pipe/mios_pipe/routing/cua.py:145-152 -->

### WS-8 perceive->act->verify computer-use. Body: {goal...

WS-8 perceive->act->verify computer-use. Body: {goal, platform?
    (windows|linux), max_steps?}. Runs the closed VLM loop and returns the trace
    {status, reached, steps[...]}. DEFAULT-OFF (MIOS_CUA_ENABLE): returns a clear
    disabled notice until the operator opts in AND a GPU VLM is loaded. Never
    claims a goal it did not verify (fail-safe in mios_cua).

<!-- mios-src:2c799238d125 from usr/lib/mios/agent-pipe/mios_pipe/routing/cua.py:212-216 -->

### Pull a screenshot PNG path out of a screenshot verb's...

Pull a screenshot PNG path out of a screenshot verb's result. The
    *_desktop_screenshot verbs write a PNG + name it in stdout; degrade-open ->
    None when no path is found.

<!-- mios-src:eb73a4780520 from usr/lib/mios/agent-pipe/mios_pipe/routing/cua.py:254-256 -->

### Take a screenshot via the platform's verb, read the PNG...

Take a screenshot via the platform's verb, read the PNG, return
    (data_uri, raw_observation). Degrade-open -> (None, ""). The data URI is what
    the VLM 'sees'; the raw observation digest drives stall detection.

<!-- mios-src:639d74e7153d from usr/lib/mios/agent-pipe/mios_pipe/routing/cua.py:263-265 -->

### One VLM call returning the model's parsed JSON object (a...

One VLM call returning the model's parsed JSON object (a plan or a verify
    verdict). Degrade-open -> {} on any backend/parse failure (the caller's
    fail-safe handles an empty verdict as NOT-done).

<!-- mios-src:a4bd18e9fb36 from usr/lib/mios/agent-pipe/mios_pipe/routing/cua.py:311-313 -->

### Run the perceive->act->verify loop until the VLM verifies...

Run the perceive->act->verify loop until the VLM verifies the goal or a
    budget/stall guard fires. Returns mios_cua.CuaTrace.to_dict(). VLM-gated +
    degrade-open: no vision model / no screenshot -> an honest non-reached stop
    (it never fabricates success).

<!-- mios-src:f60733d1b26a from usr/lib/mios/agent-pipe/mios_pipe/routing/cua.py:434-437 -->
