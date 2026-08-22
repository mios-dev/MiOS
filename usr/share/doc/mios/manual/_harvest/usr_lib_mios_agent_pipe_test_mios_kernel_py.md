<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_kernel (WS-A11/WS-3 decomposition Stage 1b: the pure Kernel facade). Pure stdlib + asyncio, no server.py/DB/pytest. Verifies Kernel.handle routes via the injected router then runs via the injected dispatcher (passing the decision + refined + ctx through), requires both router+dispatcher (ValueError otherwise), and managers() reports which seams are wired. Uses the real mios_router + a fake dispatcher.
AI-related: ./mios_kernel.py, ./mios_router.py
AI-functions: check, main, class FakeDispatcher

<!-- mios-src:fe75268d60e2 from usr/lib/mios/agent-pipe/test_mios_kernel.py:1-4 -->

