#!/bin/bash
# MIOS_APPLY_CLASS=bake-only
# AI-hint: Runs Syft to generate CycloneDX + SPDX SBOM manifests into ${MIOS_USR_DIR}/artifacts/sbom. DEGRADE-OPEN: SBOM is build PROVENANCE, never a build-critical gate -- this script must NEVER fail the image build (always exits 0).
# AI-related: mios-sbom, usr/libexec/mios/mios-bake-group (records bound-image digests -> the SBOM provenance), ADR-0003 (SBOM-not-hardcode)
# 90-generate-sbom: Generate the Software Bill of Materials (Syft).
#
# WHY degrade-open (NOT `set -e`): SBOM generation is best-effort provenance. A
# missing syft, a no-egress build, an unbound legacy var, or a syft scan hiccup
# must WARN and continue -- never kill a 17-minute bake (this was a FATAL exit=1
# regression). Reproducibility is still guaranteed by the baked OCI manifest +
# usr/libexec/mios/mios-bake-group's bound-images.tsv (ADR-0003); the Syft SBOM
# is the human/tooling-facing inventory on top, and it degrades open.
set -uo pipefail   # deliberately NOT -e

for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

# lib sources are best-effort: a rename in the naming campaign must not brick SBOM.
source "$(dirname "$0")/lib/packages.sh" 2>/dev/null || true
source "$(dirname "$0")/lib/common.sh"   2>/dev/null || true

mios_log "SBOM generation (degrade-open)"

# MIOS_USR_DIR may be unset in some build contexts -> default it (was an unbound
# 'set -u' fatal). Canonical vendor dir is /usr/share/mios.
ARTIFACT_DIR="${MIOS_USR_DIR:-/usr/share/mios}/artifacts/sbom"
if ! mkdir -p "$ARTIFACT_DIR"; then
    mios_warn "cannot create $ARTIFACT_DIR -- skipping SBOM (non-fatal)"
    exit 0
fi

# Ensure syft is present. Prefer an already-installed syft (baked via packages);
# fall back to the official installer IFF the build has egress. No egress / no
# syft -> WARN + skip (degrade-open; the bound-images.tsv provenance still exists).
if ! command -v syft &>/dev/null; then
    SYFT_PIN=$(python3 -c "import sys; sys.path.insert(0, '/usr/lib/mios'); import mios_toml; print(mios_toml.get('build.bake_refs', 'syft') or '')" 2>/dev/null)
    if [ -z "$SYFT_PIN" ]; then
        SYFT_PIN=$(grep -m1 -E '^[[:space:]]*syft[[:space:]]*=' "${MIOS_TOML:-/usr/share/mios/mios.toml}" 2>/dev/null | cut -d'"' -f2 || true)
    fi
    SYFT_PIN="${SYFT_PIN:-v1.19.0}"
    mios_log "syft not found; official install (version=${SYFT_PIN}, needs egress)"
    curl -sSfL --retry 5 --retry-delay 3 --retry-all-errors --connect-timeout 20 https://raw.githubusercontent.com/anchore/syft/main/install.sh 2>/dev/null \
        | sh -s -- -b /usr/local/bin "${SYFT_PIN}" >/dev/null 2>&1 || true
fi
if ! command -v syft &>/dev/null; then
    mios_warn "syft unavailable (no egress or install failed) -- skipping SBOM (non-fatal)"
    exit 0
fi

# Version label -- never let this line fail the script (pipefail-safe).
VERSION="$(cat /ctx/VERSION 2>/dev/null || true)"
if [ -z "$VERSION" ]; then
    VERSION="$(grep -m1 -E '^[[:space:]]*mios_version' "${MIOS_TOML:-/ctx/usr/share/mios/mios.toml}" 2>/dev/null \
        | sed -E 's/[^"]*"([^"]*)".*/\1/' 2>/dev/null || true)"
fi
VERSION="${VERSION:-unknown}"

mios_log "scanning root filesystem with syft (version=${VERSION})"

# CycloneDX (primary, for AI/automation) + SPDX (compliance). Each is non-fatal.
syft scan dir:/ --source-name mios --source-version "${VERSION}" --output "cyclonedx-json=${ARTIFACT_DIR}/mios-sbom-${VERSION}.cyclonedx.json" \
    --exclude "./ctx/**" --exclude "./var/cache/**" \
    || mios_warn "CycloneDX SBOM generation failed (non-fatal)"

syft scan dir:/ --source-name mios --source-version "${VERSION}" --output "spdx-tag-value=${ARTIFACT_DIR}/mios-sbom-${VERSION}.spdx.txt" \
    --exclude "./ctx/**" --exclude "./var/cache/**" \
    || mios_warn "SPDX SBOM generation failed (non-fatal)"

mios_log "SBOM artifacts in ${ARTIFACT_DIR}:"
ls -lh "$ARTIFACT_DIR" 2>/dev/null || true

mios_ok "done (degrade-open; SBOM is provenance, never a build gate)"
exit 0
