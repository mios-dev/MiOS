<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-A2 embedding-version hygiene -- the pure decision core for an off-hot-path re-embed (backfill) job. When the embedding model or dimensionality changes, every stored vector tagged with the OLD emb_version is stale (cosine recall silently degrades, mixing incompatible vector spaces). This module decides WHICH rows need re-embedding (emb present but emb_version != the current identity) and plans bounded batches; it also builds the parameterized candidate-SELECT + version-stamp UPDATE SQL. server.py / a CLI owns the actual DB I/O + the embed call; this module is pure (no DB, no network) so it unit-tests in isolation.
AI-related: ./mios_pg.py, ./server.py, /usr/share/mios/postgres/schema-init.sql, /usr/share/mios/mios.toml, ./test_mios_embed_backfill.py
AI-functions: needs_reembed, select_candidates_sql, stamp_version_sql, plan_batches, summarize

<!-- mios-src:f46b4186eb10 from usr/lib/mios/agent-pipe/mios_pipe/memory/embed_backfill.py:1-3 -->

