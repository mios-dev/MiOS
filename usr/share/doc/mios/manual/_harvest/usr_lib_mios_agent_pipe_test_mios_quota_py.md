<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_quota (WS-6 per-user quota + rate limit). Pure stdlib, no server.py/DB/pytest. Verifies the sliding-window RPM cap (N allowed, N+1 denied, window slide re-admits), the per-window cost budget (deny over budget), per-user isolation, unlimited-when-limit<=0 (single-user default), the no-principal pass-through, and reset.
AI-related: ./mios_quota.py
AI-functions: check, main

<!-- mios-src:e27334982989 from usr/lib/mios/agent-pipe/test_mios_quota.py:1-4 -->

