<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Unified inference-lane resolver (WS-1) -- the ONE place the agent-pipe chooses a model lane. Picks the best reachable lane from an ordered preference chain with a TTL health cache + per-lane cooldown, so a dead lane fails over (never 404s) and auto-recovers; collapses the two heavy lanes (SGLang/vLLM, both served as 'mios-heavy') behind one [ai].heavy_engine selector. Pure of server/FastAPI globals -> unit-testable.
AI-related: server.py (_pick_tool_backend, _TOOL_BACKEND*, _load_node_pool), mios.toml [ai].heavy_engine / [ai.sglang] / [ai.vllm] / [llamacpp]
AI-functions: build_chain, class Lane, class LaneResolver

<!-- mios-src:0eb6e4fd6e32 from usr/lib/mios/agent-pipe/mios_pipe/routing/lanes.py:1-3 -->

