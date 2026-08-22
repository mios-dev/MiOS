<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_manifest (WS-A1 verb-catalog manifest projection). Pure stdlib, no server.py/DB/pytest. Verifies project_verb_catalog is DETERMINISTIC (sorted, stable field subset, byte-identical on re-run), carries registry_kind="verb-catalog" (NOT the hermes-build-tools registry), projects WS-A7 conflict_group/parallel_limit, and diff_manifest detects added/removed/changed verbs + a wrong registry_kind for the --check drift gate.
AI-related: ./mios_manifest.py
AI-functions: check, main

<!-- mios-src:ae260b9cff4f from usr/lib/mios/agent-pipe/test_mios_ai_manifest.py:1-4 -->

