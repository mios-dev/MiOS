<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_cua (WS-8 perceive->act->verify computer-use loop core). Pure stdlib, no server.py/VLM/pytest. Verifies the logical-action -> per-platform verb mapping (resolve_verb, fail-closed on unknown action/platform), observation-change/stall detection, the FAIL-SAFE verify-verdict parser (unparseable -> NOT done, never false success), the loop_status terminal decision (goal/budget/stall precedence), and the CuaTrace bookkeeping.
AI-related: ./mios_cua.py
AI-functions: check, main

<!-- mios-src:6aba7f2ac495 from usr/lib/mios/agent-pipe/test_mios_cua.py:1-4 -->

