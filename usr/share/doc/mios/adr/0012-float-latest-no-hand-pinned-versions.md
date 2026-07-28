<!-- AI-hint: SSOT artifact/package/model refs carry floating intent (:latest or newest version) only; all concrete versions and checksums are resolved at build time and recorded in the SBOM — never hand-pinned in SSOT or build scripts. -->
<!-- AI-related: usr/share/mios/mios.toml, automation/90-generate-sbom.sh, automation/38-drift-checks.sh, usr/share/doc/mios/adr/0003-sbom-not-hardcode.md -->
---
adr: 0012
title: "Float-latest: no hand-pinned versions anywhere"
status: accepted
date: 2026-07-28
deciders: [operator, ai-pair]
tags: [float-latest, sbom, provenance, reproducibility, no-hardcode, supply-chain]
laws: [7, 8, 12]
ssot_keys: [image.sidecars, build.bake, build.bake_groups, ai.bake_models]
related_ws: [WS-SBOM, WS-MIOSSYS, WS-RELTOP]
supersedes: []
superseded_by: []
---

# ADR-0012: Float-latest — no hand-pinned versions anywhere

## Status

Accepted — 2026-07-28. Generalizes ADR-0003 across all artifact classes (RPM/package versions, model weights, git-clone refs, base-image tags).

## Context

In traditional system management, developers and operators frequently hardcode explicit version numbers (e.g., `python3-3.11.2`, `vllm==0.4.2`, specific commit SHA hashes for git clones) into configuration files and build scripts under the assumption that manual pinning guarantees reproducibility.

In MiOS, this practice violates core architectural principles:
1. **Law 7 (NO-HARDCODE)**: Hardcoding static version numbers in scripts or configuration files creates maintenance debt and prevents automated dependency updates.
2. **Law 8 (SSOT-PROJECTION)**: Hardcoded versions duplicate data that should be resolved dynamically from the SSOT or upstream repositories during build time.
3. **Law 12 (BAKE-NOT-FETCH)**: System components and model weights are baked into the OCI bootc image at build time. The build process must pull the newest upstream packages globally, resolve their exact versions, and record the output in the Software Bill of Materials (SBOM).

ADR-0003 established that container image digests (`@sha256:…`) must not be hardcoded in `mios.toml` and are instead resolved at build time. However, a general decision governing all other artifact classes (system packages, Python wheels, git repos, AI model weights) was noted as a required follow-up.

## Decision

Adopt the **Float-Latest Principle** across all artifact classes in the MiOS ecosystem:

1. **Floating Intent in SSOT**: Configuration files (`mios.toml`) and build scripts MUST express version intent as floating refs (e.g., `:latest`, `:main`, `:master`, or unpinned package names like `podman`, `vllm`).
2. **Build-Time Resolution**: The build engine resolves the latest available upstream version/hash at build time.
3. **Provenance via SBOM**: Exact version numbers, commit SHAs, and content hashes are recorded in the generated SBOM artifacts (`usr/share/mios/artifacts/sbom/*`) during the build pass.
4. **Reproducibility via Baked Artifacts**: Reproducibility is achieved through the baked, immutable OCI image and the SBOM manifest, NOT through manual source code pinning.

## Rationale

- **Zero-Maintenance Upgrades**: Base packages and AI components automatically upgrade to the latest secure versions upon rebuilding the image.
- **Single Source of Truth**: Upstream repositories remain the authoritative source for software updates, while the build-generated SBOM serves as the immutable audit trail.
- **Elimination of Version Drift**: Prevents mismatch between declared hardcoded versions and actual installed package dependencies.

## Alternatives

- **Manual Pinning**: Hardcode exact version strings in `mios.toml` and build scripts. *Rejected*: Causes version rot, breaks automatic security patches, and violates Law 7 (NO-HARDCODE).
- **Lockfiles in Repository**: Commit lockfiles (e.g., `Pipfile.lock`, `package-lock.json`) into the Git repository. *Rejected*: Creates unnecessary Git churn and manual update cycles for an immutable OS image.

## Consequences

### Positive
- All system components build against the latest stable upstream releases.
- Supply chain auditability is guaranteed by the generated SBOM.
- Eliminates manual version updating across build scripts and SSOT definitions.

### Negative
- Upstream breaking changes could break image builds if upstream introduces regressions (mitigated by automated drift gates and CI build tests).

## Implementation

- All package installation scripts (`automation/*.sh`) use unpinned package names.
- Git clone commands use floating branch tracking or release tags unless explicitly overridden by build flags.
- SBOM generator (`automation/90-generate-sbom.sh`) captures all resolved package versions and SHA-256 digests.

## References

- [ADR-0003: SBOM-not-hardcode — digests are build-resolved provenance](file:///C:/MiOS/usr/share/doc/mios/adr/0003-sbom-not-hardcode.md)
- `usr/share/mios/mios.toml`
- `automation/90-generate-sbom.sh`
