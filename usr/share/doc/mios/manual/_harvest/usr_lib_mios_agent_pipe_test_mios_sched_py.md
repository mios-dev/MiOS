<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Standalone unit test for mios_sched -- PriorityGate concurrency logic (permit capping, priority reordering, anti-starvation) plus the lane/scheduling/priority decision helpers (_lane_tool_cap, _agent_offload_engine, _resolve_autonomous_priority, _sched_priority, _lane_sem_key) exercised via the configure() DI seam with stubbed deps. No full agent-pipe runtime required.
AI-related: mios_sched
AI-functions: _check, _sched_cfg, t_basic_bound, third, t_priority_reorder, worker, t_fifo_tiebreak, t_anti_starvation, t_cancel_while_queued, t_cancel_after_grant, t_cap_never_exceeded, _configure_helpers, t_lane_tool_cap, t_agent_offload_engine, t_resolve_autonomous_priority, t_sched_priority, t_sched_priority_ssot_override, t_sched_priority_model_hook, t_sched_priority_unicode, t_lane_sem_key, main

<!-- mios-src:7379d7c1e7bd from usr/lib/mios/agent-pipe/test_mios_sched.py:1-3 -->

