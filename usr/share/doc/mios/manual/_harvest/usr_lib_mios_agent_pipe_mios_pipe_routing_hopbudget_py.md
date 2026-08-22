<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-4 orchestrator-worker hop-budget + effort-scaling pure core. Extracts the cross-hop recursion-bound DECISIONS (depth_exhausted, the Via-chain loop guard, the Max-Forwards-style header seed) out of server.py into pure, unit-testable functions -- the structural guard that stops a worker which re-enters the gateway from recursing unboundedly. Adds effort_width(): the first-class "effort" knob that scales orchestration intensity (fan-out width) to query complexity, so a simple turn stays narrow and a hard one fans wide. server.py owns the contextvars + HTTP headers + the A2A self-id; this module owns the math.
AI-related: ./server.py, /usr/share/mios/mios.toml, ./test_mios_hopbudget.py
AI-functions: depth_exhausted, append_via, is_loop, seed_depth, effort_width

<!-- mios-src:c20564aec4c6 from usr/lib/mios/agent-pipe/mios_pipe/routing/hopbudget.py:1-3 -->

