<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Standalone unit test for mios_pg pure helpers (WS-9...

Standalone unit test for mios_pg pure helpers (WS-9 Postgres client).

Pure stdlib + the sibling module only -- no psycopg, no live Postgres (the I/O is
verified by the operator on MiOS-DEV). Run:  python test_mios_pg.py

<!-- mios-src:d94fe0196aea from usr/lib/mios/agent-pipe/test_mios_pg.py:3-7 -->
