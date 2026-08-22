<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: HITL ask-to-run + runtime approval-gate flow extracted verbatim from server.py (refactor R7 security wave). The chat-native human-in-the-loop plane: the WS-6 runtime gate (_hitl_gate / _hitl_is_approved / _hitl_record_pending -- scoped-verb dispatch interception, gate/log modes), the structural action identity (_action_hash verb+sorted-args; _pending_hash NULL-free sha256 for the pg pending_action store), the ask-to-run round-trip (_read_recent_pending / _mark_pending_decided / _classify_approval_reply MODEL-classified approve/reject/unrelated with NO keyword list / _ask_to_run_completion stream-aware result / _maybe_run_pending_approval propose->approve->per-action-hash bypass->re-dispatch), and the Reflexion read-side (_recent_reflections). SECURITY-CRITICAL: gates are NAME-KEYED on verb keys + permission tiers (mios_secset/mios_hitl decision helpers) -- never rename a verb key, gate name, or tier; a silent gate-disable is the worst regression. mios_hitl (decision helpers), mios_jsonsalvage, mios_pg, mios_sse are imported direct; every server symbol they touch (the HITL/ASK config scalars, ROUTER/PLANNER endpoints, _PG_PRIMARY, the _db_*/_pg_mirror DB helpers, _emit_session_event, _row_age_seconds, _usage_estimate, the _hitl_approved_var ContextVar, dispatch_mios_verb) is dependency-INJECTED via configure() (one-way boundary -- this module NEVER imports server). The /v1/hitl/* endpoints + the HITL/ASK config-constant definitions stay in server.py, which re-imports every moved name verbatim under its original alias (surface-parity zero-diff).
AI-related: ./server.py, ./mios_config.py, ./mios_hitl.py, ./mios_secset.py, ./mios_jsonsalvage.py, ./mios_pg.py, ./mios_sse.py, ./test_mios_hitlflow.py
AI-functions: _action_hash, _pending_hash, _hitl_is_approved, _hitl_record_pending, _hitl_gate, _classify_approval_reply, _read_recent_pending, _mark_pending_decided, _ask_to_run_completion, _maybe_run_pending_approval, _recent_reflections, hitl_approve_logic, hitlflow_router, hitl_pending, hitl_approve, configure

<!-- mios-src:6b743cf1dde5 from usr/lib/mios/agent-pipe/mios_pipe/access/hitlflow.py:1-3 -->

