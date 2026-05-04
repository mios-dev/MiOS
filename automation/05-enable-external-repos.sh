#!/usr/bin/env bash
# ============================================================================
# automation/05-enable-external-repos.sh
# ----------------------------------------------------------------------------
# Enable external DNF repositories for 'MiOS' (Fedora 44 / Rawhide).
# Idempotent; fails fast; uses ${DNF_SETOPT[@]} from automation/lib/common.sh.
# RPM Fusion is intentionally NOT handled here -- see 01-repos.sh.
#
# v2.3 CHANGES:
#   - Added Kubernetes stable v1.32 repo (kubectl not in Fedora repos).
#   - Added ublue-os/packages COPR (uupd + greenboot; required by 43-uupd-installer.sh).
#
# v0.2.0 CHANGES:
#   - removed redundant RPM Fusion install block (was using `rpm -E %fedora`
#     which yielded 41/43 from the base image and clobbered 01-repos.sh's
#     explicit F44 pin).
#   - replaced dnf5 with dnf throughout (consistency with 01-repos.sh and
#     lib/packages.sh; on F44 `dnf` is dnf5 via symlink anyway).
#   - adopted ${DNF_SETOPT[@]} for every mutating invocation.
# ============================================================================
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

REPO_DIR=/etc/yum.repos.d

# Best-effort policy. Every external repo enable here is non-critical:
# downstream installs already pass --skip-unavailable, so a missing repo
# silently drops its packages rather than failing the build. Wrap every
# external fetch / dnf op in warn-on-failure + clean partials, and keep
# the script's overall exit at 0 (warnings are tracked separately by the
# build chain summary).

# Try a curl fetch into a target file. On failure: warn, delete partial,
# return 1 so callers can short-circuit downstream key import / sed.
try_fetch() {
    local url="$1" out="$2" label="$3"
    if scurl -fsSL --connect-timeout 20 --max-time 60 "$url" -o "$out" 2>/dev/null; then
        return 0
    fi
    warn "${label}: fetch failed (${url}) -- skipping"
    rm -f "$out"
    return 1
}

# --- 1. Terra (fyralabs) ----------------------------------------------------
# Patched WINE/Mesa/miscellaneous packages missing from Fedora + RPM Fusion.
if [[ ! -f "${REPO_DIR}/terra.repo" ]]; then
    log "enabling Terra repo (fyralabs)"
    try_fetch "https://github.com/terrapkg/subatomic-repos/raw/main/terra.repo" \
              "${REPO_DIR}/terra.repo" "Terra repo" || true
else
    log "Terra repo already present -- skipping"
fi

# --- 2. (removed) VSCodium ---------------------------------------------------
# PROJECT INVARIANT: applications ship as Flatpaks, only system dependencies
# ship as RPMs. VSCodium is an application -- it ships from Flathub via
# MIOS_FLATPAKS / the Flatpak install path, never from an RPM repo. The
# previous VSCodium .repo / gpg-import block was removed for this reason.
# If any other app RPM repo creeps into this script, delete it the same way.

# --- 7. Kubernetes stable v1.32 (kubectl) -----------------------------------
# kubectl is NOT in standard Fedora repos -- must come from the Kubernetes
# project's own RPM repository. Pinned to v1.32 (current stable).
# Only kubectl is installed from here; kubeadm/kubelet are intentionally
# excluded (k3s is used for the cluster runtime, not kubeadm).
if [[ ! -f "${REPO_DIR}/kubernetes.repo" ]]; then
    log "enabling Kubernetes stable v1.32 repo"
    cat > "${REPO_DIR}/kubernetes.repo" <<'EOF'
[kubernetes]
name=Kubernetes
baseurl=https://pkgs.k8s.io/core:/stable:/v1.32/rpm/
enabled=1
gpgcheck=1
gpgkey=https://pkgs.k8s.io/core:/stable:/v1.32/rpm/repodata/repomd.xml.key
repo_gpgcheck=1
exclude=kubelet kubeadm cri-tools kubernetes-cni
EOF
else
    log "Kubernetes repo already present -- skipping"
fi

# --- 8. ublue-os/packages COPR (uupd + greenboot) ---------------------------
# uupd and greenboot ship from the Universal Blue packages COPR.
# 43-uupd-installer.sh explicitly requires this repo to be present first.
# Using Fedora 44 repo endpoint; COPR auto-publishes new packages as they land.
if [[ ! -f "${REPO_DIR}/ublue-os-packages.repo" ]]; then
    log "enabling ublue-os/packages COPR (uupd + greenboot)"
    if try_fetch "https://copr.fedorainfracloud.org/coprs/ublue-os/packages/repo/fedora-44/ublue-os-packages-fedora-44.repo" \
                 "${REPO_DIR}/ublue-os-packages.repo" "ublue-os/packages COPR"; then
        # Lower priority than Fedora base so Fedora wins on conflicting packages.
        if ! grep -q '^priority=' "${REPO_DIR}/ublue-os-packages.repo"; then
            sed -i '/^\[/a priority=75' "${REPO_DIR}/ublue-os-packages.repo"
        fi
    fi
else
    log "ublue-os/packages COPR already present -- skipping"
fi

# ── Waydroid (Aleasto) ───────────────────────────────────────────────────
if ! [ -f /etc/yum.repos.d/_copr:copr.fedorainfracloud.org:aleasto:waydroid.repo ]; then
    log "enabling aleasto/waydroid COPR (GNOME 50 fix)"
    if ! $DNF_BIN "${DNF_SETOPT[@]}" copr enable -y aleasto/waydroid 2>/dev/null; then
        warn "aleasto/waydroid COPR enable failed -- skipping (GNOME 50 fix unavailable)"
    fi
else
    log "aleasto/waydroid COPR already present -- skipping"
fi

# ── Tailscale ────────────────────────────────────────────────────────────
# ucore:stable ships tailscale but its version can lag. Using the official
# Tailscale repo keeps it at the latest stable regardless of ucore cadence.
if [[ ! -f "${REPO_DIR}/tailscale.repo" ]]; then
    log "enabling Tailscale official repo"
    try_fetch "https://pkgs.tailscale.com/stable/fedora/tailscale.repo" \
              "${REPO_DIR}/tailscale.repo" "Tailscale repo" || true
else
    log "Tailscale repo already present -- skipping"
fi

# ── CrowdSec ─────────────────────────────────────────────────────────────
# crowdsec ships its own RPM repo; not in Fedora or RPM Fusion.
if [[ ! -f "${REPO_DIR}/crowdsec.repo" ]]; then
    log "enabling CrowdSec repo"
    # URL must be quoted -- the unquoted '&' is parsed as a job-control
    # background, which silently splits '-o "${REPO_DIR}/crowdsec.repo"'
    # onto its own command line and yields 'line N: -o: command not found'.
    # The 'dist' query parameter pins the packagecloud distro release;
    # crowdsec ships a single fedora repo across releases (the value is
    # only used for substituting $releasever in baseurl).
    try_fetch "https://packagecloud.io/crowdsec/crowdsec/config_file.repo?os=fedora&dist=44&source=script" \
              "${REPO_DIR}/crowdsec.repo" "CrowdSec repo" || true
else
    log "CrowdSec repo already present -- skipping"
fi

log "external repos enabled; refreshing metadata"
# makecache is best-effort: if a single repo's metadata is unreachable
# the next dnf install in this build will retry it. Hard-failing here
# wastes the entire build for a transient mirror hiccup.
if ! $DNF_BIN "${DNF_SETOPT[@]}" makecache -y 2>&1 | tail -20; then
    warn "dnf makecache returned non-zero -- continuing (downstream installs will retry per-repo)"
fi

log "05-enable-external-repos.sh complete"
