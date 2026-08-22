<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_ctxpack (WS-A5 priority token-budget packer). Pure stdlib, no server.py/DB/pytest. Verifies pack() keeps the highest-priority items that fit the budget, drops the rest, never exceeds the budget, preserves ORIGINAL order in the kept set, skips an over-budget item to admit a smaller lower-priority one, and honours reserve + custom text_of/priority_of accessors.
AI-related: ./mios_ctxpack.py, ./mios_tokenize.py
AI-functions: check, main

<!-- mios-src:c6dfb65f589b from usr/lib/mios/agent-pipe/test_mios_ctxpack.py:1-4 -->

