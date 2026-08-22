<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_sse (refactor WS R2 leaf extraction). Pure stdlib, no server.py/DB/pytest/FastAPI. Pins the OpenAI-streaming SSE wire shapes the whole pipe streams on: _sse_chunk emits `data: {json}\n\n` with a chat.completion.chunk delta and dual reasoning_content+reasoning fields; _sse_done is the [DONE] sentinel; _sse_status emits a content-empty mios_status pill AND (when STATUS_AS_REASONING + real content) a persistent reasoning line, suppressing bare contentless markers; _sse_status_phase resolves _HUMAN_LABELS; _stream_answer char-paces the answer byte-for-byte; _iter_answer_chunks splits at word boundaries (whitespace preserved, oversize tokens whole); _tail_latest_status lifts the newest hermes-tail event into a status chunk. Guards the extracted streaming layer against silent wire-shape drift.
AI-related: ./mios_sse.py
AI-functions: check, _decode, t_chunk, t_done, t_status, t_status_phase, t_stream_answer, t_tail, t_iter_chunks, main

<!-- mios-src:11a56f7d9177 from usr/lib/mios/agent-pipe/test_mios_sse.py:1-4 -->

