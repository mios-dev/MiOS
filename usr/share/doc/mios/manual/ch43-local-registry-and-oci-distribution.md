<!-- AI-hint: Chapter 43: Local Registry and OCI Distribution. Covers OCI distribution containers used in replication loop. Details cache boundaries speeding up successive image builds. Explains pulling local registries and switching host roots. -->

# Chapter 43: Local Registry and OCI Distribution

> Part VII: Build, Test & Upstream Maintenance of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Local Registry and OCI Distribution** under MiOS.

### <a name="43_private_registry_quadlets"></a>43.Private Registry Quadlets: Private Registry Quadlets

> Path Reference: `/usr/share/doc/mios/manual.md#43_private_registry_quadlets`

#### Overview

Sets up private registry containers for local image hosting.

## Settings
- **Service**: Managed via registry Quadlet files.
- **Ports**: Exposes local registry endpoints on loopbacks.
- **Security**: Restricts pull requests to local adapters.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="43_image_caching_strategies"></a>43.Image Caching Strategies: Image Caching Strategies

> Path Reference: `/usr/share/doc/mios/manual.md#43_image_caching_strategies`

#### Overview

Caching static container layers reduces OCI build times.

## Setup
- **Storage**: Caches OCI layers inside local disks.
- **Mechanisms**: Re-uses unchanged base steps.
- **Tuning**: Configured in build scripts.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="43_deployed_ref_updates"></a>43.Deployed Ref Updates: Deployed Ref Updates

> Path Reference: `/usr/share/doc/mios/manual.md#43_deployed_ref_updates`

#### Overview

Upgrades local hosts using updated image references.

## Actions
- **Update**: executes `bootc switch` pointing to local registries.
- **Reconciliation**: Applies structural merges to configurations.
- **Verification**: Checks image metadata on next boot.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
