<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: OpenAI streaming SSE chunk + status-emit primitives extracted from server.py (refactor WS R2 leaf wave). Encodes chat-completion deltas in the OpenAI streaming protocol so any gateway (OWUI/Discord/Slack) consumes them with its stock client: _sse_chunk (delta builder, dual reasoning_content+reasoning fields), _sse_reasoning (thinking stream), _sse_status/_sse_status_phase (content-empty mios_status pills + persistent reasoning-log lines, humanistic emoji labels from _load_status_labels/_HUMAN_LABELS), _enrich_step_emits/_node_context/_node_status (per-step + per-AI-node live emitters), _stream_answer (char-paced final answer), _iter_answer_chunks (word-boundary answer chunker for the native-loop stream), _sse_done, and _tail_latest_status (hermes-tail checkpoint -> live status). STATUS_AS_REASONING moves here (its sole consumer is _sse_status). Pure stdlib + json + re; no server.py state, no DB -- server re-imports every name verbatim (surface-parity zero-diff).
AI-related: ./server.py, ./mios_aci.py, ./mios_native_loop.py, ./test_mios_sse.py
AI-functions: _sse_chunk, _sse_reasoning, _load_status_labels, _sse_status_phase, _sse_status, _enrich_step_emits, _node_context, _node_status, _stream_answer, _iter_answer_chunks, _sse_done, _tail_latest_status

<!-- mios-src:ece7131ac707 from usr/lib/mios/agent-pipe/mios_pipe/routing/sse.py:1-3 -->

