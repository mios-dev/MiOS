<!-- AI-hint: Manual pages distilled from the source comments of observability, sanitized, each passage anchored to the comment it came from. -->

# observability

### mios_audit -- SHA-256 tamper-evident hash chaining for the...

mios_audit -- SHA-256 tamper-evident hash chaining for the MiOS event bus (SEC-03).

The agent-plane ``event`` table is an append-only observability stream. This module
makes it tamper-EVIDENT: every persisted event is linked to its predecessor by a
SHA-256 hash chain, so any later insert / delete / reorder / content edit breaks the
chain at a detectable point. It is the integrity substrate the record-replay,
self-improve-act and DGM workstreams build on (a replay you cannot trust the order of
is worthless).

DESIGN (single chokepoint, hot-path-safe, degrade-open):

* The chain is computed at the ONE place every event row is built -- ``server._db_create``
  for ``table == "event"`` (and the session-linked ``_emit_session_event``, which
  pre-stamps so its own pgvector mirror carries the chain columns). ``stamp()`` adds
  three columns to the row: ``chain_seq`` (a monotonic position assigned in WRITE order,
  not DB-insert order, since the mirror INSERT is fire-and-forget and may reorder),
  ``prev_hash`` (the predecessor's ``chain_hash``), and
  ``chain_hash = sha256(prev_hash || canonical_core(row))``.

* ``canonical_core`` hashes only the IMMUTABLE CONTENT columns
  (``source/kind/severity/summary/payload``) as sorted-keys compact JSON -- never the
  volatile / DB-assigned fields (``ts`` is set by the DB clock and is not reproducible
  at write parity, so temporal ORDER is bound by the chain itself rather than a
  self-reported timestamp; ``trace_id``/``span_id``/``passport``/``id`` are correlation
  metadata). The same canonicalization runs at verify time over the stored columns, so
  the verifier reproduces each hash deterministically.

* The chain head (last seq + last hash) lives in an in-memory ``EventChainer``, seeded
  ONCE from ``max(chain_seq)`` at startup -- so the hot path never issues a SELECT-max
  per insert. A single asyncio event loop serialises the synchronous ``stamp()``, so the
  counter needs no lock.

* DEGRADE-OPEN is absolute: a hashing error, an unseeded head (startup DB miss), or the
  feature being disabled returns the row UNCHANGED so the event still logs. Tamper-
  evidence is best-effort; event logging must never fail because of it.

The PURE primitives (``canonical_core`` / ``link_hash`` / ``EventChainer`` /
``verify_chain``) are stdlib-only and carry NO server/DB/web dependency, so the verify
CLI and the unit tests reuse the exact same algorithm. ``fastapi`` is imported behind a
degrade-open shim purely so this module also imports on a host without the web stack
(the live agent-pipe always has fastapi, so the real router binds in-process).

<!-- mios-src:67974cee6a6d from usr/lib/mios/agent-pipe/mios_pipe/observability/audit.py:4-45 -->

### Deterministic serialization of an event row's immutable...

Deterministic serialization of an event row's immutable CONTENT fields.

    Sorted-keys, compact-separator JSON over the present (non-None) ``CORE_FIELDS``.
    ``default=str`` matches how the row is serialized into storage (so a value the
    write path coerced to text, e.g. a datetime, reproduces identically here);
    ``ensure_ascii=False`` keeps unicode byte-stable on both sides.

    NG-3 payload normalisation: ``payload`` is a jsonb column. A write call-site may
    hand it in EITHER form -- a parsed dict/list (the common case) OR a pre-serialised
    JSON STRING -- but mios_pg binds a string into jsonb and psycopg reads it back as
    the PARSED object at verify time. So a string payload is parsed (``json.loads``) to
    its structural form before hashing, so WRITE and VERIFY canonicalize the SAME
    structure regardless of which form the row carried (otherwise a string-vs-dict
    asymmetry reports a spurious "broken" link). A string that is NOT valid JSON (a
    genuine free-text payload) is left unchanged; any other non-dict payload
    (number/list) is just another JSON value under the ``payload`` key, unchanged.

<!-- mios-src:355a934641b9 from usr/lib/mios/agent-pipe/mios_pipe/observability/audit.py:91-106 -->

### Return a COPY of ``fields`` with...

Return a COPY of ``fields`` with ``chain_seq``/``prev_hash``/``chain_hash``
        added, advancing the in-memory head. Degrade-open: disabled, already-stamped
        (idempotent -- the ``_emit_session_event`` pre-stamp), not-yet-seeded, or any
        error returns ``fields`` UNCHANGED so the event still logs.

<!-- mios-src:4e131c10dab5 from usr/lib/mios/agent-pipe/mios_pipe/observability/audit.py:164-167 -->

### mios_cost -- cost/energy accounting for the agent plane...

mios_cost -- cost/energy accounting for the agent plane (WS-RES-GOV).

The gap audit + completeness critic: MiOS's _budget_admit is a token-count
rolling-window TRIPWIRE; there is no $-cost and no energy/kWh/VRAM-hour
accounting -- but CLASSic's Cost axis and modern local-GPU serving treat
energy-per-token + $-per-task as first-class signals (on a fully-local GPU OS the
power/thermal envelope is the real constraint, not an API bill).

This module is the PURE accounting:
  * CostModel.estimate() -- one dispatch -> {energy_wh, usd, tokens, lane}. Local
    GPU lane: energy = gpu_watts * elapsed_s; $ = energy * usd_per_kwh. Remote
    lane: $ = tokens * usd_per_mtok (energy attributed to the provider, 0 local).
  * CostLedger -- accumulate total + per-lane energy/$/tokens for budget checks
    (remaining() against a $ ceiling) + /v1/scheduler observability.

server.py owns recording each real dispatch (tokens from usage / tokenizer,
elapsed from the call timing) + the SSOT rates; this is the deterministic core.

<!-- mios-src:f8b5847cb1a2 from usr/lib/mios/agent-pipe/mios_pipe/observability/cost.py:4-21 -->

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

<!-- mios-src:a89e85f41262 from usr/lib/mios/agent-pipe/mios_pipe/observability/trace.py:4-40 -->
