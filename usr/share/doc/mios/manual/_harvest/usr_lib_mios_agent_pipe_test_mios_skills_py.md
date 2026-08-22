<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_skills (refactor R7 SKILLS-cluster extraction). Pure stdlib, no server.py/DB/network/pytest. Pins the projector invariants (_make_schema_strict makes every property required + additionalProperties:False + null-unions optional props; _skill_to_openai_tool emits a strict mios_skill__<name> function-tool spec with required==params) and drives execute_skill through the DI seam with async stubs (configure(dispatch_verb=..., db_read=..., ...)) to prove a 1-step promoted skill runs the verb and returns the success envelope. Guards the extracted cluster so a later move/refactor can't silently change skill tool shapes or the step-engine contract.
AI-related: ./mios_skills.py
AI-functions: check, t_make_schema_strict, t_skill_to_openai_tool, t_execute_skill, t_skill_render_args, t_skill_invocation_lifecycle, t_skill_attribute_tool_call, t_slug_for_skill, t_render_skill_md, t_write_skill_md_fire, main

<!-- mios-src:3021ad6e242f from usr/lib/mios/agent-pipe/test_mios_skills.py:1-4 -->

