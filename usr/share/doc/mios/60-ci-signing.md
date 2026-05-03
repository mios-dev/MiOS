# CI, Cosign Keyless Signing, SBOM, GHCR

> Source: `.github/workflows/mios-ci.yml`, `SECURITY.md` §Image-signing,
> `SELF-BUILD.md`, `ENGINEERING.md` §Toolchain.

## CI workflow shape (`.github/workflows/mios-ci.yml`)

On every tag push and every push to `main`:

1. **Lint** -- `hadolint` on `Containerfile`, `shellcheck` on every
   numbered phase script (SC2038 fatal), TOML validation (every TOML
   under `usr/lib/bootc/kargs.d/`, `config/artifacts/`).
2. **Build** -- `podman build` with the same `--build-arg` flags as
   `just build`. The `Containerfile`'s final RUN is `bootc container
   lint`, so build success implies lint success.
3. **Rechunk** (tag pushes only) -- `bootc-base-imagectl rechunk
   --max-layers 67` for optimized Day-2 deltas.
4. **SBOM** -- `automation/90-generate-sbom.sh` runs `anchore/syft` to
   emit a CycloneDX-JSON SBOM at `artifacts/sbom/mios-sbom.json`.
5. **Sign** -- `cosign sign --yes` keyless via GitHub Actions OIDC.
6. **Push** -- push to `ghcr.io/mios-dev/mios:<tag>` and (on `main`)
   `:latest`.
7. **Verify** -- sanity `cosign verify` against the freshly-pushed image
   before marking the workflow green.

## Cosign keyless flow

```
  ephemeral keypair  ─┐
  GHA OIDC token  ───┤→  Fulcio CA  ──→  short-lived X.509 cert  ──┐
                      │   (binds workflow identity to pubkey)        │
                      └─→  cosign sign  ←─────────────────────────────┘
                          ↓
                          Rekor transparency log entry
                          ↓
                          OCI signature artifact pushed alongside image
```

The X.509 cert is valid for 10 minutes; the Rekor entry is permanent and
publicly auditable. There is no long-term key to manage or rotate.

## Verification (consumers must do this)

```bash
cosign verify \
  --certificate-identity-regexp="https://github.com/mios-dev/mios" \
  --certificate-oidc-issuer="https://token.actions.githubusercontent.com" \
  ghcr.io/mios-dev/mios:latest
```

For attestations:

```bash
# SLSA provenance
cosign verify-attestation --type slsaprovenance \
  --certificate-identity-regexp="https://github.com/mios-dev/mios" \
  --certificate-oidc-issuer="https://token.actions.githubusercontent.com" \
  ghcr.io/mios-dev/mios:latest

# CycloneDX SBOM
cosign verify-attestation --type cyclonedx \
  --certificate-identity-regexp="https://github.com/mios-dev/mios" \
  --certificate-oidc-issuer="https://token.actions.githubusercontent.com" \
  ghcr.io/mios-dev/mios:latest
```

## GHCR auth

In CI: `GITHUB_TOKEN` with `packages: write` permission. In local builds
(`mios-build-local.ps1` Mode 2 or `just` Mode 3): a GitHub PAT with the
same scope.

## GHCR retention

Untagged manifests are pruned after 90 days by default. 'MiOS' protects:

- The latest signed digest (`:latest`)
- The last 5 release-tag digests

Older tagged digests are pruned manually on a quarterly cadence to keep
the registry footprint bounded.

## Multi-arch

Multi-arch manifests are produced by:

```
podman manifest create ghcr.io/mios-dev/mios:<tag>
podman manifest add    ghcr.io/mios-dev/mios:<tag> docker://localhost/mios-amd64:latest
podman manifest add    ghcr.io/mios-dev/mios:<tag> docker://localhost/mios-arm64:latest
podman manifest push --all ghcr.io/mios-dev/mios:<tag>
```

Currently 'MiOS' publishes `linux/amd64` only; `linux/arm64` is on the
roadmap once the NVIDIA stack on aarch64 (Grace, Orin, Spark) stabilizes.

## image-versions.yml + Renovate

`image-versions.yml` pins every base/tool image digest by SHA256.
Renovate watches it and opens PRs when upstream digests advance. Auto-merge
is gated on green CI. Commented-out entries in the file (e.g.
`image_builder_cli_digest`) are placeholders for upcoming tools tracked
ahead of integration.
