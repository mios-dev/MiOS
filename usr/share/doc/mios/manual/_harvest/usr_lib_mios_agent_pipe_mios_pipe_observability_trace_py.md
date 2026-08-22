<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-A8 per-request trace/span observability primitive for the agent-pipe. Provides Span + Tracer (a pure-stdlib, bounded in-memory span emitter): a chat_completions request mints a trace_id, each pipeline stage (route/plan/dispatch/synthesize) opens a child Span under the current parent, and finished spans land in a capped per-trace ring buffer that backs GET /v1/trace/{trace_id} with ZERO DB hit. server.py owns the wiring (contextvars, the async span context manager, the inbound/outbound X-MiOS-Trace header, and stamping the active trace_id/span_id onto `event` rows for correlation); this module owns only the reusable mechanism. Finished spans live ONLY in this in-memory ring -- they are NOT mirrored to the DB as their own rows. No tracing backend, no network, no deps.
AI-related: ./server.py, ./mios_sched.py, ./test_mios_trace.py, /usr/share/mios/postgres/schema-init.sql
AI-functions: new_trace_id, new_span_id, start_span, record, get_trace, recent, stats, finish, to_dict, class Span, class Tracer

<!-- mios-src:a149cc6e83e9 from usr/lib/mios/agent-pipe/mios_pipe/observability/trace.py:1-3 -->

