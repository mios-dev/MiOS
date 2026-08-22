<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_batch (WS-A6 batch coalescing). Stdlib + asyncio, no DB/pytest. Verifies batch_key normalization (scheme + /v1 stripped), the is_native_batch BYPASS test (vLLM/SGLang/llama.cpp lanes -> bypass client-side coalescing, the research-grounded core), the CoalesceWindow flush decision (open-on-first, flush on max-size OR interval-elapsed, deterministic via passed-in now), and the async Coalescer: a disabled or native call is never awaited, concurrent same-key callers leave as ONE group, max_size flushes without waiting out the interval, distinct keys never share a window, a group is sealed on flush so the next caller opens a fresh one, and no window is left behind. The T-226 chokepoint wiring is proven by its own sibling, test_mios_httpclient.py.
AI-related: ./mios_batch.py, ./mios_pipe/kernel/httpclient.py
AI-functions: check, t_key, t_native_bypass, t_window_size, t_window_interval, t_coalescer, main

<!-- mios-src:c6b4fb7ac747 from usr/lib/mios/agent-pipe/test_mios_batch.py:1-4 -->

