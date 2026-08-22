<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_dispatcher (WS-A11/WS-3 decomposition Stage 1c: the pure mode Dispatcher) + its integration with mios_router + mios_kernel. Pure stdlib + asyncio, no server.py/DB/pytest. Verifies run() routes a RouteDecision.mode to the injected handler, forwards ctx, falls back to the default mode for an unknown mode, raises KeyError when neither handler nor fallback exists, modes()/can_handle introspection, and the full Router->Dispatcher flow via Kernel.
AI-related: ./mios_dispatcher.py, ./mios_router.py, ./mios_kernel.py
AI-functions: check, main

<!-- mios-src:011af160fde4 from usr/lib/mios/agent-pipe/test_mios_dispatcher.py:1-4 -->

