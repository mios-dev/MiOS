<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: SKILLS execution cluster extracted verbatim from server.py (refactor R7/mios_skills wave). Skill row readers (_skill_fetch/_skill_list, pg-native when primary), the engine that runs a promoted skill's step list 1:1 via dispatch_mios_verb (execute_skill -- sequence/try-each modes, expand_from fan-out, invocation open/close + tool_call attribution, last_used_at bump, skill_run events), and the OpenAI function-tool projectors consumed verbatim by Hermes/OpenCode (_skill_to_openai_tool, _mcp_tool_to_openai_tool, _make_schema_strict). Pure pieces (_skill_to_openai_tool/_make_schema_strict/_mcp_tool_to_openai_tool) need no server state; mios_pg imported directly for rid_to_pg_id. The server-side DB helpers (_db_read/_db_post/_db_update/_db_write), the verb dispatcher (dispatch_mios_verb), the invocation/attribution helpers (_skill_invocation_open/_skill_invocation_close/_skill_attribute_tool_call), the arg renderer (_skill_render_args), the $-token regex (_PARAM_TOKEN_RE) and the SKILLS_ENABLED flag are dependency-INJECTED via configure() (one-way boundary -- mios_skills NEVER imports server). ALSO owns the episodic SKILL.md mirror (closed-loop self-learning): _write_skill_md_fire (fire-and-forget public entry injected back into the chat/native-loop/verity paths) + its private _slug_for_skill / _render_skill_md, with the target dir + enable flag injected as server-owned SSOT and _a2a_now (canonical UTC-ISO stamp) imported directly from mios_a2a. server.py re-imports every name verbatim under its original alias (surface-parity zero-diff).
AI-related: ./server.py, ./mios_config.py, ./mios_pg.py, ./mios_a2a.py, ./test_mios_skills.py
AI-functions: _skill_fetch, _skill_list, execute_skill, _skill_to_openai_tool, _make_schema_strict, _mcp_tool_to_openai_tool, _slug_for_skill, _render_skill_md, _write_skill_md_fire, configure

<!-- mios-src:6b1f5ee9e721 from usr/lib/mios/agent-pipe/mios_skills.py:1-3 -->

