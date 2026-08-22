<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_hopbudget (WS-4 hop-budget guard + effort scaling). Pure stdlib, no server.py/DB/pytest. Verifies the recursion bound (depth_exhausted incl. disabled when max<=0), the Via-chain ops (append_via, is_loop case-insensitive self-detect), seed_depth parse/clamp/default (so the bound crosses an HTTP hop), and effort_width named-tier + float-score mapping clamped to [1,cap].
AI-related: ./mios_hopbudget.py
AI-functions: check, main

<!-- mios-src:d6da3f69053b from usr/lib/mios/agent-pipe/test_mios_hopbudget.py:1-4 -->

