<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Sub-agent TOOL LOOP for the OpenAI /v1 surface (MiOS is /v1-only), extracted verbatim from server.py (refactor R4 + a later move-home wave). Holds _v1_secondary_tool_loop (the pipe-side READ-ONLY OpenAI /chat/completions tool-loop every /v1 sub-agent runs through): POST non-streaming -> read message.tool_calls, RESCUE a narrated call, EXECUTE read verbs via the broker, append role:tool, re-call up to SECONDARY_TOOL_MAX_ITERS or until SATISFIED. Plus its LOAD-BEARING loop guards now owned HERE: the anti-disclaimer _TOOL_NUDGE + _looks_like_disclaimer/_DISCLAIM_MARKERS, the no-progress signature _tool_call_sig, the failure verdict _tmsgs_indicate_failure, the closed-loop _REPLAN_NUDGE, and _daemon_diagnose (a fresh monitor-LLM pass over a FAILED step so the bounded retry is GUIDED not blind). _exec_tool_calls + _rescue_tool_calls (mios_toolexec) and loads_lenient (mios_jsonsalvage) are imported directly from those siblings; the remaining server-side symbols (config scalars SECONDARY_TOOL_MAX_ITERS/SECONDARY_REPLAN_MAX, the _DAEMON_DIAGNOSE_* constants, and the helpers _apply_outbound_auth/_endpoint_supports_parallel_tools) are dependency-INJECTED via configure() (one-way boundary -- this module NEVER imports server). server.py re-imports every moved name verbatim under its original alias (surface-parity zero-diff).
AI-related: ./server.py, ./mios_toolexec.py, ./mios_jsonsalvage.py, ./mios_agent_call.py, ./mios_config.py, ./test_mios_secondary_loop.py
AI-functions: _daemon_diagnose, _v1_secondary_tool_loop, _looks_like_disclaimer, _tool_call_sig, _tmsgs_indicate_failure, configure

<!-- mios-src:cc15a5547030 from usr/lib/mios/agent-pipe/mios_pipe/routing/secondary_loop.py:1-3 -->

