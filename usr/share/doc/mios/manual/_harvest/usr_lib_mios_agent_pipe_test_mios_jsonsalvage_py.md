<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_jsonsalvage.loads_lenient (lenient JSON-grammar salvage for small-model output). Pure stdlib, no pytest/DB/network/server.py. Verifies the documented contract: clean objects round-trip, ```json fences/leading-trailing prose are stripped, trailing commas / // and /* */ comments / Python True/False/None|NaN|undefined literals / empty-value-after-colon are repaired, truncated tails are best-effort re-balanced, field-level harvest recovers scalars+flat arrays around an unrecoverable break, and the documented NEGATIVES return None (empty/None/whitespace, pure non-JSON, top-level arrays, single-quoted keys, unterminated strings). Also pins the surprising flat-harvest nested-key leak.
AI-related: ./mios_jsonsalvage.py
AI-functions: check, main

<!-- mios-src:016dc447c75b from usr/lib/mios/agent-pipe/test_mios_jsonsalvage.py:1-4 -->

