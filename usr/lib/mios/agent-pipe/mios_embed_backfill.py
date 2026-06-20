# AI-hint: WS-A2 embedding-version hygiene -- the pure decision core for an off-hot-path re-embed (backfill) job. When the embedding model or dimensionality changes, every stored vector tagged with the OLD emb_version is stale (cosine recall silently degrades, mixing incompatible vector spaces). This module decides WHICH rows need re-embedding (emb present but emb_version != the current identity) and plans bounded batches; it also builds the parameterized candidate-SELECT + version-stamp UPDATE SQL. server.py / a CLI owns the actual DB I/O + the embed call; this module is pure (no DB, no network) so it unit-tests in isolation.
# AI-related: ./mios_pg.py, ./server.py, /usr/share/mios/postgres/schema-init.sql, /usr/share/mios/mios.toml, ./test_mios_embed_backfill.py
# AI-functions: needs_reembed, select_candidates_sql, stamp_version_sql, plan_batches, summarize
"""mios_embed_backfill -- embedding-version hygiene for the MiOS agent-pipe
(WS-A2, the AIOS Memory-Manager embedding-identity layer).

Pure stdlib so it unit-tests in isolation, in the sibling-module style of
mios_sched / mios_pdp. server.py (or a maintenance CLI) owns the DB I/O and the
embedding call; this module owns only the DECISIONS: is a row's vector stale,
which rows are candidates, and how to batch the work so a backfill never
stampedes the embedder or the DB.

Why versioning
==============
Every embedded row carries emb_model + emb_version. The embedding space is only
comparable WITHIN one identity: if the model (or its dimensionality) changes,
old vectors are meaningless under the new model, so cosine recall silently
returns garbage neighbours. Tagging each row lets a backfill find + re-embed the
stale rows off the hot path, and lets recall optionally restrict to the current
identity until the backfill catches up.
"""

from __future__ import annotations

from typing import List, Optional, Tuple


def needs_reembed(has_emb: bool, row_version: Optional[str],
                  current_version: str) -> bool:
    """True if a row should be re-embedded: it HAS a vector but its emb_version
    differs from (or predates -- NULL) the current identity. A row with no
    vector is left for the normal embed-on-write path, not the backfill."""
    if not has_emb:
        return False
    rv = (row_version or "").strip()
    cur = (current_version or "").strip()
    return rv != cur


def select_candidates_sql(table: str, current_version: str,
                          limit: int = 500) -> Tuple[str, dict]:
    """Parameterized SELECT for rows whose vector is stale under the current
    emb_version (emb present AND emb_version IS DISTINCT FROM current). Returns
    (sql, params). `table` is validated against a small allow-list by the caller;
    here it is interpolated as an identifier ONLY after that check (never user
    input)."""
    lim = max(1, int(limit))
    sql = (
        f"SELECT id FROM {table} "
        f"WHERE emb IS NOT NULL "
        f"AND (emb_version IS DISTINCT FROM %(ver)s) "
        f"ORDER BY id "
        f"LIMIT %(lim)s"
    )
    return sql, {"ver": str(current_version), "lim": lim}


def stamp_version_sql(table: str) -> str:
    """Parameterized UPDATE that writes a freshly-computed vector + the current
    identity onto one row. Caller binds %(emb)s/%(model)s/%(ver)s/%(id)s."""
    return (
        f"UPDATE {table} "
        f"SET emb = %(emb)s, emb_model = %(model)s, emb_version = %(ver)s "
        f"WHERE id = %(id)s"
    )


def plan_batches(ids: List, batch_size: int = 50) -> List[list]:
    """Split a candidate id list into bounded batches so the backfill embeds +
    writes in chunks (never one giant transaction, never one-at-a-time)."""
    bs = max(1, int(batch_size))
    return [list(ids[i:i + bs]) for i in range(0, len(ids), bs)]


def summarize(candidate_count: int, batch_size: int = 50) -> dict:
    """A cheap plan summary for logging / the /v1/scheduler diagnostics."""
    bs = max(1, int(batch_size))
    n = max(0, int(candidate_count))
    return {
        "candidates": n,
        "batch_size": bs,
        "batches": (n + bs - 1) // bs,
    }
