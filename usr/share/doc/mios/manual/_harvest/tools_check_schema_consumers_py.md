<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Drift gate for dead schema....

!/usr/bin/env python3
AI-hint: Drift gate for dead schema. Every table in usr/share/mios/postgres/schema-init.sql must have at least one non-doc consumer in the tree -- something that SELECTs, INSERTs or otherwise names it in code -- or be listed in the shrink-only [schema].unconsumed register with a reason. A table nobody reads or writes is either planned-but-unbuilt (which should be recorded, not invisible) or a trap: mios_identity.account_preferences shadows the live account_preference by one letter, so a writer aimed at the wrong one would look correct and lose every row. Registered entries may only be REMOVED, so the register drains as tables get built or dropped.
AI-related: usr/share/mios/postgres/schema-init.sql, usr/share/mios/mios.toml [schema], tools/test_check-schema-consumers.py
AI-functions: declared_tables, has_consumer, main

<!-- mios-src:588e1e2a0b1e from tools/check-schema-consumers.py:1-4 -->

