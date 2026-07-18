#!/usr/bin/env bash
# AI-hint: Automates the retrieval, compilation, and installation of the k3s SELinux policy for Fedora 44, ensuring K3s compatibility by staging the compiled .pp file in the immutable /usr tree.
set -euo pipefail

echo "==> Compiling K3s SELinux policy (k3s.pp) for Fedora 44 and staging it in /usr/share/selinux/packages/mios/..."

# shellcheck source=lib/packages.sh
source "$(dirname "$0")/lib/packages.sh"
source "$(dirname "$0")/lib/common.sh"

install_packages "k3s-selinux-build"

# Pin to a specific stable release tag -- HEAD clones pick up unreviewed commits.
# Update K3S_SELINUX_TAG when bumping K3s to stay in sync with its SELinux policy.
# Audit v1.5.stable.2 was deleted upstream; resolve "the latest
# v* tag" dynamically and fall back to the override or master if discovery
# fails.
K3S_SELINUX_REPO="https://github.com/k3s-io/k3s-selinux.git"
if [[ -z "${K3S_SELINUX_TAG:-}" ]]; then
    K3S_SELINUX_TAG=$(git ls-remote --tags --refs "$K3S_SELINUX_REPO" 'v*' 2>/dev/null \
        | awk -F/ '{print $NF}' \
        | sort -V \
        | tail -n1) || true
    K3S_SELINUX_TAG="${K3S_SELINUX_TAG:-master}"
fi
record_version k3s-selinux "$K3S_SELINUX_TAG" "https://github.com/k3s-io/k3s-selinux/tree/${K3S_SELINUX_TAG}"

echo "==> Cloning k3s-selinux at ref ${K3S_SELINUX_TAG}..."
git clone --depth 1 --branch "${K3S_SELINUX_TAG}" \
    "$K3S_SELINUX_REPO" /tmp/k3s-selinux 2>/dev/null \
    || git clone --depth 1 "$K3S_SELINUX_REPO" /tmp/k3s-selinux

cd /tmp/k3s-selinux

# K3s SELinux repo stores policies in subdirectories (e.g., policy/coreos or policy/centos9)
# We find the best matching policy source files for Fedora.
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
    echo "FATAL: Could not find k3s.te in the repository."
    exit 1
fi

echo "Using policy source from: $POLICY_DIR"
cp -p "$POLICY_DIR"/k3s.* .

# Compile the policy using the Fedora 44 SELinux Makefile
make -f /usr/share/selinux/devel/Makefile k3s.pp

# ARCHITECTURAL FIX: Instead of installing at build-time with 'semodule -i',
# we ship the compiled policy in the immutable /usr tree.
# This ensures that 'bootc upgrade' doesn't create opaque policy layers.
mkdir -p /usr/share/selinux/packages/mios
install -m 0644 k3s.pp /usr/share/selinux/packages/mios/k3s.pp

# Clean up
cd /
rm -rf /tmp/k3s-selinux
echo "==> K3s SELinux Policy staged in /usr/share/selinux/packages/mios/"
