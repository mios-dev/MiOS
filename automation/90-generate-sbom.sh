#!/bin/bash
# AI-hint: Executes the Syft tool to scan the root filesystem and generate CycloneDX and SPDX manifest files in ${MIOS_USR_DIR}/artifacts/sbom for compliance and inventory tracking.
# AI-related: mios-sbom
# 'MiOS' v0.2.4  90-generate-sbom: Generate Software Bill of Materials (SBOM)
# Uses Syft to generate CycloneDX and SPDX manifests for the final image.
set -euo pipefail

# shellcheck source=lib/packages.sh
source "$(dirname "$0")/lib/packages.sh"
source "$(dirname "$0")/lib/common.sh"

echo "[90-generate-sbom] Starting SBOM generation..."

ARTIFACT_DIR="${MIOS_USR_DIR}/artifacts/sbom"
mkdir -p "$ARTIFACT_DIR"

if ! command -v syft &> /dev/null; then
    echo "[90-generate-sbom] WARN: Syft not found. Attempting to install via official script..."
    if curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin; then
        echo "[90-generate-sbom] Syft installed successfully."
    else
        echo "[90-generate-sbom] WARN: syft installation failed -- skipping SBOM generation (non-fatal)."
        exit 0
    fi
fi

VERSION=$(cat /ctx/VERSION 2>/dev/null || grep -m1 -E '^[[:space:]]*mios_version' "${MIOS_TOML:-/ctx/usr/share/mios/mios.toml}" 2>/dev/null | sed -E 's/[^"]*"([^"]*)".*/\1/')

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
