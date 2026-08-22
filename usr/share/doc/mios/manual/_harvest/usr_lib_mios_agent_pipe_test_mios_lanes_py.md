<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Standalone unit test for mios_lanes (WS-1 unified lane resolver) -- verifies build_chain ordering, health-cached pick, per-lane cooldown failover, terminal-floor degrade, and recovery, with a fake clock + fake probe and no agent-pipe runtime deps.
AI-related: mios_lanes
AI-functions: _check, t_build_chain, t_pick_prefers_heavy, t_failover_to_vllm_then_light, t_cooldown_skips_reprobe, t_ttl_caches, t_recovery_after_cooldown, t_terminal_floor, t_mark_down, main

<!-- mios-src:c12ef6af0e07 from usr/lib/mios/agent-pipe/test_mios_lanes.py:1-3 -->

