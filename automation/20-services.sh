#!/bin/bash
# MiOS v0.2.0 — 20-services: Enable systemd services + bare-metal/VM gating
#
# CHANGELOG v1.3:
#   - systemd 260: cgroup v1 support REMOVED — all services must use cgroup v2
#   - systemd 260: SysV service scripts no longer supported
#   - Fixed: pmcd/pmlogger services removed (only pmproxy is installed)
#   - Added: bootloader-update.service for bootc systems
#   - Added: podman-auto-update.timer for quadlet auto-updates
#   - Improved: Bare-metal vs VM vs WSL2 service gating
set -euo pipefail

echo "  MiOS v0.2.0 — Service Configuration"

# ─── Fix systemd unit file permissions ────────────────────────────────────────
# Container builds sometimes leave bad perms from COPY operations.
for unit_file in \
    /usr/lib/systemd/system/var-home.mount \
    /usr/lib/systemd/system/var-lib-containers.mount \
    /usr/lib/systemd/system/ceph-bootstrap.service \
    /usr/lib/systemd/system/cockpit.socket.d/listen.conf \
; do
    [ -f "$unit_file" ] && chmod 644 "$unit_file"
done
echo "[20-services] Fixed systemd unit file permissions"

# ─── Service Configuration Note ──────────────────────────────────────────────
# CORE and OPTIONAL services are now primarily managed via:
# usr/lib/systemd/system-preset/90-mios.preset
# Role-specific services are managed by mios-role.service at runtime.

# ─── WSL2 & Container Service Gating ─────────────────────────────────────────
# These services skip OCI/WSL2 via drop-ins in system_files overlay.
echo "[20-services] WSL2/Container skip drop-ins active via overlay"

# ─── nvidia-powerd: skip in ALL VMs (no physical NVIDIA GPU) ─────────────────
# Drop-in handled via overlay.

# ─── TuneD: set throughput-performance profile ──────────────────────────────
tuned-adm profile throughput-performance 2>/dev/null || true

echo "[20-services] Service configuration baseline complete. v1.4"
