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


import json
import logging
import os
import asyncio
import httpx
import mios_pg as _mios_pg

log = logging.getLogger("mios-agent-pipe")

PK_MAP = {
    "skill": "id",
    "verb": "name",
    "tool_call": "id",
    "directory_entry": "id",
    "event": "id",
    "session": "id"
}


def get_embed_config() -> Tuple[str, str]:
    light_port = os.environ.get("MIOS_PORT_LLM_LIGHT") or "8450"
    light_base = f"http://localhost:{light_port}"
    url = os.environ.get("MIOS_VERB_EMBED_URL") or f"{light_base}/v1/embeddings"
    model = os.environ.get("MIOS_VERB_EMBED_MODEL") or "nomic-embed-text"
    return url, model


def get_text_projection(table: str, row: dict) -> Optional[str]:
    if table == "skill":
        name = row.get("name") or ""
        desc = row.get("description") or ""
        return f"Skill: {name}\nDescription: {desc}".strip() or None
    elif table == "verb":
        facing = row.get("model_name") or row.get("name") or ""
        desc = row.get("desc_default") or ""
        txt = f"{facing}: {desc}"
        examples = row.get("examples")
        if examples:
            if isinstance(examples, str):
                try:
                    examples = json.loads(examples)
                except Exception:
                    pass
            if isinstance(examples, list):
                txt += "\nExample requests: " + " | ".join(str(e) for e in examples if str(e).strip())
        return txt.strip() or None
    elif table == "tool_call":
        tool = row.get("tool") or ""
        args = row.get("args") or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                pass
        result = row.get("result_preview") or row.get("output") or ""
        return f"Tool Call: {tool}\nArguments: {json.dumps(args)}\nResult: {result}".strip() or None
    elif table == "directory_entry":
        path = row.get("path") or ""
        kind = row.get("kind") or ""
        size = row.get("size") or 0
        summary = row.get("summary") or ""
        return f"File: {path}\nKind: {kind}\nSize: {size} bytes\nSummary: {summary}".strip() or None
    elif table == "event":
        act_type = row.get("act_type") or ""
        summary = row.get("summary") or ""
        return f"Event: {act_type}\nSummary: {summary}".strip() or None
    elif table == "session":
        meta = row.get("meta") or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}
        title = row.get("title") or meta.get("title") or ""
        first_prompt = row.get("first_prompt") or meta.get("first_prompt") or meta.get("first_user_text") or ""
        return f"Session Title: {title}\nPrompt: {first_prompt}".strip() or None
    return None


async def embed_text_with_retry(client: httpx.AsyncClient, text: str, url: str, model: str, prefix: str = "search_document: ") -> Optional[list[float]]:
    if prefix and not text.startswith(prefix):
        text = prefix + text
    backoff = 1.0
    for attempt in range(3):
        try:
            r = await client.post(
                url,
                json={"model": model, "input": text},
                headers={"Content-Type": "application/json"},
                timeout=10.0
            )
            if r.status_code == 200:
                data = r.json()
                v = data.get("embedding")
                if v is None:
                    _d = data.get("data")
                    if isinstance(_d, list) and _d:
                        v = _d[0].get("embedding")
                if isinstance(v, list) and v:
                    return [float(x) for x in v]
            log.warning("Embedding attempt %d failed with status %d", attempt + 1, r.status_code)
        except Exception as e:
            log.warning("Embedding attempt %d raised exception: %s", attempt + 1, e)
        
        if attempt < 2:
            await asyncio.sleep(backoff)
            backoff *= 2.0
    return None


async def run_backfill(current_version: str = "nomic-768-v1") -> dict:
    url, model = get_embed_config()
    results = {}
    
    for table, pk in PK_MAP.items():
        cols_map = {
            "skill": "id, name, description",
            "verb": "name, desc_default, examples, model_name",
            "tool_call": "id, tool, args, result_preview, output",
            "directory_entry": "id, path, kind, size, summary",
            "event": "id, act_type, summary",
            "session": "id, meta"
        }
        cols = cols_map[table]
        
        table_ver = current_version
        if table == "verb":
            try:
                from mios_pipe.routing.toolsearch import _verb_embed_fingerprint
                table_ver = _verb_embed_fingerprint()
            except Exception as e_fp:
                log.debug("Failed to get verb catalog fingerprint: %s", e_fp)
                
        select_query = (
            f"SELECT {cols} FROM {table} "
            f"WHERE emb IS NULL OR (emb_version IS DISTINCT FROM %(ver)s) "
            f"ORDER BY {pk} LIMIT 500"
        )
        try:
            rows = await _mios_pg.execute(select_query, {"ver": table_ver}, fetch=True)
        except Exception as e:
            log.warning("Failed to fetch backfill candidates for table %s: %s", table, e)
            continue
            
        if not rows:
            results[table] = 0
            continue
            
        embedded_count = 0
        async with httpx.AsyncClient() as client:
            for row in rows:
                pk_val = row[pk]
                txt = get_text_projection(table, row)
                if not txt:
                    continue
                    
                vec = await embed_text_with_retry(client, txt, url, model)
                if vec is None:
                    log.warning("Failed to embed text for %s row %s", table, pk_val)
                    continue
                    
                update_query = (
                    f"UPDATE {table} "
                    f"SET emb = %(emb)s::vector, emb_model = %(model)s, emb_version = %(ver)s "
                    f"WHERE {pk} = %(id)s"
                )
                try:
                    res = await _mios_pg.execute(update_query, {
                        "emb": vec,
                        "model": model,
                        "ver": table_ver,
                        "id": pk_val
                    })
                    if res is not None:
                        embedded_count += 1
                except Exception as e_up:
                    log.warning("Failed to update embedding for %s row %s: %s", table, pk_val, e_up)
                    
        results[table] = embedded_count
        log.info("Completed embedding backfill for table %s: %d rows updated", table, embedded_count)
        
    return results

async def main():
    log.info("Starting embedding backfill worker...")
    res = await run_backfill("nomic-768-v1")
    log.info("Backfill completed. Results: %s", res)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
