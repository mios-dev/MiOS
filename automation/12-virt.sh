#!/bin/bash
# 'MiOS' v0.2.0 -- 12-virt: Virtualization, containers, orchestration, gaming
#
# CHANGELOG v1.3:
#   - Looking Glass B7: MOVED to 53-bake-lookingglass-client.sh (refactored out)
#   - KVMFR module: MOVED to 52-bake-kvmfr.sh (refactored out)
#   - K3s: MOVED to 13-ceph-k3s.sh (no longer duplicated here)
#   - CrowdSec: Updated sovereign mode config (RE2 regex engine default)
#   - Added Podman quadlet example for CrowdSec
#   - VirtIO-Win ISO: Updated URL pattern
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/packages.sh"
source "${SCRIPT_DIR}/lib/common.sh"

KVER=$(cat /tmp/mios-kver 2>/dev/null || find /usr/lib/modules/ -mindepth 1 -maxdepth 1 -printf "%f\n" | sort -V | tail -1)

# ── KVM / QEMU / Libvirt ────────────────────────────────────────────────────
echo "[12-virt] Installing KVM/QEMU/Libvirt..."
install_packages "virt"

# ── Containers (Podman, Buildah, Skopeo, bootc, self-build tools) ────────────
echo "[12-virt] Installing container runtime and self-building tools..."
install_packages "containers"

# Extra self-build tools (image-rechunking, etc. - may be repo-dependent)
install_packages "self-build"

# ── Cockpit Web Management ──────────────────────────────────────────────────
echo "[12-virt] Installing Cockpit..."
install_packages_strict "cockpit"

# ── Boot & Update Management (bootupd, ukify, etc.) ─────────────────────────
echo "[12-virt] Installing boot and update management tools..."
install_packages "boot"

# ── CrowdSec IPS (sovereign/offline mode) ───────────────────────────────────
echo "[12-virt] Installing CrowdSec..."
install_packages "security"

# Sovereign mode: disable Central API, use local-only decisions
if [ -d /etc/crowdsec ]; then
    # acquis.d/journalctl.yaml managed via  overlay

    # Disable online API for sovereign operation
    if [ -f /etc/crowdsec/config.yaml ]; then
        sed -i 's/^online_client:/# online_client:/' /etc/crowdsec/config.yaml 2>/dev/null || true
    fi
    echo "[12-virt] CrowdSec configured for sovereign/offline mode"
fi

# ── Windows Interop & Remote Desktop ────────────────────────────────────────
echo "[12-virt] Installing Windows interop tools..."
install_packages "wintools"

# ── Gaming (Steam, Wine, Gamescope) ─────────────────────────────────────────
# NOTE: steam-devices and udev-joystick-blacklist-rm (terra weak dep of
# gamescope-session-steam) both ship the same udev rules file. Exclude it.
echo "[12-virt] Installing gaming packages..."
GAMING_PKGS=$(get_packages "gaming")
if [[ -n "$GAMING_PKGS" ]]; then
    ($DNF_BIN "${DNF_SETOPT[@]}" install -y "${DNF_OPTS[@]}" --skip-unavailable --exclude=udev-joystick-blacklist-rm $GAMING_PKGS) || {
        echo "[12-virt] WARNING: Some gaming packages failed to install" >&2
    }
fi

# ── Guest Agents ────────────────────────────────────────────────────────────
echo "[12-virt] Installing guest agents..."
install_packages "guests"

# ── Storage ─────────────────────────────────────────────────────────────────
echo "[12-virt] Installing storage packages..."
install_packages "storage"

# ── High Availability (Pacemaker/Corosync) ──────────────────────────────────
echo "[12-virt] Installing HA stack..."
install_packages "ha"

# ── CLI Utilities ───────────────────────────────────────────────────────────
echo "[12-virt] Installing CLI utilities..."
install_packages "utils"

# ── Android (Waydroid) ──────────────────────────────────────────────────────
echo "[12-virt] Installing Waydroid..."
install_packages "android"

# ── VirtIO-Win ISO (latest stable) ─────────────────────────────────────────
echo "[12-virt] Downloading VirtIO-Win ISO..."
VIRTIO_URL="https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso"
mkdir -p ${MIOS_SHARE_DIR}/virtio
scurl -sL "$VIRTIO_URL" -o ${MIOS_SHARE_DIR}/virtio/virtio-win.iso 2>/dev/null || {
    echo "[12-virt] WARNING: VirtIO-Win ISO download failed -- download manually later"
}

# Symlink the immutable ISO into /var/lib/libvirt/images via tmpfiles.d so it survives upgrades
# Managed via usr/lib/tmpfiles.d/mios-virtio.conf

echo "[12-virt] Virtualization stack complete. (LG: refactored to 53-lg; K3s: refactored to 13-ceph-k3s)"
