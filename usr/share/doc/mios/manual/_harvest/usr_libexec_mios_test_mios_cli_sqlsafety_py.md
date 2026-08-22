<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone adversarial...

!/usr/bin/env python3
AI-hint: Standalone adversarial integration test proving the python memory CLIs (mios-kg, mios-remember) route TAINTED input (argv phrase/scope/fact/filter) through bound PARAMS, never spliced into the SQL string (WS-A3 CLI SQL-safety). Pure stdlib, no DB/pytest: loads each hyphenated tool via SourceFileLoader, replaces its single DB choke (_pg_json) with a capture stub, fires a SQL-injection payload, and asserts the payload appears ONLY in params and never as SQL ("drop table" absent from every statement; $-placeholders present).
AI-related: ./mios-kg, ./mios-remember, ./mios-pg-query
AI-functions: _load, check, main

<!-- mios-src:26250a13cae4 from usr/libexec/mios/test_mios_cli_sqlsafety.py:1-4 -->

