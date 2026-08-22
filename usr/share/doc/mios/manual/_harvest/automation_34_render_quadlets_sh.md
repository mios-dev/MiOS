<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash MIOS_APPLY_CLASS=universal AI-hint...

!/usr/bin/env bash
MIOS_APPLY_CLASS=universal
AI-hint: Processes Quadlet container files by replacing ${MIOS_*} placeholders with values from mios.toml using envsubst, ensuring systemd-compatible container definitions are baked with correct host-specific UIDs, GIDs, and network configs.
AI-related: /usr/share/mios/kb
AI-functions: _render_with_envsubst, _render_with_bash

<!-- mios-src:69517bcb5de2 from automation/34-render-quadlets.sh:1-5 -->

