<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-A11/WS-3 server.py decomposition -- Stage 1b: the pure Kernel facade. Composes the AIOS managers (Scheduler / Memory / Context / Tool / Access) + the Router (mios_router) + a Dispatcher behind ONE seam, by INJECTION (server.py provides concrete impls built from its existing functions), so this module stays server.py-free + unit-testable. Defines the route->dispatch flow contract (Kernel.handle: router.route(refined) -> dispatcher.run(decision)) that chat_completions will delegate to in Stage 2 (VM-verified). Additive + unwired in Stage 1 -> zero behaviour change.
AI-related: ./mios_router.py, ./server.py, ./test_mios_kernel.py
AI-functions: handle, managers, class Kernel

<!-- mios-src:43f42e62fcfa from usr/lib/mios/agent-pipe/mios_pipe/kernel/kernel.py:1-3 -->

