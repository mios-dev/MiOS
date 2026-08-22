<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/bin/bash MIOS_APPLY_CLASS=universal AI-hint: Configures...

!/bin/bash
MIOS_APPLY_CLASS=universal
AI-hint: Configures systemd services, enforces cgroup v2 compliance, fixes unit file permissions, and applies environment-specific gating for bare-metal, VM, and WSL2 deployments.
AI-related: mios-role, bootloader-update.service, podman-auto-update.timer, mios-ceph-bootstrap.service, cockpit.socket, mios-role.service, var-home.mount, var-lib-containers.mount

<!-- mios-src:1886e470b5a4 from automation/41-services.sh:1-4 -->

