<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_embed_backfill (WS-A2 embedding-version hygiene). Pure stdlib, no server.py / DB / pytest -- runs as `python3 test_mios_embed_backfill.py` (exit 0 = pass) on the build host and as a build.sh sub-phase. Covers the staleness predicate (needs_reembed: only emb-present rows with a mismatched/NULL version), the parameterized candidate-SELECT + version-stamp UPDATE SQL shapes, batch planning, and the plan summary.
AI-related: ./mios_embed_backfill.py
AI-functions: check, main

<!-- mios-src:f3c540655bc1 from usr/lib/mios/agent-pipe/test_mios_embed_backfill.py:1-4 -->

