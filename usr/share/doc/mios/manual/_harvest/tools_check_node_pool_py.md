<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Drift gate for the fan-out...

!/usr/bin/env python3
AI-hint: Drift gate for the fan-out pool. [nodes.*] is dispatched by capacity behind per-lane and per-endpoint semaphores, so a node that repeats another node's (endpoint, model, lane) is not a lane -- it is the same backend counted twice. Four of six nodes were byte-identical aliases of the SGLang endpoint, `local-cpu` declared lane="gpu" pointing at the GPU lane so the pool had NO cpu lane while [dispatch] budgeted one, and `local-llamaswap`'s own comment described the llama.cpp light lane on a retired port while its fields said SGLang. Also fails a lane outside [dispatch].lane_priority, two nodes disagreeing about one endpoint's lane, a `blade` naming no [blades] entry, and an endpoint that bakes a port an /etc/mios overlay could never move.
AI-related: usr/share/mios/mios.toml, usr/lib/mios/agent-pipe/mios_pipe/routing/agentreg.py, usr/lib/mios/agent-pipe/mios_pipe/scheduler/blades.py, tools/test_check-node-pool.py
AI-functions: nodes, lane_vocabulary, blades, aliases, lane_conflicts, illegal_lanes, orphan_blades, unmovable_endpoints, classify, main

<!-- mios-src:436fe6c87e93 from tools/check-node-pool.py:1-4 -->

