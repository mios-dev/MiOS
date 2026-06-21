<!-- AI-hint: WS-A3 completion record -- the SurrealDB->Postgres+pgvector cutover for the agent CLIs: the mios-pg-query extended-protocol (--exec-json) parameter-binding keystone, parameterized knowledge eviction, the canonical pg kanban queue, the per-tool CLI SQL-injection fixes + dead-SurrealQL deletions, the drift-check 10 regression lock, and the explicitly-named deferred residuals (mios-daemon dead SurrealQL + read-gating, mios-viking migration).
     AI-related: ../../../../../usr/libexec/mios/mios-pg-query, ../../../../../usr/libexec/mios/mios-db, ../../../../../usr/lib/mios/agent-pipe/mios_evict.py, ../../../../../automation/38-drift-checks.sh -->
# WS-A3 — SurrealDB → Postgres cutover: parameterized eviction, canonical kanban, CLI SQL-safety

Status: **offline-complete + gated** (operator live-tests in the VM). 2026-06-20.

SurrealDB (`:8000`, BSL 1.1) is retired; the agent datastore is Postgres+pgvector.
Any code still emitting SurrealQL **silently no-ops** on pg (the connection fails,
the error is swallowed, a 30s backoff arms) — so dead SurrealQL is not just cruft,
it is a *silently broken feature*. And every value that was f-string-spliced into
SQL (mitigated only by hand-rolled `_pgesc`/`_pgq` single-quote doubling) was a
SQL-injection surface. WS-A3 closes both.

## The keystone: parameter binding for the pure-stdlib pg client

`mios-pg-query` only spoke the **simple** query protocol (raw SQL in a `Q`
message) — it *could not bind parameters at all*, which is *why* every CLI
f-string-spliced values. It now also speaks the **extended** protocol
(Parse/Bind/Execute/Sync, text format, backend-inferred types) behind a
backward-compatible `--exec-json` mode reading a stdin envelope:

```
{"sql": "... $1 ... $2 ...", "params": [v1, v2]}            # single statement
{"statements": [{"sql": "...", "params": [...]}, ...]}      # atomic BEGIN/COMMIT
```

No flag → the legacy simple-`Q` path is byte-for-byte unchanged (zero risk to
existing callers). `mios-db --pg-json` forwards the same envelope with the
SSOT-mapped `MIOS_PG_*` connection env, so it stays the single DB entry point.
Integers (LIMIT, interval counts) stay inline via `int()` coercion; strings /
vectors / text bind out-of-band. 36 byte-level wire asserts in
`test_mios_pgwire.py`.

## Done

- **Parameterized eviction** (`mios_evict.py` + server.py `_db_count`/
  `_evict_select_ids`/`_evict_delete_ids`/`_evict_knowledge`): was SurrealQL
  (`??`, `time::now() - Nd`, record-id `DELETE a,b;`) → never ran on pg → the
  knowledge table never evicted. Now parameterized pg (`COALESCE`, `now() -
  make_interval`, `id = ANY(%(ids)s)`). 25 asserts.
- **Canonical kanban** (server.py `_shadow_queue_tasks`): wrote to SurrealDB
  `kanban_shadow` (dead) whose pg mirror targeted a non-existent table → the
  refined multi-task queue was invisible. Now a parameterized upsert into the
  canonical pg `kanban` (`INSERT … ON CONFLICT (id) DO UPDATE`).
- **CLI SQL-safety** — parameterized via the envelope + dead SurrealQL deleted:
  `mios-remember`, `mios-kg`, `mios-rag`, `mios-ingest`, `mios-directory-lookup`,
  `mios-skills` (this also un-breaks the SPM miner, which in the default `dual`
  mode read the retired `:8000` and *never mined a skill*), `mios-day0-reset`
  (bash), and `mios-db` (the `--embed` python-source-injection nit). The
  `mios-knowledge-add`/`-search` tools were already parameterized (sqlite `?`).
  Adversarial `test_mios_cli_sqlsafety.py` fires a `drop table` / `delete from`
  payload and asserts it lands **only** in `params`, never in any SQL statement.
- **mios-daemon** live pg writes parameterized (`_pg_insert`,
  `_pg_replace_directory_entries` — the latter splices filesystem paths + file
  content) via a signature-preserving internal rewrite (zero call-site churn for
  the runtime-critical daemon).
- **Regression lock**: `38-drift-checks.sh` check (10) fails the gate if any
  libexec tool reintroduces `post_sql`/`_sql`/`:8000/sql`/`_pgesc`/`_pgq`.
- **Build gate**: all `usr/libexec/mios/test_mios_*.py` now run in `build.sh`.

## Deferred residuals (NOT silent — allowlisted in drift-check 10)

These are *functional-hygiene / migration* items, not live injection holes; the
drift-gate names them so they can't hide:

1. **mios-daemon dead SurrealQL** — ~20 harmless no-op SurrealQL branches
   (`_db_post`/`_db_create` CREATE strings/`time::now()` log queries) remain.
   Higher-risk to excise blind in the always-running daemon (runaway history; not
   host-live-testable from the build host). Its **live pg writes are already
   parameterized** (above).
2. **mios-daemon read-gating** — several reads gate the pg path on `_PG_PRIMARY`
   not `_PG_ENABLED`, so in the default `dual` mode the rolling report /
   satisfaction monitor read the dead `:8000` and get `[]`. Flip to `_PG_ENABLED`
   (+ supply pg_sql for the two untranslated reads) once VM-verifiable. The one
   tainted read value (`_tool_calls_for_refine` `refine_ts`) only reaches a
   `_PG_PRIMARY`-gated branch; bind it as `$1` when that gate flips.
3. ~~**mios-viking**~~ — DONE: dead `_db_sql` SurrealDB transport removed, the
   knowledge-ns reads (`_ls_knowledge` filter, `_cat_knowledge` id) bound via
   `mios-db --pg-json`; no longer in the drift-10 allowlist.

Operator: live-test the memory/skill/kanban/RAG paths in the VM
(`just build` → boot → `mios-remember add`, `mios-kg lookup`, `mios-skills mine`,
a multi-task prompt, `mios-rag query`).
