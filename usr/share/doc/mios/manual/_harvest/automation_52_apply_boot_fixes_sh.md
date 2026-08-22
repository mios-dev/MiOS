<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash MIOS_APPLY_CLASS=universal AI-hint...

!/usr/bin/env bash
MIOS_APPLY_CLASS=universal
AI-hint: Fixes boot-time failures by restoring execution bits on MiOS binaries, correcting USBGuard permissions, resolving systemd-resolved user mappings, and resolving ordering cycles for GPU passthrough.
AI-related: mios-role, mios-cdi-detect, mios-gpu-nvidia, mios-role.service, mios-cdi-detect.service, systemd-resolved.service, docker.socket, mios-gpu-nvidia.service, sockets.target, basic.target

<!-- mios-src:36e65d1db3c4 from automation/52-apply-boot-fixes.sh:1-4 -->

