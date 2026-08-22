<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_owui (OWUI RAG/task-template scaffold stripper). Pure stdlib, no server.py/DB/pytest. Verifies strip_owui_scaffold recovers the genuine user question from each OWUI scaffold shape (trailing-after-</context>, explicit <user_query>/<query>/<question>/<prompt> tag, head-before-### Task:, marker-sentence detection) and passes plain/non-OWUI text through unchanged, plus empty/whitespace and the recognised-but-uis olable fallback.
AI-related: ./mios_owui.py
AI-functions: check, main

<!-- mios-src:6729b18cf0de from usr/lib/mios/agent-pipe/test_mios_owui.py:1-4 -->

