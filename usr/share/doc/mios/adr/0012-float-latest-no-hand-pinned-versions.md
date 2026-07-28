<!-- AI-hint: Float-latest / no-hand-pinned-version principle: SSOT carries version intent (:latest/newest); build resolves and records exact provenance in SBOM. -->
<!-- AI-related: usr/share/mios/mios.toml [image.sidecars], [build.bake], [build.bake_groups], [ai.bake_models], automation/90-generate-sbom.sh -->
---
adr: 0012
title: "Float-latest: no hand-pinned versions across any artifact class"
status: accepted
date: 2026-07-28
deciders: [operator, ai-pair]
tags: [float-latest, sbom, provenance, reproducibility, no-hand-pin, supply-chain]
laws: [7, 8, 12]
ssot_keys: [image.sidecars, build.bake, build.bake_groups, ai.bake_models]
related_ws: [WS-SBOM, WS-MIOSSYS, WS-RELTOP]
supersedes: []
superseded_by: []
---

# ADR-0012: Float-latest — no hand-pinned versions across any artifact class

## Status

Accepted — 2026-07-28. Generalizes the decision in ADR-0003 across all artifact classes (RPM packages, git clone references, model weights, and base image tags).

## Context

In MiOS, the single source of truth is `usr/share/mios/mios.toml`. Architectural Law 7 (NO-HARDCODE) mandates that every configurable value resolves through the SSOT, Law 8 (SSOT-PROJECTION) mandates that all derived files are generated and drift-gated, and Law 12 (BAKE-NOT-FETCH) specifies that service dependencies and assets are baked into the immutable image.

ADR-0003 addressed container image digests, deciding that hand-written `@sha256:…` pins inside `mios.toml` duplicate SBOM provenance data and cause unnecessary drift. However, the underlying operator principle — **"NO hand-pinned versions anywhere; everything floats latest at intent, resolved at build and recorded in the SBOM"** — needed to be explicitly formalized across all artifact classes.

Without a unified principle, different layers of the codebase used conflicting strategies:
- Git clone steps occasionally hardcoded commit SHAs in script bodies.
- Package installation specifications sometimes included static version numbers.
- Model weight download paths mixed explicit tag refs with unpinned floating URLs.

## Decision

Adopt the **Float-Latest Principle** across all artifact classes:

1. **Intent in SSOT is Floating / Floating-Latest**:
   - `mios.toml` specifies *version intent* (e.g., `:latest`, `newest`, or high-level tag selectors).
   - No hand-pinned SHA digests, git commit hashes, or rigid package version pins inside `mios.toml` or build scripts unless required by an explicit upstream breaking-change gate.

2. **Resolution & Provenance at Build Time**:
   - The build process (e.g., `automation/build-mios.sh`, `automation/90-generate-sbom.sh`) resolves floating intent into concrete, verifiable artifacts.
   - Exact SHAs, RPM EVRs, OCI image digests, and git commit IDs are recorded into the baked Software Bill of Materials (SBOM) and `manifest.json`.

3. **Reproducibility Definition**:
   - Reproducibility in MiOS is defined as the **baked OCI manifest plus the generated SBOM**, rather than static hand-written literals in source code.

## Rationale

- Eliminates manual churn and false drift-gate failures when upstream dependencies release minor updates.
- Maintains supply-chain transparency by making the build-time SBOM the single authoritative record of exact versions.
- Ensures consistent adherence to Law 7 (NO-HARDCODE) and Law 8 (SSOT-PROJECTION) across the entire OS assembly pipeline.

## Alternatives

- **Hand-pinning all versions in SSOT**: High maintenance overhead; leads to stale dependencies and brittle builds.
- **Pinning only in external lockfiles**: Introduces secondary sources of truth outside `mios.toml`, violating Law 8.

## Consequences

### Positive
- Unified version management rule across images, packages, git repositories, and AI models.
- Builds automatically pick up upstream bug fixes and security updates at bake time.
- Clear separation between human intent (`:latest`) and machine provenance (`sha256:...`).

### Negative
- Requires robust CI smoke tests (`tests/bake-smoke.sh`, drift gates) to catch upstream regressions at build time.

## Implementation

- Enforced via drift checks (e.g., `check_containerfile_pinned_clones`).
- Rendered into SBOM via `automation/90-generate-sbom.sh`.

## References

- [ADR-0003: SBOM-not-hardcode](file:///C:/MiOS/usr/share/doc/mios/adr/0003-sbom-not-hardcode.md)
- [Architectural Laws 7, 8, 12](file:///C:/MiOS/usr/share/mios/mios.toml)
