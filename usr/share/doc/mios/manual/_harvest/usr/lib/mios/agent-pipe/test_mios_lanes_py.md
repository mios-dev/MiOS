<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Standalone unit test for mios_lanes (WS-1). Pure stdlib +...

Standalone unit test for mios_lanes (WS-1).

Pure stdlib + the sibling module only -- no server.py import, so it runs on any
Python 3.10+ without the agent-pipe runtime deps (httpx/fastapi/...). Mirrors the
mios_sched test pattern: a mock-free asyncio harness with explicit asserts and a
PASS/FAIL summary; exit code != 0 on any failure.

Run:  python test_mios_lanes.py

<!-- mios-src:2da9cf12d2ec from usr/lib/mios/agent-pipe/test_mios_lanes.py:3-11 -->
