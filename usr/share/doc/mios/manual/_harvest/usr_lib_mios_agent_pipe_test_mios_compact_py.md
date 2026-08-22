<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_compact (WS-A5 rolling-summary compaction planner). Pure stdlib, no server.py/DB/pytest. Verifies plan_compaction is a no-op when history fits, always keeps the last keep_recent non-system messages + system messages verbatim, marks the OLDEST overflow for summarization, and the kept set stays within budget.
AI-related: ./mios_compact.py, ./mios_tokenize.py
AI-functions: check, main

<!-- mios-src:38efd4dcb887 from usr/lib/mios/agent-pipe/test_mios_compact.py:1-4 -->

