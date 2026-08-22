<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_toolconflict.ConflictGate (WS-A7). Pure stdlib + asyncio, no server.py / DB / pytest -- runs as `python3 test_mios_toolconflict.py` (exit 0 = pass) both on the build host and as a build.sh sub-phase. Covers the no-op fast path, parallel_limit caps, conflict_group mutual exclusion, group+limit composition (deadlock-free), cancellation-safety (no permit leak), release-on-exception, and from_catalog parsing.
AI-related: ./mios_toolconflict.py, ./test_mios_sched.py
AI-functions: _run, _peak_under, check, main

<!-- mios-src:56e3f1742081 from usr/lib/mios/agent-pipe/test_mios_toolconflict.py:1-4 -->

