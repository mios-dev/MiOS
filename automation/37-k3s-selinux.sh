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
    tar -xf "/usr/share/mios/vendored/k3s/k3s-selinux.tar.gz" -C /tmp/k3s-selinux --strip-components=1 2>/dev/null || true
else
    mios_log "Cloning k3s-selinux at ${K3S_SELINUX_TAG}"
    git clone --depth 1 --branch "${K3S_SELINUX_TAG}" \
        "$K3S_SELINUX_REPO" /tmp/k3s-selinux 2>/dev/null \
        || git clone --depth 1 "$K3S_SELINUX_REPO" /tmp/k3s-selinux
fi

cd /tmp/k3s-selinux

POLICY_DIR=""
if [ -d "policy/coreos" ]; then
    POLICY_DIR="policy/coreos"
elif [ -d "policy/centos9" ]; then
    POLICY_DIR="policy/centos9"
elif [ -d "policy/rhel9" ]; then
    POLICY_DIR="policy/rhel9"
else
    POLICY_DIR=$(find policy -name k3s.te -printf '%h\n' | head -n 1)
fi

if [ -z "$POLICY_DIR" ]; then
    mios_err "k3s.te not found in repository"
    exit 1
fi

mios_log "Policy source $POLICY_DIR"
cp -p "$POLICY_DIR"/k3s.* .

make -f /usr/share/selinux/devel/Makefile k3s.pp

mkdir -p /usr/share/selinux/packages/mios
install -m 0644 k3s.pp /usr/share/selinux/packages/mios/k3s.pp

cd /
rm -rf /tmp/k3s-selinux
mios_ok "k3s.pp staged in /usr/share/selinux/packages/mios/"
