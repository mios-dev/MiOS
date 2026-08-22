<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_reflect (strangler-fig extraction). Pure stdlib, no server.py/DB/network/pytest. Pins the self-assessment invariants of the extracted cluster: _inline_satisfaction_check early-returns None on a missing session / non-dict refine (the cheap gate), folds a chat-with-no-tools turn to user_query_satisfied(chat_no_tools_expected), an all-success tool_call set to user_query_satisfied(all_succeeded), and a failed tool_call to user_query_unsatisfied(failed_tools) -- every DB read/write stubbed via configure(); reflect_on_step_failure early-returns None when REFINE is disabled (the gate), returns the model's corrected step dict on a canned 200, and returns None on an empty-tool "unfixable" verdict -- httpx monkeypatched + _recent_reflections + the session-event emitter stubbed. Guards the moved bodies + their configure() DI seam so a later move can't silently change verdict/correction behaviour.
AI-related: ./mios_reflect.py
AI-functions: check, _mk_db_read, _wire_inline, t_inline_gate, t_inline_chat, t_inline_success, t_inline_failed, _wire_reflect, t_reflect_gate, t_reflect_corrected, t_reflect_unfixable, t_recent_verdicts, t_recent_tool_history, _mk_judge_client, _wire_judge, t_judge_empty, t_judge_yes_no, t_judge_degrade, _mk_panel_client, _wire_panel, t_panel_off_is_single_lane, t_panel_majority, t_panel_weight_beats_headcount, t_panel_abstain_not_a_no, t_panel_no_quorum_falls_back, main

<!-- mios-src:eb04bf8eb81c from usr/lib/mios/agent-pipe/test_mios_reflect.py:1-4 -->

