# PostgreSQL + pgvector Unification (WS-9) — patterns brief + migration draft

> Status: DRAFT (2026-06-04). Operator decision: migrate the agent-plane
> datastore off **SurrealDB (BSL 1.1, source-available — not OSI-FOSS)** onto
> **PostgreSQL + pgvector (OSI-FOSS)**, done the standard ("native") way. Schema
> artifact: `usr/share/mios/postgres/schema-init.sql`. Companion:
> `llamacpp-engine-conversion.md` (the engine-side draft).

## 1. Why this is the standard ("native") pattern, not a bespoke port

The research is unambiguous — the industry has converged on "just use Postgres +
pgvector" for agent state + memory + retrieval:

- **Embeddings live in the same table/transaction as the rows** — no separate
  vector DB. A `vector(768)` column + an HNSW index *is* the vector store.
- **HNSW is the 2026 default index** (build-before-data, <20 ms at 1M vectors,
  >95% recall). Canonical DDL: `CREATE INDEX … USING hnsw (emb vector_cosine_ops)
  WITH (m=16, ef_construction=64)`; query `ORDER BY emb <=> $1 LIMIT k` with
  `SET hnsw.ef_search`. nomic-embed's **768 dims < pgvector's 2000-dim HNSW
  limit**, so plain `vector` (no halfvec).
- **Hybrid search** (vector `<=>` + Postgres `tsvector` full-text) is the
  standard quality lever — MiOS's Python topical-anchor guard becomes a real
  tsvector fusion (a generated `fts` column + GIN index, language-neutral
  `simple` config).
- **Letta/MemGPT, Memori, and OWUI all use exactly this stack.** OWUI is native:
  `DATABASE_URL=postgresql://…` + `VECTOR_DB=pgvector` (pgvector + Chroma are the
  only two OWUI-maintained vector stores) — so OWUI folds onto the **same**
  container.
- **The OpenAI embeddings flow is unchanged**: nomic-embed via the
  OpenAI-compatible `/v1/embeddings` endpoint (Law 5), 768-dim, stored in
  `vector(768)`.

## 2. What consolidates vs what stays separate

**Onto the one Postgres+pgvector container (agent plane):** `knowledge`,
`agent_memory` (mios-remember), `event`, `tool_call`, `session`, `skill` /
`skill_invocation`, `sys_env`, `pending_action` (WS-6), `run_template` (WS-6),
`scratch` (folds the in-process `_SCRATCHPADS` → restart-survivable), `kanban`
(authoritative; retires Hermes' SQLite + the SurrealDB shadow). Plus **OWUI**
(`DATABASE_URL`+`VECTOR_DB=pgvector`) and **Guacamole** (already Postgres → point
at the same instance, separate database).

**Stay separate (domain appliances — own schema + upgrade path):** Forgejo,
Ceph, K3s/etcd, AdGuard, CrowdSec. Force-merging couples failure domains for ~no
gain.

## 3. Schema

Full DDL in `usr/share/mios/postgres/schema-init.sql` — idempotent, the standard
relational + JSONB + `vector(768)` pattern. Highlights: HNSW cosine indexes on
`knowledge.emb` + `agent_memory.emb`; a generated `fts` tsvector + GIN on
`knowledge` for hybrid search; btree indexes on the hot filters (ts, session_id,
tier, status, class); `passport` ed25519 envelopes preserved as JSONB.

## 4. The shared `mios-db` client (the migration seam)

A single psycopg-based `mios-db` client replaces the **~9 callers that
reimplement the SurrealDB `/sql` POST** (one hardcodes `root:root`). Every query
goes through it → centralizes creds (from `mios.toml`/secret, no literals),
gives one place to swap engines, and is the seam the cutover happens behind.
Agent-pipe's `_db_post`/`_db_create`/`_recall_knowledge`, `mios-remember`,
`mios-daemon`, `mios-skills` all migrate to it. This is dedup-audit Cluster 2.

## 5. Migration stages (staged, reversible, default-on per directive)

1. **Stand up** a Postgres+pgvector quadlet (FOSS image `docker.io/pgvector/
   pgvector:pg17`, Apache/PostgreSQL-licensed) alongside SurrealDB — additive,
   breaks nothing. SSOT `[postgres]`/`[ports].postgres`; run `schema-init.sql`.
2. **Build the psycopg `mios-db`** client + port the read/write helpers behind
   it (SurrealQL → SQL). Keep SurrealDB reads as a fallback during cutover.
3. **Native vector recall**: replace `_recall_knowledge`'s SELECT-60-then-Python-
   cosine with pgvector `<=>` HNSW (+ optional tsvector hybrid). (Quick win.)
4. **Scratchpad + kanban** → Postgres tables (quick wins: persistence +
   authoritative).
5. **Point OWUI** at Postgres (`DATABASE_URL`+`VECTOR_DB=pgvector`); migrate its
   knowledge/RAG. **Guacamole** → same instance.
6. **Backfill** the existing SurrealDB rows (export → INSERT) — knowledge/events/
   tool_call/etc. Verify counts + a recall smoke test.
7. **Retire SurrealDB** (drop the quadlet + BSL image) once parity is confirmed.

## 6. Quick wins (the engine-agnostic consolidation) — subsumed here

Shared client + kill hardcoded creds (step 2) · native vector recall (3) ·
scratchpad persistence (4) · kanban authoritative (4). All land inside the
Postgres migration done the standard way.

## 7. License resolution

This closes the consistency gap: MiOS is FOSS, and its unified datastore becomes
**OSI-FOSS** (PostgreSQL License + pgvector PostgreSQL License) instead of
SurrealDB's BSL 1.1 — the same license class flagged for the Wide-Moat OCU.

Sources: pgvector (github.com/pgvector/pgvector); OpenAI Cookbook vector-DB / RAG
examples; OWUI docs (DATABASE_URL + VECTOR_DB=pgvector); Letta/Memori
agent-memory-on-Postgres. Verify against current code before each stage.

---

## Build status — additive step (2026-06-04): DONE, alongside SurrealDB

Stood up the Postgres+pgvector container + the client foundation WITHOUT touching
the live SurrealDB path (cutover = WS-9c). New / edited:
- `usr/share/mios/postgres/schema-init.sql` — canonical pgvector DDL (idempotent;
  runs on first init via the initdb mount).
- `usr/share/containers/systemd/mios-pgvector.container` — quadlet
  (pgvector/pgvector:pg17, host-net, schema-init mount, PGDATA volume, uid 826).
- `usr/lib/mios/agent-pipe/mios_pg.py` — psycopg client foundation (pure DSN /
  vector-literal / parameterized INSERT + cosine-recall builders; lazy psycopg;
  degrade-open). `test_mios_pg.py` = **18/18 pass**.
- `usr/libexec/mios/mios-db` — new `--pg '<sql>'` mode (local psql → container
  psql fallback; SSOT creds, no hardcodes). `bash -n` OK.
- SSOT: `mios.toml` `[ports].pgvector=5432`, `[image.sidecars].pgvector` (pg17),
  `[services.pgvector]` (uid 826), `[pgvector]` config section. TOML parses.
- Identity/wiring: `sysusers.d/50-mios-services.conf` (mios-pgvector 826 +
  mios-ai), `tmpfiles.d/mios-pgvector.conf` (PGDATA dir), `tools/lib/userenv.sh`
  (pgvector → MIOS_PG_*/MIOS_PGVECTOR_* maps), `automation/15-render-quadlets.sh`
  (bash-fallback allow-list). `bash -n` OK.

Deploy (operator): `just build` (bakes the quadlet + sysusers + pulls the pgvector
image via bound-images) OR live: `wsl sudo cp` the quadlet + schema →
`mios-sync-env` → `systemctl daemon-reload && systemctl start
mios-pgvector.service`. Verify: `mios-db --pg "SELECT extversion FROM
pg_extension WHERE extname='vector';"` and the agent-plane tables exist
(`mios-db --pg '\dt'`). Nothing live moved — SurrealDB still serves the pipe.

## Build status — cutover code (WS-9c, 2026-06-04): DONE, default `dual` (safe)

The cutover is wired with a **backend selector** (`[pgvector].db_backend`, env
`MIOS_DB_BACKEND`): `surreal` | `dual` | `postgres`. **Default `dual`** = the
standard safe live-migration: writes mirror to BOTH stores, reads stay on
SurrealDB — so Postgres is exercised + verifiable live WITHOUT risking the read
path or any data loss.

- `mios_pg.py` — added `insert()` + native `recall()` (one-connection
  `SET hnsw.ef_search` + `<=>` SELECT) + jsonb handling in `build_insert` + a 30s
  connect-failure backoff (so `dual` is cheap even before mios-pgvector is
  deployed). `test_mios_pg.py` = **23/23**.
- `server.py` — `import mios_pg`; `DB_BACKEND`/`_PG_ENABLED`/`_PG_PRIMARY` +
  `_pg_mirror()` after `_db_fire`; fire-and-forget mirrors in the hot writes
  (`_store_knowledge_task` knowledge, `_emit_session_event` event,
  `_hitl_record_pending` pending_action, `_capture_run_template` run_template);
  `_recall_knowledge_pg()` native recall used when `_PG_PRIMARY` (inert in `dual`,
  degrade-open to SurrealDB). `py_compile` OK.
- `mios.toml [pgvector].db_backend = "dual"`.

Operator cutover sequence: deploy the container (additive step above) + add
`psycopg[binary]` to the agent-pipe env → run with default `dual` → verify the
mirror fills (`mios-db --pg 'SELECT count(*) FROM knowledge;'` rises alongside
SurrealDB) → backfill historical rows (export SurrealDB → INSERT) → flip
`db_backend="postgres"` (native `<=>` recall goes live) → after a soak, retire
SurrealDB + point OWUI/Guacamole at this instance.

NOTE: `_store_knowledge_task` etc. still ALSO write SurrealDB in `dual`; the
remaining one-liners (mios-remember/daemon/skills writing to PG) move at the
`postgres`-flip. psycopg must be in the agent-pipe venv for the mirror to
actually write (absent → degrade-open no-op).
