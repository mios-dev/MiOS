#!/bin/bash
# 37-aichat: Install AIChat and AIChat-NG Rust CLI tools
set -euo pipefail
# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/packages.sh"

echo "[37-aichat] Installing AI-related packages (redis, sqlite)..."
install_packages "ai"

echo "[37-aichat] Installing AIChat and AIChat-NG binaries..."

# Fetch latest release tags
# v0.2.0: Wrap in subshell + || true to prevent pipefail from killing the script if API is down
AICHAT_TAG=$( (scurl -s https://api.github.com/repos/sigoden/aichat/releases/latest | grep -Po '"tag_name": "\K.*?(?=")') 2>/dev/null || true)
AICHAT_NG_TAG=$( (scurl -s https://api.github.com/repos/blob42/aichat-ng/releases/latest | grep -Po '"tag_name": "\K.*?(?=")') 2>/dev/null || true)

# Fallbacks if API fails
if [[ -z "$AICHAT_TAG" ]]; then
    AICHAT_TAG="v0.25.0"
    echo "[37-aichat]   AIChat API unavailable — using fallback ${AICHAT_TAG}"
else
    echo "[37-aichat]   Detected AIChat version: ${AICHAT_TAG}"
fi

if [[ -z "$AICHAT_NG_TAG" ]]; then
    AICHAT_NG_TAG="v0.25.0"
    echo "[37-aichat]   AIChat-NG API unavailable — using fallback ${AICHAT_NG_TAG}"
else
    echo "[37-aichat]   Detected AIChat-NG version: ${AICHAT_NG_TAG}"
fi

# ── AIChat ────────────────────────────────────────────────────────────────────
AICHAT_ARCH="aichat-${AICHAT_TAG}-x86_64-unknown-linux-musl.tar.gz"
AICHAT_BASE="https://github.com/sigoden/aichat/releases/download/${AICHAT_TAG}"

mkdir -p /tmp/aichat-dl
scurl -sfL "${AICHAT_BASE}/${AICHAT_ARCH}" -o "/tmp/aichat-dl/${AICHAT_ARCH}"
scurl -sfL "${AICHAT_BASE}/${AICHAT_ARCH}.sha256" -o "/tmp/aichat-dl/${AICHAT_ARCH}.sha256" 2>/dev/null || {
    echo "[37-aichat] WARN: sha256 sidecar unavailable for AIChat — cannot verify integrity"
    rm -f "/tmp/aichat-dl/${AICHAT_ARCH}.sha256"
}

if [[ -f "/tmp/aichat-dl/${AICHAT_ARCH}.sha256" ]]; then
    # sha256 sidecar format: "<hash>  <filename>" or "<hash> *<filename>"
    (cd /tmp/aichat-dl && grep "${AICHAT_ARCH}" "${AICHAT_ARCH}.sha256" | sha256sum -c -) \
        || die "AIChat ${AICHAT_TAG} SHA256 mismatch — aborting"
    echo "[37-aichat]   ✓ AIChat sha256 verified"
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
    echo "[37-aichat] WARN: sha256 sidecar unavailable for AIChat-NG — cannot verify integrity"
    rm -f "/tmp/aichat-ng-dl/${AICHAT_NG_ARCH}.sha256"
}

if [[ -f "/tmp/aichat-ng-dl/${AICHAT_NG_ARCH}.sha256" ]]; then
    (cd /tmp/aichat-ng-dl && grep "${AICHAT_NG_ARCH}" "${AICHAT_NG_ARCH}.sha256" | sha256sum -c -) \
        || die "AIChat-NG ${AICHAT_NG_TAG} SHA256 mismatch — aborting"
    echo "[37-aichat]   ✓ AIChat-NG sha256 verified"
fi

tar -xzf "/tmp/aichat-ng-dl/${AICHAT_NG_ARCH}" -C /usr/bin/ aichat-ng
chmod +x /usr/bin/aichat-ng
rm -rf /tmp/aichat-ng-dl

echo "[37-aichat] AIChat and AIChat-NG installed successfully."
