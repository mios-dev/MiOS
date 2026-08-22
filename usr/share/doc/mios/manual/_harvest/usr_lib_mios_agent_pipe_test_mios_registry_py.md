<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_registry (WS-A17 versioned package + registry projection). Pure stdlib, no server.py/DB/pytest. Verifies build_package produces a versioned self-describing descriptor, build_registry is deterministic (sorted by kind,name), the index path layout (ai/v1/packages/<author>/<name>/<version>/mios-pkg.toml), the count, and verify_registry detects added/removed packages + a wrong schema for the drift gate.
AI-related: ./mios_registry.py, ./mios_manifest.py
AI-functions: check, main

<!-- mios-src:e25e237874ff from usr/lib/mios/agent-pipe/test_mios_registry.py:1-4 -->

