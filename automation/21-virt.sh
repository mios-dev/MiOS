#!/bin/bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Installs and configures virtualization (KVM/QEMU/Libvirt), container runtimes (Podman/Buildah), Cockpit management, and CrowdSec security tools to establish the core virtualization and containerization stack.
# AI-related: mios-kver, mios-virtio
# 'MiOS' - 12-virt: Virtualization, containers, orchestration, gaming
#
# CHANGELOG v1.3:
#   - Looking Glass B7: MOVED to 69-bake-lookingglass-client.sh (refactored out)
#   - KVMFR module: MOVED to 68-bake-kvmfr.sh (refactored out)
#   - K3s: MOVED to 36-ceph-k3s.sh (no longer duplicated here)
#   - CrowdSec: Updated sovereign mode config (RE2 regex engine default)
#   - Added Podman quadlet example for CrowdSec
#   - VirtIO-Win ISO: Updated URL pattern
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/packages.sh"
source "${SCRIPT_DIR}/lib/common.sh"

KVER=$(cat /tmp/mios-kver 2>/dev/null || find /usr/lib/modules/ -mindepth 1 -maxdepth 1 -printf "%f\n" | sort -V | tail -1)

# ── KVM / QEMU / Libvirt ────────────────────────────────────────────────────
mios_log "install KVM/QEMU/Libvirt"
install_packages "virt"

# ── Containers (Podman, Buildah, Skopeo, bootc, self-build tools) ────────────
mios_log "install container runtime + self-build tools"
install_packages "containers"

# Extra self-build tools (image-rechunking, etc. - may be repo-dependent)
install_packages "self-build"

# ── Build toolchain (image-build only; stripped by 91-strip-build-toolchain.sh) ──
# Required by 37-k3s-selinux.sh (SELinux module compile) and
# 69-bake-lookingglass-client.sh (Looking Glass B7 from source). Removed
# before image commit so the runtime carries no compilers.
mios_log "install build toolchain (image-build only; will be stripped)"
install_packages "build-toolchain"

# ── Cockpit Web Management ──────────────────────────────────────────────────
mios_log "install Cockpit"
install_packages_strict "cockpit"

# ── Boot & Update Management (bootupd, ukify, etc.) ─────────────────────────
mios_log "install boot + update management tools"
install_packages "boot"

# ── CrowdSec IPS (sovereign/offline mode) ───────────────────────────────────
mios_log "install CrowdSec"
install_packages "security"

# Sovereign mode: disable Central API, use local-only decisions
if [ -d /etc/crowdsec ]; then
    # acquis.d/journalctl.yaml managed via  overlay

    # Disable online API for sovereign operation
    if [ -f /etc/crowdsec/config.yaml ]; then
        sed -i 's/^online_client:/# online_client:/' /etc/crowdsec/config.yaml 2>/dev/null || true
    fi
    mios_ok "CrowdSec sovereign/offline mode configured"
fi

# ── mDNS / DNS-SD LAN discovery (avahi) ──────────────────────────────────────
# Backs FED-G5 A2A peer discovery + announce (mios-a2a-mdns / mios-a2a-discover).
# avahi-daemon is enabled by preset but stays INERT for A2A until the operator opts
# in via mios.toml [a2a].mdns_discovery / mdns_advertise. Best-effort install that
# honors the [packages.network-discovery].enable toggle.
mios_log "install mDNS/DNS-SD discovery (avahi)"
install_packages "network-discovery"

# ── Windows Interop & Remote Desktop ────────────────────────────────────────
mios_log "install Windows interop tools"
install_packages "wintools"

# ── Gaming (Steam, Wine, Gamescope) ─────────────────────────────────────────
# NOTE: steam-devices and udev-joystick-blacklist-rm (terra weak dep of
# gamescope-session-steam) both ship the same udev rules file. Exclude it.
mios_log "install gaming packages"
GAMING_PKGS=$(get_packages "gaming")
if [[ -n "$GAMING_PKGS" ]]; then
    ($DNF_BIN "${DNF_SETOPT[@]}" install -y "${DNF_OPTS[@]}" --skip-unavailable --exclude=udev-joystick-blacklist-rm $GAMING_PKGS) || {
        mios_warn "some gaming packages failed to install"
    }
fi

# ── Guest Agents ────────────────────────────────────────────────────────────
mios_log "install guest agents"
install_packages "guests"

# ── Storage ─────────────────────────────────────────────────────────────────
mios_log "install storage packages"
install_packages "storage"

# ── High Availability (Pacemaker/Corosync) ──────────────────────────────────
mios_log "install HA stack"
install_packages "ha"

# ── CLI Utilities ───────────────────────────────────────────────────────────
mios_log "install CLI utilities"
install_packages "utils"

# ── Android (Waydroid) ──────────────────────────────────────────────────────
mios_log "install Waydroid"
install_packages "android"

# ── VirtIO-Win ISO (latest stable) ─────────────────────────────────────────
mios_log "download VirtIO-Win ISO"
VIRTIO_URL="https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso"
mkdir -p ${MIOS_SHARE_DIR}/virtio
scurl -sL "$VIRTIO_URL" -o ${MIOS_SHARE_DIR}/virtio/virtio-win.iso 2>/dev/null || {
    mios_warn "VirtIO-Win ISO download failed -- download manually later"
}

# Symlink the immutable ISO into /var/lib/libvirt/images via tmpfiles.d so it survives upgrades
# Managed via usr/lib/tmpfiles.d/mios-virtio.conf

mios_ok "virtualization stack ready (LG: refactored to 53-lg; K3s: refactored to 13-ceph-k3s)"
