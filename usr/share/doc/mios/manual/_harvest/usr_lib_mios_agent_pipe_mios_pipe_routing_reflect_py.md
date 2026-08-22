<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Reflection / self-assessment cluster extracted verbatim from server.py (strangler-fig wave). Two cohesive async helpers that ASSESS execution outcomes and emit verdict/correction events: _inline_satisfaction_check (synchronous per-turn Definition-of-Done check -- AND-folds this turn's tool_call rows, or trusts a delivered agent answer, into a user_query_(un)satisfied event so polish can ground-truth the wrapped reply on the CURRENT turn instead of waiting for mios-daemon's 30s async loop; also carries the structural write-action-claim guard keyed on the verb-permission class) and reflect_on_step_failure (ReWOO-style single-step reflection -- routes a failed DAG node + its captured error back to the small REFINE model for ONE corrected step, emitting reflect_corrected / reflect_unfixable session events). Both moved byte-for-byte. The server-side DB writers (_db_read/_db_write/_emit_session_event), the live _VERB_CATALOG, the REFINE_* model-call constants and the _REFLECT_SYSTEM prompt are dependency-INJECTED via configure() under their EXACT original server names (one-way boundary -- this module NEVER imports server); the sibling readers _recent_reflections (mios_hitlflow) and loads_lenient (mios_jsonsalvage) are imported directly. server.py re-imports both names verbatim so its public surface is byte-identical.
AI-related: ./server.py, ./mios_hitlflow.py, ./mios_jsonsalvage.py, ./consensus.py, ./test_mios_reflect.py, ./test_mios_consensus.py
AI-functions: _inline_satisfaction_check, reflect_on_step_failure, _recent_satisfaction_verdicts, _recent_tool_history, _judge_answer_satisfied, _judge_lane_vote, _judge_panel_verdict, configure

<!-- mios-src:fc7cb180d6e6 from usr/lib/mios/agent-pipe/mios_pipe/routing/reflect.py:1-3 -->

