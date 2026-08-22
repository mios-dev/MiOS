<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Unit tests for...

!/usr/bin/env python3
AI-hint: Unit tests for tools/check-ssot-consumer-keys.py. Builds throwaway trees holding a fake consumer and asserts every direction: a read that resolves is silent, one whose key is declared under a DIFFERENT table is reported as misplaced and names both paths, one declared nowhere is reported as undeclared, a test_*.py file is not scanned, both call spellings are matched, and the register behaves as a ratchet -- unsorted, duplicated, over-ceiling, ceiling-left-high, an entry that resolves again, and an entry nothing reads all fail. Plus the real tree.
AI-related: tools/check-ssot-consumer-keys.py, usr/share/mios/mios.toml, tests/drift-gate-negatives.sh

<!-- mios-src:fd2487e81809 from tools/test_check-ssot-consumer-keys.py:1-3 -->

