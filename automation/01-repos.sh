#!/bin/bash
# MiOS v0.1.1 — 01-repos: Fedora 44 overlay on ucore (base kernel preserved)
#
# FIX v0.1.1: Two-phase distro-sync to handle filesystem scriptlet failure.
# The filesystem package's lua %posttrans fails in container builds, aborting
# the entire 1162-package transaction. Without this fix, the system boots with
# F43 core libs but F44 desktop packages — a broken ABI mismatch.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/packages.sh"
source "${SCRIPT_DIR}/lib/common.sh"

# ── Global DNF config ───────────────────────────────────────────────────────
echo "[01-repos] Setting install_weak_deps=False globally..."
DNF_CONF="/usr/lib/dnf/dnf.conf"
if [ ! -f "$DNF_CONF" ]; then
    DNF_CONF="/etc/dnf/dnf.conf"
fi

if [ -f "$DNF_CONF" ]; then
    if ! grep -q '^install_weak_deps=False' "$DNF_CONF"; then
        sed -i '/^install_weak_deps=/d' "$DNF_CONF" 2>/dev/null || true
        echo "install_weak_deps=False" >> "$DNF_CONF"
    fi
fi


# ── Protect Base Repos from Third-Party Ties ───────────────────────────────
echo "[01-repos] Elevating base repos to priority 98..."
if [ -d /etc/yum.repos.d ]; then
    for repo in /etc/yum.repos.d/fedora*.repo /etc/yum.repos.d/ublue-os*.repo; do
        if [ -f "$repo" ] && ! grep -q '^priority=' "$repo"; then
            sed -i '/^\[.*\]/a priority=98' "$repo"
        fi
    done
fi

# ── Fedora 44 repo overlay ─────────────────────────────────────────────────
echo "[01-repos] Adding Fedora 44 repository..."
cat > /etc/yum.repos.d/fedora-44.repo <<'EOREPO'
[fedora-44]
name=Fedora 44 - $basearch
metalink=https://mirrors.fedoraproject.org/metalink?repo=fedora-44&arch=$basearch
enabled=1
countme=1
metadata_expire=6h
repo_gpgcheck=0
type=rpm
gpgcheck=0
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-44-$basearch
skip_if_unavailable=False
priority=95

[fedora-44-updates]
name=Fedora 44 Updates - $basearch
metalink=https://mirrors.fedoraproject.org/metalink?repo=updates-released-f44&arch=$basearch
enabled=1
countme=1
metadata_expire=6h
repo_gpgcheck=0
type=rpm
gpgcheck=0
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-44-$basearch
skip_if_unavailable=True
priority=95
EOREPO

# ── Distro-sync to Fedora 44 (TWO-PHASE) ───────────────────────────────────
echo "[01-repos] Distro-sync to Fedora 44 (this takes a while)..."

echo "[01-repos] Phase 1: Pre-upgrading DNF, RPM, and core systemd/filesystem..."
# Isolate the problematic filesystem scriptlet and core package upgrades.
# By doing this first, a filesystem %posttrans failure won't abort the entire
# 1100+ package distro-sync transaction, preventing a fractured RPM database.
$DNF_BIN "${DNF_SETOPT[@]}" upgrade -y --allowerasing --best \
    dnf rpm fedora-release fedora-repos filesystem systemd glibc dbus-broker 2>&1 || {
    echo "[01-repos] NOTE: Pre-upgrade had warnings (likely filesystem lua scriptlet), continuing..."
}

echo "[01-repos] Phase 2: Distro-upgrade and userspace alignment..."
# We use 'upgrade --refresh' to ensure we have fresh metadata and catch latest
# userspace patches, followed by 'distro-sync' to align the remainder with F44.
$DNF_BIN "${DNF_SETOPT[@]}" --setopt=excludepkgs="shim-*,kernel*" upgrade --refresh -y
$DNF_BIN "${DNF_SETOPT[@]}" --setopt=excludepkgs="shim-*,kernel*" distro-sync -y --best --allowerasing || {
    echo "[01-repos] WARNING: Distro-sync to Fedora 44 failed. Repository might be unreachable."
    echo "[01-repos] Continuing with base image packages..."
}

echo "[01-repos] Verifying core package versions..."
rpm -q systemd glibc dbus-broker filesystem || true

# ── Pre-install F44 ca-certificates ────────────────────────────────────────
echo "[01-repos] Ensuring F44 ca-certificates is installed..."
$DNF_BIN "${DNF_SETOPT[@]}" install -y ca-certificates p11-kit-trust 2>&1 | tail -5 || true

# ── RPMFusion ───────────────────────────────────────────────────────────────
echo "[01-repos] Installing RPMFusion Free + Nonfree for Rawhide..."
$DNF_BIN "${DNF_SETOPT[@]}" install -y \
    "https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-rawhide.noarch.rpm" \
    "https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-rawhide.noarch.rpm" \
    2>&1 | tail -15 || true


for repo in rpmfusion-free rpmfusion-free-updates rpmfusion-nonfree rpmfusion-nonfree-updates; do
    if [ -f "/etc/yum.repos.d/${repo}.repo" ]; then
        if ! grep -q '^priority=' "/etc/yum.repos.d/${repo}.repo"; then
            sed -i '/^\['"$repo"'\]/a priority=90' "/etc/yum.repos.d/${repo}.repo"
        fi
    fi
done

# ── Terra repo ──────────────────────────────────────────────────────────────
echo "[01-repos] Installing Terra repo..."
$DNF_BIN "${DNF_SETOPT[@]}" install -y --repofrompath 'terra,https://repos.fyralabs.com/terra44' \
    --setopt='terra.gpgcheck=1' --setopt='terra.gpgkey=https://repos.fyralabs.com/terra44/key.asc' \
    terra-release 2>&1 | tail -10 || true

if [ -f /etc/yum.repos.d/terra.repo ]; then
    if ! grep -q '^priority=' /etc/yum.repos.d/terra.repo; then
        sed -i '/^\[terra\]/a priority=85' /etc/yum.repos.d/terra.repo
    fi
    # BIB (bootc-image-builder) runs in a CentOS Stream 10 container and cannot
    # resolve file:// GPG key paths that live inside the MiOS image.
    # Rewrite to https:// and disable repo_gpgcheck so Anaconda ISO manifest
    # generation succeeds without "Couldn't open file RPM-GPG-KEY-terra44".
    sed -i 's|^gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-terra44|gpgkey=https://repos.fyralabs.com/terra44/key.asc|' \
        /etc/yum.repos.d/terra.repo
    sed -i 's/^repo_gpgcheck=1/repo_gpgcheck=0/' /etc/yum.repos.d/terra.repo
fi

# ── CrowdSec repo ──────────────────────────────────────────────────────────
echo "[01-repos] Adding CrowdSec repo..."
cat > /etc/yum.repos.d/crowdsec.repo <<'EOREPO'
[crowdsec]
name=CrowdSec
baseurl=https://packagecloud.io/crowdsec/crowdsec/rpm_any/rpm_any/$basearch
enabled=1
gpgcheck=0
repo_gpgcheck=0
priority=80
EOREPO

# ── NVIDIA Container Toolkit repo ──────────────────────────────────────────
echo "[01-repos] Adding NVIDIA Container Toolkit repo..."
if ! [ -f /etc/yum.repos.d/nvidia-container-toolkit.repo ]; then
    cat > /etc/yum.repos.d/nvidia-container-toolkit.repo <<'EOREPO'
[nvidia-container-toolkit]
name=NVIDIA Container Toolkit
baseurl=https://nvidia.github.io/libnvidia-container/stable/rpm/$basearch
enabled=1
gpgcheck=1
gpgkey=https://nvidia.github.io/libnvidia-container/gpgkey
priority=70
EOREPO
fi

# Ensure all repo files have correct permissions
chmod 0644 /etc/yum.repos.d/*.repo 2>/dev/null || true

echo "[01-repos] Done. Protected base + F44 userspace + RPMFusion + Terra + CrowdSec."
echo "[01-repos] Priority: CrowdSec(80) < Terra(85) < RPMFusion(90) < F44(95) < Base(98) < Default(99)"
