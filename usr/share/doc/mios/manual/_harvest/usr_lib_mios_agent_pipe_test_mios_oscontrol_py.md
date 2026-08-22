<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Offline stdlib test for...

!/usr/bin/env python3
AI-hint: Offline stdlib test for mios_oscontrol (refactor R9): stubs every sibling (fastapi.responses + mios_sse/mios_jsonsalvage/mios_dci/mios_dispatch/mios_verity/mios_knowledge) in sys.modules so mios_oscontrol imports with no network/DB, then drives the window enum/verify path on a synthetic before/after window set -- asserts _window_diff identifies the opened/closed windows, _window_delta_text renders them, and _verify_os_action's anti-fabrication verdict is TRUE when a launch produced a NEW window but FALSE when the launch fired yet no window appeared (the failure mode the fast-path exists to stop). Pure assert-script.
AI-related: ./mios_oscontrol.py, ./server.py
AI-functions: main

<!-- mios-src:9be91b3a06b9 from usr/lib/mios/agent-pipe/test_mios_oscontrol.py:1-4 -->

