<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_smartroute (WS-A16 cost/quality SmartRouting). Pure stdlib, no server.py/network/pytest. Verifies the researched local-first cascade: order_lanes puts ALL local lanes first (cheapest/strongest) then remotes by cost; choose_next prefers an untried local lane, returns a paid remote ONLY on escalate=True AND within the CostLedger budget; should_escalate fires on quality-fail OR local-exhausted; the ledger gates escalation when the budget is spent.
AI-related: ./mios_smartroute.py
AI-functions: check, main

<!-- mios-src:aad8b39de33f from usr/lib/mios/agent-pipe/test_mios_smartroute.py:1-4 -->

