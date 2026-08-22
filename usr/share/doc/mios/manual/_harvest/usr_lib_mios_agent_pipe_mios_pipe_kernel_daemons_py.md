<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: BACKGROUND async daemon-loop bodies extracted VERBATIM from server.py
AI-related: ./server.py, ./mios_config.py, ./mios_gossip.py, ./mios_pg.py, ./mios_reputation.py, ./mios_selfimprove.py, ./mios_kvgc.py, ./mios_kvfork.py, ./test_mios_daemons.py
AI-functions: _membership_watch_loop, _gossip_loop, _reputation_restore, _reputation_flush, _selfimprove_report, _selfimprove_loop, _kv_gc_sweep_once, _kv_gc_loop, _consolidate_memory_sweep_once, _consolidate_group, _consolidate_memory_loop, daemons_router, selfimprove_report_ep, configure

<!-- mios-src:37c5c6243ef8 from usr/lib/mios/agent-pipe/mios_pipe/kernel/daemons.py:1-3 -->

