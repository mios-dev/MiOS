<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Sibling unit test for...

!/usr/bin/env python3
AI-hint: Sibling unit test for tools/check-redact-coverage.py: builds throwaway schema/SSOT/pg.py trees and asserts the gate passes a fully classified schema and fails an unclassified table, a table classified in both lists, a classified table absent from the schema, a free-text agent table dropped from the redact side, and a pg.py that hardcodes its redaction tuple or ignores the SSOT.
AI-related: tools/check-redact-coverage.py, usr/share/mios/mios.toml, usr/share/mios/postgres/schema-init.sql

<!-- mios-src:a0236a774608 from tools/test_check-redact-coverage.py:1-3 -->

