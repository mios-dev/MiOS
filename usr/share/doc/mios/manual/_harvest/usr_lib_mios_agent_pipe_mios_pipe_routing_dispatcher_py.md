<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-A11/WS-3 server.py decomposition -- Stage 1c: the pure Dispatcher. Runs a RouteDecision (from mios_router) by routing its `mode` to the matching per-mode HANDLER, where handlers are INJECTED (server.py provides the concrete chat/dispatch/swarm/dag/agent runners built from its existing branch bodies), so this module imports nothing from server.py and is unit-testable. Completes the Router(decide) -> Dispatcher(run) split the Kernel facade composes. Unknown mode falls back to the 'agent' handler (the safe full-pipeline default). Additive + unwired in Stage 1 -> zero behaviour change.
AI-related: ./mios_router.py, ./mios_kernel.py, ./server.py, ./test_mios_dispatcher.py
AI-functions: run, modes, can_handle, class Dispatcher

<!-- mios-src:9d40472cead9 from usr/lib/mios/agent-pipe/mios_pipe/routing/dispatcher.py:1-3 -->

