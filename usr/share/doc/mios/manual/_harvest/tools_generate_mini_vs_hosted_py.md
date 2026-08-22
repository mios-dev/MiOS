<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: GENERATES...

!/usr/bin/env python3
AI-hint: GENERATES usr/share/doc/mios/reference/mini-vs-hosted.md -- the systematic, surface-by-surface comparison of a MiOS-Mini seat against a fully hosted, feature-complete MiOS blade. Every number is DERIVED from mios.toml ([blade.archetypes], [blade.requires], [blade].seat_side, [greenboot], [urls]), because a hand-written comparison is exactly the document that goes stale the moment an archetype gains a capability. --check is the drift gate.
AI-related: usr/share/mios/mios.toml, usr/share/doc/mios/adr/0016-blade-node-topology.md, automation/98-drift-checks.sh, tools/test_generate-mini-vs-hosted.py
AI-functions: load, archetype_rows, seat_units, gated_off_on_seat, greenboot_rows, overlay_keys, baked_payloads, render, main

<!-- mios-src:ec8790a47788 from tools/generate-mini-vs-hosted.py:1-4 -->

