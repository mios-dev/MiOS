<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Unit tests for...

!/usr/bin/env python3
AI-hint: Unit tests for tools/check-service-urls.py. Cover the four ways a port's addressing can be wrong -- unclassified, double-classified, a register entry naming a port that does not exist, and a duplicated register entry -- plus the empty-set case, because a gate that passes over no ports is the failure this whole family of gates exists to prevent.
AI-related: tools/check-service-urls.py, usr/share/mios/mios.toml, tests/drift-gate-negatives.sh

<!-- mios-src:dd4655254bd8 from tools/test_check-service-urls.py:1-3 -->

