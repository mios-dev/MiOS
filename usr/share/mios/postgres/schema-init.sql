-- AI-hint: Initializes the PostgreSQL schema for the agent-plane, establishing the knowledge table with pgvector support for 768-dim embeddings and GIN indexes for hybrid-search across Q&A pairs.
-- AI-related: mios-remember, mios-skills, mios-daemon, mios-directory-lookup
-- MiOS agent-plane schema for PostgreSQL + pgvector (WS-9, 2026-06-04).
-- FOSS-pure replacement for the SurrealDB (BSL 1.1) agent store. Standard
-- "back to SQL" agent-memory pattern (Letta/MemGPT/Memori/OWUI all converge
-- here): relational columns + JSONB for flexible/document fields + a vector(768)
-- column with an HNSW cosine index wherever semantic recall is needed.
--
-- Embeddings: 768-dim from nomic-embed-text via the OpenAI-compatible
-- /v1/embeddings endpoint (served by mios-llm-light; MiOS Law 5). 768 < pgvector's 2000-dim HNSW
-- limit for the `vector` type, so no halfvec needed. Cosine distance operator is
-- `<=>` with opclass vector_cosine_ops.
--
-- Idempotent: safe to run on every container start (schema-init step).
-- Domain appliances (Forgejo/Ceph/K3s/AdGuard/CrowdSec) keep their own stores.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS mios_letta;

-- ── knowledge: every finished Q+A (auto-append) + semantic recall ────────────
CREATE TABLE IF NOT EXISTS knowledge (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    q             text NOT NULL,
    answer        text NOT NULL,
    sources       jsonb        DEFAULT '[]'::jsonb,
    emb           vector(768),
    tier          text         DEFAULT 'warm',     -- warm | hot
    access_count  integer      DEFAULT 0,
    recall_hits   integer      DEFAULT 0,
    satisfied     boolean,                          -- outcome signal (P2)
    pinned        boolean      DEFAULT false,       -- never evicted
    session_id    text,
    passport      jsonb,                            -- ed25519 attribution envelope
    last_access   timestamptz,
    ts            timestamptz  DEFAULT now(),
    -- hybrid-search full-text vector (language-neutral 'simple' config; the
    -- topical-anchor guard becomes a real tsvector fusion). NO stemming so it
    -- carries no language assumption (NO-HARDCODED-ENGLISH spirit).
    fts           tsvector GENERATED ALWAYS AS
                  (to_tsvector('simple', coalesce(q,'') || ' ' || coalesce(answer,''))) STORED
);
CREATE INDEX IF NOT EXISTS knowledge_emb_hnsw
    ON knowledge USING hnsw (emb vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS knowledge_fts_gin   ON knowledge USING gin (fts);
CREATE INDEX IF NOT EXISTS knowledge_ts        ON knowledge (ts DESC);
CREATE INDEX IF NOT EXISTS knowledge_tier      ON knowledge (tier);
CREATE INDEX IF NOT EXISTS knowledge_last_acc  ON knowledge (last_access);
-- #59 WS-5: owner_user -- the principal that produced/owns the row, so per-owner
-- RLS can scope recall in a multi-user deployment. Additive + nullable (NULL =
-- unowned/single-user); the drift-tolerant pg insert populates it when the chat
-- surface forwards a principal. Idempotent (matches the established pattern).
ALTER TABLE knowledge    ADD COLUMN IF NOT EXISTS owner_user text;
CREATE INDEX IF NOT EXISTS knowledge_owner ON knowledge (owner_user);
-- WS-A2 embedding-version hygiene: stamp the embedding identity on every vector
-- so a model/dimension change is detectable + the row can be re-embedded off the
-- hot path (mios_embed_backfill). Additive + nullable (NULL = pre-migration /
-- un-stamped -> a backfill treats it as stale). Idempotent.
ALTER TABLE knowledge    ADD COLUMN IF NOT EXISTS emb_model   text;
ALTER TABLE knowledge    ADD COLUMN IF NOT EXISTS emb_version text;

-- ── agent_memory: tool-driven self-editing facts (mios-remember) ─────────────
CREATE TABLE IF NOT EXISTS agent_memory (
    id        bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fact      text NOT NULL,
    scope     text DEFAULT 'global',               -- global | agent:<name> | conversation:<id>
    mem_key   text,                                -- optional update/forget key
    source    text DEFAULT 'agent',                -- agent | operator
    emb       vector(768),
    passport  jsonb,
    ts        timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS agent_memory_emb_hnsw
    ON agent_memory USING hnsw (emb vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS agent_memory_scope ON agent_memory (scope);
CREATE UNIQUE INDEX IF NOT EXISTS agent_memory_scope_key
    ON agent_memory (scope, mem_key) WHERE mem_key IS NOT NULL;
-- WS-5: owner_user for per-owner RLS (additive + nullable; NULL = shared/legacy).
ALTER TABLE agent_memory ADD COLUMN IF NOT EXISTS owner_user text;
CREATE INDEX IF NOT EXISTS agent_memory_owner ON agent_memory (owner_user);
-- WS-A2 embedding-version hygiene (see knowledge above): stamp the embedding
-- identity so a model/dim change can trigger an off-hot-path re-embed.
ALTER TABLE agent_memory ADD COLUMN IF NOT EXISTS emb_model   text;
ALTER TABLE agent_memory ADD COLUMN IF NOT EXISTS emb_version text;

-- ── event: append-only observability stream ──────────────────────────────────
CREATE TABLE IF NOT EXISTS event (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source      text,
    kind        text,
    severity    text,
    summary     text,
    payload     jsonb,
    session_id  text,
    passport    jsonb,
    -- WS-A8: per-request trace correlation. An event emitted during a traced
    -- chat_completions request carries the request trace_id + the active span_id
    -- so the observability stream stitches to GET /v1/trace. parent_span_id is
    -- reserved for a future per-span mirror -- currently only trace_id/span_id are
    -- written; finished spans live in the agent-pipe in-memory ring, not the DB.
    trace_id        text,
    span_id         text,
    parent_span_id  text,
    ts          timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS event_kind    ON event (kind);
CREATE INDEX IF NOT EXISTS event_session ON event (session_id);
CREATE INDEX IF NOT EXISTS event_ts      ON event (ts DESC);
-- WS-A8: forward-compat for an EXISTING event table (the CREATE above is a
-- no-op once the table exists, so add the trace columns idempotently).
ALTER TABLE event ADD COLUMN IF NOT EXISTS trace_id       text;
ALTER TABLE event ADD COLUMN IF NOT EXISTS span_id        text;
ALTER TABLE event ADD COLUMN IF NOT EXISTS parent_span_id text;
CREATE INDEX IF NOT EXISTS event_trace   ON event (trace_id);
-- SEC-03 (T-034): SHA-256 tamper-evident hash chain over the event stream. Each
-- chained row carries its position (chain_seq, monotonic in WRITE order -- the
-- pgvector mirror INSERT is fire-and-forget so the IDENTITY `id` can reorder, hence
-- a write-order seq), the predecessor's chain_hash (prev_hash), and
-- chain_hash = sha256(prev_hash || canonical-JSON of the immutable content fields).
-- A verifier walks chain_seq order, recomputes each link, and flags the first broken
-- one. Additive + idempotent so an existing event table migrates cleanly; columns are
-- NULL for pre-chain rows (the verifier walks only chained rows, WHERE chain_hash IS
-- NOT NULL, starting from genesis).
ALTER TABLE event ADD COLUMN IF NOT EXISTS chain_seq  bigint;
ALTER TABLE event ADD COLUMN IF NOT EXISTS prev_hash  text;
ALTER TABLE event ADD COLUMN IF NOT EXISTS chain_hash text;
CREATE INDEX IF NOT EXISTS event_chain_seq ON event (chain_seq);
-- DCI act analytics (T-028 / ORCH-01): the deliberation layer (mios_dci) logs each
-- typed epistemic act as an event row -- kind='dci_act' for a persona/critic act,
-- kind='dissent' for an unresolved Challenger objection. The act name lived ONLY in
-- the JSONB payload, so dissent + per-act analytics needed a JSONB extract on every
-- query. Promote it to a top-level column so "every Challenger dissent" / the
-- act-type distribution is a plain indexed scan (WHERE act_type = ...). Additive +
-- nullable (NULL = a non-DCI event); the drift-tolerant pg insert populates it once
-- the column exists, so a pre-migration row degrades to NULL rather than failing.
-- Partial index keeps it to the act-bearing rows, not the whole event stream.
ALTER TABLE event ADD COLUMN IF NOT EXISTS act_type text;
CREATE INDEX IF NOT EXISTS event_act_type ON event (act_type) WHERE act_type IS NOT NULL;

-- ── tool_call: every dispatched verb + result + taint ────────────────────────
CREATE TABLE IF NOT EXISTS tool_call (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id     text,
    tool           text,
    args           jsonb,
    result_preview text,                              -- code field (matches agent-pipe writes)
    success        boolean,                           -- read by the satisfaction check
    output         text,
    stderr         text,
    exit_code      integer,
    latency_ms     integer,
    tainted        boolean DEFAULT false,
    taint_reason   text,
    passport       jsonb,
    ts             timestamptz DEFAULT now()
);
-- Reconcile pre-existing tool_call tables to the code's actual fields (idempotent).
ALTER TABLE tool_call ADD COLUMN IF NOT EXISTS result_preview text;
ALTER TABLE tool_call ADD COLUMN IF NOT EXISTS success        boolean;
CREATE INDEX IF NOT EXISTS tool_call_session ON tool_call (session_id);
CREATE INDEX IF NOT EXISTS tool_call_tool    ON tool_call (tool);
CREATE INDEX IF NOT EXISTS tool_call_taint   ON tool_call (session_id) WHERE tainted;
CREATE INDEX IF NOT EXISTS tool_call_ts      ON tool_call (ts DESC);

-- ── session: agent-side sessions (link to OWUI chat ids) ─────────────────────
CREATE TABLE IF NOT EXISTS session (
    id            text PRIMARY KEY,                 -- caller-provided id
    kind          text,                             -- hermes | cron | cli | delegate | mcp
    owui_chat_id  text,
    meta          jsonb,
    ts            timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS session_chat ON session (owui_chat_id);

-- ── skills (mined/promoted) + per-run audit ──────────────────────────────────
CREATE TABLE IF NOT EXISTS skill (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name         text,
    description  text,                              -- code field (mios-skills writes)
    status       text,                              -- candidate | promoted | retired
    body         jsonb,
    confidence   double precision,
    support      integer,                           -- SPM frequency support
    source       text,                              -- mined | operator | import
    version      integer DEFAULT 1,
    created_at   timestamptz DEFAULT now(),
    updated_at   timestamptz,
    last_used_at timestamptz,
    ts           timestamptz DEFAULT now()
);
-- Reconcile pre-existing skill tables to mios-skills' actual fields (idempotent).
ALTER TABLE skill ADD COLUMN IF NOT EXISTS description  text;
ALTER TABLE skill ADD COLUMN IF NOT EXISTS support      integer;
ALTER TABLE skill ADD COLUMN IF NOT EXISTS created_at   timestamptz;
ALTER TABLE skill ADD COLUMN IF NOT EXISTS updated_at   timestamptz;
ALTER TABLE skill ADD COLUMN IF NOT EXISTS last_used_at timestamptz;
CREATE INDEX IF NOT EXISTS skill_name   ON skill (name);
CREATE INDEX IF NOT EXISTS skill_status ON skill (status);

CREATE TABLE IF NOT EXISTS skill_invocation (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    skill       text,
    success     boolean,
    session_id  text,
    ts          timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS skill_inv_skill ON skill_invocation (skill);

-- ── sys_env: singleton live environment cache ────────────────────────────────
CREATE TABLE IF NOT EXISTS sys_env (
    id    text PRIMARY KEY,                         -- 'current'
    data  jsonb,
    ts    timestamptz DEFAULT now()
);

-- ── WS-6 pending_action (HITL gate) ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pending_action (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tool              text,
    args              jsonb,
    action_hash       text,
    status            text DEFAULT 'pending',       -- pending | approved | denied
    session_id        text,
    approver          text,
    decided_at        timestamptz,
    passport          jsonb,
    approval_passport jsonb,
    ts                timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS pending_action_status ON pending_action (status);
CREATE INDEX IF NOT EXISTS pending_action_hash   ON pending_action (action_hash);

-- ── WS-6 run_template (replayable DAG plans) ─────────────────────────────────
CREATE TABLE IF NOT EXISTS run_template (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    class       text,                               -- structural plan-shape hash
    summary     text,
    node_count  integer,
    dag         jsonb,
    session_id  text,
    ts          timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS run_template_class ON run_template (class);
CREATE INDEX IF NOT EXISTS run_template_ts    ON run_template (ts DESC);

-- ── scratch: per-chat working memory (folds the in-process _SCRATCHPADS so it
--    survives agent-pipe restarts) ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scratch (
    id       bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chat_id  text,
    agent    text,
    lane     text,
    phase    text,
    note     text,
    ts       timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS scratch_chat ON scratch (chat_id, ts DESC);
-- Reconcile the SurrealDB-era scratch shape (source/topic/body) the mios-daemon
-- nudger mirrors verbatim into pg (_db_create('scratch', {source,topic,body}) ->
-- INSERT INTO scratch(source,topic,body)). Both writers coexist additively:
-- the pipe scratchpad uses chat_id/agent/lane/phase/note, the daemon uses
-- source/topic/body. Missing columns broke every nudge write (2026-06-18 audit).
ALTER TABLE scratch ADD COLUMN IF NOT EXISTS source text;
ALTER TABLE scratch ADD COLUMN IF NOT EXISTS topic  text;
ALTER TABLE scratch ADD COLUMN IF NOT EXISTS body   text;
-- WS-5: owner_user for per-owner RLS (additive + nullable; NULL = shared/legacy).
ALTER TABLE scratch ADD COLUMN IF NOT EXISTS owner_user text;
CREATE INDEX IF NOT EXISTS scratch_owner ON scratch (owner_user);

-- ── kanban: task queue (authoritative here; retires Hermes' kanban.db + the
--    SurrealDB shadow) ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS kanban (
    id       text PRIMARY KEY,
    title    text,
    status   text,                                  -- todo | doing | done | blocked
    detail   jsonb,
    ts       timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS kanban_status ON kanban (status);

-- ── PKG (personal knowledge graph): app-resolution. Flattens the SurrealDB
--    `alias ->resolves_to-> app_install` GRAPH into relational join tables so
--    kg_lookup becomes a JOIN. Populated by the PKG writer (WS-9c follow-up:
--    convert the writer + the agent-pipe kg_lookup reads to these tables). ─────
CREATE TABLE IF NOT EXISTS app_install (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    short_name   text,
    app_id       text,
    source       text,
    label        text,
    launch_hint  text,
    ts           timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS app_install_short ON app_install (short_name);

CREATE TABLE IF NOT EXISTS alias (
    id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    phrase text,
    ts     timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS alias_phrase ON alias (phrase);

-- Natural-key edge (phrase -> app_install.app_id): avoids RETURNING-id
-- round-trips through subprocess-psql; kg_lookup is a JOIN on app_id.
CREATE TABLE IF NOT EXISTS resolves_to (
    phrase  text,
    app_id  text,
    PRIMARY KEY (phrase, app_id)
);
CREATE INDEX IF NOT EXISTS resolves_to_phrase ON resolves_to (phrase);

-- ── directory_entry: mios-daemon's directory-map index (R15: was SurrealDB).
--    Read by mios-directory-lookup (the directory_lookup verb). The indexer
--    DELETE-by-root then batch-UPSERTs on path. Substring search via pg_trgm
--    GIN on lower(basename|path) (the reader uses strpos/ILIKE). mtime is the
--    file's mtime as an ISO string (display only, not queried). ───────────────
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE TABLE IF NOT EXISTS directory_entry (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    path        text UNIQUE NOT NULL,
    parent      text,
    basename    text,
    kind        text,                                 -- file | dir | symlink
    size        bigint,
    mtime       text,
    ext         text,
    summary     text,
    root_label  text,
    updated_at  timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_direntry_root ON directory_entry (root_label);
CREATE INDEX IF NOT EXISTS idx_direntry_ext  ON directory_entry (ext);
CREATE INDEX IF NOT EXISTS idx_direntry_kind ON directory_entry (kind);
CREATE INDEX IF NOT EXISTS idx_direntry_basename_trgm
    ON directory_entry USING gin (lower(basename) gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_direntry_path_trgm
    ON directory_entry USING gin (lower(path) gin_trgm_ops);

-- ── log_digest: mios-daemon's consolidated log analysis (R15: was SurrealDB).
--    Append-only summaries from the classify/rollup loops. ─────────────────────
CREATE TABLE IF NOT EXISTS log_digest (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    summary      text,
    tags         jsonb DEFAULT '[]'::jsonb,
    severity     text,
    event_count  integer,
    batch_count  integer,
    ts           timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS log_digest_ts ON log_digest (ts DESC);


-- ===== WS-9: tables ported from SurrealDB -> pgvector (2026-06-13) =====
-- person: one row per operator on this host (PKG; was SurrealDB `person`).
-- Read by `mios-kg who`, written by `mios-kg bootstrap`. Singleton in the
-- single-operator case; username is the natural upsert key. No embeddings.
CREATE TABLE IF NOT EXISTS person (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username    text NOT NULL,
    fullname    text,
    hostname    text,
    created_at  timestamptz DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS person_username ON person (username);

-- ── account: the tenant / owner identity model (multi-tenant FOUNDATION) ──────
--   The agent-plane shipped with NO account/role model: `owner_user` on the
--   RLS-scoped tables (knowledge/agent_memory/scratch) was a free-text label with
--   no backing entity. This table makes the owner a FIRST-CLASS row so accounts
--   (human users + system/service tenants) can be enumerated, displayed, and later
--   FK-referenced. LINKAGE CONVENTION: owner_user == account.name (a soft natural
--   key today). A hard foreign-key rewrite across the owner-scoped tables is a
--   deliberate follow-up -- this migration is ADDITIVE and never rewrites a row.
--   `kind` distinguishes a human user from a system/service tenant. An account IS
--   the owner, so it carries no owner_user of its own and is intentionally OUTSIDE
--   the RLS set below (federation-global, like peer_reputation). Idempotent.
CREATE TABLE IF NOT EXISTS account (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        text UNIQUE NOT NULL,                -- == owner_user (linkage convention)
    kind        text DEFAULT 'user',                 -- user | system | service
    display     text,
    created_at  timestamptz DEFAULT now(),
    meta        jsonb
);
CREATE INDEX IF NOT EXISTS account_kind ON account (kind);
-- Seed accounts WITHOUT a hardcoded name (NO-HARDCODE law forbids restating the
-- SSOT operator identity as a SQL literal). Derive them from the identities the
-- database ALREADY holds, so every existing owner gains a home:
--   (1) the PKG operator singleton (person, populated from the host [identity]); and
--   (2) every distinct owner_user already attached to an owned row.
-- Both are idempotent (ON CONFLICT (name) DO NOTHING) and harmless no-ops on a
-- fresh DB (person empty / no owned rows yet). There is no separate runtime-default
-- account key: the operator [identity] (via `person`) IS the default owner, and the
-- per-request owner is the principal the chat surface forwards.
INSERT INTO account (name, display)
SELECT username, fullname FROM person
WHERE username IS NOT NULL AND btrim(username) <> ''
ON CONFLICT (name) DO NOTHING;
INSERT INTO account (name)
SELECT DISTINCT owner_user FROM (
    SELECT owner_user FROM knowledge    WHERE owner_user IS NOT NULL
    UNION SELECT owner_user FROM agent_memory WHERE owner_user IS NOT NULL
    UNION SELECT owner_user FROM scratch      WHERE owner_user IS NOT NULL
) o
WHERE btrim(owner_user) <> ''
ON CONFLICT (name) DO NOTHING;

-- ── agent_keypair: Ed25519 agent-passport public-key registry (mios-passport;
--    R15: was SurrealDB). provision/rotate INSERTs a row + retires prior live
--    rows; verify reads the live PEM as a filesystem fallback. public_key_pem
--    is the raw multi-line PEM text. ed25519 keys carry no embedding (no emb). ─
CREATE TABLE IF NOT EXISTS agent_keypair (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    agent           text NOT NULL,
    kid             text,
    alg             text DEFAULT 'ed25519',
    public_key_pem  text,
    retired         boolean DEFAULT false,
    provisioned_at  timestamptz DEFAULT now(),
    rotated_at      timestamptz
);
CREATE INDEX IF NOT EXISTS agent_keypair_agent ON agent_keypair (agent);
CREATE INDEX IF NOT EXISTS agent_keypair_live  ON agent_keypair (agent) WHERE NOT retired;

-- ── mios_rag: document-RAG store (chunk text + 768-dim embedding) ─────────────
--    Was created LAZILY only by `mios-rag ingest`, so a fresh/cleared DB had no
--    table and every `mios-rag query` + agent-pipe recall (mios_pg.build_recall,
--    table=='mios_rag') hit `relation "mios_rag" does not exist` (2026-06-18
--    audit). Declared here so it always exists. 768-dim matches [pgvector].
--    embed_model = nomic-embed-text (same vector(768) as knowledge/agent_memory).
CREATE TABLE IF NOT EXISTS mios_rag (
    id       bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source   text,
    content  text,
    emb      vector(768),
    ts       timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS mios_rag_emb_hnsw
    ON mios_rag USING hnsw (emb vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- ── peer_reputation: WS-A18 persistent A2A peer reliability (mios_reputation) ──
-- The in-process PeerReputation flushes its raw counters here so reliability
-- SURVIVES an agent-pipe restart (load via restore() on startup, flush on a
-- timer). Federation-global (not owner-scoped) -> intentionally OUTSIDE the WS-5
-- RLS set below. Idempotent.
CREATE TABLE IF NOT EXISTS peer_reputation (
    peer_id    text PRIMARY KEY,
    ok         integer DEFAULT 0,
    bad        integer DEFAULT 0,
    streak_bad integer DEFAULT 0,
    ts         timestamptz DEFAULT now()
);

-- ── gateway_sessions: conversational history persistence for gateway-agent ──
CREATE TABLE IF NOT EXISTS gateway_sessions (
    session_id text PRIMARY KEY,
    messages   jsonb NOT NULL,
    updated_at timestamptz DEFAULT now()
);


-- ── WS-5: native Postgres Row-Level Security (defense-in-depth owner scoping) ──
-- RESEARCHED best practice (AWS / Supabase / Postgres RLS guides): the app sets a
-- PER-REQUEST session var `mios.owner_user` keyed on the VERIFIED principal
-- (WS-A10), and these policies enforce owner isolation IN THE DATABASE -- so even
-- if the app-side owner filter (mios_pg.build_recall) is bypassed or has a bug, a
-- caller sees only its OWN rows + shared (owner_user IS NULL) rows.
--
-- SAFE / behaviour-preserving: current_setting('mios.owner_user', true) returns
-- NULL when UNSET (single-user, or before the app wires the var), and the policy
-- is PERMISSIVE when unset -> ALL rows visible exactly as today. Isolation engages
-- only once the app SETs the var per request (`SET LOCAL mios.owner_user = ...`).
-- FORCE so the table-owner connection is subject to it too. Idempotent.
--
-- T-068 WIRING (who SETs the var): the agent-pipe pg path (mios_pg.recall/insert/
-- execute) and the confined mios-pg-query CLI emit
-- `set_config('mios.owner_user', <verified-owner>, true)` -- SET LOCAL semantics,
-- with the owner BOUND as a parameter (never spliced) -- gated by the SSOT flag
-- [pgvector].rls_enable (default false -> nothing emitted -> the permissive path
-- above). The var name set there MUST stay equal to the one read here. Owner-less
-- internal connections (daemon / seeding / system) emit nothing, so the GUC is
-- unset and these policies stay permissive for them (never locked out).
DO $mios_rls$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['knowledge', 'agent_memory', 'scratch'] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format('DROP POLICY IF EXISTS %I_owner_rls ON %I', t, t);
    -- USING clause: unset session var -> permissive (single-user / pre-wiring);
    -- shared (NULL-owner) rows always visible; else only the caller's own rows.
    EXECUTE format('CREATE POLICY %I_owner_rls ON %I USING (current_setting(''mios.owner_user'', true) IS NULL OR owner_user IS NULL OR owner_user = current_setting(''mios.owner_user'', true))', t, t);
  END LOOP;
END
$mios_rls$;


