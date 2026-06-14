<!-- AI-hint: Documentation for Sigstore/Cosign keyless signing and verification — the specific CLI commands and OIDC identity that validate MiOS OCI container images and their attestations before bootc deploys them. Explains why a signed image is the unit of trust in an immutable, self-replicating OS (Architectural Law 3, BOUND-IMAGES).
     AI-related: mios-ci, mios-dev -->
# Cosign / Sigstore — Keyless Image Signing

## Purpose in MiOS

MiOS is one OCI image: the whole immutable Fedora-bootc workstation — desktop,
GPU wiring, virtualization, cluster path, **and** the local agentic AI stack —
ships as a single signed artifact (`ghcr.io/mios-dev/mios:latest`). Because
**the image *is* the deployed system root**, the image is also the unit of
trust. A host does not assemble MiOS from packages; it pulls one ref and runs
it via `bootc switch`/`bootc upgrade`, and it can `bootc rollback` to the prior
ref like a Ctrl-Z. That self-replicating "the OS reproduces itself from one
rebuildable image" property only holds if every host can prove the image it
pulled is the one CI actually built.

This doc covers the mechanism that closes that loop: **cosign keyless signing**.
It supports Architectural Law 3 (BOUND-IMAGES — every Quadlet image, including
the AI containers, ships *inside* the host image) by extending the same
"trust the image, not the runtime pull" discipline up to the top-level OS image
itself. Verify before you boot it.

> CI signs **every** push with cosign keyless via GitHub Actions OIDC
> (`.github/workflows/mios-ci.yml`, the `Cosign keyless sign` step) — including
> the `:latest` tag from `main`, not just `v*` release tags.
> Source: the verbatim verify command lives in
> `usr/share/doc/mios/guides/deploy.md` §Image verification.

## Project

- Repo: <https://github.com/sigstore/cosign>
- What is Sigstore: <https://sbomify.com/2024/08/12/what-is-sigstore/>
- Verification walkthrough: <https://secure-pipelines.com/ci-cd-security/signing-verifying-container-images-sigstore-cosign/>
- Attestation walkthrough: <https://www.augmentedmind.de/2025/03/02/docker-image-signing-with-cosign/>

CI installs cosign via the upstream `sigstore/cosign-installer@v3` action;
the build job carries `permissions: id-token: write` so the keyless OIDC
exchange below can run.

## Keyless flow

```
ephemeral keypair (in-memory)
  → OIDC token (from GitHub Actions: token.actions.githubusercontent.com)
  → Fulcio CA issues short-lived (~10 min) X.509 cert binding identity
  → image digest signed
  → signature uploaded to Rekor transparency log
  → signature pushed to OCI registry as a companion artifact (`<digest>.sig`)
```

No long-lived signing key ever touches disk. Identity is the GitHub
Actions workflow itself. In CI the signing step runs with
`COSIGN_EXPERIMENTAL=1` and `cosign sign --yes` over every tag the push
produced (`:latest`, the bare `VERSION`, the semver tag on `v*`, and the
`VERSION-TIMESTAMP-SHA` build tag).

## MiOS verification

```bash
cosign verify \
  --certificate-identity-regexp="https://github.com/mios-dev/mios" \
  --certificate-oidc-issuer="https://token.actions.githubusercontent.com" \
  ghcr.io/mios-dev/mios:latest
```

This is the verbatim verification command from
`usr/share/doc/mios/guides/deploy.md` §Image verification. The
`--certificate-identity-regexp` matches any `mios-dev/mios*` workflow path
(CI's `IMAGE_NAME` is `mios-dev/mios`); tighten in production to the specific
`.github/workflows/mios-ci.yml@refs/tags/v*` if you want pinned trust.

Run this *before* `bootc switch ghcr.io/mios-dev/mios:latest` — the verified
digest is what you then deploy and (if a release misbehaves) roll back from.

## Attestations (SLSA, SBOM, vuln, OpenVEX)

```bash
# Attach an attestation (e.g., SLSA provenance produced by the workflow)
cosign attest \
  --predicate provenance.json \
  --type slsaprovenance \
  ghcr.io/mios-dev/mios:latest

# Verify it
cosign verify-attestation \
  --type slsaprovenance \
  --certificate-identity-regexp="..." \
  --certificate-oidc-issuer="..." \
  ghcr.io/mios-dev/mios:latest
```

Predicate types: `slsaprovenance`, `slsaprovenance1`, `spdxjson`,
`cyclonedx`, `vuln`, `openvex`. MiOS generates its SBOM in
`automation/90-generate-sbom.sh` (Phase-2 sub-phase) with **syft**, emitting
*both* a CycloneDX-JSON manifest (primary, for AI/automation consumers) and an
SPDX tag-value manifest (compliance) into `${MIOS_USR_DIR}/artifacts/sbom`.
The CycloneDX form is the one suited to attaching as a `cyclonedx` predicate.

## Cross-refs

- `usr/share/doc/mios/guides/deploy.md` — bootc Day-2 lifecycle + the canonical
  §Image verification command (the SSOT for the verify invocation above).
- `usr/share/doc/mios/guides/security.md` — full security posture (SELinux,
  fapolicyd, USBGuard, CrowdSec, kernel-lockdown, MOK signing).
- `usr/share/doc/mios/upstream/ghcr.md` — the registry the signed image and its
  `<digest>.sig` companions live in.
- `usr/share/doc/mios/upstream/secureblue.md` — adjacent hardening upstream.
