# AI-hint: Provides pure, DB-free logic for generating SurrealQL fragments and parsing results to identify and prune stale, low-access, and non-pinned rows from the WS-3 knowledge-table.
# AI-functions: protect_where, ttl_where, parse_count, parse_ids, delete_stmt, plan_sweep
"""mios_evict -- pure helpers for the WS-3 knowledge-table eviction sweep.

DB-free + stdlib-only so the SQL-building, response-parsing, and eviction-
planning logic unit-tests in isolation (sibling-module pattern, like mios_sched
/ mios_jsonsalvage). server.py owns the actual SurrealDB I/O, the config knobs,
and the background loop; this module owns only the deterministic, testable parts.

The knowledge table is append-only (one row per finished turn), so it grows
unbounded. Eviction removes only STALE, never-recalled, neutral-outcome rows and
NEVER touches a hot / satisfied / pinned / recently-accessed row.
"""

from __future__ import annotations

from typing import Optional


def protect_where(min_access: int) -> str:
    """SurrealQL WHERE fragment matching EVICTABLE rows only: never hot, never a
    satisfied outcome, never pinned (e.g. a user-remembered fact), and recalled
    fewer than `min_access` times. NULL-safe via ?? so legacy rows that predate
    the tiering fields are handled (a missing field reads as its neutral
    default, which keeps the row evictable rather than crashing)."""
    return (
        "(tier ?? 'warm') != 'hot' "
        "AND (satisfied ?? false) != true "
        "AND (pinned ?? false) != true "
        f"AND (access_count ?? 0) < {int(min_access)}"
    )


def ttl_where(protect: str, ttl_days: int) -> str:
    """Extend the evictable fragment with the age predicate: not accessed (or,
    failing that, not created) within the last `ttl_days` days."""
    return f"{protect} AND (last_access ?? ts) < time::now() - {int(ttl_days)}d"


def parse_count(resp: Optional[list]) -> int:
    """Pull the integer out of a `SELECT count() AS c ... GROUP ALL` response
    (the SurrealDB /sql statement-result list). Degrade-open -> 0."""
    for st in (resp or []):
        if isinstance(st, dict) and isinstance(st.get("result"), list) \
                and st["result"]:
            row = st["result"][0]
            if isinstance(row, dict):
                try:
                    return int(row.get("c") or 0)
                except (TypeError, ValueError):
                    return 0
    return 0


def parse_ids(resp: Optional[list]) -> list:
    """Extract record-id strings ('knowledge:abc') from a `SELECT id` response.
    Anything without a ':' is skipped (defensive against malformed rows)."""
    ids: list = []
    for st in (resp or []):
        if isinstance(st, dict) and isinstance(st.get("result"), list):
            for r in st["result"]:
                if not isinstance(r, dict):
                    continue
                rid = r.get("id")
                rid = rid if isinstance(rid, str) else str(rid)
                if ":" in rid:
                    ids.append(rid)
    return ids


def delete_stmt(ids: list) -> str:
    """Build a single `DELETE a, b, c;` statement, or '' when there are no valid
    record ids (so the caller can skip the round-trip)."""
    valid = [s for s in (str(i) for i in ids) if ":" in s]
    if not valid:
        return ""
    return "DELETE " + ", ".join(valid) + ";"


def plan_sweep(total: int, ttl_candidates: int, max_rows: int,
               batch: int) -> dict:
    """Pure decision arithmetic: given the live row count, the TTL-candidate
    count, the row cap, and the per-sweep batch ceiling, decide how many rows to
    remove from the TTL set and the cap-overflow set. TTL removals take priority
    within the batch budget; cap removals use what's left. (server.py executes
    the SQL; this is the testable arithmetic that bounds blast radius.)"""
    batch = max(0, int(batch))
    ttl_del = min(max(0, int(ttl_candidates)), batch)
    overflow = max(0, int(total) - max(0, int(max_rows)))
    cap_del = min(overflow, max(0, batch - ttl_del))
    return {"overflow": overflow, "ttl_delete": ttl_del, "cap_delete": cap_del}
