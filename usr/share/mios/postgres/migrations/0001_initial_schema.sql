-- Migration 0001: Initial Core Schema and Vector Extension
-- Sets up pgvector extension and core agent knowledge base tables.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS knowledge (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    q             text NOT NULL,
    answer        text NOT NULL,
    sources       jsonb        DEFAULT '[]'::jsonb,
    emb           vector(768),
    tier          text         DEFAULT 'warm',
    access_count  integer      DEFAULT 0,
    recall_hits   integer      DEFAULT 0,
    satisfied     boolean,
    pinned        boolean      DEFAULT false,
    session_id    text,
    passport      jsonb,
    last_access   timestamptz,
    ts            timestamptz  DEFAULT now(),
    origin_node   text         NOT NULL DEFAULT 'local',
    logical_ts    bigint       NOT NULL DEFAULT 0,
    logical_clock bigint       NOT NULL DEFAULT 0,
    fts           tsvector GENERATED ALWAYS AS
                  (to_tsvector('simple', coalesce(q,'') || ' ' || coalesce(answer,''))) STORED
);

CREATE INDEX IF NOT EXISTS knowledge_emb_hnsw
    ON knowledge USING hnsw (emb vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS knowledge_fts_gin   ON knowledge USING gin (fts);
CREATE INDEX IF NOT EXISTS knowledge_ts        ON knowledge (ts DESC);
