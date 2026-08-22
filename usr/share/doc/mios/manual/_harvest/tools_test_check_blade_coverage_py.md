<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Unit tests for...

!/usr/bin/env python3
AI-hint: Unit tests for tools/check-blade-coverage.py. Cover every way the activation axis can be wrong -- a container classified neither way, one classified both ways, a requires or register entry naming no real container, an empty capability list that gates nothing, a capability no archetype grants, and a duplicated register entry -- plus the empty-set case, because a gate that passes over no containers is the failure this family exists to prevent.
AI-related: tools/check-blade-coverage.py, usr/share/mios/mios.toml, tests/drift-gate-negatives.sh

<!-- mios-src:509866a3cffe from tools/test_check-blade-coverage.py:1-3 -->

