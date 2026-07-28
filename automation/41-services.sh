#!/bin/bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Configures systemd services, enforces cgroup v2 compliance, fixes unit file permissions, and applies environment-specific gating for bare-metal, VM, and WSL2 deployments.
# AI-related: mios-role, bootloader-update.service, podman-auto-update.timer, ceph-bootstrap.service, cockpit.socket, mios-role.service, var-home.mount, var-lib-containers.mount
# 'MiOS' - 20-services: Enable systemd services + bare-metal/VM gating
#
# CHANGELOG v1.3:
#   - systemd 260: cgroup v1 support REMOVED -- all services must use cgroup v2
#   - systemd 260: SysV service scripts no longer supported
#   - Fixed: PCP stack restored -- pmcd, pmlogger, pmproxy now all enabled
#     via 90-mios.preset (pcp-zeroconf is in [packages.cockpit] and supplies
#     the default pmlogger archive-collection config). Required for Cockpit
#     Metrics history to populate.
#   - Added: bootloader-update.service for bootc systems
#   - Added: podman-auto-update.timer for quadlet auto-updates
#   - Improved: Bare-metal vs VM vs WSL2 service gating
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

mios_log "service configuration ${MIOS_VERSION:-}"

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

# ─── Cockpit config: project from mios.toml [cockpit] SSOT ─────────
# /etc/cockpit/cockpit.conf is rendered by the SINGLE authoritative generator
# tools/generate-cockpit-conf.py from mios.toml [cockpit] -- it is NOT hand-
# maintained and NOT the divergent usr/lib/cockpit/cockpit.conf fallback that
# 99-postcheck reads only when /etc has no copy. Run the generator in write
# mode against the build source tree, then install the rendered file into the
# image /etc so the deployed system's Cockpit config derives entirely from the
# operator-defined SSOT (drift-gated by 98-drift-checks.sh check 95).
_mios_src_root="$(cd "$(dirname "$0")/.." && pwd)"
_cockpit_gen="${_mios_src_root}/tools/generate-cockpit-conf.py"
if [[ -f "$_cockpit_gen" ]] && command -v python3 >/dev/null 2>&1; then
    python3 "$_cockpit_gen"
    install -D -m 0644 "${_mios_src_root}/etc/cockpit/cockpit.conf" /etc/cockpit/cockpit.conf
    echo "[20-services] projected /etc/cockpit/cockpit.conf from mios.toml [cockpit] SSOT"
else
    echo "[20-services] WARN: generate-cockpit-conf.py or python3 unavailable -- /etc/cockpit/cockpit.conf not projected"
fi

# ─── Service Configuration Note ──────────────────────────────────────────────
# CORE and OPTIONAL services are now primarily managed via:
# usr/lib/systemd/system-preset/90-mios.preset
# Role-specific services are managed by mios-role.service at runtime.

# ─── WSL2 & Container Service Gating ─────────────────────────────────────────
# These services skip OCI/WSL2 via drop-ins in system_files overlay.
echo "[20-services] WSL2/OCI service-skip drop-ins delivered via system_files overlay (not by this step)"

# ─── nvidia-powerd: skip in ALL VMs (no physical NVIDIA GPU) ─────────────────
# Drop-in handled via overlay.

# ─── TuneD: set throughput-performance profile ──────────────────────────────
tuned-adm profile throughput-performance 2>/dev/null || true

echo "[20-services] chmod 644 applied to unit files; TuneD profile set to throughput-performance"
