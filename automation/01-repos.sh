#!/usr/bin/env bash
# 'MiOS' v0.2.0 — 01-repos: Fedora 44 overlay on ucore
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
# On ucore (which is CoreOS-based on Fedora), the key is usually present already.
GPG_KEY_PATH="/etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-44-x86_64"
if [[ ! -f "$GPG_KEY_PATH" ]]; then
    # Fallback: import from the package. Failure here is fatal — the F44 repo
    # below uses repo_gpgcheck=1 and silently dropping the key would surface
    # later as opaque "package not signed" errors on every install. (Audit
    # 2026-05-01 finding: do not swallow this with 2>/dev/null.)
    $DNF_BIN "${DNF_SETOPT[@]}" install -y fedora-gpg-keys
fi

echo "[01-repos] Adding Fedora 44 repository..."
# F44 is in development at build time. Dev-tree repodata is NOT GPG-signed —
# the .asc detached signature returns 404 from every Fedora mirror. Setting
# repo_gpgcheck=1 turns that 404 into a fatal metadata-load error that
# cascades into every subsequent dnf transaction.
#   - repo_gpgcheck=0 : accept unsigned dev metadata (audit 2026-05-01).
#   - gpgcheck=1      : individual *packages* still verified by RPM signature.
#   - skip_if_unavailable=True : when F44 mirrors are intermittently down,
#     fall back to F43 (base image) instead of breaking the whole build.
cat > /etc/yum.repos.d/fedora-44.repo <<EOREPO
[fedora-44]
name=Fedora 44 - \$basearch
metalink=https://mirrors.fedoraproject.org/metalink?repo=fedora-44&arch=\$basearch
enabled=1
repo_gpgcheck=0
type=rpm
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-44-x86_64
skip_if_unavailable=True
priority=95
timeout=10
minrate=1k
max_parallel_downloads=10
ip_resolve=4

[fedora-44-updates]
name=Fedora 44 Updates - \$basearch
metalink=https://mirrors.fedoraproject.org/metalink?repo=updates-released-f44&arch=\$basearch
enabled=1
repo_gpgcheck=0
type=rpm
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-44-x86_64
skip_if_unavailable=True
priority=95
timeout=10
minrate=1k
max_parallel_downloads=10
ip_resolve=4
EOREPO

echo "[01-repos] Phase 1: Pre-upgrading core systemd/filesystem..."
# --best dropped per audit 2026-05-01: on the F44↔ucore boundary --best can
# refuse the transaction over a single unresolvable kernel-adjacent dep, which
# is then logged-and-continued, masking real breakage. --allowerasing is enough.
# --skip-unavailable: packages from external repos (crowdsec, tailscale) have
# no repo configured at this stage; skip them cleanly instead of aborting.
$DNF_BIN "${DNF_SETOPT[@]}" upgrade -y --allowerasing --skip-unavailable \
    dnf rpm fedora-release fedora-repos filesystem systemd glibc dbus-broker 2>&1 || {
    echo "[01-repos] NOTE: Pre-upgrade had warnings, continuing..."
}

# Packages whose repos are not yet configured (crowdsec) or whose ucore version
# is intentionally newer than F44 (tailscale 1.96→1.94 downgrade).  Excluded
# here; 05-enable-external-repos.sh and later scripts own their lifecycle.
_THIRD_PARTY_EXCLUDES="shim-*,kernel*,tailscale*,crowdsec*,crowdsec-firewall-bouncer*"

echo "[01-repos] Phase 2: Distro-upgrade and userspace alignment..."
$DNF_BIN "${DNF_SETOPT[@]}" \
    --setopt=excludepkgs="${_THIRD_PARTY_EXCLUDES}" \
    upgrade --refresh -y --skip-unavailable || {
    echo "[01-repos] WARN: upgrade --refresh had conflicts (ucore vs F44 pkgs) — continuing"
}
# distro-sync is retried once: F44 mirrors are occasionally in-progress sync state,
# causing RPM signature mismatches that resolve on a second attempt with fresh metadata.
_dsync_ok=0
for _attempt in 1 2; do
    if $DNF_BIN "${DNF_SETOPT[@]}" \
            --setopt=excludepkgs="${_THIRD_PARTY_EXCLUDES}" \
            distro-sync -y --allowerasing --skip-unavailable; then
        _dsync_ok=1; break
    fi
    echo "[01-repos] WARN: distro-sync attempt $_attempt failed — cleaning cache and retrying..."
    $DNF_BIN clean metadata 2>/dev/null || true
done
if [[ $_dsync_ok -eq 0 ]]; then
    echo "[01-repos] WARN: distro-sync failed after 2 attempts — ucore packages may differ from Fedora 44."
    echo "[01-repos] Continuing; individual package installs will use available repos."
fi

# Clean metadata so subsequent scripts start from a consistent cache state
$DNF_BIN clean metadata 2>/dev/null || true

echo "[01-repos] Verifying core package versions..."
rpm -q systemd glibc dbus-broker filesystem || true
