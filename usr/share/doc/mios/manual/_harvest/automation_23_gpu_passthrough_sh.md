<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash MIOS_APPLY_CLASS=universal AI-hint...

!/usr/bin/env bash
MIOS_APPLY_CLASS=universal
AI-hint: Configures GPU passthrough by symlinking systemd unit files for NVIDIA/AMD/Intel drivers into the multi-user.target.wants directory and enabling the container_use_devices SELinux boolean.
AI-related: mios-gpu-status, mios-gpu-nvidia, mios-gpu-amd, mios-gpu-intel, multi-user.target, mios-gpu-status.service, mios-gpu-nvidia.service, mios-gpu-amd.service, mios-gpu-intel.service

<!-- mios-src:44c7907f57aa from automation/23-gpu-passthrough.sh:1-4 -->

