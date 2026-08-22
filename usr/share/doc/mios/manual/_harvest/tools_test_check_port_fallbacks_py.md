<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Unit tests for...

!/usr/bin/env python3
AI-hint: Unit tests for tools/check-port-fallbacks.py. Covers every idiom that hid a stale number -- an unconditional Environment= pin, a ${X:-N} shell fallback, get("X","N"), the DOUBLE fallback get(K,"N") or M whose second literal is the one that actually runs, the PowerShell _MiosPort 'X' N table, and the MIOS_<KEY>_PORT alias spelling -- plus a comment (never a finding), the shrink-only register in both directions, and the real tree, which must be clean.
AI-related: tools/check-port-fallbacks.py, usr/share/mios/mios.toml, tests/drift-gate-negatives.sh

<!-- mios-src:b076f5dc6f53 from tools/test_check-port-fallbacks.py:1-3 -->

