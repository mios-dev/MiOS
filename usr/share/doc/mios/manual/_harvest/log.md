<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Unified log aggregation...

!/usr/bin/env python3
AI-hint: Unified log aggregation pipeline streaming systemd journald events to pgvector system_logs table with nomic-embed-text vector indexing.
AI-related: usr/lib/systemd/system/mios-log-streamer.service, tests/test-log-streamer.py, usr/share/mios/postgres/schema-init.sql
AI-functions: parse_journal_record, generate_embeddings_batch, format_sql_insert, stream_journal_records, process_log_batch, main

<!-- mios-src:b23a95bc8279 from usr/libexec/mios/log/mios-log-streamer:1-4 -->
