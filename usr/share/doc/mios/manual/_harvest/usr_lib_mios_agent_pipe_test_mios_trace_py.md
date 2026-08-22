<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_trace (WS-A8 trace/span observability). Pure stdlib, no server.py / DB / pytest -- runs as `python3 test_mios_trace.py` (exit 0 = pass) on the build host and as a build.sh sub-phase. Covers span lifecycle (open->finish, duration, status/error), parent linkage, the bounded buffer (per-trace span cap + LRU trace eviction), disabled-tracer no-op, get_trace ordering, recent() shape, and id uniqueness.
AI-related: ./mios_trace.py, ./test_mios_sched.py
AI-functions: check, main

<!-- mios-src:3def79b145b4 from usr/lib/mios/agent-pipe/test_mios_trace.py:1-4 -->

