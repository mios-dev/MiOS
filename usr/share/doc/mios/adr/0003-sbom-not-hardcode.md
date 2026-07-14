<!-- AI-hint: SSOT image/artifact refs carry TAG intent only; every sha256 digest / hash / checksum / resolved version is SBOM data resolved+recorded at BUILD, never hand-pinned — read before adding or "fixing" any @sha256 in mios.toml or a Quadlet. -->
<!-- AI-related: usr/share/mios/mios.toml [image.sidecars], usr/libexec/mios/mios-bake-group, /usr/share/mios/artifacts/sbom/bound-images.tsv, automation/90-generate-sbom.sh, automation/15-render-quadlets.sh, automation/38-drift-checks.sh -->
---
adr: 0003
title: "SBOM-not-hardcode: digests are build-resolved provenance"
status: accepted
date: 2026-07-12
deciders: [operator, ai-pair]
tags: [sbom, provenance, reproducibility, security, no-hardcode, supply-chain]
laws: [7, 8, 12]
ssot_keys: [image.sidecars, build.bake_groups, build.bake_group]
related_ws: [WS-SBOM]
supersedes: []
superseded_by: []
---

# ADR-0003: SBOM-not-hardcode — digests are build-resolved provenance

## Status
Accepted — 2026-07-12. DONE for container images (see Consequences); the same
rule extends to other artifact classes (model checksums, package version-hashes)
as PLANNED follow-up.

## Context

MiOS is an immutable bootc/OCI Fedora image whose single source of truth is
`usr/share/mios/mios.toml`. Every operator-tunable value resolves through that
SSOT; a hardcoded constant that belongs in the TOML is a bug (Law 7 NO-HARDCODE),
and any file *derived* from the SSOT must be generated and drift-gated (Law 8
SSOT-PROJECTION). MiOS bakes its whole service fleet into the image (Law 12
BAKE-NOT-FETCH), so identity of every baked artifact is a supply-chain concern.

The **prior convention** was: pin each sidecar image by `@sha256` **in**
`mios.toml [image.sidecars]` "for reproducible builds" (pgvector, searxng,
forge, adguard, open_webui, code_server, and others carried hand-written digests).
The recurring pain that exposed this as wrong is recorded in memory as the
"Quadlet digest drift" problem: a broad `git add` strips the `@sha256` pins from
generated Quadlets, turning the drift-gate red; the manual fix was to regenerate
and stage explicit paths and never `git add -A` (the tree is shared with another
agent). That the pins keep *drifting* out of committed generated files is the
tell — a hand-pinned digest is duplicated SBOM data that can and does diverge from
the resolved reality.

**The operator's emphatic directive (2026-07-12): NO HARDCODES ANYWHERE.**
Specifically for image/artifact identity, a hand-written `@sha256:…` in the SSOT
(a) duplicates SBOM data — the tag `:latest` already appears alongside it, (b)
can drift from the resolved reality, and (c) is a hardcode. The SBOM is the single
provenance record, and reproducibility must come from the SBOM plus the baked OCI
manifest — not from a literal in the SSOT.

## Decision

Split *intent* from *identity*:

1. **SSOT refs carry the TAG/version intent only.** In `mios.toml [image.sidecars]`
   an entry is `registry/repo:latest` (or `registry/repo:<version>`), **no
   digest**. `:latest` means "track newest globally" (MiOS's latest-packages
   convention); a bare version tag is fine. A hand-written `@sha256:…` is **not**
   allowed.
2. **All `sha256@…` digests, GPG/checksum hashes, recorded checksums, and
   resolved version numbers are SBOM data** — resolved and recorded **at build
   time**, never hand-maintained literals in `mios.toml`, Quadlets, or scripts.
3. **Reproducibility = the SBOM + the baked OCI manifest**, not a hardcoded digest
   in the SSOT.

Concretely, the reconciled model keeps runtime pinning **without** SSOT hardcodes:
- SSOT `[image.sidecars]` holds `registry/repo:latest` (no digest).
- The **build** resolves each `:latest` → concrete digest at pull time and
  **records it in the SBOM** (`usr/libexec/mios/mios-bake-group` appends the
  resolved manifest digest to `/usr/share/mios/artifacts/sbom/bound-images.tsv`;
  `automation/90-generate-sbom.sh` generates the full SBOM via Syft). Where a
  reproducible *runtime* pin is wanted, the build pins the resolved digest **into
  the rendered Quadlets** (`automation/15-render-quadlets.sh` / a resolve step) —
  the digest is a build output, not a hand-edited input.
- The rendered-Quadlet digest-drift check then validates the **build-resolved**
  digests, not SSOT-hand-pinned ones.

This **reverses** the older "pin `@sha256` in `[image.sidecars]`" convention. The
pgvector/searxng/forge/adguard/open_webui/code_server entries that carry
hand-pinned digests are now the hardcodes to strip.

## Rationale

- **Law 7 (NO-HARDCODE).** A digest in the SSOT is a literal that belongs to the
  build's provenance output, not to operator-tunable config. Removing it removes a
  class of hardcode.
- **Law 8 (SSOT-PROJECTION).** The SBOM and any digest-pinned rendered Quadlet are
  *derived* surfaces, emitted by a generator and guarded by a regenerate-and-diff
  drift-check. A hand-edited derived digest is a build failure — which is exactly
  the drift that kept turning the gate red.
- **Law 12 (BAKE-NOT-FETCH).** Bake identity must be captured *by the bake*. The
  SBOM records the concrete identity of what was actually baked; the OCI manifest
  is the reproducibility anchor.
- **Single provenance record.** One place (the SBOM) answers "what exactly is in
  this image," content-addressed. Duplicating that into the SSOT can only drift.
- **Upstream precedent.** Syft/SPDX/CycloneDX SBOMs and OCI image manifests are
  the industry provenance surfaces; content-addressed digests are recorded, not
  authored. This mirrors how `bootc`/OCI already pins the base by manifest.

## Alternatives considered

- **Keep `@sha256` pins in `[image.sidecars]` (status quo).** Rejected: it is a
  hardcode, duplicates SBOM data, and demonstrably drifts out of committed
  generated files (the "never `git add -A`" workaround is a symptom, not a fix).
- **Drop pinning entirely, rely on `:latest` at runtime.** Rejected: loses
  reproducibility of what a given built image actually runs. The build must still
  *resolve* and *record* the digest; it just must not be authored by hand.
- **Pin digests only in Quadlets, not the SSOT, but hand-maintain them there.**
  Rejected: still a hardcode, still drifts. The Quadlet digest must be
  *build-resolved* and drift-gated, not hand-written.

## Consequences

Positive:
- The SSOT expresses intent (`:latest` / version) and stays stable across upstream
  bumps; identity is captured fresh every build.
- The "Quadlet digest drift" git-hygiene problem becomes **moot** once digests are
  build-resolved rather than committed — there is no hand-pinned digest to strip.
- One provenance record (the SBOM) instead of two disagreeing copies.

Negative / honest costs:
- The build must reliably resolve + record digests (network + a resolve step);
  `mios-bake-group` already retries pulls ×3 and records `unknown` on failure — the
  SBOM must be inspected, not assumed complete.
- Air-gapped/offline reproducibility now depends on shipping the SBOM + the baked
  store together, not on reading a digest out of the SSOT.

Status — **DONE (WS-SBOM, images):**
- 12 hand-pinned digests stripped from `[image.sidecars]`.
- 27 Quadlets regenerated digest-free.
- The bound-image bake records resolved digests to the SBOM at pull time
  (`usr/libexec/mios/mios-bake-group` writes `bound-images.tsv`).
- The drift-gate is green against build-resolved digests.

**PLANNED:** apply the same rule beyond images — llama.cpp model checksums,
package version-hashes, and any other recorded checksum become SBOM data resolved
at build (the `automation/38-llamacpp-prep.sh` checksum mold is the pattern), with
no hand-maintained literals in the SSOT.

## Implementation

Current tree (DONE):
- `C:\MiOS\usr\share\mios\mios.toml [image.sidecars]` — entries carry
  `registry/repo:latest` (or `:version`), no `@sha256`.
- `C:\MiOS\usr\libexec\mios\mios-bake-group` — after each successful pull, runs
  `podman image inspect --format '{{.Digest}}'` and appends
  `<image>\t<digest>\t<group>` to `/usr/share/mios/artifacts/sbom/bound-images.tsv`
  (`SBOM_DIR` = `/usr/share/mios/artifacts/sbom`). The header comment states the
  rule verbatim: "Digests are SBOM data (build-time-recorded), NEVER hardcoded in
  the SSOT."
- `C:\MiOS\automation\90-generate-sbom.sh` — Syft-generated SBOM for the full image.
- `C:\MiOS\automation\15-render-quadlets.sh` — renders Quadlet `Image=` from SSOT;
  the resolve/pin-into-rendered-Quadlet step is where a reproducible runtime digest
  is applied as a build output.
- `C:\MiOS\automation\38-drift-checks.sh` — the rendered-Quadlet digest-drift check
  validates build-resolved digests.

Cross-references: ADR-0002 (consolidation is the moment to digest-lock the floating
`:latest` ingredients — as SBOM records, never SSOT literals) and ADR-0001 (the
bake plan feeds `mios-bake-group`, which is where digests are recorded).

## References

- Syft (SBOM generation): <https://github.com/anchore/syft>
- SPDX: <https://spdx.dev/> · CycloneDX: <https://cyclonedx.org/>
- OCI image manifest / content-addressable digests:
  <https://github.com/opencontainers/image-spec/blob/main/manifest.md>
- containers-storage `pull_options` (`convert_images`, `enable_partial_images`):
  <https://github.com/containers/storage/blob/main/docs/containers-storage.conf.5.md>
- MiOS memory: "Quadlet digest drift" (the git-hygiene symptom this decision retires).
- Sibling ADRs: ADR-0001, ADR-0002.
