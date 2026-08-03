#!/usr/bin/env bash
# MIOS_APPLY_CLASS=bake-only
# AI-hint: Automates the retrieval, compilation, and installation of the k3s SELinux policy for Fedora 44, ensuring K3s compatibility by staging the compiled .pp file in the immutable /usr tree.
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

mios_log "Compiling k3s.pp SELinux policy for Fedora 44"

source "$(dirname "$0")/lib/packages.sh"
source "$(dirname "$0")/lib/common.sh"

install_packages "k3s-selinux-build"

K3S_SELINUX_REPO="https://github.com/k3s-io/k3s-selinux.git"
if [[ -z "${K3S_SELINUX_TAG:-}" ]]; then
    K3S_SELINUX_TAG=$(git ls-remote --tags --refs "$K3S_SELINUX_REPO" 'v*' 2>/dev/null \
        | awk -F/ '{print $NF}' \
        | sort -V \
        | tail -n1) || true
    K3S_SELINUX_TAG="${K3S_SELINUX_TAG:-master}"
fi
record_version k3s-selinux "$K3S_SELINUX_TAG" "https://github.com/k3s-io/k3s-selinux/tree/${K3S_SELINUX_TAG}"

if [ -f "/usr/share/mios/vendored/k3s/k3s-selinux.tar.gz" ]; then
    mios_log "Offline vendored k3s-selinux.tar.gz found"
    mkdir -p /tmp/k3s-selinux
    # `|| true` alone left an EMPTY dir on a bad tarball and the failure only
    # surfaced later as a confusing "k3s.te not found". Verify the extraction
    # produced sources and fall back to the clone if it did not.
    if ! tar -xf "/usr/share/mios/vendored/k3s/k3s-selinux.tar.gz" \
             -C /tmp/k3s-selinux --strip-components=1 2>/dev/null \
       || ! find /tmp/k3s-selinux -name 'k3s.te' -print -quit | grep -q .; then
        mios_log "Vendored tarball unusable -- falling back to clone"
        rm -rf /tmp/k3s-selinux
        git clone --depth 1 --branch "${K3S_SELINUX_TAG}" \
            "$K3S_SELINUX_REPO" /tmp/k3s-selinux 2>/dev/null \
            || git clone --depth 1 "$K3S_SELINUX_REPO" /tmp/k3s-selinux 2>/dev/null \
            || mios_log "Clone unavailable (offline) -- continuing with what was extracted"
    fi
else
    mios_log "Cloning k3s-selinux at ${K3S_SELINUX_TAG}"
    git clone --depth 1 --branch "${K3S_SELINUX_TAG}" \
        "$K3S_SELINUX_REPO" /tmp/k3s-selinux 2>/dev/null \
        || git clone --depth 1 "$K3S_SELINUX_REPO" /tmp/k3s-selinux
fi

cd /tmp/k3s-selinux

# Layout differs by upstream version. >=0.2 nests the sources under
# policy/<distro>/; <=0.1.x (which is what the vendored tarball is --
# k3s-selinux-0.1.1-rc2) keeps k3s.te FLAT at the archive root with no policy/
# directory at all. The old `find policy ...` had no fallback for that and, with
# `set -euo pipefail`, a missing policy/ aborted the whole phase two seconds in
# with a bare exit 1 -- which is what the bake logged as "[WARN] 37-k3s-selinux".
POLICY_DIR=""
if [ -d "policy/coreos" ]; then
    POLICY_DIR="policy/coreos"
elif [ -d "policy/centos9" ]; then
    POLICY_DIR="policy/centos9"
elif [ -d "policy/rhel9" ]; then
    POLICY_DIR="policy/rhel9"
elif [ -f "k3s.te" ]; then
    POLICY_DIR="."
elif [ -d "policy" ]; then
    POLICY_DIR="$(find policy -name k3s.te -printf '%h\n' 2>/dev/null | head -n 1 || true)"
fi

if [ -z "$POLICY_DIR" ] || [ ! -f "$POLICY_DIR/k3s.te" ]; then
    # Degrade explicitly instead of dying: k3s.pp is an optional hardening
    # artefact and the rest of the image is unaffected without it.
    mios_skip "k3s.te not found (checked policy/{coreos,centos9,rhel9}, repo root, policy/**) -- skipping k3s.pp"
    cd /
    rm -rf /tmp/k3s-selinux
    exit 0
fi

mios_log "Policy source $POLICY_DIR"
# `cp ./k3s.* .` onto itself is an error under set -e; only copy when the
# sources actually live in a subdirectory.
if [ "$POLICY_DIR" != "." ]; then
    cp -p "$POLICY_DIR"/k3s.* .
fi

make -f /usr/share/selinux/devel/Makefile k3s.pp

mkdir -p /usr/share/selinux/packages/mios
install -m 0644 k3s.pp /usr/share/selinux/packages/mios/k3s.pp

cd /
rm -rf /tmp/k3s-selinux
mios_ok "K3s.pp staged in /usr/share/selinux/packages/mios/"
