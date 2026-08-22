<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash MIOS_APPLY_CLASS=universal AI-hint...

!/usr/bin/env bash
MIOS_APPLY_CLASS=universal
AI-hint: Installs systemd drop-in files for NVIDIA services to implement ExecCondition guards, ensuring units skip execution if the kernel's nvidia module is not yet registered by akmods/depmod.
AI-related: mios-akmod-guard, systemd.service

<!-- mios-src:47bd81d6c74a from automation/22-akmod-guards.sh:1-4 -->

