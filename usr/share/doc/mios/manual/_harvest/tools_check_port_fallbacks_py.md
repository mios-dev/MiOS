<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Drift gate for Law 7 at the...

!/usr/bin/env python3
AI-hint: Drift gate for Law 7 at the point it actually bites -- a MIOS_PORT_<KEY> paired with a literal that disagrees with [ports].<key>. Four shipped units pinned Environment=MIOS_PORT_*=<literal> unconditionally, three of them retired ports, so agent-pipe bound :8640 while MIOS_AI_ENDPOINT dialled :8700; the Windows LAN proxy's eleven fallbacks were an entire previous generation of numbers, and its env is never set on that side, so the fallback was always what ran. Comments, docs and generated projections are out of scope (check_doc_port_scheme owns those); the residue drains through the shrink-only [ports].stale_fallbacks register.
AI-related: usr/share/mios/mios.toml, tools/test_check-port-fallbacks.py, automation/98-drift-checks.sh, tests/drift-gate-negatives.sh
AI-functions: ports_map, scan_paths, findings, register, classify, main

<!-- mios-src:2cab21774760 from tools/check-port-fallbacks.py:1-4 -->

