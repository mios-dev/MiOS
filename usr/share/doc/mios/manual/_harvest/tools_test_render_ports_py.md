<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Unit tests for...

!/usr/bin/env python3
AI-hint: Unit tests for render-ports.py -- proves the [ports.categories] allocator derives base + index*stride, honours pinned ports, and that the schema validator catches collisions, band overlap, orphans and double membership.
AI-related: tools/render-ports.py, usr/share/mios/mios.toml, automation/98-drift-checks.sh
AI-functions: load_module, TestDerivePorts, TestFindViolations, TestRenderTable, TestSweeperSkipsItsOwnEvidence

<!-- mios-src:2c2753632004 from tools/test_render_ports.py:1-4 -->

