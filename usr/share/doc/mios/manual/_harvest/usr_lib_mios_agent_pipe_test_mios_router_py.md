<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_router (WS-A11/WS-3 decomposition Stage 1: the pure Router). Pure stdlib, no server.py/DB/pytest. Verifies each intent (chat|dispatch|multi_task|agent|dag) maps to the right RouteDecision mode, dispatch carries the tool + deterministic flag, deep promotes an agent turn to broad/fanout, multi_task/dag fan out, an unknown/empty intent falls to the safe agent default, and the to_dict shape.
AI-related: ./mios_router.py
AI-functions: check, main

<!-- mios-src:0b59bfc4e5ca from usr/lib/mios/agent-pipe/test_mios_router.py:1-4 -->

