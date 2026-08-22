<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-A6 batch-coalescing core, designed per 2026 best practice (researched): vLLM/SGLang/llama.cpp already do SERVER-SIDE continuous batching (a rolling scheduler coalesces incoming prompts into GPU batches optimally), so client-side request-batching on those lanes would DOUBLE-BATCH and add latency for no gain. Therefore this coalescer BYPASSES native-continuous-batching lanes (all of MiOS's local lanes) and only applies a small batch_interval WINDOW to NON-native endpoints (e.g. a rate-limited remote API). Pure stdlib: batch_key derivation, is_native_batch bypass test (host:port hint list), and a CoalesceWindow flush decision (interval-elapsed OR max-size). Coalescer drives the async hold-and-flush over those windows so the behaviour is testable without a server; server.py only wires it, flag-gated, as an httpx request hook on the ONE shared AsyncClient.
AI-related: ./mios_lanes.py, ./mios_sched.py, ./server.py, /usr/share/mios/mios.toml, ./test_mios_batch.py
AI-functions: batch_key, is_native_batch, class CoalesceWindow, class Coalescer

<!-- mios-src:67609fdd0cd6 from usr/lib/mios/agent-pipe/mios_pipe/scheduler/batch.py:1-3 -->

