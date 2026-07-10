# AI-hint: Provides a PostgreSQL and pgvector client for the agent plane (WS-9), offering a standalone, SQL-injection-safe replacement for the SurrealDB client using parameterized queries and HNSW-indexed vector recall.
# AI-functions: _pg_skip, _pg_mark_down, rid_to_pg_id, pg_config, dsn, vector_literal, build_insert, build_recall, recall_tuning, rls_enabled, build_set_owner, _owner_scope, execute, _table_columns, insert, recall
"""mios_pg -- PostgreSQL + pgvector client foundation for the agent plane (WS-9).

FOSS-pure replacement path for the SurrealDB HTTP client. The PURE, deterministic
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

This is ADDITIVE: it is NOT yet wired into the live agent-pipe (that is the
staged cutover, WS-9c). It stands up next to the SurrealDB client so the engine
swap happens behind one seam.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Optional

log = logging.getLogger("mios-agent-pipe")

# Connect-failure backoff (mirrors the SurrealDB _db_post 30s backoff): when the
# DB is down / not yet deployed, skip attempts for a window so a default "dual"
# backend doesn't churn one failed 5s connect per write. Module-global; single
# event loop.
_pg_down_until = 0.0
_PG_BACKOFF_S = 30.0


def _pg_skip() -> bool:
    return time.monotonic() < _pg_down_until


def _pg_mark_down() -> None:
    global _pg_down_until
    _pg_down_until = time.monotonic() + _PG_BACKOFF_S


def rid_to_pg_id(rid: Any) -> "Optional[int]":
    """Extract the Postgres bigint id from an agent-plane row id that may be a
    SurrealDB 'table:NNN' record-string OR a bare bigint (int or numeric str).

    WS-MEM-TIER: several agent-plane UPDATE sites round-trip a row id from a
    SELECT back into an UPDATE. On SurrealDB the id is a record-string
    ('knowledge:abc'); on pgvector it is a bigint. A caller converting such an
    UPDATE to a parameterized PG statement needs the bigint. Returns None when the
    trailing segment is not an integer (e.g. a legacy surreal alpha id with no pg
    analog) so the caller can SKIP the pg write rather than bind a bad id. Pure +
    deterministic (no DB)."""
    if rid is None:
        return None
    try:
        tail = str(rid).split(":")[-1].strip()
        return int(tail)
    except (TypeError, ValueError):
        return None


# ── config / DSN (SSOT: mios.toml [pgvector] -> MIOS_PG_* env via userenv.sh) ──
def pg_config(env: Optional[dict] = None) -> dict:
    """Resolve connection settings from the environment (already layered from
    mios.toml by userenv.sh). Local-only defaults match the quadlet."""
    e = env if env is not None else os.environ
    return {
        "host": e.get("MIOS_PG_HOST", "localhost"),
        "port": int(e.get("MIOS_PORT_PGVECTOR", "8432") or 8432),
        "user": e.get("MIOS_PG_USER", "mios"),
        "password": e.get("MIOS_PG_PASS", "mios"),
        "dbname": e.get("MIOS_PG_DB", "mios"),
    }


def dsn(cfg: Optional[dict] = None) -> str:
    """Build a libpq connection URI from a config dict (or the env)."""
    c = cfg or pg_config()
    return (f"postgresql://{c['user']}:{c['password']}"
            f"@{c['host']}:{c['port']}/{c['dbname']}")


# ── pgvector helpers ─────────────────────────────────────────────────────────
def vector_literal(vec) -> str:
    """Format a float sequence as a pgvector text literal: '[0.1,0.2,...]'.
    (psycopg binds this to a `vector` column via the `::vector` cast.)"""
    return "[" + ",".join(repr(float(x)) for x in (vec or [])) + "]"


# ── parameterized SQL builders (return (sql, params); psycopg binds params) ───
def build_insert(table: str, fields: dict) -> "tuple[str, dict]":
    """`INSERT INTO <table> (cols) VALUES (%(col)s, ...)` -- never interpolates
    values. `emb` (if a list) is bound as a pgvector via the ::vector cast."""
    cols = list(fields.keys())
    params: dict = {}
    placeholders = []
    for c in cols:
        v = fields[c]
        if c == "emb" and isinstance(v, (list, tuple)):
            params[c] = vector_literal(v)
            placeholders.append(f"%({c})s::vector")
        elif isinstance(v, (dict, list, tuple)):
            # document/array fields -> jsonb (sources, args, payload, dag, ...)
            params[c] = json.dumps(v, default=str)
            placeholders.append(f"%({c})s::jsonb")
        else:
            params[c] = v
            placeholders.append(f"%({c})s")
    sql = (f"INSERT INTO {table} (" + ", ".join(cols) + ") VALUES ("
           + ", ".join(placeholders) + ") RETURNING id;")
    return sql, params


def build_recall(table: str = "knowledge", k: int = 3,
                 owner: "Optional[str]" = None,
                 emb_version: "Optional[str]" = None) -> "tuple[str, dict]":
    """pgvector HNSW cosine recall: nearest `k` rows to %(qvec)s, returning the
    cosine SIMILARITY (1 - distance). Threshold-filter app-side (matches the
    current recall). Pair with `SET hnsw.ef_search` (see recall_tuning).

    TABLE-AWARE projection (P1/P3): non-knowledge tables don't have q/answer.
    agent_memory has fact/scope/mem_key; mios_rag has source/content. Projecting
    the knowledge columns against them raises UndefinedColumn -> recall()'s
    degrade-open arms the 30s global _pg_mark_down backoff, which would blank the
    LIVE knowledge recall inside every turn. Project the right columns per table.

    #59 WS-5 RLS (MECHANISM ONLY): when `owner` is passed, scope recall to that
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
    version AND a versioned table are present."""
    if table == "agent_memory":
        # + ts so the shared blended recall rerank can apply its bounded recency
        # decay (agent_memory carries no access_count/tier/satisfied columns -- those
        # blend terms degrade-open to neutral; ts is its one tie-breaking signal).
        proj = "mem_key AS id, fact, scope, source, ts"
    elif table == "mios_rag":
        proj = "id, source, content"
    else:  # knowledge (default) -- + ts/last_access for the recall recency decay
        proj = "id, q, answer, tier, satisfied, access_count, ts, last_access"
    where = "emb IS NOT NULL"
    params = {"qvec": None, "k": int(k)}  # caller sets qvec = vector_literal(q)
    if owner is not None:
        where += " AND (owner_user = %(owner)s OR owner_user IS NULL)"
        params["owner"] = owner
    # Only the emb_version-bearing tables (schema-init.sql) can be version-filtered;
    # applying it to mios_rag (no such column) would raise UndefinedColumn and arm
    # the degrade-open backoff that blanks LIVE recall, so restrict to the set.
    if emb_version and table in ("knowledge", "agent_memory"):
        where += " AND (emb_version = %(emb_version)s OR emb_version IS NULL)"
        params["emb_version"] = emb_version
    sql = (
        f"SELECT {proj}, "
        f"1 - (emb <=> %(qvec)s::vector) AS score "
        f"FROM {table} WHERE {where} "
        f"ORDER BY emb <=> %(qvec)s::vector LIMIT %(k)s;"
    )
    return sql, params


def recall_tuning(ef_search: int = 100) -> str:
    """Per-query HNSW recall/speed knob; run before the recall SELECT."""
    return f"SET hnsw.ef_search = {int(ef_search)};"


# ── WS-5 / T-068 native Postgres Row-Level-Security owner binding ─────────────
# The session GUC the schema-init.sql RLS policies read (current_setting(
# 'mios.owner_user', true)). It is a protocol / schema-contract constant -- it MUST
# match the var name the policies in postgres/schema-init.sql read -- so it lives
# here as ONE named constant (it is NOT an SSOT mios.toml value to restate). Set per
# request/transaction so the policies scope rows to the verified principal; UNSET
# leaves the policy permissive, so single-user / system / daemon / seeding paths see
# all rows exactly as today.
_RLS_OWNER_GUC = "mios.owner_user"


def rls_enabled(env: "Optional[dict]" = None) -> bool:
    """DB-side Row-Level-Security ENFORCEMENT toggle (SSOT [pgvector].rls_enable ->
    MIOS_DB_RLS_ENABLE, bridged by userenv.sh). DEFAULT FALSE: no SET LOCAL is
    emitted, the schema policies stay permissive, and every executed statement is
    byte-identical to the pre-RLS path. Reads the env per call (like pg_config) so a
    live mios.toml edit + mios-sync-env takes effect without a code change."""
    e = env if env is not None else os.environ
    return str(e.get("MIOS_DB_RLS_ENABLE", "") or "").strip().lower() in {
        "1", "true", "yes", "on"}


def build_set_owner(owner: str) -> "tuple[str, dict]":
    """Parameterized statement that scopes THIS transaction's RLS GUC to ``owner``:
    ``SELECT set_config('mios.owner_user', %(owner)s, true)``. is_local=true gives
    SET LOCAL semantics (transaction-scoped, so it never leaks to a later request on
    a reused/pooled connection). BOTH the GUC name and the owner are BOUND (never
    string-spliced), mirroring the WS-A3 extended-protocol binding precedent."""
    return ("SELECT set_config(%(guc)s, %(owner)s, true)",
            {"guc": _RLS_OWNER_GUC, "owner": str(owner)})


def _principal_enforced() -> bool:
    """Whether THIS deployment VERIFIES the request principal -- i.e.
    [security].principal_bind_mode == 'enforce', the ONLY mode under which the owner
    fed to the RLS GUC is reconciled against the AUTHENTICATED caller-key's bound
    account (mios_grounding._client_env) instead of the spoofable forwarded body/header
    `user`. Read through that flag's SSOT owner, mios_grounding._principal_bind_mode,
    via a LAZY import so this module keeps its stdlib-only module surface and the pure
    builders still test without grounding/server (the default RLS-off path never reaches
    here, so the import only loads once RLS is enabled). Degrade-CLOSED for RLS: any
    failure -> NOT verified -> no SET LOCAL (honest: never claim isolation we can't
    back, never lock anyone out)."""
    try:
        from mios_grounding import _principal_bind_mode
        return _principal_bind_mode() == "enforce"
    except Exception:  # noqa: BLE001 -- unresolvable bind mode -> treat as unverified
        return False


# One-time loud warning for the misconfiguration RLS-on-but-not-enforce: the operator
# enabled DB-side isolation that CANNOT be applied (the owner principal is unverified /
# spoofable), so we degrade to the permissive policy and say so ONCE per process rather
# than silently pretending to isolate. Module-global flag; single event loop.
_RLS_UNVERIFIED_WARNED = False


def _warn_rls_unverified_once() -> None:
    global _RLS_UNVERIFIED_WARNED
    if _RLS_UNVERIFIED_WARNED:
        return
    _RLS_UNVERIFIED_WARNED = True
    log.warning(
        "[pgvector].rls_enable is on but [security].principal_bind_mode != enforce -- "
        "the owner principal is unverified/spoofable, so RLS is NOT applied; set "
        "principal_bind_mode=enforce for real per-tenant isolation")


def _owner_scope(rls_owner: "Optional[str]",
                 env: "Optional[dict]" = None) -> "Optional[tuple[str, dict]]":
    """The (sql, params) binding the per-request RLS owner GUC, or None to emit
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
    mios.toml [security]), exactly as the request path resolves it."""
    owner = str(rls_owner).strip() if rls_owner is not None else ""
    if not owner or not rls_enabled(env):
        return None
    if not _principal_enforced():
        _warn_rls_unverified_once()
        return None
    return build_set_owner(owner)


# ── OPT-IN bounded async connection pool ([pgvector].pool_*) ─────────────────
# DEFAULT-OFF: execute()/recall() open a fresh connection per query and close it
# (the historic per-call path, byte-identical). ON: a bounded free-list of live
# AsyncConnections is REUSED across queries so a swarm/DAG fan-out (N concurrent
# nodes) does not open N fresh connects. psycopg_pool is NOT a hard dependency --
# this is a minimal bounded reuse pool over the SAME lazy psycopg connect path, so
# the pure builders + the pre-cutover (no-psycopg) deployment are unaffected.
# Degrade-open everywhere: pool exhaustion/error falls back to a direct ephemeral
# connect (a query NEVER fails on the pool); a broken/dirty connection is discarded
# rather than reused. SECURITY: a connection is cleaned on check-in (any open/aborted
# transaction is rolled back), which also discards a transaction-scoped SET LOCAL --
# the RLS owner GUC (build_set_owner uses is_local=true) -- so no per-request owner
# scope can leak to the next checkout.
def pool_config(env: "Optional[dict]" = None) -> dict:
    """Resolve the opt-in pool settings (SSOT [pgvector].pool_* -> MIOS_PG_POOL_*
    via userenv.sh). Read per call (like rls_enabled) so a live mios.toml edit +
    mios-sync-env takes effect. enable default FALSE -> the per-call connect path."""
    e = env if env is not None else os.environ
    enable = str(e.get("MIOS_PG_POOL_ENABLE", "") or "").strip().lower() in {
        "1", "true", "yes", "on"}
    try:
        pmin = max(0, int(e.get("MIOS_PG_POOL_MIN", "0") or 0))
    except (TypeError, ValueError):
        pmin = 0
    try:
        pmax = max(1, int(e.get("MIOS_PG_POOL_MAX", "8") or 8))
    except (TypeError, ValueError):
        pmax = 8
    return {"enable": enable, "min": min(pmin, pmax), "max": pmax}


async def _open_conn(cfg: "Optional[dict]" = None):
    """Open ONE AsyncConnection with the SAME args as the historic per-call path,
    so a pooled connection is indistinguishable from a direct one (only its
    lifetime differs: reused vs closed)."""
    import psycopg  # lazy: only at cutover, never for the pure helpers
    return await psycopg.AsyncConnection.connect(
        dsn(cfg), autocommit=True, connect_timeout=5)


class AsyncConnPool:
    """Minimal bounded reuse pool for psycopg AsyncConnections (opt-in).

    `max_size` caps the total live (idle + checked-out) connections; `min_size`
    pre-opens that many on first use (psycopg_pool min_size semantics). Idle
    connections are health-checked on checkout and discarded if dead; on check-in a
    connection is cleaned (any open/aborted transaction rolled back -- which also
    discards a transaction-scoped SET LOCAL owner GUC) so no per-request state
    leaks to the next checkout. When the pool is exhausted, acquire() returns an
    ephemeral (un-pooled) connection so the request path never blocks/fails on the
    pool. Single asyncio event loop (the agent-pipe's), guarded by one Lock."""

    def __init__(self, *, min_size: int = 0, max_size: int = 8,
                 cfg: "Optional[dict]" = None) -> None:
        self._min = max(0, int(min_size))
        self._max = max(1, int(max_size))
        self._cfg = cfg
        self._free: list = []
        self._size = 0            # total live (idle + checked-out)
        self._lock = asyncio.Lock()
        self._warm = False

    @staticmethod
    def _is_live(conn) -> bool:
        return bool(conn) and not getattr(conn, "closed", False) \
            and not getattr(conn, "broken", False)

    @staticmethod
    async def _close(conn) -> None:
        try:
            await conn.close()
        except BaseException:     # noqa: BLE001 -- best-effort teardown
            pass

    async def _clean_for_reuse(self, conn) -> bool:
        """Return the connection to a clean session so it is safe to reuse: roll back
        any transaction left open or aborted (this ALSO discards any transaction-
        scoped SET LOCAL -- the RLS owner GUC -- so it cannot leak to the next
        checkout). True iff still live afterwards; False -> the caller discards it."""
        try:
            status = getattr(getattr(conn, "info", None), "transaction_status", 0)
            if status:            # non-IDLE: a txn/error was left open -> reset it
                await conn.rollback()
            return self._is_live(conn)
        except BaseException:     # noqa: BLE001 -- cannot verify clean -> do not reuse
            return False

    async def _ensure_warm(self, cfg: "Optional[dict]" = None) -> None:
        """Lazily pre-open up to `min` idle connections on first use. Best-effort:
        a connect failure stops warm-up (degrade-open) and the pool grows on
        demand instead."""
        if self._warm:
            return
        self._warm = True
        target = min(self._min, self._max)
        while True:
            async with self._lock:
                if self._size >= target:
                    return
                self._size += 1
            try:
                conn = await _open_conn(cfg if cfg is not None else self._cfg)
            except BaseException:  # noqa: BLE001 -- degrade-open: stop warming
                async with self._lock:
                    self._size -= 1
                return
            async with self._lock:
                self._free.append(conn)

    async def acquire(self, cfg: "Optional[dict]" = None):
        """Check out a connection. Returns (conn, pooled): pooled=True MUST be
        returned via release(); pooled=False is a degrade-open ephemeral connection
        the caller closes. Reuses a live idle connection, else grows up to max, else
        (exhausted) hands back an ephemeral direct connection (never blocks)."""
        await self._ensure_warm(cfg)
        async with self._lock:
            while self._free:
                conn = self._free.pop()
                if self._is_live(conn):
                    return conn, True
                self._size -= 1                # drop a dead idle connection
            grow = self._size < self._max
            if grow:
                self._size += 1
        if grow:
            try:
                conn = await _open_conn(cfg if cfg is not None else self._cfg)
            except BaseException:               # noqa: BLE001 -- undo the reservation
                async with self._lock:
                    self._size -= 1
                raise
            return conn, True
        # At capacity, none free -> degrade-open: a direct ephemeral connection
        # (not counted against the pool; closed on release). Never block a query.
        return await _open_conn(cfg if cfg is not None else self._cfg), False

    async def release(self, conn, pooled: bool, ok: bool = True) -> None:
        """Return a checked-out connection. A healthy, cleanly-finished POOLED
        connection is cleaned + put back on the free-list; an ephemeral (degrade)
        connection or a broken/errored one is closed (and a pooled discard frees its
        slot)."""
        if conn is None:
            return
        if not pooled:                          # ephemeral degrade conn -> always close
            await self._close(conn)
            return
        if ok and self._is_live(conn) and await self._clean_for_reuse(conn):
            async with self._lock:
                self._free.append(conn)
            return
        await self._close(conn)                 # broken / dirty / errored -> discard
        async with self._lock:
            self._size -= 1

    async def closeall(self) -> None:
        """Close every idle connection + drop the pool (graceful teardown / tests)."""
        async with self._lock:
            conns, self._free, self._size, self._warm = self._free, [], 0, False
        for c in conns:
            await self._close(c)


_POOL: "Optional[AsyncConnPool]" = None


def _get_pool(env: "Optional[dict]" = None, cfg: "Optional[dict]" = None):
    """The process-wide pool when [pgvector].pool_enable is on, else None (-> the
    byte-identical per-call connect path). Lazily created with the SSOT
    pool_min/pool_max on first enabled use; the flag is read per call so a live
    mios.toml edit + mios-sync-env takes effect without a restart."""
    global _POOL
    pc = pool_config(env)
    if not pc["enable"]:
        return None
    if _POOL is None:
        _POOL = AsyncConnPool(min_size=pc["min"], max_size=pc["max"], cfg=cfg)
    return _POOL


async def _reset_pool() -> None:
    """Close + drop the process pool (graceful teardown / test hook)."""
    global _POOL
    p, _POOL = _POOL, None
    if p is not None:
        await p.closeall()


@asynccontextmanager
async def _conn(cfg: "Optional[dict]" = None):
    """Async-context connection for ONE query bracket, shared by execute()/recall().

    DEFAULT (pool disabled): byte-identical to the historic per-call path -- open a
    fresh AsyncConnection, use it, close it (psycopg closes the connection on
    ``async with conn`` exit). Pool ENABLED: check a reused connection out of the
    bounded pool and return it on exit (a body that raises discards it). DEGRADE-
    OPEN: any pool checkout error falls back to a direct ephemeral connect, so a
    query never fails because of the pool."""
    import psycopg  # lazy; execute()/recall() already guarded its presence
    pool = None
    try:
        pool = _get_pool(cfg=cfg)
    except BaseException:          # noqa: BLE001 -- a pool misconfig never breaks a query
        pool = None
    if pool is None:
        async with await psycopg.AsyncConnection.connect(
                dsn(cfg), autocommit=True, connect_timeout=5) as conn:
            yield conn
        return
    try:
        conn, pooled = await pool.acquire(cfg)
    except BaseException:          # noqa: BLE001 -- exhausted/broken -> direct connect
        async with await psycopg.AsyncConnection.connect(
                dsn(cfg), autocommit=True, connect_timeout=5) as conn:
            yield conn
        return
    ok = True
    try:
        yield conn
    except BaseException:
        ok = False
        raise
    finally:
        await pool.release(conn, pooled, ok)


# ── async I/O (psycopg v3, imported lazily) ──────────────────────────────────
async def execute(sql: str, params: Optional[dict] = None,
                  *, fetch: bool = False, cfg: Optional[dict] = None,
                  rls_owner: "Optional[str]" = None) -> Any:
    """Best-effort async query via psycopg v3. Returns rows (list[dict]) when
    fetch=True, else None. Degrade-open: any error -> None (mirrors _db_post),
    so a DB hiccup never breaks a turn.

    ``rls_owner`` (T-068): when _owner_scope emits a scope (DB-side RLS enabled AND an
    enforce-verified owner -- see its P2-1 gate), the per-request owner GUC is bound +
    SET LOCAL inside the SAME transaction as the query, so the schema RLS policies scope
    rows to that owner. Default (None / RLS off / unverified) emits NO extra statement
    -> byte-identical to the pre-RLS path."""
    if _pg_skip():
        return None
    try:
        import psycopg  # lazy: only needed at cutover, not for the pure helpers
        from psycopg.rows import dict_row
    except Exception:  # noqa: BLE001 -- psycopg not installed (pre-cutover)
        return None
    try:
        scope = _owner_scope(rls_owner)
        async with _conn(cfg) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                if scope is not None:
                    # SET LOCAL is transaction-scoped: the GUC + the query MUST share
                    # one transaction (autocommit would otherwise discard the LOCAL
                    # setting right after it ran). The owner is bound as a parameter.
                    async with conn.transaction():
                        await cur.execute(scope[0], scope[1])
                        await cur.execute(sql, params or {})
                        return await cur.fetchall() if fetch else None
                await cur.execute(sql, params or {})
                if fetch:
                    return await cur.fetchall()
                return None
    except Exception:  # noqa: BLE001 -- degrade-open
        _pg_mark_down()
        return None


_COLS_CACHE: dict = {}


async def _table_columns(table: str, *, cfg: Optional[dict] = None) -> set:
    """Cached set of a table's column names (information_schema). Lets insert()
    drop fields the live schema doesn't have, so code<->schema drift degrades to
    a PARTIAL row instead of a silent total failure (+ a 30s backoff that would
    poison every other table's mirror too)."""
    if table in _COLS_CACHE:
        return _COLS_CACHE[table]
    rows = await execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = %(t)s",
        {"t": table}, fetch=True, cfg=cfg)
    cols = {r["column_name"] for r in (rows or []) if r.get("column_name")}
    if cols:
        _COLS_CACHE[table] = cols
    return cols


async def insert(table: str, fields: dict, *, cfg: Optional[dict] = None,
                 rls_owner: "Optional[str]" = None) -> Any:
    """Build + run a parameterized INSERT (WS-9c dual-write mirror). Filters the
    fields to the live table's columns first (drift-tolerant -- a code field the
    schema lacks is dropped, not fatal). Degrade-open -> None (psycopg/PG absent
    or error never breaks the caller). ``rls_owner`` (T-068) is forwarded to
    execute(): with RLS enabled AND an enforce-verified principal it SET-LOCALs the
    owner GUC in the insert's transaction so FORCE row-level security validates the new
    row (owner_user is written == this owner); default None / RLS off / unverified ->
    byte-identical (see _owner_scope's P2-1 gate)."""
    cols = await _table_columns(table, cfg=cfg)
    if cols:
        fields = {k: v for k, v in fields.items() if k in cols}
    if not fields:
        return None
    sql, params = build_insert(table, fields)
    return await execute(sql, params, fetch=False, cfg=cfg, rls_owner=rls_owner)


async def recall(qvec, *, table: str = "knowledge", k: int = 3,
                 ef_search: int = 100, owner: "Optional[str]" = None,
                 emb_version: "Optional[str]" = None,
                 cfg: Optional[dict] = None,
                 rls_owner: "Optional[str]" = None) -> list:
    """Native pgvector HNSW cosine recall on ONE connection (SET hnsw.ef_search
    then the SELECT must share a session). Returns rows [{id,q,answer,tier,
    satisfied,access_count,score}] (score = cosine similarity), or [] on any
    error / no psycopg. Caller applies the score threshold (matches the
    SurrealDB recall). `owner` (#59 WS-5): when set, scopes recall to that owner
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
    unverified emits NOTHING -> byte-identical (see _owner_scope's P2-1 gate)."""
    if _pg_skip():
        return []
    try:
        import psycopg
        from psycopg.rows import dict_row
    except Exception:  # noqa: BLE001
        return []
    try:
        scope = _owner_scope(rls_owner)
        sql, params = build_recall(table, k, owner=owner, emb_version=emb_version)
        params["qvec"] = vector_literal(qvec)
        async with _conn(cfg) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                if scope is not None:
                    # SET LOCAL owner GUC + the tuning SET + the SELECT share ONE
                    # transaction so the transaction-scoped GUC governs the SELECT
                    # (autocommit would otherwise discard it). Owner bound, not spliced.
                    async with conn.transaction():
                        await cur.execute(scope[0], scope[1])
                        await cur.execute(recall_tuning(ef_search))
                        await cur.execute(sql, params)
                        return await cur.fetchall()
                await cur.execute(recall_tuning(ef_search))
                await cur.execute(sql, params)
                return await cur.fetchall()
    except Exception:  # noqa: BLE001 -- degrade-open
        _pg_mark_down()
        return []
