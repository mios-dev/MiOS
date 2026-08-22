<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_pg -- PostgreSQL + pgvector client foundation for the...

mios_pg -- PostgreSQL + pgvector client foundation for the agent plane (WS-9).

FOSS-pure PostgreSQL + pgvector client for the agent plane. The PURE, deterministic
parts (DSN building, pgvector literal formatting, parameterized INSERT/recall SQL
builders) are stdlib-only so they unit-test in isolation (sibling-module pattern,
like mios_sched / mios_evict / mios_hitl). The actual connection + execute use
psycopg (v3) imported LAZILY, so importing this module + testing the builders
needs no psycopg and no live database.

Standard pattern (the "native" way): values are NEVER string-interpolated into
SQL -- every builder returns (sql, params) with %(name)s placeholders for psycopg
to bind, which kills SQL-injection and is how OpenAI's / pgvector's own cookbooks
do it. Vector recall uses the pgvector cosine operator `<=>` against an HNSW
index (`ORDER BY emb <=> %(qvec)s::vector LIMIT k`); similarity = 1 - distance.

This is the native agent-plane datastore client (WS-9c cutover: db_backend=postgres).

<!-- mios-src:22543cd68850 from usr/lib/mios/agent-pipe/mios_pipe/memory/pg.py:3-19 -->

### Extract the Postgres bigint id from an agent-plane row id...

Extract the Postgres bigint id from an agent-plane row id that may be a
    legacy 'table:NNN' record-string OR a bare bigint (int or numeric str).

    WS-MEM-TIER: several agent-plane UPDATE sites round-trip a row id from a
    SELECT back into an UPDATE. A legacy record-string id is 'knowledge:abc';
    on pgvector it is a bigint. A caller converting such an
    UPDATE to a parameterized PG statement needs the bigint. Returns None when the
    trailing segment is not an integer (e.g. a legacy alpha id with no pg
    analog) so the caller can SKIP the pg write rather than bind a bad id. Pure +
    deterministic (no DB).

<!-- mios-src:adaca6b76fc4 from usr/lib/mios/agent-pipe/mios_pipe/memory/pg.py:79-88 -->

### pgvector HNSW cosine recall

pgvector HNSW cosine recall: nearest `k` rows to %(qvec)s, returning the
    cosine SIMILARITY (1 - distance). Threshold-filter app-side (matches the
    current recall). Pair with `SET hnsw.ef_search` (see recall_tuning).

    TABLE-AWARE projection (P1/P3): non-knowledge tables don't have q/answer.
    agent_memory has fact/scope/mem_key; mios_rag has source/content. Projecting
    the knowledge columns against them raises UndefinedColumn -> recall()'s
    degrade-open arms the 30s global _pg_mark_down backoff, which would blank the
    LIVE knowledge recall inside every turn. Project the right columns per table.

    owner -- `owner_user = %(owner)s OR owner_user IS NULL` (legacy/shared rows
    with a NULL owner stay visible, so turning enforcement on never blanks
    existing recall). owner=None (the default) leaves the SQL BYTE-IDENTICAL to
    the pre-RLS query -> zero behaviour change when off. The CALLER decides policy
    (read [pgvector].rls_mode) and MUST pass owner only for a table that HAS an
    owner_user column (knowledge AND agent_memory both do; schema-init.sql);
    passing it for an owner_user-less table would raise UndefinedColumn and arm
    the backoff.

    A3 embedding-version hygiene: when an ACTIVE `emb_version` is passed AND the
    table carries the WS-A2 emb_version column (knowledge / agent_memory --
    schema-init.sql; mios_rag does NOT), scope recall to rows of the SAME
    embedding space -- `emb_version = %(emb_version)s OR emb_version IS NULL` --
    so a model/dimension change can't silently mix incompatible vector spaces in
    one cosine query. DEGRADE-OPEN: NULL/un-stamped rows (pre-migration data) stay
    visible, and emb_version=None/'' (active version unknown) adds NO filter, so
    the SQL is byte-identical to the pre-A3 query. Only filter when BOTH the active
    version AND a versioned table are present.

<!-- mios-src:6ff8c56a2993 from usr/lib/mios/agent-pipe/mios_pipe/memory/pg.py:149-176 -->

### Whether THIS deployment VERIFIES the request principal --...

Whether THIS deployment VERIFIES the request principal -- i.e.
    [security].principal_bind_mode == 'enforce', the ONLY mode under which the owner
    fed to the RLS GUC is reconciled against the AUTHENTICATED caller-key's bound
    account (mios_grounding._client_env) instead of the spoofable forwarded body/header
    `user`. Read through that flag's SSOT owner, mios_grounding._principal_bind_mode,
    via a LAZY import so this module keeps its stdlib-only module surface and the pure
    builders still test without grounding/server (the default RLS-off path never reaches
    here, so the import only loads once RLS is enabled). Degrade-CLOSED for RLS: any
    failure -> NOT verified -> no SET LOCAL (honest: never claim isolation we can't
    back, never lock anyone out).

<!-- mios-src:15d0eefec29f from usr/lib/mios/agent-pipe/mios_pipe/memory/pg.py:314-323 -->

### The (sql, params) binding the per-request RLS owner GUC, or...

The (sql, params) binding the per-request RLS owner GUC, or None to emit
    NOTHING. None whenever DB-side RLS is disabled (the default) OR no owner is
    resolvable -- so an owner-less system/daemon/seeding connection leaves the GUC
    UNSET and the schema policy stays permissive (degrade-open: NEVER locked out).

    SECURITY (P2-1): when RLS IS enabled, the owner GUC is emitted ONLY for an
    ENFORCE-VERIFIED principal (_principal_enforced). The owner derives from the
    forwarded body/header `user`, which a direct caller can spoof; it is reconciled to
    the authenticated caller-key ONLY under [security].principal_bind_mode=enforce. With
    RLS on but bind-mode NOT enforce, emitting SET LOCAL would DB-scope rows on an
    attacker-controlled string -- FALSE isolation -- so we emit NOTHING (degrade to the
    permissive policy = HONEST) and warn ONCE. rls_enable=false stays byte-identical.

    The `env` arg drives the rls_enable read (synthetic-env unit-testable); the
    verified-ness read goes through the live SSOT (env MIOS_PRINCIPAL_BIND_MODE ->
    mios.toml [security]), exactly as the request path resolves it.

<!-- mios-src:d84e4ed57bb5 from usr/lib/mios/agent-pipe/mios_pipe/memory/pg.py:347-362 -->

### Minimal bounded reuse pool for psycopg AsyncConnections...

Minimal bounded reuse pool for psycopg AsyncConnections (opt-in).

    `max_size` caps the total live (idle + checked-out) connections; `min_size`
    pre-opens that many on first use (psycopg_pool min_size semantics). Idle
    connections are health-checked on checkout and discarded if dead; on check-in a
    connection is cleaned (any open/aborted transaction rolled back -- which also
    discards a transaction-scoped SET LOCAL owner GUC) so no per-request state
    leaks to the next checkout. When the pool is exhausted, acquire() returns an
    ephemeral (un-pooled) connection so the request path never blocks/fails on the
    pool. Single asyncio event loop (the agent-pipe's), guarded by one Lock.

<!-- mios-src:997db546507a from usr/lib/mios/agent-pipe/mios_pipe/memory/pg.py:400-409 -->

### Lazily pre-open up to `min` idle connections on first use....

Lazily pre-open up to `min` idle connections on first use. Best-effort:
        a connect failure stops warm-up (degrade-open) and the pool grows on
        demand instead.

<!-- mios-src:ee728aad9dc4 from usr/lib/mios/agent-pipe/mios_pipe/memory/pg.py:447-449 -->

### Check out a connection. Returns (conn, pooled): pooled=True...

Check out a connection. Returns (conn, pooled): pooled=True MUST be
        returned via release(); pooled=False is a degrade-open ephemeral connection
        the caller closes. Reuses a live idle connection, else grows up to max, else
        (exhausted) hands back an ephemeral direct connection (never blocks).

<!-- mios-src:f9f2fe18a108 from usr/lib/mios/agent-pipe/mios_pipe/memory/pg.py:469-472 -->

### Return a checked-out connection. A healthy...

Return a checked-out connection. A healthy, cleanly-finished POOLED
        connection is cleaned + put back on the free-list; an ephemeral (degrade)
        connection or a broken/errored one is closed (and a pooled discard frees its
        slot).

<!-- mios-src:09bbb8d7d1b6 from usr/lib/mios/agent-pipe/mios_pipe/memory/pg.py:494-497 -->

### Async-context connection for ONE query bracket, shared by...

Async-context connection for ONE query bracket, shared by execute()/recall().

    DEFAULT (pool disabled): byte-identical to the historic per-call path -- open a
    fresh AsyncConnection, use it, close it (psycopg closes the connection on
    ``async with conn`` exit). Pool ENABLED: check a reused connection out of the
    bounded pool and return it on exit (a body that raises discards it). DEGRADE-
    OPEN: any pool checkout error falls back to a direct ephemeral connect, so a
    query never fails because of the pool.

<!-- mios-src:a106a4568520 from usr/lib/mios/agent-pipe/mios_pipe/memory/pg.py:546-553 -->

### Best-effort async query via psycopg v3. Returns rows...

Best-effort async query via psycopg v3. Returns rows (list[dict]) when
    fetch=True, else None. Degrade-open: any error -> None (mirrors _db_post),
    so a DB hiccup never breaks a turn.

    ``rls_owner`` (T-068): when _owner_scope emits a scope (DB-side RLS enabled AND an
    enforce-verified owner -- see its P2-1 gate), the per-request owner GUC is bound +
    SET LOCAL inside the SAME transaction as the query, so the schema RLS policies scope
    rows to that owner. Default (None / RLS off / unverified) emits NO extra statement
    -> byte-identical to the pre-RLS path.

<!-- mios-src:27713e2677e8 from usr/lib/mios/agent-pipe/mios_pipe/memory/pg.py:585-593 -->

### Cached set of a table's column names (information_schema)....

Cached set of a table's column names (information_schema). Lets insert()
    drop fields the live schema doesn't have, so code<->schema drift degrades to
    a PARTIAL row instead of a silent total failure (+ a 30s backoff that would
    poison every other table's mirror too).

<!-- mios-src:ce08711b6560 from usr/lib/mios/agent-pipe/mios_pipe/memory/pg.py:652-655 -->

### Build + run a parameterized INSERT (WS-9c dual-write...

Build + run a parameterized INSERT (WS-9c dual-write mirror). Filters the
    fields to the live table's columns first (drift-tolerant -- a code field the
    schema lacks is dropped, not fatal). Degrade-open -> None (psycopg/PG absent
    or error never breaks the caller). ``rls_owner`` (T-068) is forwarded to
    execute(): with RLS enabled AND an enforce-verified principal it SET-LOCALs the
    owner GUC in the insert's transaction so FORCE row-level security validates the new
    row (owner_user is written == this owner); default None / RLS off / unverified ->
    byte-identical (see _owner_scope's P2-1 gate).

<!-- mios-src:d7a6b2222530 from usr/lib/mios/agent-pipe/mios_pipe/memory/pg.py:670-677 -->

### Native pgvector HNSW cosine recall on ONE connection (SET...

Native pgvector HNSW cosine recall on ONE connection (SET hnsw.ef_search
    then the SELECT must share a session). Returns rows [{id,q,answer,tier,
    satisfied,access_count,score}] (score = cosine similarity), or [] on any
    error / no psycopg. Caller applies the score threshold (matches the
    prior recall). `owner` (#59 WS-5): when set, scopes recall to that owner
    (+ NULL/shared rows); None = no filter, byte-identical to pre-RLS. Pass only
    for owner_user-bearing tables -- see build_recall. `emb_version` (A3): when
    set, scopes recall to the active embedding space (+ NULL/un-stamped rows) for
    the emb_version-bearing tables; None = no filter, byte-identical. The caller
    passes the SSOT [pgvector].emb_version (degrade-open if unset).

    `rls_owner` (T-068, the DB-side defense-in-depth layer, DISTINCT from the
    app-side `owner` WHERE-filter above): with RLS enabled AND an enforce-verified
    principal it SET-LOCALs the owner GUC in the recall transaction so the schema
    policies enforce owner isolation IN THE DATABASE -- even if the app-side filter is
    bypassed, the caller sees only its own + shared rows. Default None / RLS off /
    unverified emits NOTHING -> byte-identical (see _owner_scope's P2-1 gate).

<!-- mios-src:6e7309d758c6 from usr/lib/mios/agent-pipe/mios_pipe/memory/pg.py:695-711 -->
