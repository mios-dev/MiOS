<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-A3 pure, DB-free logic for the knowledge-table eviction sweep -- now PARAMETERIZED POSTGRES (the cutover). Builds parameterized pg SQL (named %(min_access)s/%(ttl_days)s/%(limit)s/%(ids)s placeholders -- NO string interpolation, injection-safe) + parses pg dict-rows, replacing the old legacy query fragments that NO-OP'd under db_backend=postgres (the legacy DELETE/count never reached pg). server.py owns the mios_pg I/O + the loop; this module owns the deterministic SQL-building + parsing + the blast-radius arithmetic so it unit-tests in isolation.
AI-related: ./mios_pg.py, ./server.py, /usr/share/mios/postgres/schema-init.sql, ./test_mios_evict.py
AI-functions: evict_where, order_by, count_sql, select_ids_sql, delete_ids_sql, evict_params, parse_count, parse_ids, plan_sweep

<!-- mios-src:3a88dc42092a from usr/lib/mios/agent-pipe/mios_pipe/scheduler/evict.py:1-3 -->

