<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_preempt (WS-A12 RR-preemption state machine + snapshot contract, PLUS the T-019/SCHED-01 turn-boundary seam). Pure stdlib + asyncio, no server.py/engine/pytest. Verifies Quantum expiry/remaining (incl. limit<=0 = unlimited), the bounded snapshot-slot free-list (acquire to exhaustion, release returns, idempotent), suspend/resume with PRIORITY-ordered resume + FIFO tie-break, the admission cap, stats, AND the turn_boundary() hook contract via synthetic turns: default-off = no-op (scheduler NOT consulted), enabled = consulted with a snapshot/resume round-trip, degrade-open = a scheduler error falls back to running the turn, plus the cooperative-yield depth/quantum backstops + the [scheduler] SSOT fallbacks + configure() aliases.
AI-related: ./mios_preempt.py, ./mios_config.py, ./mios_tokenize.py
AI-functions: check, main, t_as_bool, t_scheduler_cfg_defaults, t_turn_boundary_disabled, t_turn_boundary_enabled_roundtrip, t_turn_boundary_consulted_spy, t_turn_boundary_no_higher_waiter, t_turn_boundary_unwired_probe, t_turn_boundary_degrade_open, t_turn_boundary_quantum_backstop, t_configure_aliases_and_stats, t_queue_cfg_defaults, t_token_slice_queue_structure, t_token_slice_queue_fifo_tiebreak, t_token_slice_account, t_token_slice_head_priority, t_token_slice_queue_bounded, t_slice_boundary_disabled, t_slice_boundary_triggers_reeval, t_slice_boundary_no_higher_waiter, t_slice_boundary_text_counts_via_tokenize, t_slice_boundary_degrade_open, t_turn_boundary_default_off_ignores_queue, class _SpySched, class _SpyQueue

<!-- mios-src:ee6689e66701 from usr/lib/mios/agent-pipe/test_mios_preempt.py:1-4 -->

