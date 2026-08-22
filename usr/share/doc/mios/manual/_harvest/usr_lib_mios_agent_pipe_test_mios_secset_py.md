<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_secset (WS-A14 SSOT-derived security sets). Pure stdlib, no server.py/DB/pytest. Verifies high_privilege_set = curated base UNION SSOT additions (curated is the never-droppable floor; SSOT only adds), taint_verb_set merges built-in external-fetch verbs with SSOT taint_verbs, normalization (strip/drop-empty), and provenance() origin accounting (ssot_only / curated_only).
AI-related: ./mios_secset.py
AI-functions: check, main

<!-- mios-src:aba8d887cfc6 from usr/lib/mios/agent-pipe/test_mios_secset.py:1-4 -->

