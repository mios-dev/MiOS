<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_batch -- batch-interval coalescing for the MiOS...

mios_batch -- batch-interval coalescing for the MiOS agent-pipe (WS-A6, the
AIOS scheduler call-coalescing layer).

Pure stdlib. RESEARCH NOTE (the proper solution): the modern inference engines
MiOS runs locally -- vLLM (PagedAttention), SGLang (RadixAttention), and
llama.cpp -- all implement CONTINUOUS BATCHING: the engine's own scheduler forms
a rolling batch from concurrent requests with no fixed timer/count, which is
strictly better than any client-side grouping. So coalescing must NOT touch
those lanes (double-batching only adds head-of-line latency). It applies ONLY to
endpoints WITHOUT native continuous batching -- a rate-limited remote API where
grouping calls in a short window genuinely reduces request count. Hence the core
here is: bypass native lanes; window-bound the rest.

Sources: vLLM continuous batching (docs.vllm.ai), SGLang OpenAI-compatible
serving, BentoML "Static, dynamic and continuous batching" (LLM Inference Handbook).

<!-- mios-src:5201464ad550 from usr/lib/mios/agent-pipe/mios_pipe/scheduler/batch.py:3-18 -->
