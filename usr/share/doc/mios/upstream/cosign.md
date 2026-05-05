# Cosign / Sigstore — Keyless Image Signing

> CI signs every push with cosign keyless via GitHub Actions OIDC
> (`.github/workflows/mios-ci.yml`). Verify before deploying.
> Source: `SECURITY.md` §Image-signing, `usr/share/doc/mios/guides/deploy.md` §Image-verification.

## Project

- Repo: <https://github.com/sigstore/cosign>
- What is Sigstore: <https://sbomify.com/2024/08/12/what-is-sigstore/>
- Verification walkthrough: <https://secure-pipelines.com/ci-cd-security/signing-verifying-container-images-sigstore-cosign/>
- Attestation walkthrough: <https://www.augmentedmind.de/2025/03/02/docker-image-signing-with-cosign/>

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
Actions workflow itself.

## MiOS verification

```bash
cosign verify \
  --certificate-identity-regexp="https://github.com/mios-dev/mios" \
  --certificate-oidc-issuer="https://token.actions.githubusercontent.com" \
  ghcr.io/mios-dev/mios:latest
```

This is the verbatim verification command from `SECURITY.md` and
`usr/share/doc/mios/guides/deploy.md`. The `--certificate-identity-regexp` matches any
`mios-dev/mios*` workflow path; tighten in production to the specific
`.github/workflows/mios-ci.yml@refs/tags/v*` if you want pinned trust.

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
`cyclonedx`, `vuln`, `openvex`. MiOS uses `cyclonedx` for SBOM via
`automation/90-generate-sbom.sh` (syft).

## Cross-refs

- `usr/share/doc/mios/60-ci-signing.md`
- `usr/share/doc/mios/upstream/ghcr.md`
- `usr/share/doc/mios/upstream/secureblue.md`
