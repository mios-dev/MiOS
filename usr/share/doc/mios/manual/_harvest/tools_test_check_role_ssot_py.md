<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Unit tests for...

!/usr/bin/env python3
AI-hint: Unit tests for tools/check-role-ssot.py. Covers every way the role axis can go wrong -- an illegal [blade].type, an archetype whose derived target is not shipped, an alias landing off the archetype table or shadowing it, an incomplete conflict graph (the state the DEFAULT role shipped in: it conflicted with nothing), an Alias= whose suffix systemd cannot install, a resurrected [profile].role, a keep-list still naming the retired MIOS_PROFILE_* vars, and an archetype name spelled as a literal in the blade code. Ends on the real tree, because a gate that only ever sees synthetic data is a gate that has never met its subject.
AI-related: tools/check-role-ssot.py, usr/share/mios/mios.toml, usr/lib/mios/blade.sh, tests/drift-gate-negatives.sh

<!-- mios-src:ad7cffe533a2 from tools/test_check-role-ssot.py:1-3 -->

