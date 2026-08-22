<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone unit test for the...

!/usr/bin/env python3
AI-hint: Standalone unit test for the mios-daemon refusal/fabrication detector after the NO-HARDCODE cutover. Proves the detector is MODEL-DRIVEN (the deleted refusal-patterns.txt English-regex PRE-FILTER no longer gates whether to even check): loads the hyphenated CLI via SourceFileLoader, stubs its single model choke (llm_chat) to assert (1) a "YES" verdict on a response with NO refusal-keyword text still records a refusal -- the judge is consulted on EVERY candidate, (2) a "NO" verdict records nothing, (3) an unreachable lane (empty llm_chat) and an unparseable verdict both DEGRADE-OPEN to None (skip, never fabricate, never fall back to a keyword list), and (4) mode != model disables the judge without consulting the model, and the deleted pattern loader/gate (_load_refusal_patterns / _refusal_res / REFUSAL_PATTERNS_FILE) is gone.
AI-related: ./mios-daemon, /usr/share/mios/mios.toml
AI-functions: _load, check, main

<!-- mios-src:34f82d41ff09 from usr/libexec/mios/test_mios_daemon_refusal.py:1-4 -->

