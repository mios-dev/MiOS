<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_trace -- per-request trace/span observability for the...

mios_trace -- per-request trace/span observability for the MiOS agent-pipe
(WS-A8, the AIOS observability seam).

Pure stdlib (uuid / time / collections) so it unit-tests in isolation, in the
sibling-module style of mios_sched / mios_toolconflict. server.py owns the
wiring (the SSOT enable flag, the trace/span contextvars, the async span
context manager, the inbound/outbound X-MiOS-Trace header propagation, and
stamping the active trace_id/span_id onto `event` rows for correlation); this
module owns only the reusable mechanism: ids, the Span record, and a bounded
in-memory buffer that serves the trace-read endpoint without touching the DB.

Finished spans are NOT persisted as their own rows -- they live only in the
in-memory ring. Durable per-span mirroring would require a per-span DB write on
the hot tracing path, which this seam deliberately avoids; `event` rows emitted
during a traced request carry the trace_id/span_id so the stream still stitches
to a trace.

Model
=====
A *trace* is one request (one chat_completions call); it has a `trace_id`. A
*span* is one timed stage within it (route, plan, dispatch, synthesize, ...),
with a `span_id`, an optional `parent_id` (the enclosing span), a name, a
status (ok/error), a duration, and free-form attributes. Spans form a tree via
parent_id; the buffer keeps them in finish order per trace.

Bounded by construction
========================
The Tracer keeps at most `max_traces` traces (LRU eviction of the oldest trace
when a new one starts) and at most `max_spans_per_trace` spans per trace
(further spans are counted but not stored). So the buffer is O(max_traces *
max_spans_per_trace) bounded regardless of load -- safe to leave enabled.

Disabled tracer
===============
`enabled=False` makes record() a no-op (and server.py's span context manager
degrades to a near-no-op), so tracing carries ~zero cost when turned off.

<!-- mios-src:a89e85f41262 from usr/lib/mios/agent-pipe/mios_pipe/observability/trace.py:3-39 -->
