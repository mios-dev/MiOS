<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash MIOS_APPLY_CLASS=universal AI-hint...

!/usr/bin/env bash
MIOS_APPLY_CLASS=universal
AI-hint: Configures and enables systemd units for NVIDIA CDI (Container Device Interface) auto-refresh, removes legacy oci-nvidia-hook.json to prevent conflicts, and ensures the GPU runtime environment is correctly wired for container orchestration.
AI-related: mios-gpu, mios-nvidia-cdi, nvidia-cdi-refresh.service, nvidia-persistenced.service, multi-user.target

<!-- mios-src:7082ca180466 from automation/26-nvidia-cdi-refresh.sh:1-4 -->

