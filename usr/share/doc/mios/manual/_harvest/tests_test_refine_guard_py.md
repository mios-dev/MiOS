<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Smoke-test script to verify...

!/usr/bin/env python3
AI-hint: Smoke-test script to verify that the `refine_intent` logic correctly overrides "chat" classifications for actionable commands (like URLs or shell commands) to ensure they are correctly routed to the dispatcher.
AI-related: /usr/lib/mios/agent-pipe, /usr/share/mios/mios.toml, mios-open-url
AI-functions: main

<!-- mios-src:c724dbd94b1f from tests/test-refine-guard.py:1-4 -->

