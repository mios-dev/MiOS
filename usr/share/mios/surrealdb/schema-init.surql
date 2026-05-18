-- /usr/share/mios/surrealdb/schema-init.surql
--
-- Unified AI-surface schemas. Operator directive 2026-05-18:
-- "unify all AI Surfaces!!" -- every MiOS agent (OWUI pipe,
-- hermes, mios-daemon, future OpenCode) reads/writes the same
-- tables. The DB is the SHARED GROUND TRUTH; agents don't
-- fabricate state from context window.
--
-- Idempotent (DEFINE ... if not exists). Re-running is safe.

USE NS mios;
USE DB mios;

-- agent: registry row per AI surface in the stack.
DEFINE TABLE agent SCHEMAFULL PERMISSIONS NONE;
DEFINE FIELD name             ON agent TYPE string;
DEFINE FIELD role             ON agent TYPE string;          -- router / refine / orchestrator / micro / critic / nudger / ...
DEFINE FIELD model            ON agent TYPE option<string>;
DEFINE FIELD endpoint         ON agent TYPE option<string>;
DEFINE FIELD device           ON agent TYPE option<string>;  -- cpu / nvidia / amd-igpu / intel-igpu
DEFINE FIELD pid              ON agent TYPE option<int>;
DEFINE FIELD started_at       ON agent TYPE option<datetime>;
DEFINE FIELD last_seen        ON agent TYPE option<datetime>;
DEFINE FIELD enabled          ON agent TYPE bool DEFAULT true;
DEFINE INDEX agent_name_unique ON agent COLUMNS name UNIQUE;

-- session: one row per chat / cron run / delegate spawn.
DEFINE TABLE session SCHEMAFULL PERMISSIONS NONE;
DEFINE FIELD started_at       ON session TYPE datetime;
DEFINE FIELD ended_at         ON session TYPE option<datetime>;
DEFINE FIELD platform         ON session TYPE string;        -- owui / cron / cli / mcp
DEFINE FIELD chat_id          ON session TYPE option<string>;
DEFINE FIELD model            ON session TYPE option<string>;
DEFINE FIELD operator         ON session TYPE option<string>;
DEFINE FIELD turn_count       ON session TYPE int DEFAULT 0;
DEFINE FIELD outcome          ON session TYPE option<string>;-- success / partial / error / abandoned
DEFINE INDEX session_chat     ON session COLUMNS chat_id;

-- tool_call: one row per dispatched verb. Source of truth for
-- "did the agent actually run X?" -- replaces text-parsing the
-- raw hermes stream.
DEFINE TABLE tool_call SCHEMAFULL PERMISSIONS NONE;
DEFINE FIELD session          ON tool_call TYPE record<session>;
DEFINE FIELD ts               ON tool_call TYPE datetime;
DEFINE FIELD tool             ON tool_call TYPE string;
DEFINE FIELD args             ON tool_call TYPE object;
DEFINE FIELD result_preview   ON tool_call TYPE option<string>;
DEFINE FIELD success          ON tool_call TYPE option<bool>;
DEFINE FIELD latency_ms       ON tool_call TYPE option<int>;
DEFINE FIELD dispatched_by    ON tool_call TYPE option<record<agent>>;
DEFINE INDEX tool_call_ts     ON tool_call COLUMNS ts;
DEFINE INDEX tool_call_tool   ON tool_call COLUMNS tool;

-- memory: durable cross-session memory. Operator + agents both
-- write here; agents query before fabricating.
DEFINE TABLE memory SCHEMAFULL PERMISSIONS NONE;
DEFINE FIELD ts               ON memory TYPE datetime;
DEFINE FIELD kind             ON memory TYPE string;         -- user / feedback / project / reference
DEFINE FIELD subject          ON memory TYPE string;         -- short topic key
DEFINE FIELD body             ON memory TYPE string;
DEFINE FIELD source           ON memory TYPE option<record<agent>>;
DEFINE FIELD tags             ON memory TYPE array<string> DEFAULT [];
-- Optional vector embedding for semantic recall. Dim = nomic-embed
-- size 768; agents that don't embed can leave it null.
DEFINE FIELD embedding        ON memory TYPE option<array<float>>;
DEFINE INDEX memory_subject   ON memory COLUMNS subject;
DEFINE INDEX memory_kind      ON memory COLUMNS kind;

-- event: append-only observability stream (launch verifier hits,
-- refusal pattern matches, classify summaries, critic verdicts,
-- ...). Per-thread streams instead of polling state.json.
DEFINE TABLE event SCHEMAFULL PERMISSIONS NONE;
DEFINE FIELD ts               ON event TYPE datetime;
DEFINE FIELD source           ON event TYPE string;          -- agent name
DEFINE FIELD kind             ON event TYPE string;          -- launch_failure / classify / nudge / refusal / critic_verdict / ...
DEFINE FIELD severity         ON event TYPE string DEFAULT 'info'; -- info / warn / high
DEFINE FIELD summary          ON event TYPE string;
DEFINE FIELD payload          ON event TYPE option<object>;
DEFINE INDEX event_ts         ON event COLUMNS ts;
DEFINE INDEX event_source     ON event COLUMNS source;
DEFINE INDEX event_kind       ON event COLUMNS kind;

-- kanban_shadow: live mirror of hermes-side kanban.db (operator
-- + non-hermes agents can read without opening the SQLite file).
-- mios-daemon task_collector_loop populates on its 5-min cadence.
DEFINE TABLE kanban_shadow SCHEMAFULL PERMISSIONS NONE;
DEFINE FIELD hermes_task_id   ON kanban_shadow TYPE string;
DEFINE FIELD title             ON kanban_shadow TYPE string;
DEFINE FIELD status            ON kanban_shadow TYPE string;
DEFINE FIELD priority          ON kanban_shadow TYPE option<string>;
DEFINE FIELD tags              ON kanban_shadow TYPE array<string> DEFAULT [];
DEFINE FIELD synced_at         ON kanban_shadow TYPE datetime;
DEFINE INDEX kanban_shadow_task ON kanban_shadow COLUMNS hermes_task_id UNIQUE;

-- scratch: shared-mutable note surface (operator + agents both
-- write). Free-form; agents can leave one-line context notes for
-- their successors.
DEFINE TABLE scratch SCHEMAFULL PERMISSIONS NONE;
DEFINE FIELD ts               ON scratch TYPE datetime;
DEFINE FIELD source           ON scratch TYPE string;
DEFINE FIELD topic            ON scratch TYPE string;
DEFINE FIELD body             ON scratch TYPE string;
DEFINE FIELD ttl_at           ON scratch TYPE option<datetime>;  -- agent-defined expiry
DEFINE INDEX scratch_topic    ON scratch COLUMNS topic;

-- doc: index entry per .md doc surface (mios-docs-index output
-- shadow). Lets agents semantic-search docs without re-walking
-- the filesystem on every turn.
DEFINE TABLE doc SCHEMAFULL PERMISSIONS NONE;
DEFINE FIELD path             ON doc TYPE string;
DEFINE FIELD description      ON doc TYPE option<string>;
DEFINE FIELD size             ON doc TYPE int;
DEFINE FIELD updated_at       ON doc TYPE datetime;
DEFINE FIELD embedding        ON doc TYPE option<array<float>>;
DEFINE INDEX doc_path_unique  ON doc COLUMNS path UNIQUE;
