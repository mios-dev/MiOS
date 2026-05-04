#!/bin/bash
# 37-aichat: Install AIChat and AIChat-NG Rust CLI tools
#
# OPEN TASK (project invariant: VM | Container | Flatpak only):
# These are user-facing AI CLI applications. Per the project-wide
# delivery rule, they should run inside a Distrobox container, not
# directly on the host. The current /usr/bin install is transitional;
# the migration is to package them as a Distrobox container with
# wrapper scripts in /usr/bin that exec into the container. See
# usr/share/mios/PACKAGES.md > "AI Tools" section for context.
set -euo pipefail
# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/packages.sh"

echo "[37-aichat] Resolving 'ai' package block (currently empty -- aichat/aichat-ng ship as tarballs, not RPMs)..."
install_packages "ai"

echo "[37-aichat] Installing AIChat and AIChat-NG binaries..."

# Resolve latest release tags from upstream. Project policy: every dependency
# tracks :latest from its source, so no fallback pin -- if api.github.com is
# unreachable, fail loud rather than silently shipping a stale version.
AICHAT_TAG=$( (scurl -s https://api.github.com/repos/sigoden/aichat/releases/latest | grep -Po '"tag_name": "\K.*?(?=")') 2>/dev/null || true)
AICHAT_NG_TAG=$( (scurl -s https://api.github.com/repos/blob42/aichat-ng/releases/latest | grep -Po '"tag_name": "\K.*?(?=")') 2>/dev/null || true)

[[ -n "$AICHAT_TAG"    ]] || die "AIChat: api.github.com release-latest lookup returned empty"
[[ -n "$AICHAT_NG_TAG" ]] || die "AIChat-NG: api.github.com release-latest lookup returned empty"
record_version aichat    "$AICHAT_TAG"    "https://github.com/sigoden/aichat/releases/tag/${AICHAT_TAG}"
record_version aichat-ng "$AICHAT_NG_TAG" "https://github.com/blob42/aichat-ng/releases/tag/${AICHAT_NG_TAG}"

# ── AIChat ────────────────────────────────────────────────────────────────────
AICHAT_ARCH="aichat-${AICHAT_TAG}-x86_64-unknown-linux-musl.tar.gz"
AICHAT_BASE="https://github.com/sigoden/aichat/releases/download/${AICHAT_TAG}"

mkdir -p /tmp/aichat-dl
scurl -sfL "${AICHAT_BASE}/${AICHAT_ARCH}" -o "/tmp/aichat-dl/${AICHAT_ARCH}"
scurl -sfL "${AICHAT_BASE}/${AICHAT_ARCH}.sha256" -o "/tmp/aichat-dl/${AICHAT_ARCH}.sha256" 2>/dev/null || {
    echo "[37-aichat] WARN: sha256 sidecar unavailable for AIChat -- cannot verify integrity"
    rm -f "/tmp/aichat-dl/${AICHAT_ARCH}.sha256"
}

if [[ -f "/tmp/aichat-dl/${AICHAT_ARCH}.sha256" ]]; then
    # sha256 sidecar format: "<hash>  <filename>" or "<hash> *<filename>"
    (cd /tmp/aichat-dl && grep "${AICHAT_ARCH}" "${AICHAT_ARCH}.sha256" | sha256sum -c -) \
        || die "AIChat ${AICHAT_TAG} SHA256 mismatch -- aborting"
    echo "[37-aichat]   [ok] AIChat sha256 verified"
fi

tar -xzf "/tmp/aichat-dl/${AICHAT_ARCH}" -C /usr/bin/ aichat
chmod +x /usr/bin/aichat
rm -rf /tmp/aichat-dl

# ── AIChat-NG ────────────────────────────────────────────────────────────────
AICHAT_NG_ARCH="aichat-ng-${AICHAT_NG_TAG}-x86_64-unknown-linux-musl.tar.gz"
AICHAT_NG_BASE="https://github.com/blob42/aichat-ng/releases/download/${AICHAT_NG_TAG}"

mkdir -p /tmp/aichat-ng-dl
scurl -sfL "${AICHAT_NG_BASE}/${AICHAT_NG_ARCH}" -o "/tmp/aichat-ng-dl/${AICHAT_NG_ARCH}"
scurl -sfL "${AICHAT_NG_BASE}/${AICHAT_NG_ARCH}.sha256" -o "/tmp/aichat-ng-dl/${AICHAT_NG_ARCH}.sha256" 2>/dev/null || {
    echo "[37-aichat] WARN: sha256 sidecar unavailable for AIChat-NG -- cannot verify integrity"
    rm -f "/tmp/aichat-ng-dl/${AICHAT_NG_ARCH}.sha256"
}

if [[ -f "/tmp/aichat-ng-dl/${AICHAT_NG_ARCH}.sha256" ]]; then
    (cd /tmp/aichat-ng-dl && grep "${AICHAT_NG_ARCH}" "${AICHAT_NG_ARCH}.sha256" | sha256sum -c -) \
        || die "AIChat-NG ${AICHAT_NG_TAG} SHA256 mismatch -- aborting"
    echo "[37-aichat]   [ok] AIChat-NG sha256 verified"
fi

tar -xzf "/tmp/aichat-ng-dl/${AICHAT_NG_ARCH}" -C /usr/bin/ aichat-ng
chmod +x /usr/bin/aichat-ng
rm -rf /tmp/aichat-ng-dl

echo "[37-aichat] AIChat and AIChat-NG installed successfully."
