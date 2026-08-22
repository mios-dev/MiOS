<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_arbiter (WS-9 out-of-process policy-arbiter decision core). Pure stdlib, no server.py/HTTP/DB/pytest. Verifies the rule order (deny-list always wins; exclusive allow-list; risk-tier ceiling; default allow), fail-closed handling of an unknown tier (ranks above top -> blocked when a block_tier is set), and the Verdict shape.
AI-related: ./mios_arbiter.py
AI-functions: check, main

<!-- mios-src:0d38d25d282c from usr/lib/mios/agent-pipe/test_mios_arbiter.py:1-4 -->

