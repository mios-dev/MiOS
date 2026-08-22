<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash MIOS_APPLY_CLASS=bake-only AI-hint...

!/usr/bin/env bash
MIOS_APPLY_CLASS=bake-only
AI-hint: Finalizes the build by applying systemd presets, setting the default boot target, scrubbing credential leaks, purging DNF caches, and generating the MiOS version metadata files in /usr/lib/mios/.
AI-related: /usr/lib/mios/., /etc/mios/role.conf, /etc/mios/version, mios-version, graphical.target, multi-user.target

<!-- mios-src:df75ba429858 from automation/88-finalize.sh:1-4 -->

