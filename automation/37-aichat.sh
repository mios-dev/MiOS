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
# ... (rest of the script)

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

# Download and install AIChat
scurl -L -o /tmp/aichat.tar.gz "https://github.com/sigoden/aichat/releases/download/${AICHAT_TAG}/aichat-${AICHAT_TAG}-x86_64-unknown-linux-musl.tar.gz"
tar -xzf /tmp/aichat.tar.gz -C /usr/bin/ aichat
chmod +x /usr/bin/aichat

# Download and install AIChat-NG
scurl -L -o /tmp/aichat-ng.tar.gz "https://github.com/blob42/aichat-ng/releases/download/${AICHAT_NG_TAG}/aichat-ng-${AICHAT_NG_TAG}-x86_64-unknown-linux-musl.tar.gz"
tar -xzf /tmp/aichat-ng.tar.gz -C /usr/bin/ aichat-ng
chmod +x /usr/bin/aichat-ng

# Cleanup
rm -f /tmp/aichat.tar.gz /tmp/aichat-ng.tar.gz

echo "[37-aichat] AIChat and AIChat-NG installed successfully."
