<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Integration test script to...

!/usr/bin/env python3
AI-hint: Integration test script to verify that the `refine` post-parse logic correctly demotes long, multi-step prompts to `agent` intent while preserving short, direct commands as `dispatch` intents.
AI-related: /usr/lib/mios/agent-pipe, /usr/share/mios/mios.toml
AI-functions: main

<!-- mios-src:d3071ba91087 from tests/test-refine-guards.py:1-4 -->

