-- Migration 0003: Observability Event Streams and Tool Call Ledgers
-- Adds tamper-evident SHA-256 event chaining and tool execution telemetry tables.

CREATE TABLE IF NOT EXISTS event (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source        text,
    kind          text,
    severity      text,
    summary       text,
    payload       jsonb,
    session_id    text,
    passport      jsonb,
    trace_id      text,
    span_id       text,
    parent_span_id text,
    chain_seq     bigint,
    prev_hash     text,
    chain_hash    text,
    act_type      text,
    emb           vector(768),
    emb_model     varchar(128),
    emb_version   varchar(64),
    ts            timestamptz DEFAULT now(),
    origin_node   text NOT NULL DEFAULT 'local',
    logical_ts    bigint NOT NULL DEFAULT 0,
    logical_clock bigint NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS event_kind    ON event (kind);
CREATE INDEX IF NOT EXISTS event_session ON event (session_id);
CREATE INDEX IF NOT EXISTS event_ts      ON event (ts DESC);
CREATE INDEX IF NOT EXISTS event_chain   ON event (chain_seq);

CREATE TABLE IF NOT EXISTS tool_call (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id     text,
    tool           text,
    args           jsonb,
    result_preview text,
    success        boolean,
    output         text,
    stderr         text,
    exit_code      integer,
    latency_ms     integer,
    tainted        boolean DEFAULT false,
    taint_reason   text,
    passport       jsonb,
    ts             timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS tool_call_session ON tool_call (session_id);
CREATE INDEX IF NOT EXISTS tool_call_tool    ON tool_call (tool);
CREATE INDEX IF NOT EXISTS tool_call_ts      ON tool_call (ts DESC);
