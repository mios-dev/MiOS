<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_evict -- pure helpers for the knowledge-table eviction...

mios_evict -- pure helpers for the knowledge-table eviction sweep (WS-A3).

DB-free + stdlib-only so the SQL-building, response-parsing, and planning logic
unit-tests in isolation (sibling-module pattern). server.py owns the actual
Postgres I/O (mios_pg.execute), the config knobs, and the background loop.

WS-A3 cutover: this emits PARAMETERIZED Postgres (named placeholders bound by
mios_pg) -- the previous legacy query fragments (`??`, record-id
`DELETE a, b;`) silently no-op'd once db_backend='postgres' (the legacy :8000
backend is retired), so eviction never ran. The knowledge table is append-only; eviction
removes only STALE, never-recalled, neutral-outcome rows and NEVER a
hot/satisfied/pinned/recently-accessed one.

<!-- mios-src:8727fd3fb90c from usr/lib/mios/agent-pipe/mios_pipe/scheduler/evict.py:3-15 -->
