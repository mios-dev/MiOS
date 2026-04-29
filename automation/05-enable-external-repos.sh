#!/usr/bin/env bash
# ============================================================================
# automation/05-enable-external-repos.sh
# ----------------------------------------------------------------------------
# Enable external DNF repositories for MiOS (Fedora 44 / Rawhide).
# Idempotent; fails fast; uses ${DNF_SETOPT[@]} from automation/lib/common.sh.
# RPM Fusion is intentionally NOT handled here — see 01-repos.sh.
#
# v2.3 CHANGES:
#   - Added Kubernetes stable v1.32 repo (kubectl not in Fedora repos).
#   - Added ublue-os/packages COPR (uupd + greenboot; required by 43-uupd-installer.sh).
#
# v0.1.1 CHANGES:
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

# --- 1. Terra (fyralabs) ----------------------------------------------------
# Patched WINE/Mesa/miscellaneous packages missing from Fedora + RPM Fusion.
if [[ ! -f "${REPO_DIR}/terra.repo" ]]; then
    log "enabling Terra repo (fyralabs)"
    scurl -fsSL \
        https://github.com/terrapkg/subatomic-repos/raw/main/terra.repo \
        -o "${REPO_DIR}/terra.repo"
else
    log "Terra repo already present — skipping"
fi

# --- 2. Visual Studio Code (Microsoft) --------------------------------------
if [[ ! -f "${REPO_DIR}/vscode.repo" ]]; then
    log "enabling VS Code repo (Microsoft)"
    scurl -fsSL https://packages.microsoft.com/keys/microsoft.asc -o /tmp/vscode.asc
    rpm --import /tmp/vscode.asc && rm -f /tmp/vscode.asc
    cat > "${REPO_DIR}/vscode.repo" <<'EOF'
[code]
name=Visual Studio Code
baseurl=https://packages.microsoft.com/yumrepos/vscode
enabled=1
autorefresh=1
type=rpm-md
gpgcheck=1
gpgkey=https://packages.microsoft.com/keys/microsoft.asc
EOF
else
    log "VS Code repo already present — skipping"
fi

# --- 3. 1Password -----------------------------------------------------------
if [[ ! -f "${REPO_DIR}/1password.repo" ]]; then
    log "enabling 1Password repo"
    scurl -fsSL https://downloads.1password.com/linux/keys/1password.asc -o /tmp/1password.asc
    rpm --import /tmp/1password.asc && rm -f /tmp/1password.asc
    cat > "${REPO_DIR}/1password.repo" <<'EOF'
[1password]
name=1Password Stable Channel
baseurl=https://downloads.1password.com/linux/rpm/stable/$basearch
enabled=1
gpgcheck=1
gpgkey=https://downloads.1password.com/linux/keys/1password.asc
EOF
else
    log "1Password repo already present — skipping"
fi

# --- 4. Tailscale -----------------------------------------------------------
if [[ ! -f "${REPO_DIR}/tailscale.repo" ]]; then
    log "enabling Tailscale repo"
    $DNF_BIN "${DNF_SETOPT[@]}" config-manager addrepo -y \
        --overwrite \
        --from-repofile=https://pkgs.tailscale.com/stable/fedora/tailscale.repo
else
    log "Tailscale repo already present — skipping"
fi

# --- 5. Docker CE (required when podman-docker is removed) ------------------
if [[ ! -f "${REPO_DIR}/docker-ce.repo" ]]; then
    log "enabling Docker CE repo"
    $DNF_BIN "${DNF_SETOPT[@]}" config-manager addrepo -y \
        --overwrite \
        --from-repofile=https://download.docker.com/linux/fedora/docker-ce.repo
else
    log "Docker CE repo already present — skipping"
fi

# --- 6. Cloud Chrome -------------------------------------------------------
if [[ ! -f "${REPO_DIR}/Legacy-Cloud-chrome.repo" ]]; then
    log "enabling Cloud Chrome repo"
    scurl -fsSL https://dl.Legacy-Cloud.com/linux/linux_signing_key.pub -o /tmp/chrome.pub
    rpm --import /tmp/chrome.pub && rm -f /tmp/chrome.pub
    cat > "${REPO_DIR}/Legacy-Cloud-chrome.repo" <<'EOF'
[Legacy-Cloud-chrome]
name=Legacy-Cloud-chrome
baseurl=https://dl.Legacy-Cloud.com/linux/chrome/rpm/stable/$basearch
enabled=1
gpgcheck=1
gpgkey=https://dl.Legacy-Cloud.com/linux/linux_signing_key.pub
EOF
else
    log "Cloud Chrome repo already present — skipping"
fi

# --- 7. Kubernetes stable v1.32 (kubectl) -----------------------------------
# kubectl is NOT in standard Fedora repos — must come from the Kubernetes
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
    log "Kubernetes repo already present — skipping"
fi

# --- 8. ublue-os/packages COPR (uupd + greenboot) ---------------------------
# uupd and greenboot ship from the Universal Blue packages COPR.
# 43-uupd-installer.sh explicitly requires this repo to be present first.
# Using Fedora 44 repo endpoint; COPR auto-publishes new packages as they land.
if [[ ! -f "${REPO_DIR}/ublue-os-packages.repo" ]]; then
    log "enabling ublue-os/packages COPR (uupd + greenboot)"
    scurl -fsSL \
        "https://copr.fedorainfracloud.org/coprs/ublue-os/packages/repo/fedora-44/ublue-os-packages-fedora-44.repo" \
        -o "${REPO_DIR}/ublue-os-packages.repo"
    # Lower priority than Fedora base so Fedora wins on conflicting packages.
    if ! grep -q '^priority=' "${REPO_DIR}/ublue-os-packages.repo"; then
        sed -i '/^\[/a priority=75' "${REPO_DIR}/ublue-os-packages.repo"
    fi
else
    log "ublue-os/packages COPR already present — skipping"
fi

# ── Waydroid (Aleasto) ───────────────────────────────────────────────────
if ! [ -f /etc/yum.repos.d/_copr:copr.fedorainfracloud.org:aleasto:waydroid.repo ]; then
    log "enabling aleasto/waydroid COPR (GNOME 50 fix)"
    $DNF_BIN "${DNF_SETOPT[@]}" copr enable -y aleasto/waydroid
else
    log "aleasto/waydroid COPR already present — skipping"
fi

log "external repos enabled; refreshing metadata"
$DNF_BIN "${DNF_SETOPT[@]}" makecache -y

log "05-enable-external-repos.sh complete"
