# AI-hint: WS-A3 pure, DB-free logic for the knowledge-table eviction sweep -- now PARAMETERIZED POSTGRES (the cutover). Builds parameterized pg SQL (named %(min_access)s/%(ttl_days)s/%(limit)s/%(ids)s placeholders -- NO string interpolation, injection-safe) + parses pg dict-rows, replacing the old SurrealQL fragments that NO-OP'd under db_backend=postgres (the SurrealQL DELETE/count never reached pg). server.py owns the mios_pg I/O + the loop; this module owns the deterministic SQL-building + parsing + the blast-radius arithmetic so it unit-tests in isolation.
# AI-related: ./mios_pg.py, ./server.py, /usr/share/mios/postgres/schema-init.sql, ./test_mios_evict.py
# AI-functions: evict_where, order_by, count_sql, select_ids_sql, delete_ids_sql, evict_params, parse_count, parse_ids, plan_sweep
"""mios_evict -- pure helpers for the knowledge-table eviction sweep (WS-A3).

DB-free + stdlib-only so the SQL-building, response-parsing, and planning logic
unit-tests in isolation (sibling-module pattern). server.py owns the actual
Postgres I/O (mios_pg.execute), the config knobs, and the background loop.

WS-A3 cutover: this emits PARAMETERIZED Postgres (named placeholders bound by
mios_pg) -- the previous SurrealQL (`??`, `time::now() - Nd`, record-id
`DELETE a, b;`) silently no-op'd once db_backend='postgres' (SurrealDB :8000 is
retired), so eviction never ran. The knowledge table is append-only; eviction
removes only STALE, never-recalled, neutral-outcome rows and NEVER a
hot/satisfied/pinned/recently-accessed one.
"""

from __future__ import annotations

from typing import List, Optional, Tuple


def evict_where(*, with_ttl: bool) -> str:
    """The EVICTABLE-rows WHERE fragment (parameterized pg). Matches rows that are
    never hot, never a satisfied outcome, never pinned, and recalled fewer than
    %(min_access)s times. COALESCE makes legacy rows (missing tiering fields)
    read as their neutral default (-> evictable, never a crash). with_ttl adds
    the age predicate (not accessed/created within %(ttl_days)s days)."""
    base = (
        "COALESCE(tier, 'warm') <> 'hot' "
        "AND COALESCE(satisfied, false) <> TRUE "
        "AND COALESCE(pinned, false) <> TRUE "
        "AND COALESCE(access_count, 0) < %(min_access)s"
    )
    if with_ttl:
        base += (" AND COALESCE(last_access, ts) < "
                 "now() - make_interval(days => %(ttl_days)s)")
    return base


def order_by(*, cap: bool) -> str:
    """Eviction order. TTL sweep: oldest-accessed first. Cap-overflow sweep:
    least-recalled then oldest (shed the lowest-value rows first)."""
    if cap:
        return "COALESCE(access_count, 0) ASC, COALESCE(last_access, ts) ASC"
    return "COALESCE(last_access, ts) ASC"


def count_sql(table: str, where: str) -> str:
    """`SELECT count(*) AS c` over the evictable set. `table` is a validated
    identifier (KNOWLEDGE_TABLE), never user input; `where` is parameterized."""
    return f"SELECT count(*) AS c FROM {table} WHERE {where}"


def select_ids_sql(table: str, where: str, order: str) -> str:
    """Select up to %(limit)s evictable ids, lowest-value first."""
    return f"SELECT id FROM {table} WHERE {where} ORDER BY {order} LIMIT %(limit)s"


def delete_ids_sql(table: str) -> str:
    """Delete a set of bigint ids in one parameterized statement (pg `id` is a
    bigint identity, NOT a 'table:xyz' record id -> = ANY(%(ids)s), not concat)."""
    return f"DELETE FROM {table} WHERE id = ANY(%(ids)s)"


def evict_params(min_access: int, ttl_days: int, limit: int = 0) -> dict:
    """The bound params for the builders above (named -> reused across count +
    select; the SQL ignores any it doesn't reference)."""
    return {"min_access": int(min_access), "ttl_days": int(ttl_days),
            "limit": max(0, int(limit))}


def parse_count(rows: Optional[list]) -> int:
    """Pull the integer from a `SELECT count(*) AS c` pg result (dict rows).
    Degrade-open -> 0."""
    for r in (rows or []):
        if isinstance(r, dict):
            try:
                return int(r.get("c") or 0)
            except (TypeError, ValueError):
                return 0
    return 0


def parse_ids(rows: Optional[list]) -> List[int]:
    """Extract bigint ids from a `SELECT id` pg result (dict rows). Skips
    anything non-integer (defensive)."""
    ids: List[int] = []
    for r in (rows or []):
        if not isinstance(r, dict):
            continue
        try:
            ids.append(int(r.get("id")))
        except (TypeError, ValueError):
            continue
    return ids


def plan_sweep(total: int, ttl_candidates: int, max_rows: int,
               batch: int) -> dict:
    """Pure decision arithmetic (UNCHANGED): given the live row count, the
    TTL-candidate count, the row cap, and the per-sweep batch ceiling, decide how
    many to remove from the TTL set and the cap-overflow set. TTL takes priority
    within the batch budget; cap uses what's left (bounds blast radius)."""
    batch = max(0, int(batch))
    ttl_del = min(max(0, int(ttl_candidates)), batch)
    overflow = max(0, int(total) - max(0, int(max_rows)))
    cap_del = min(overflow, max(0, batch - ttl_del))
    return {"overflow": overflow, "ttl_delete": ttl_del, "cap_delete": cap_del}
