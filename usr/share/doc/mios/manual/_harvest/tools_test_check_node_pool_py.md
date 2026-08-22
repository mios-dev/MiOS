<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Unit tests for...

!/usr/bin/env python3
AI-hint: Unit tests for tools/check-node-pool.py. One case per way the fan-out pool can lie -- an exact alias counted as two lanes, one endpoint declared as two lanes, a lane [dispatch] does not budget, a blade that does not exist, and an endpoint with a baked port no overlay can move -- plus the declared-inert placeholder (an empty endpoint is not a defect), the empty-pool case, and the real tree.
AI-related: tools/check-node-pool.py, usr/share/mios/mios.toml, tests/drift-gate-negatives.sh

<!-- mios-src:ccdca199ece7 from tools/test_check-node-pool.py:1-3 -->

