<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash MIOS_APPLY_CLASS=bake-only AI-hint...

!/usr/bin/env bash
MIOS_APPLY_CLASS=bake-only
AI-hint: Enables and symlinks core greenboot systemd services (health checks, grub2 status, and auto-reboot) and sets execution bits on greenboot check scripts to ensure system health monitoring is active.
AI-related: greenboot-healthcheck.service, greenboot-rpm-ostree-grub2-check-fallback.service, greenboot-grub2-set-counter.service, greenboot-grub2-set-success.service, greenboot-status.service, redboot-auto-reboot.service, multi-user.target

<!-- mios-src:24a3e8afd23f from automation/78-greenboot.sh:1-4 -->

