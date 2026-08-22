<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Stdlib offline unit tests for mios_council_diversity -- the council input-diversity gate (T-047 RouteMoA GAP-1) + confidence-aware aggregation bypass (T-048 MOSAIC GAP-2). No network / no DB / no live model: a deterministic text->vector stub embedder feeds the pure geometry (select_diverse / should_bypass / medoid_index) and the async orchestrator (apply_council_gates). Proves the two Done-When cases: two identical council responses -> the duplicate is replaced/dropped (one selected); three identical responses above threshold -> the aggregator is bypassed (caller skips it) + the aggregator_bypass event is logged. Also proves degrade-open (both gates off => no embed call, nodes unchanged; a missing embedding => no-op) and the bypassed_pct counter. Run: python test_mios_council_diversity.py
AI-related: ./mios_council_diversity.py, ./mios_pipe/routing/swarm.py, ./mios_pipe/kernel/clusterhealth.py
AI-functions: main

<!-- mios-src:814ed0e5b4bc from usr/lib/mios/agent-pipe/test_mios_council_diversity.py:1-3 -->

