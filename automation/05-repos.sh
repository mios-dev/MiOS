#!/usr/bin/env bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Configures Fedora 44 repository metadata, sets `install_weak_deps=False` in DNF, and enforces priority 98 for base repos to ensure stable package resolution on ucore.
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/packages.sh"
source "${SCRIPT_DIR}/lib/common.sh"

mios_log "Set install_weak_deps=False globally"
DNF_CONF="/usr/lib/dnf/dnf.conf"
[[ -f "$DNF_CONF" ]] || DNF_CONF="/etc/dnf/dnf.conf"
if [[ -f "$DNF_CONF" ]]; then
    sed -i '/^install_weak_deps=/d' "$DNF_CONF" 2>/dev/null || true
    echo "Install_weak_deps=False" >> "$DNF_CONF"
fi

mios_log "Elevate base repos to priority 98"
if [[ -d /etc/yum.repos.d ]]; then
    for repo in /etc/yum.repos.d/fedora*.repo /etc/yum.repos.d/ublue-os*.repo; do
        if [[ -f "$repo" ]] && ! grep -q '^priority=' "$repo"; then
            sed -i '/^\[.*\]/a priority=98' "$repo"
        fi
    done
fi

_fver="${FEDORA_VERSION:-44}"

mios_log "Import Fedora ${_fver} GPG key"
GPG_KEY_PATH="/etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-${_fver}-x86_64"
if [[ ! -f "$GPG_KEY_PATH" ]]; then
    $DNF_BIN "${DNF_SETOPT[@]}" install -y --skip-unavailable fedora-gpg-keys \
        || warn "[01-repos] fedora-gpg-keys import failed; continuing"
fi

mios_log "Add Fedora ${_fver} repository"
if command -v miosd >/dev/null 2>&1; then
    _online_flag=""
    if [[ "${MIOS_ONLINE_BUILD:-0}" == "1" ]]; then
        _online_flag="--online"
    fi
    miosd render-repos --fedora-version "$_fver" $_online_flag
    mios_ok "Rendered fedora-${_fver}.repo via miosd"
elif [ -d "/usr/share/mios/vendored/rpms" ] && [[ "${MIOS_ONLINE_BUILD:-0}" != "1" ]]; then
    mios_log "Using local vendored RPM mirror for Fedora ${_fver}"
    cat > /etc/yum.repos.d/fedora-${_fver}.repo <<EOREPO
[fedora-${_fver}]
name=Fedora ${_fver} - \$basearch
baseurl=file:///usr/share/mios/vendored/rpms/fedora-${_fver}/\$basearch
enabled=1
repo_gpgcheck=0
type=rpm
gpgcheck=0
skip_if_unavailable=True
priority=95

[fedora-${_fver}-updates]
name=Fedora ${_fver} Updates - \$basearch
baseurl=file:///usr/share/mios/vendored/rpms/updates-released-f${_fver}/\$basearch
enabled=1
repo_gpgcheck=0
type=rpm
gpgcheck=0
skip_if_unavailable=True
priority=95
EOREPO
else
    cat > /etc/yum.repos.d/fedora-${_fver}.repo <<EOREPO
[fedora-${_fver}]
name=Fedora ${_fver} - \$basearch
metalink=https://mirrors.fedoraproject.org/metalink?repo=fedora-${_fver}&arch=\$basearch
enabled=1
repo_gpgcheck=0
type=rpm
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-${_fver}-x86_64
skip_if_unavailable=True
priority=95
timeout=10
minrate=1k
max_parallel_downloads=10
ip_resolve=4

[fedora-${_fver}-updates]
name=Fedora ${_fver} Updates - \$basearch
metalink=https://mirrors.fedoraproject.org/metalink?repo=updates-released-f${_fver}&arch=\$basearch
enabled=1
repo_gpgcheck=0
type=rpm
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-${_fver}-x86_64
skip_if_unavailable=True
priority=95
timeout=10
minrate=1k
max_parallel_downloads=10
ip_resolve=4
EOREPO
fi

mios_step "Phase 1: pre-upgrade core systemd/filesystem"
$DNF_BIN "${DNF_SETOPT[@]}" upgrade -y --allowerasing --skip-unavailable \
    dnf rpm fedora-release fedora-repos filesystem systemd glibc dbus-broker 2>&1 || {
    mios_warn "Dnf upgrade of systemd/glibc/dbus-broker/filesystem returned non-zero; continuing"
}

_THIRD_PARTY_EXCLUDES="shim-*,kernel*,tailscale*,crowdsec*,crowdsec-firewall-bouncer*"

mios_step "Phase 2: distro-upgrade and userspace alignment"
$DNF_BIN "${DNF_SETOPT[@]}" \
    --setopt=excludepkgs="${_THIRD_PARTY_EXCLUDES}" \
    upgrade --refresh -y --skip-unavailable || {
    mios_warn "Upgrade"
}
_dsync_ok=0
for _attempt in 1 2; do
    if $DNF_BIN "${DNF_SETOPT[@]}" \
            --setopt=excludepkgs="${_THIRD_PARTY_EXCLUDES}" \
            distro-sync -y --allowerasing --skip-unavailable; then
        _dsync_ok=1; break
    fi
    mios_warn "Distro-sync attempt $_attempt failed"
    $DNF_BIN clean metadata 2>/dev/null || true
done
if [[ $_dsync_ok -eq 0 ]]; then
    mios_warn "Distro-sync failed after 2 attempts"
    mios_log "Continuing; individual package installs will use available repos"
fi

$DNF_BIN clean metadata 2>/dev/null || true

mios_log "Query installed versions of systemd glibc dbus-broker filesystem via rpm -q"
rpm -q systemd glibc dbus-broker filesystem || true
