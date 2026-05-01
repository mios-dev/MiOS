#!/bin/bash
# MiOS v0.2.0  90-generate-sbom: Generate Software Bill of Materials (SBOM)
# Uses Syft to generate CycloneDX and SPDX manifests for the final image.
set -euo pipefail

# shellcheck source=lib/packages.sh
source "$(dirname "$0")/lib/packages.sh"
source "$(dirname "$0")/lib/common.sh"

echo "[90-generate-sbom] Starting SBOM generation..."

ARTIFACT_DIR="/usr/lib/mios/artifacts/sbom"
mkdir -p "$ARTIFACT_DIR"

if ! command -v syft &> /dev/null; then
    echo "[90-generate-sbom] WARN: Syft not found. Attempting to install via PACKAGES.md..."
    install_packages "sbom-tools" || {
        echo "[90-generate-sbom] ERROR: Failed to install Syft. Skipping SBOM generation."
        exit 0 # Non-fatal
    }
fi

VERSION=$(cat /ctx/VERSION 2>/dev/null || echo "v0.2.0")

echo "[90-generate-sbom] Scanning root filesystem..."

# Generate CycloneDX (JSON) - Primary for AI and automation
syft scan dir:/ \
    --output cyclonedx-json \
    --file "${ARTIFACT_DIR}/mios-sbom-${VERSION}.cyclonedx.json" \
    --exclude "/ctx" \
    --exclude "/var/cache"

# Generate SPDX (Tag-Value) - Standard compliance
syft scan dir:/ \
    --output spdx-tag-value \
    --file "${ARTIFACT_DIR}/mios-sbom-${VERSION}.spdx.txt" \
    --exclude "/ctx" \
    --exclude "/var/cache"

echo "[90-generate-sbom] SBOMs generated in ${ARTIFACT_DIR}:"
ls -lh "$ARTIFACT_DIR"

echo "[90-generate-sbom] Done."
