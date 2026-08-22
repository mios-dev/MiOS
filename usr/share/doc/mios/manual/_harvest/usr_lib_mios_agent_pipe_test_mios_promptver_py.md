<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_promptver (WS-LIFECYCLE-VER prompt-version registry). Pure stdlib, no server.py/pytest. Verifies the stable content-hash, register() version semantics (bump only on content change, idempotent for unchanged), bounded history, rollback() (restore prior content as a forward version), and the content-free snapshot (never leaks prompt text).
AI-related: ./mios_promptver.py
AI-functions: check, main

<!-- mios-src:8076ae66638c from usr/lib/mios/agent-pipe/test_mios_promptver.py:1-4 -->

