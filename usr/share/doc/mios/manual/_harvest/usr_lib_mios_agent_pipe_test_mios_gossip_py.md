<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_gossip (WS-A18 epidemic-gossip + SWIM anti-entropy discovery core). Pure stdlib, no server.py/DB/pytest. Verifies seeded deterministic peer selection (reproducible per round, fanout cap, exclude, coverage rotation across seeds), SWIM heartbeat merge (new accepted, higher-incarnation wins, stale/equal rejected), TRUST-GATED merge (low-reputation/revoked rumor rejected; trust_of override), batch merge count, TTL prune with keep-list, and the anti-entropy digest.
AI-related: ./mios_gossip.py
AI-functions: check, main

<!-- mios-src:5abaddbd6fca from usr/lib/mios/agent-pipe/test_mios_gossip.py:1-4 -->

