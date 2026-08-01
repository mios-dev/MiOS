#!/bin/bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Installs the Oh-My-Posh shell prompt customizer by fetching the latest Go binary from GitHub, placing it in /usr/bin/oh-my-posh for system-wide use by mios-prompt.sh.
# AI-related: mios-prompt.sh, /usr/libexec/mios/oh-my-posh/, mios-prompt
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"

OMP_BIN=/usr/bin/oh-my-posh

mios_log "Resolving latest release tag from upstream"
OMP_TAG=$( (scurl -s https://api.github.com/repos/JanDeDobbeleer/oh-my-posh/releases/latest \
            | grep -Po '"tag_name": "\K.*?(?=")') 2>/dev/null || true)
if [[ -z "$OMP_TAG" ]]; then
    mios_warn "api.github.com release lookup returned empty -- skipping"
    exit 0
fi
record_version oh-my-posh "$OMP_TAG" \
    "https://github.com/JanDeDobbeleer/oh-my-posh/releases/tag/${OMP_TAG}"

ARCH="$(uname -m)"
case "$ARCH" in
    x86_64)  ASSET="posh-linux-amd64" ;;
    aarch64) ASSET="posh-linux-arm64" ;;
    *)
        mios_warn "unsupported arch '${ARCH}' -- skipping"
        exit 0
        ;;
esac

URL="https://github.com/JanDeDobbeleer/oh-my-posh/releases/download/${OMP_TAG}/${ASSET}"
mios_log "Fetching ${URL}"
if ! scurl -fsL --max-time 60 "$URL" -o "${OMP_BIN}.new"; then
    mios_warn "download failed -- prompt falls back to bash default"
    rm -f "${OMP_BIN}.new"
    exit 0
fi

if scurl -fsL --max-time 30 \
        "https://github.com/JanDeDobbeleer/oh-my-posh/releases/download/${OMP_TAG}/checksums.txt" \
        -o /tmp/omp-checksums.txt 2>/dev/null; then
    expected="$(grep "${ASSET}\$" /tmp/omp-checksums.txt | awk '{print $1}')"
    if [[ -n "$expected" ]]; then
        actual="$(sha256sum "${OMP_BIN}.new" | awk '{print $1}')"
        if [[ "$expected" == "$actual" ]]; then
            mios_ok "sha256 verified"
        else
            mios_warn "sha256 mismatch -- aborting"
            rm -f "${OMP_BIN}.new" /tmp/omp-checksums.txt
            exit 1
        fi
    fi
    rm -f /tmp/omp-checksums.txt
fi

mv -f "${OMP_BIN}.new" "${OMP_BIN}"
chmod 0755 "${OMP_BIN}"

sbom_dir="/usr/share/mios/artifacts/sbom"
mkdir -p "$sbom_dir"
sha=""
if command -v sha256sum >/dev/null 2>&1; then
    sha="$(sha256sum "${OMP_BIN}" | awk '{print $1}')"
fi
printf '%s\t%s\t%s\n' "oh-my-posh" "${OMP_TAG}" "${sha:-unknown}" >> "${sbom_dir}/binaries.tsv"

mios_ok "installed at ${OMP_BIN} (${OMP_TAG})"
