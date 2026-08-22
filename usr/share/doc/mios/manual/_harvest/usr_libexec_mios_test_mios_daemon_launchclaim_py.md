<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone unit test for the...

!/usr/bin/env python3
AI-hint: Standalone unit test for the mios-daemon launch-claim detector after the NO-HARDCODE cutover. Proves the detector is MODEL-DRIVEN (no English-phrase regex, no Steam|Epic|Ubisoft|Uplay app-name list): loads the hyphenated CLI via SourceFileLoader, stubs its single model choke (llm_chat) to assert (1) a JSON "claim" verdict yields the model-named target generically, (2) a "not a claim" verdict yields no claim, (3) an unreachable lane (empty llm_chat) and a non-"model" mode both DEGRADE-OPEN to None (skip, never fabricate), and (4) the deleted keyword/app-name gate is gone so a hardcoded "Steam ... launched" string is NOT detected without the model.
AI-related: ./mios-daemon, /usr/share/mios/mios.toml
AI-functions: _load, check, main

<!-- mios-src:d7975732a77f from usr/libexec/mios/test_mios_daemon_launchclaim.py:1-4 -->

