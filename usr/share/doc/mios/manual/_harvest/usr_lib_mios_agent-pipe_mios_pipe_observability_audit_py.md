<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

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

<!-- mios-src:67974cee6a6d from usr/lib/mios/agent-pipe/mios_pipe/observability/audit.py:3-44 -->

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

<!-- mios-src:355a934641b9 from usr/lib/mios/agent-pipe/mios_pipe/observability/audit.py:90-105 -->

### Return a COPY of ``fields`` with...

Return a COPY of ``fields`` with ``chain_seq``/``prev_hash``/``chain_hash``
        added, advancing the in-memory head. Degrade-open: disabled, already-stamped
        (idempotent -- the ``_emit_session_event`` pre-stamp), not-yet-seeded, or any
        error returns ``fields`` UNCHANGED so the event still logs.

<!-- mios-src:4e131c10dab5 from usr/lib/mios/agent-pipe/mios_pipe/observability/audit.py:163-166 -->
