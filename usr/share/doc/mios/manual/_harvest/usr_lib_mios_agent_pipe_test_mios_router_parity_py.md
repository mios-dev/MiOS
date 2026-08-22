<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_router Stage-2 parity. Pure stdlib, no server.py/DB/pytest. Loads tests/router_corpus.json and verifies Router.route(plan).mode matches expected_mode and cascade_mode for every row.
AI-related: ./mios_router.py, ./tests/router_corpus.json
AI-functions: check, cascade_mode, main

<!-- mios-src:8be1c62a5f07 from usr/lib/mios/agent-pipe/test_mios_router_parity.py:1-4 -->

