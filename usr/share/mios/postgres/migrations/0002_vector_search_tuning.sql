-- Migration 0002: Vector Search Index Tuning and RAG Document Store
-- Adds agent_memory, mios_rag, and person_pref with tuned HNSW vector indexing.

CREATE TABLE IF NOT EXISTS agent_memory (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fact          text NOT NULL,
    scope         text DEFAULT 'global',
    mem_key       text,
    source        text DEFAULT 'agent',
    emb           vector(768),
    passport      jsonb,
    importance    numeric DEFAULT 1.0,
    ts            timestamptz DEFAULT now(),
    origin_node   text NOT NULL DEFAULT 'local',
    logical_ts    bigint NOT NULL DEFAULT 0,
    logical_clock bigint NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS agent_memory_emb_hnsw
    ON agent_memory USING hnsw (emb vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS agent_memory_scope ON agent_memory (scope);

CREATE TABLE IF NOT EXISTS mios_rag (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source        text,
    content       text,
    emb           vector(768),
    ts            timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS mios_rag_emb_hnsw
    ON mios_rag USING hnsw (emb vector_cosine_ops) WITH (m = 16, ef_construction = 64);
