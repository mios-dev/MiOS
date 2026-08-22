<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Sibling unit test for...

!/usr/bin/env python3
AI-hint: Sibling unit test for tools/check-schema-consumers.py. Builds throwaway git repos holding a synthetic schema-init.sql plus a mios.toml register, and asserts every direction: a table with a real code consumer passes, one with only a doc or .toml mention FAILS (a config file declares policy about a table, it does not read rows -- and counting .toml would let the register satisfy itself), a registered dead table passes, a registered table that GAINS a consumer fails so the register drains, and a register entry naming a dropped table fails. Run: python3 test_check-schema-consumers.py
AI-related: ./check-schema-consumers.py, usr/share/mios/mios.toml [schema]
AI-functions: mkrepo, run, t_generated_projection_is_not_a_consumer, main

<!-- mios-src:dad6d6af1953 from tools/test_check-schema-consumers.py:1-4 -->

