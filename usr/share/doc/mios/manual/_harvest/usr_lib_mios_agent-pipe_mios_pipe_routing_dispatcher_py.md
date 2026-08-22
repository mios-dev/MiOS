<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_dispatcher -- the pure mode Dispatcher (WS-A11/WS-3...

mios_dispatcher -- the pure mode Dispatcher (WS-A11/WS-3, Stage 1c).

The "run" half of the AIOS Router/Dispatcher split. mios_router classifies a
refined plan into a RouteDecision(mode, ...); this Dispatcher routes that mode to
a registered async handler. Handlers are injected by server.py (the concrete
chat / dispatch / multi_task / dag / agent execution paths, lifted from the
current inline cascade), so the routing table is pure + testable while the heavy
bodies stay where they are until Stage 2 rewires them behind this seam.

<!-- mios-src:5d320ab2c8f9 from usr/lib/mios/agent-pipe/mios_pipe/routing/dispatcher.py:3-11 -->

### Run the decision via its mode handler. Falls back to the...

Run the decision via its mode handler. Falls back to the default-mode
        handler for an unknown/missing mode; raises KeyError if neither exists
        (a fail-loud wiring error, not a runtime degrade).

<!-- mios-src:20f5579b3de8 from usr/lib/mios/agent-pipe/mios_pipe/routing/dispatcher.py:34-36 -->
