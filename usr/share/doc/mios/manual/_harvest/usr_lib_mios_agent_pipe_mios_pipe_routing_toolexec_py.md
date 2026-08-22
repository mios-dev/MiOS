<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Tool-call EXECUTION primitive extracted verbatim from server.py (refactor R4 wave). The universal pipe-side tool-loop's hands: _exec_tool_calls (executes an OpenAI tool_calls[] list via the broker -- skill/recipe/MCP/code_mode/dispatch_to_nodes/verb branches, permission+firewall+taint gated) and the LOAD-BEARING narrated-tool-call RESCUE corpus (_rescue_tool_calls + _norm_tool_call + the _RESCUE_* regexes) that promotes a model's NARRATED call (Qwen <function=> XML, ```json fence, <tool_call>{json}</tool_call>, OpenAI {"function":...} blob) back into real tool_calls[] so the loop still fires it -- the model-agnostic structural fix for the #1 agentic-loop failure. Plus _cap_verb_result/_verb_result_cap (ACI head-tail result capping) and _format_tool_error. Config scalars + the verb/recipe/high-priv/web-enrich catalogs + the orch-ctx ContextVar + every server-side helper (dispatch_mios_verb, _mcp_call_tool, _record_mcp_tool_call, the DAG/swarm fan-out helpers, _resolve_verb_key, _session_is_tainted, the DB-event helpers, _src_record, _allowed_tool_names, the dispatch-depth guards) are dependency-INJECTED via configure() (one-way boundary -- mios_toolexec NEVER imports server). _loads_lenient/_aci_normalize/execute_skill are imported directly from their sibling modules. server.py re-imports every moved name verbatim under its original alias (surface-parity zero-diff).
AI-related: ./server.py, ./mios_config.py, ./mios_jsonsalvage.py, ./mios_aci.py, ./mios_skills.py, ./test_mios_toolexec.py
AI-functions: _norm_tool_call, _rescue_tool_calls, _allowed_tool_names, _verb_result_cap, _cap_verb_result, _format_tool_error, _exec_tool_calls, configure

<!-- mios-src:fcfd6b93149d from usr/lib/mios/agent-pipe/mios_pipe/routing/toolexec.py:1-3 -->

