<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash MIOS_APPLY_CLASS=dev-only AI-hint...

!/usr/bin/env bash
MIOS_APPLY_CLASS=dev-only
AI-hint: Configures Hyper-V GPU-PV (dxgkrnl) support by creating mount points, ld.so.conf entries, and a systemd service to detect and bridge host-side GPU drivers for Mesa D3D12 and NVIDIA CUDA.
AI-related: mios-gpu-pv, mios-gpu-pv-detect, mios-gpu-pv-detect.service, display-manager.service, local-fs.target, multi-user.target
AI-functions: log

<!-- mios-src:62c44b589edb from automation/24-gpu-pv-shim.sh:1-5 -->

