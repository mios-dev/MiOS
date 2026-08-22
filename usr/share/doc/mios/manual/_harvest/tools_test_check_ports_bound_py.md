<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Unit tests for...

!/usr/bin/env python3
AI-hint: Unit tests for tools/check-ports-bound.py. Cover the four ways an allocated port can be wrong -- unreferenced and unregistered, registered though it IS referenced (the register must only shrink), a register entry naming no real port, and a duplicated entry -- plus the empty-set case, because a gate that passes over no ports is the exact failure this family of gates exists to prevent.
AI-related: tools/check-ports-bound.py, usr/share/mios/mios.toml, tests/drift-gate-negatives.sh

<!-- mios-src:7ccb687e6f38 from tools/test_check-ports-bound.py:1-3 -->

