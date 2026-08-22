<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash MIOS_APPLY_CLASS=universal AI-hint...

!/usr/bin/env bash
MIOS_APPLY_CLASS=universal
AI-hint: Enables core MiOS systemd units (mios-role.service and mios-podman-gc.timer) by creating symlinks in multi-user.target.wants to ensure the Unified Role Engine and podman garbage collection are active.
AI-related: /usr/libexec/mios/role-apply, mios-role, mios-podman-gc, mios-role.service, mios-podman-gc.timer, multi-user.target

<!-- mios-src:8b902d31f9af from automation/47-init-service.sh:1-4 -->

