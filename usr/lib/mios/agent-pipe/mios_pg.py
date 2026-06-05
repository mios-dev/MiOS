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

import json
import os
import time
from typing import Any, Optional

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


# ── config / DSN (SSOT: mios.toml [pgvector] -> MIOS_PG_* env via userenv.sh) ──
def pg_config(env: Optional[dict] = None) -> dict:
    """Resolve connection settings from the environment (already layered from
    mios.toml by userenv.sh). Local-only defaults match the quadlet."""
    e = env if env is not None else os.environ
    return {
        "host": e.get("MIOS_PG_HOST", "localhost"),
        "port": int(e.get("MIOS_PORT_PGVECTOR", "5432") or 5432),
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


def build_recall(table: str = "knowledge", k: int = 3) -> "tuple[str, dict]":
    """pgvector HNSW cosine recall: nearest `k` rows to %(qvec)s, returning the
    cosine SIMILARITY (1 - distance). Threshold-filter app-side (matches the
    current recall). Pair with `SET hnsw.ef_search` (see recall_tuning)."""
    sql = (
        f"SELECT id, q, answer, tier, satisfied, access_count, "
        f"1 - (emb <=> %(qvec)s::vector) AS score "
        f"FROM {table} WHERE emb IS NOT NULL "
        f"ORDER BY emb <=> %(qvec)s::vector LIMIT %(k)s;"
    )
    return sql, {"qvec": None, "k": int(k)}  # caller sets qvec = vector_literal(q)


def recall_tuning(ef_search: int = 100) -> str:
    """Per-query HNSW recall/speed knob; run before the recall SELECT."""
    return f"SET hnsw.ef_search = {int(ef_search)};"


# ── async I/O (psycopg v3, imported lazily) ──────────────────────────────────
async def execute(sql: str, params: Optional[dict] = None,
                  *, fetch: bool = False, cfg: Optional[dict] = None) -> Any:
    """Best-effort async query via psycopg v3. Returns rows (list[dict]) when
    fetch=True, else None. Degrade-open: any error -> None (mirrors _db_post),
    so a DB hiccup never breaks a turn. NOT wired into the live pipe yet."""
    if _pg_skip():
        return None
    try:
        import psycopg  # lazy: only needed at cutover, not for the pure helpers
        from psycopg.rows import dict_row
    except Exception:  # noqa: BLE001 -- psycopg not installed (pre-cutover)
        return None
    try:
        async with await psycopg.AsyncConnection.connect(
                dsn(cfg), autocommit=True, connect_timeout=5) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
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


async def insert(table: str, fields: dict, *, cfg: Optional[dict] = None) -> Any:
    """Build + run a parameterized INSERT (WS-9c dual-write mirror). Filters the
    fields to the live table's columns first (drift-tolerant -- a code field the
    schema lacks is dropped, not fatal). Degrade-open -> None (psycopg/PG absent
    or error never breaks the caller)."""
    cols = await _table_columns(table, cfg=cfg)
    if cols:
        fields = {k: v for k, v in fields.items() if k in cols}
    if not fields:
        return None
    sql, params = build_insert(table, fields)
    return await execute(sql, params, fetch=False, cfg=cfg)


async def recall(qvec, *, table: str = "knowledge", k: int = 3,
                 ef_search: int = 100, cfg: Optional[dict] = None) -> list:
    """Native pgvector HNSW cosine recall on ONE connection (SET hnsw.ef_search
    then the SELECT must share a session). Returns rows [{id,q,answer,tier,
    satisfied,access_count,score}] (score = cosine similarity), or [] on any
    error / no psycopg. Caller applies the score threshold (matches the
    SurrealDB recall)."""
    if _pg_skip():
        return []
    try:
        import psycopg
        from psycopg.rows import dict_row
    except Exception:  # noqa: BLE001
        return []
    try:
        async with await psycopg.AsyncConnection.connect(
                dsn(cfg), autocommit=True, connect_timeout=5) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(recall_tuning(ef_search))
                sql, params = build_recall(table, k)
                params["qvec"] = vector_literal(qvec)
                await cur.execute(sql, params)
                return await cur.fetchall()
    except Exception:  # noqa: BLE001 -- degrade-open
        _pg_mark_down()
        return []
