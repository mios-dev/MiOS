#!/bin/bash
# 38-oh-my-posh: install the Oh-My-Posh prompt customizer.
#
# Static Go binary; not in Fedora repos. Fetched from upstream releases
# at build time (same pattern as 37-aichat.sh). Installed to
#   /usr/bin/oh-my-posh
# (canonical PATH location for a CLI). Sourced via
#   /etc/profile.d/mios-prompt.sh
# for every interactive bash/zsh login.
#
# Per the project invariant (VM | Container | Flatpak only) Oh-My-Posh
# is a SYSTEM-LEVEL CLI utility -- a shell-prompt renderer in the same
# class as bash, vim, btop, fastfetch -- so it ships as an on-host
# binary, not a Flatpak. Containerizing a per-prompt-render call would
# add ~100ms per shell prompt for no security gain (the binary reads
# git status of the cwd; nothing it does benefits from sandboxing).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

# Single canonical home: /usr/bin/oh-my-posh. Earlier iterations put
# the binary at /usr/libexec/mios/oh-my-posh/ off PATH, which forced
# every consumer to use an absolute path -- a fragile contract that
# broke when the dev-overlay (live install) used /usr/bin (the standard
# location). mios-prompt.sh now resolves via `command -v` with a
# fallback to the legacy libexec path for back-compat.
OMP_BIN=/usr/bin/oh-my-posh

log "[38-oh-my-posh] resolving latest release tag from upstream"
OMP_TAG=$( (scurl -s https://api.github.com/repos/JanDeDobbeleer/oh-my-posh/releases/latest \
            | grep -Po '"tag_name": "\K.*?(?=")') 2>/dev/null || true)
if [[ -z "$OMP_TAG" ]]; then
    warn "[38-oh-my-posh] api.github.com release lookup returned empty -- skipping"
    exit 0
fi
record_version oh-my-posh "$OMP_TAG" \
    "https://github.com/JanDeDobbeleer/oh-my-posh/releases/tag/${OMP_TAG}"

ARCH="$(uname -m)"
case "$ARCH" in
    x86_64)  ASSET="posh-linux-amd64" ;;
    aarch64) ASSET="posh-linux-arm64" ;;
    *)
        warn "[38-oh-my-posh] unsupported arch '${ARCH}' -- skipping"
        exit 0
        ;;
esac

URL="https://github.com/JanDeDobbeleer/oh-my-posh/releases/download/${OMP_TAG}/${ASSET}"
log "[38-oh-my-posh] fetching ${URL}"
if ! scurl -fsL --max-time 60 "$URL" -o "${OMP_BIN}.new"; then
    warn "[38-oh-my-posh] download failed -- prompt falls back to bash default"
    rm -f "${OMP_BIN}.new"
    exit 0
fi

# Optional: SHA256 sidecar verification. Upstream publishes
# checksums.txt next to the binaries; if it's reachable, verify.
if scurl -fsL --max-time 30 \
        "https://github.com/JanDeDobbeleer/oh-my-posh/releases/download/${OMP_TAG}/checksums.txt" \
        -o /tmp/omp-checksums.txt 2>/dev/null; then
    expected="$(grep "${ASSET}\$" /tmp/omp-checksums.txt | awk '{print $1}')"
    if [[ -n "$expected" ]]; then
        actual="$(sha256sum "${OMP_BIN}.new" | awk '{print $1}')"
        if [[ "$expected" == "$actual" ]]; then
            log "[38-oh-my-posh] [ok] sha256 verified"
        else
            warn "[38-oh-my-posh] sha256 mismatch -- aborting"
            rm -f "${OMP_BIN}.new" /tmp/omp-checksums.txt
            exit 1
        fi
    fi
    rm -f /tmp/omp-checksums.txt
fi

mv -f "${OMP_BIN}.new" "${OMP_BIN}"
chmod 0755 "${OMP_BIN}"
log "[38-oh-my-posh] installed at ${OMP_BIN} (${OMP_TAG})"
