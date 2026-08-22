<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_evict (WS-A3 parameterized-pg eviction). Pure stdlib, no server.py/DB/pytest. Verifies the WHERE fragment is PARAMETERIZED pg (named %(...)s placeholders, COALESCE not ??, no legacy time::now()/record-ids), TTL added only with_ttl, the count/select/delete SQL shapes (count(*) AS c, LIMIT %(limit)s, DELETE ... id = ANY(%(ids)s)), pg dict-row parsing (count + bigint ids), and plan_sweep arithmetic.
AI-related: ./mios_evict.py
AI-functions: check, main

<!-- mios-src:a41137dbbb7a from usr/lib/mios/agent-pipe/test_mios_evict.py:1-4 -->

