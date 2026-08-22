<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/bin/bash MIOS_APPLY_CLASS=bake-only AI-hint: Runs Syft to...

!/bin/bash
MIOS_APPLY_CLASS=bake-only
AI-hint: Runs Syft to generate CycloneDX + SPDX SBOM manifests into ${MIOS_USR_DIR}/artifacts/sbom. DEGRADE-OPEN: SBOM is build PROVENANCE, never a build-critical gate -- this script must NEVER fail the image build (always exits 0).
AI-related: mios-sbom, usr/libexec/mios/mios-bake-group (records bound-image digests -> the SBOM provenance), ADR-0003 (SBOM-not-hardcode)

<!-- mios-src:66712f57ae16 from automation/90-generate-sbom.sh:1-4 -->

