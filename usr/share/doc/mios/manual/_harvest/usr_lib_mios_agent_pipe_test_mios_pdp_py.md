<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_pdp (WS-A9 PDP capability gate). Pure stdlib, no server.py / DB / pytest -- runs as `python3 test_mios_pdp.py` (exit 0 = pass) on the build host and as a build.sh sub-phase. Covers permission_rank (known/unknown tier), resolve_ceiling (empty=no-ceiling, known=rank, UNKNOWN=fail-closed-to-0 -- the WS-A9 fail-OPEN fix), and decide (denied, allowed-not-in, max_permission ceiling, non-verb passthrough, empty-policy allow-all).
AI-related: ./mios_pdp.py
AI-functions: check, main

<!-- mios-src:5d10afb00dba from usr/lib/mios/agent-pipe/test_mios_pdp.py:1-4 -->

