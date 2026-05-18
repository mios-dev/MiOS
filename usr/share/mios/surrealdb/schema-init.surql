-- /usr/share/mios/surrealdb/schema-init.surql
--
-- Cross-agent state only. Operator directive 2026-05-18: "make
-- sure this is all Ollama (and other OpenSource Alternatives /
-- Local Endpoints / Self-Hosted Endpoints) and Open WebUI Native
-- DB(s) for knowledge/memory/context/scratch/skills/functions/
-- tools/etc-etc". So:
--
--   OWUI native (read via mios-db --owui '<sql>' over webui.db):
--     chat / message / memory / knowledge / file / tool /
--     function / model / user / group
--   Ollama native (read via mios-db --embed '<text>' or
--     curl http://localhost:11434/v1/embeddings):
--     models, embeddings, completions
--   SurrealDB (this schema -- ONLY for what's NOT in OWUI native):
--     agent / session / tool_call / event / kanban_shadow /
--     scratch / agent_metric
--
-- Idempotent (DEFINE TABLE / DEFINE FIELD safe to re-run).

USE NS mios;
USE DB mios;

-- agent: registry row per AI surface in the stack. NOT in OWUI
-- (OWUI tracks `model` rows, not the running agents downstream
-- of those models).
DEFINE TABLE agent SCHEMAFULL PERMISSIONS NONE;
DEFINE FIELD name             ON agent TYPE string;
DEFINE FIELD role             ON agent TYPE string;      -- router / refine / orchestrator / micro / critic / nudger / ...
DEFINE FIELD model            ON agent TYPE option<string>;
DEFINE FIELD endpoint         ON agent TYPE option<string>;
DEFINE FIELD device           ON agent TYPE option<string>;  -- cpu / nvidia / amd-igpu / intel-igpu
DEFINE FIELD pid              ON agent TYPE option<int>;
DEFINE FIELD started_at       ON agent TYPE option<datetime>;
DEFINE FIELD last_seen        ON agent TYPE option<datetime>;
DEFINE FIELD enabled          ON agent TYPE bool DEFAULT true;
DEFINE INDEX agent_name_unique ON agent COLUMNS name UNIQUE;

-- session: agent-side session (Hermes + cron + delegate + future
-- OpenCode). OWUI's chat table covers OWUI chats; this covers
-- everything else + carries the OWUI chat_id when applicable.
DEFINE TABLE session SCHEMAFULL PERMISSIONS NONE;
DEFINE FIELD started_at       ON session TYPE datetime;
DEFINE FIELD ended_at         ON session TYPE option<datetime>;
DEFINE FIELD platform         ON session TYPE string;    -- owui / cron / cli / mcp / delegate
DEFINE FIELD owui_chat_id     ON session TYPE option<string>;  -- joins to OWUI chat.id
DEFINE FIELD agent            ON session TYPE option<record<agent>>;
DEFINE FIELD model            ON session TYPE option<string>;
DEFINE FIELD turn_count       ON session TYPE int DEFAULT 0;
DEFINE FIELD outcome          ON session TYPE option<string>;
DEFINE INDEX session_owui     ON session COLUMNS owui_chat_id;

-- tool_call: every dispatched verb across every agent (including
-- the OWUI pipe's router-dispatch, hermes's tool_use, mios-daemon
-- background calls). Source of truth for "did the agent actually
-- run X?". OWUI's chat table has streamed-text status emits but
-- NOT structured tool_result; this fills that gap.
DEFINE TABLE tool_call SCHEMAFULL PERMISSIONS NONE;
DEFINE FIELD session          ON tool_call TYPE option<record<session>>;
DEFINE FIELD ts               ON tool_call TYPE datetime;
DEFINE FIELD tool             ON tool_call TYPE string;
DEFINE FIELD OVERWRITE args   ON tool_call TYPE object FLEXIBLE;
DEFINE FIELD result_preview   ON tool_call TYPE option<string>;
DEFINE FIELD success          ON tool_call TYPE option<bool>;
DEFINE FIELD latency_ms       ON tool_call TYPE option<int>;
DEFINE FIELD dispatched_by    ON tool_call TYPE option<record<agent>>;
-- Phase A.3 of the AgentOS roadmap: taint-aware memory tagging. The
-- `tainted` flag is set when the tool produced output from an
-- untrusted source (web fetch, non-allowlisted open_url destination,
-- RAG content sourced from a third-party doc, etc.) or when an
-- earlier tool_call in the same session was tainted (propagation).
-- The Semantic Firewall (Phase B.3 / partial A.3) refuses high-
-- privilege follow-up verbs when ANY upstream tool_call in the
-- session is tainted.
DEFINE FIELD tainted          ON tool_call TYPE bool DEFAULT false;
-- Optional reason string: "web_fetch", "external_open_url",
-- "inherited:n2", etc. Operator-readable when the firewall blocks.
DEFINE FIELD taint_reason     ON tool_call TYPE option<string>;
DEFINE INDEX tool_call_ts     ON tool_call COLUMNS ts;
DEFINE INDEX tool_call_tool   ON tool_call COLUMNS tool;
DEFINE INDEX tool_call_tainted ON tool_call COLUMNS tainted;

-- event: append-only observability stream (launch verifier hits,
-- refusal-pattern matches, classify summaries, critic verdicts,
-- nudger output, gpu CDI changes, ...). Per-thread streams
-- instead of polling state.json files.
DEFINE TABLE event SCHEMAFULL PERMISSIONS NONE;
DEFINE FIELD ts               ON event TYPE datetime;
DEFINE FIELD source           ON event TYPE string;          -- agent name
DEFINE FIELD kind             ON event TYPE string;          -- launch_failure / classify / nudge / refusal / critic_verdict / cdi_change / ...
DEFINE FIELD severity         ON event TYPE string DEFAULT 'info'; -- info / warn / high
DEFINE FIELD summary          ON event TYPE string;
DEFINE FIELD OVERWRITE payload ON event TYPE option<object> FLEXIBLE;
DEFINE INDEX event_ts         ON event COLUMNS ts;
DEFINE INDEX event_source     ON event COLUMNS source;
DEFINE INDEX event_kind       ON event COLUMNS kind;

-- kanban_shadow: live mirror of hermes-side kanban.db so the
-- OWUI pipe + mios-daemon + future OpenCode can read the task
-- queue without opening the SQLite file directly. Hermes
-- remains the authoritative WRITE side via kanban_* tools.
DEFINE TABLE kanban_shadow SCHEMAFULL PERMISSIONS NONE;
DEFINE FIELD hermes_task_id   ON kanban_shadow TYPE string;
DEFINE FIELD title            ON kanban_shadow TYPE string;
DEFINE FIELD status           ON kanban_shadow TYPE string;
DEFINE FIELD priority         ON kanban_shadow TYPE option<string>;
DEFINE FIELD tags             ON kanban_shadow TYPE array<string> DEFAULT [];
DEFINE FIELD synced_at        ON kanban_shadow TYPE datetime;
DEFINE INDEX kanban_shadow_task ON kanban_shadow COLUMNS hermes_task_id UNIQUE;

-- scratch: cross-agent transient note surface. Filesystem
-- /var/lib/mios/scratch/ remains the bulk store for .md files;
-- this DB layer is for typed scratch items agents share by topic.
DEFINE TABLE scratch SCHEMAFULL PERMISSIONS NONE;
DEFINE FIELD ts               ON scratch TYPE datetime;
DEFINE FIELD source           ON scratch TYPE string;
DEFINE FIELD topic            ON scratch TYPE string;
DEFINE FIELD body             ON scratch TYPE string;
DEFINE FIELD ttl_at           ON scratch TYPE option<datetime>;
DEFINE INDEX scratch_topic    ON scratch COLUMNS topic;

-- agent_metric: time-series for tool latencies, success rates,
-- per-agent throughput. mios-daemon writes; the nudger reads.
DEFINE TABLE agent_metric SCHEMAFULL PERMISSIONS NONE;
DEFINE FIELD ts               ON agent_metric TYPE datetime;
DEFINE FIELD agent            ON agent_metric TYPE record<agent>;
DEFINE FIELD metric           ON agent_metric TYPE string;   -- tool_latency_ms / dispatch_success_rate / turns_per_chat / ...
DEFINE FIELD value             ON agent_metric TYPE float;
DEFINE FIELD OVERWRITE labels ON agent_metric TYPE option<object> FLEXIBLE;
DEFINE INDEX agent_metric_ts  ON agent_metric COLUMNS ts;

-- DROPPED on operator directive (these belong in OWUI native):
--   memory      -> OWUI memory table (chat-bound recall)
--   doc         -> OWUI knowledge + file tables (RAG corpus)
--   knowledge   -> OWUI knowledge collection (mios-owui-apply-knowledge)
-- Use mios-db --owui '<sql>' to query those instead.
