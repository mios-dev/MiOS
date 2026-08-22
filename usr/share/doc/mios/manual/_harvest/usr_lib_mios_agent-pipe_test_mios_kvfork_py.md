<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Standalone unit test for mios_kvfork (WS-8 KV-cache fork...

Standalone unit test for mios_kvfork (WS-8 KV-cache fork primitives).

Pure stdlib + the sibling module only -- no server.py import, so it runs on any
Python 3.10+ without the agent-pipe runtime deps. Mirrors the mios_sched /
mios_evict standalone-test pattern: explicit asserts, PASS/FAIL summary, exit
code != 0 on any failure.

Run:  python test_mios_kvfork.py

<!-- mios-src:195641361b15 from usr/lib/mios/agent-pipe/test_mios_kvfork.py:3-11 -->
