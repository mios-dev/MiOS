<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_kvgc (WS-A4 KV-file GC planner). Pure stdlib, no server.py/DB/podman/pytest. Verifies the TTL pass (age-out old files), the total-size cap (oldest-first eviction until under cap), that protected/active-slot files are NEVER evicted (even when over cap), freed-bytes accounting, and the empty/no-op cases.
AI-related: ./mios_kvgc.py
AI-functions: check, main

<!-- mios-src:28c084d97d7d from usr/lib/mios/agent-pipe/test_mios_kvgc.py:1-4 -->

