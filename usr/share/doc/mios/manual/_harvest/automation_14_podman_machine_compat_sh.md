<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash MIOS_APPLY_CLASS=dev-only AI-hint...

!/usr/bin/env bash
MIOS_APPLY_CLASS=dev-only
AI-hint: Configures Podman machine backend compatibility by ensuring the 'core' user exists via sysusers and symlinking essential systemd units like podman.socket and qemu-guest-agent.service for container runtime support.
AI-related: podman.socket, qemu-guest-agent.service, sshd.service, cloud-init.service, cloud-final.service, multi-user.target

<!-- mios-src:ccf74554c3ad from automation/14-podman-machine-compat.sh:1-4 -->

