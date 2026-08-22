<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_manifest (WS-A1 verb-catalog -> ai/v1 manifest projection; drift-check 8 depends on it). Pure stdlib, no server.py/DB/pytest. Verifies load_verbs_from_toml section-gating (skips sectionless configurator buttons) from a temp .toml, project_verb_catalog deterministic shape/ordering (sorted-by-name, fixed field subset, registry_kind="verb-catalog", conflict_group/parallel_limit conditional projection, hidden flag), and diff_manifest ([] on identical, +add/-remove/~changed incl. conflict_group/parallel_limit drift + registry_kind guard).
AI-related: ./mios_manifest.py
AI-functions: check, main

<!-- mios-src:37769efc9771 from usr/lib/mios/agent-pipe/test_mios_manifest.py:1-4 -->

