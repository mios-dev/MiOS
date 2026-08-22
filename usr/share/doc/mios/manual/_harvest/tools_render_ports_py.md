<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Renders the flat [ports]...

!/usr/bin/env python3
AI-hint: Renders the flat [ports] projection from the [ports.categories] numbering SSOT -- every port is derived as base + index*stride, so an operator retargets a whole category by changing one base. --check is the drift gate.
AI-related: usr/share/mios/mios.toml, automation/98-drift-checks.sh, usr/lib/mios/mios_toml.py, automation/lib/globals.ps1
AI-functions: derive_ports, category_band, find_violations, render_table, main

<!-- mios-src:3e1f89d12072 from tools/render-ports.py:1-4 -->

