<!-- AI-hint: ADR 0004: Version Floating, Image Sidecars, and Offline Vendoring Policy. MiOS requires reproducible builds while supporting floating upstream images and dependencies where appropriate. Certain services (such as `rancher/k3s`) are vendored offline for air-gapped installation and require explicit SSOT ve
     AI-related: usr/share/mios/mios.toml, docs/adr/, AGY-TASKS.md -->
# ADR 0004: Version Floating, Image Sidecars, and Offline Vendoring Policy

## Context
MiOS requires reproducible builds while supporting floating upstream images and dependencies where appropriate.
Certain services (such as `rancher/k3s`) are vendored offline for air-gapped installation and require explicit SSOT version tracking, whereas registry-pulled sidecars express `:latest` (or floating major version) intent.

## Decision
1. **Dynamic Image Floating**: Sidecars pulled dynamically at runtime use floating tags (e.g., `:latest` or `:v19`) in `mios.toml [image.sidecars]`. Resolved `@sha256` digests are recorded into the SBOM manifest at build time (`automation/90-generate-sbom.sh` / `MiOS-SBOM.csv`).
2. **Offline Vendored Sidecars Exception**: Components required for offline bootstrap (such as `rancher/k3s`) pin exact upstream tags in `[image.sidecars]` and `[versions]`. Any version bump flows through SSOT (`mios.toml`) -> offline re-vendoring -> build manifest update.
3. **No Hand-Typed Digests**: No `@sha256:` hashes are hand-pinned in `mios.toml`; digests are strictly resolved during the OCI build step.

## Status
Accepted (2026-08-02).
