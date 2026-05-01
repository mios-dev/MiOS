#!/usr/bin/env bash
# MiOS v0.2.0 — 01-repos: Fedora 44 overlay on ucore
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/packages.sh"
source "${SCRIPT_DIR}/lib/common.sh"

echo "[01-repos] Setting install_weak_deps=False globally..."
DNF_CONF="/usr/lib/dnf/dnf.conf"
[[ -f "$DNF_CONF" ]] || DNF_CONF="/etc/dnf/dnf.conf"
if [[ -f "$DNF_CONF" ]]; then
    sed -i '/^install_weak_deps=/d' "$DNF_CONF" 2>/dev/null || true
    echo "install_weak_deps=False" >> "$DNF_CONF"
fi

echo "[01-repos] Elevating base repos to priority 98..."
if [[ -d /etc/yum.repos.d ]]; then
    for repo in /etc/yum.repos.d/fedora*.repo /etc/yum.repos.d/ublue-os*.repo; do
        if [[ -f "$repo" ]] && ! grep -q '^priority=' "$repo"; then
            sed -i '/^\[.*\]/a priority=98' "$repo"
        fi
    done
fi

echo "[01-repos] Importing Fedora 44 GPG key..."
# The fedora-gpg-keys package ships the key at this path on Fedora-based systems.
# On ucore (which is CoreOS-based on Fedora), the key is present.
GPG_KEY_PATH="/etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-44-x86_64"
if [[ ! -f "$GPG_KEY_PATH" ]]; then
    # Fallback: import from the package if key file is missing
    $DNF_BIN "${DNF_SETOPT[@]}" install -y fedora-gpg-keys 2>/dev/null || true
fi

echo "[01-repos] Adding Fedora 44 repository..."
cat > /etc/yum.repos.d/fedora-44.repo <<EOREPO
[fedora-44]
name=Fedora 44 - \$basearch
metalink=https://mirrors.fedoraproject.org/metalink?repo=fedora-44&arch=\$basearch
enabled=1
repo_gpgcheck=1
type=rpm
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-44-x86_64
skip_if_unavailable=False
priority=95

[fedora-44-updates]
name=Fedora 44 Updates - \$basearch
metalink=https://mirrors.fedoraproject.org/metalink?repo=updates-released-f44&arch=\$basearch
enabled=1
repo_gpgcheck=1
type=rpm
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-44-x86_64
skip_if_unavailable=True
priority=95
EOREPO

echo "[01-repos] Phase 1: Pre-upgrading core systemd/filesystem..."
$DNF_BIN "${DNF_SETOPT[@]}" upgrade -y --allowerasing --best     dnf rpm fedora-release fedora-repos filesystem systemd glibc dbus-broker 2>&1 || {
    echo "[01-repos] NOTE: Pre-upgrade had warnings, continuing..."
}

echo "[01-repos] Phase 2: Distro-upgrade and userspace alignment..."
$DNF_BIN "${DNF_SETOPT[@]}" --setopt=excludepkgs="shim-*,kernel*" upgrade --refresh -y
$DNF_BIN "${DNF_SETOPT[@]}" --setopt=excludepkgs="shim-*,kernel*" distro-sync -y --best --allowerasing || {
    echo "FATAL: distro-sync failed"
    exit 1
}

echo "[01-repos] Verifying core package versions..."
rpm -q systemd glibc dbus-broker filesystem || true
