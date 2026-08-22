<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_sandbox (WS-A13 risk-tier dispatch sandbox). Pure stdlib, no server.py/bwrap/podman/pytest. Verifies the tier->profile mapping (read=none, write=workspace, interactive=strict), the explicit override, the FAIL-CLOSED stance (unknown/missing tier -> strictest, never none -- the security-critical property), and the per-dispatch workspace path (hashed verb, sanitized uniq, under the base).
AI-related: ./mios_sandbox.py
AI-functions: check, main

<!-- mios-src:b5de04c18472 from usr/lib/mios/agent-pipe/test_mios_sandbox.py:1-4 -->

