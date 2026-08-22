<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_memory (WS-A15 MemoryProvider seam). Pure stdlib + asyncio, no server.py / DB / pytest -- runs as `python3 test_mios_memory.py` (exit 0 = pass) on the build host and as a build.sh sub-phase. Uses an injected FakeBackend (records recall/insert calls) to prove the PgVectorMemoryProvider forwards retrieve/add VERBATIM (golden parity vs the old direct mios_pg calls), and that get_memory_provider is fail-CLOSED (ValueError on an unknown name) + register_provider works.
AI-related: ./mios_memory.py
AI-functions: check, main, class FakeBackend

<!-- mios-src:1b78d3fea49a from usr/lib/mios/agent-pipe/test_mios_memory.py:1-4 -->

