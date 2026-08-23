#!/bin/bash
# MIOS_APPLY_CLASS=bake-only
# AI-hint: Runs Syft to generate CycloneDX + SPDX SBOM manifests into ${MIOS_USR_DIR}/artifacts/sbom.
# AI-doc: usr/share/doc/mios/manual/automation.md
set -uo pipefail   # deliberately NOT -e

for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

source "$(dirname "$0")/lib/packages.sh" 2>/dev/null || true
source "$(dirname "$0")/lib/common.sh"   2>/dev/null || true

mios_log "SBOM generation"

# MIOS_USR_DIR may be unset in some build contexts -> default it (was an unbound
ARTIFACT_DIR="${MIOS_USR_DIR:-/usr/share/mios}/artifacts/sbom"
if ! mkdir -p "$ARTIFACT_DIR"; then
    mios_warn "Cannot create $ARTIFACT_DIR"
    exit 0
fi

if ! command -v syft &>/dev/null; then
    SYFT_PIN=$(python3 -c "import sys; sys.path.insert(0, '/usr/lib/mios'); import mios_toml; print(mios_toml.get('build.bake_refs', 'syft') or '')" 2>/dev/null)
    if [ -z "$SYFT_PIN" ]; then
        SYFT_PIN=$(grep -m1 -E '^[[:space:]]*syft[[:space:]]*=' "${MIOS_TOML:-/usr/share/mios/mios.toml}" 2>/dev/null | cut -d'"' -f2 || true)
    fi
    SYFT_PIN="${SYFT_PIN:-v1.19.0}"
    mios_log "Syft not found; official install"
    curl -sSfL --retry 5 --retry-delay 3 --retry-all-errors --connect-timeout 20 https://raw.githubusercontent.com/anchore/syft/main/install.sh 2>/dev/null \
        | sh -s -- -b /usr/local/bin "${SYFT_PIN}" >/dev/null 2>&1 || true
fi
if ! command -v syft &>/dev/null; then
    mios_warn "Syft unavailable"
    exit 0
fi

VERSION="$(cat /ctx/VERSION 2>/dev/null || true)"
if [ -z "$VERSION" ]; then
    VERSION="$(grep -m1 -E '^[[:space:]]*mios_version' "${MIOS_TOML:-/ctx/usr/share/mios/mios.toml}" 2>/dev/null \
        | sed -E 's/[^"]*"([^"]*)".*/\1/' 2>/dev/null || true)"
fi
VERSION="${VERSION:-unknown}"

mios_log "Scanning root filesystem with syft"

syft scan dir:/ --source-name mios --source-version "${VERSION}" --output "cyclonedx-json=${ARTIFACT_DIR}/mios-sbom-${VERSION}.cyclonedx.json" \
    --exclude "./ctx/**" --exclude "./var/cache/**" \
    || mios_warn "CycloneDX SBOM generation failed"

syft scan dir:/ --source-name mios --source-version "${VERSION}" --output "spdx-tag-value=${ARTIFACT_DIR}/mios-sbom-${VERSION}.spdx.txt" \
    --exclude "./ctx/**" --exclude "./var/cache/**" \
    || mios_warn "SPDX SBOM generation failed"

mios_log "SBOM artifacts in ${ARTIFACT_DIR}:"
ls -lh "$ARTIFACT_DIR" 2>/dev/null || true

mios_ok "Done"
exit 0
