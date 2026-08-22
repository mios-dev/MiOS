<!-- AI-hint: Chapter 18: Supply Chain and Image Integrity. Defines policy-based verification of OCI signatures at pull time. Covers keyless image signing using OIDC identity providers. Explains the generation and verification of build SBOMs. -->

# Chapter 18: Supply Chain and Image Integrity

> Part V: Deep Security, Cryptography & Hardware of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Supply Chain and Image Integrity** under MiOS.

### <a name="18_sigstore_verification_policies"></a>18.Sigstore Verification Policies: Sigstore Verification Policies

> Path Reference: `/usr/share/doc/mios/manual.md#18_sigstore_verification_policies`

#### Overview

Sigstore policies ensure only trusted images can be executed.

## Enforcements
- **Signature Check**: Validates signatures on container pulls.
- **Policy Config**: Configured in [42-cosign-policy.sh](automation/42-cosign-policy.sh).
- **Rules**: Rejects unsigned images or those with invalid certs.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="18_keyless_cosign_signing"></a>18.Keyless Cosign Signing: Keyless Cosign Signing

> Path Reference: `/usr/share/doc/mios/manual.md#18_keyless_cosign_signing`

#### Overview

Keyless signing uses OIDC trust systems to sign OCI container images.

## Features
- **Keys**: No private keys are stored; signatures use ephemeral certificates.
- **Logs**: Certs are logged in public Rekor transparency ledgers.
- **CI**: Integrates with GitHub and local runner actions.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="18_build_time_attestation"></a>18.Build Time Attestation: Build-Time Attestation

> Path Reference: `/usr/share/doc/mios/manual.md#18_build_time_attestation`

#### Overview

Attestations verify the build origin and contents of OCI images.

## Output
- **SBOM**: Generates a CycloneDX SBOM during the OCI build.
- **Attestation**: Baked directly into the image layers.
- **Verification**: Validated during deployment checks.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
