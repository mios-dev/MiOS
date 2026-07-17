#!/bin/bash
# AI-hint: Installs Ceph client tools and the K3s Kubernetes orchestrator, handling version resolution and offline vendoring to provision the storage and container orchestration layer of the MiOS cluster.
# AI-related: /usr/share/mios/k3s-manifests/, /usr/share/mios/vendored/k3s, /usr/share/mios/vendored/k3s-install.sh, /usr/share/mios/vendored/sha256sum-amd64.txt, /usr/libexec/mios/ceph-bootstrap.sh, mios-ceph-bootstrap, ceph-bootstrap.service, mios-ceph-bootstrap.service, k3s.service, var-home.mount
# 'MiOS' - 13-ceph-k3s: Ceph distributed storage + K3s Kubernetes
# Cephadm runs ALL server daemons as Podman containers.
# Only client tools + orchestrator binary are baked into the image.
#
# FIXES:
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
# Version SSOT: [image.sidecars].k3s_version in mios.toml -> exported as
# MIOS_K3S_VERSION by tools/lib/userenv.sh (sourced via lib/common.sh above). The
# HOST BINARY installed here and the rancher/k3s CONTAINER image
# ([image.sidecars].k3s) now read ONE version key, so they can never drift -- the
# prior split-brain (binary tracked GitHub `latest`, image was pinned) is closed.
# The container image tag uses '-k3s1' (Docker tags forbid '+'); the GitHub
# release + binary-download tag uses '+k3s1', so translate the SSOT image tag to
# the release tag for the download URLs below.
echo "[13-ceph-k3s] Resolving K3s release tag from mios.toml SSOT (MIOS_K3S_VERSION)..."
# Offline check: do we have local k3s files?
USE_OFFLINE=false
if [ -f "/usr/share/mios/vendored/k3s" ] && [ -f "/usr/share/mios/vendored/k3s-install.sh" ]; then
    echo "[13-ceph-k3s] Found offline vendored K3s files. Using them."
    USE_OFFLINE=true
    K3S_TAG="vendored"
else
    K3S_TAG="${MIOS_K3S_VERSION:-}"
    # Docker image tag (...-k3s1) -> GitHub release/download tag (...+k3s1).
    K3S_TAG="${K3S_TAG/-k3s/+k3s}"
fi

if [[ -z "$K3S_TAG" ]]; then
    echo "[13-ceph-k3s] WARN: K3s version SSOT empty (MIOS_K3S_VERSION unset). Skipping K3s binary installation."
    K3S_TAG=""
fi

if [[ -n "$K3S_TAG" ]]; then
    echo "[13-ceph-k3s] K3s tag (from SSOT): $K3S_TAG"
    record_version k3s "$K3S_TAG" "https://github.com/k3s-io/k3s/releases/tag/${K3S_TAG}"

    mkdir -p /tmp/k3s-dl
    if [ "$USE_OFFLINE" = true ]; then
        cp /usr/share/mios/vendored/k3s /tmp/k3s-dl/k3s
        cp /usr/share/mios/vendored/k3s-install.sh /tmp/k3s-dl/k3s-install.sh
        if [ -f "/usr/share/mios/vendored/sha256sum-amd64.txt" ]; then
            cp /usr/share/mios/vendored/sha256sum-amd64.txt /tmp/k3s-dl/sha256sum.txt
        else
            local_sum=$(sha256sum /usr/share/mios/vendored/k3s | awk '{print $1}')
            echo "${local_sum}  k3s" > /tmp/k3s-dl/sha256sum.txt
        fi
        download_ok=true
    else
        echo "[13-ceph-k3s] Downloading K3s binary, checksum, and install script..."
        K3S_URL="https://github.com/k3s-io/k3s/releases/download/${K3S_TAG}/k3s"
        K3S_SUM_URL="https://github.com/k3s-io/k3s/releases/download/${K3S_TAG}/sha256sum-amd64.txt"
        K3S_INSTALL_URL="https://raw.githubusercontent.com/k3s-io/k3s/${K3S_TAG}/install.sh"
        download_ok=false
        if scurl -sfL "$K3S_URL" -o /tmp/k3s-dl/k3s && \
           scurl -sfL "$K3S_SUM_URL" -o /tmp/k3s-dl/sha256sum.txt && \
           scurl -sfL "$K3S_INSTALL_URL" -o /tmp/k3s-dl/k3s-install.sh; then
            download_ok=true
        fi
    fi

    if [ "$download_ok" = true ]; then
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
