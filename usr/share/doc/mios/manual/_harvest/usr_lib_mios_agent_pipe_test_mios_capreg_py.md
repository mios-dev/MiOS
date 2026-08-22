<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_capreg (WS-2 unified RBAC-filtered capability manifest). Pure stdlib, no server.py/DB/pytest. Verifies tier_rank ordering + fail-closed (unknown tier ranks beyond highest), allowed() admission (cap<=ceiling; unknown cap excluded; unknown ceiling admits nothing), recipe platform detection, the unified verb+recipe projection (RBAC filter by ceiling, platform filter, kind/tier tagging, deterministic sort), and the summary counts.
AI-related: ./mios_capreg.py
AI-functions: check, main

<!-- mios-src:be389a734067 from usr/lib/mios/agent-pipe/test_mios_capreg.py:1-4 -->

