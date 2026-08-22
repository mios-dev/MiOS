<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: DURA-02 persist-redaction...

!/usr/bin/env python3
AI-hint: DURA-02 persist-redaction coverage gate: asserts every table in postgres/schema-init.sql is classified in exactly one of [security.redact].tables or .exempt, that the agent-plane content tables are on the redact side, and that memory/pg.py reads the SSOT list instead of hardcoding table names.
AI-related: usr/share/mios/mios.toml, usr/share/mios/postgres/schema-init.sql, usr/lib/mios/agent-pipe/mios_pipe/memory/pg.py, usr/lib/mios/agent-pipe/mios_pipe/redact.py

<!-- mios-src:5fdb177d3ec4 from tools/check-redact-coverage.py:1-3 -->

