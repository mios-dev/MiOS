#!/bin/bash
# 'MiOS' v0.2.0 -- 13-ceph-k3s: Ceph distributed storage + K3s Kubernetes
# Cephadm runs ALL server daemons as Podman containers.
# Only client tools + orchestrator binary are baked into the image.
#
# v0.2.0 FIXES:
#   - K3s manifests stored in /usr/share/mios/k3s-manifests/ (not /var)
#     First-boot service copies them to /var/lib/rancher/k3s/server/manifests/
#     This fixes bootc lint: /var content must use tmpfiles.d entries
#   - systemctl enables moved to Containerfile STEP D (unit files in )
set -euo pipefail
# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/packages.sh"

# ─── Ceph Client + Orchestrator ──────────────────────────────────────────────
echo "[13-ceph-k3s] Installing Ceph client tools and cephadm..."
install_packages "ceph"

# ─── K3s Prerequisites ───────────────────────────────────────────────────────
echo "[13-ceph-k3s] Installing K3s prerequisites..."
install_packages "k3s"

# Note: k3s-selinux policy is compiled from source in 19-k3s-selinux.sh

# ─── K3s Binary & Install Script ─────────────────────────────────────────────
echo "[13-ceph-k3s] Resolving latest K3s release tag..."
# Retry 3 times for flaky networks
K3S_TAG=""
for i in 1 2 3; do
    # v0.2.0: Wrap in subshell + || true to prevent pipefail from killing the script if API is down
    K3S_TAG=$( (scurl -sL -o /dev/null -w "%{url_effective}" https://github.com/k3s-io/k3s/releases/latest | grep -oE '[^/]+$') 2>/dev/null || true)
    if [[ -n "$K3S_TAG" && "$K3S_TAG" != "latest" ]]; then break; fi
    sleep 2
done

if [[ -z "$K3S_TAG" || "$K3S_TAG" == "latest" ]]; then
    echo "[13-ceph-k3s] WARN: Could not resolve latest K3s tag. Skipping K3s binary installation."
    K3S_TAG=""
fi

if [[ -n "$K3S_TAG" ]]; then
    echo "[13-ceph-k3s] Latest K3s tag: $K3S_TAG"
    record_version k3s "$K3S_TAG" "https://github.com/k3s-io/k3s/releases/tag/${K3S_TAG}"

    echo "[13-ceph-k3s] Downloading K3s binary, checksum, and install script..."
    K3S_URL="https://github.com/k3s-io/k3s/releases/download/${K3S_TAG}/k3s"
    K3S_SUM_URL="https://github.com/k3s-io/k3s/releases/download/${K3S_TAG}/sha256sum-amd64.txt"
    K3S_INSTALL_URL="https://raw.githubusercontent.com/k3s-io/k3s/${K3S_TAG}/install.sh"

    mkdir -p /tmp/k3s-dl
    if scurl -sfL "$K3S_URL" -o /tmp/k3s-dl/k3s && \
       scurl -sfL "$K3S_SUM_URL" -o /tmp/k3s-dl/sha256sum.txt && \
       scurl -sfL "$K3S_INSTALL_URL" -o /tmp/k3s-dl/k3s-install.sh; then
        cd /tmp/k3s-dl
        if grep -E "  k3s$" sha256sum.txt | sha256sum -c - >/dev/null 2>&1; then
            echo "[13-ceph-k3s] [ok] K3s SHA256 checksum verified"
            # Install into /usr/bin (immutable image surface). /usr/local is
            # a symlink to /var/usrlocal on bootc/FCOS layouts and
            # /var/usrlocal/bin/ does not exist at OCI build time (it's
            # created at first boot by usr/lib/tmpfiles.d/mios.conf).
            install -m 0755 -t /usr/bin/ k3s
            install -m 0755 -t /usr/bin/ k3s-install.sh

            # Symlink only if no official RPM binaries claim the names.
            [ ! -e /usr/bin/kubectl ] && ln -sf k3s /usr/bin/kubectl || true
            [ ! -e /usr/bin/crictl ]  && ln -sf k3s /usr/bin/crictl  || true
            [ ! -e /usr/bin/ctr ]     && ln -sf k3s /usr/bin/ctr     || true

            echo "[13-ceph-k3s] K3s binary and install script installed (tag: $K3S_TAG)"
        else
            echo "[13-ceph-k3s] ERROR: K3s binary SHA256 checksum mismatch! Skipping."
        fi
        cd - >/dev/null
    else
        echo "[13-ceph-k3s] WARN: K3s download failed. Skipping K3s installation."
    fi
    rm -rf /tmp/k3s-dl
fi

# ─── Make bootstrap script executable ────────────────────────────────────────
# Script lives at /usr/libexec/mios/ceph-bootstrap.sh on the image
# surface. The legacy /usr/local/bin path resolved to /var/usrlocal
# on bootc/FCOS layouts and was wiped by the build-time /var cleanup;
# both ceph-bootstrap.service + mios-ceph-bootstrap.service now
# ExecStart at the immutable libexec path.
chmod 755 /usr/libexec/mios/ceph-bootstrap.sh 2>/dev/null || true

# ─── NOTE: Service enables are in Containerfile STEP D ───────────────────────
# k3s.service, mios-ceph-bootstrap.service, var-home.mount,
# var-lib-containers.mount all live in  and are enabled
# AFTER the COPY step in the Containerfile.

echo "[13-ceph-k3s] Ceph + K3s stack installed."
echo "[13-ceph-k3s]   Ceph Dashboard:  https://<host>:8443 (after bootstrap)"
echo "[13-ceph-k3s]   K3s API server:  https://<host>:6443 (after boot)"
