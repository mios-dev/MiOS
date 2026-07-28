<!-- AI-hint: Architecture decision defining the three bootc install legs (to-existing-root, to-disk, to-filesystem) and offline OCI tar transport. -->
<!-- AI-related: automation/build-mios.sh, installation/mios-install.sh, usr/share/mios/ventoy/mios-kickstart.cfg -->
---
adr: 0014
title: "The bootc-install bare-metal leg: bootc install to-disk --transport oci"
status: proposed
date: 2026-07-28
deciders: [operator, ai-pair]
tags: [bootc, bare-metal, installation, oci, offline]
laws: [3, 4, 12]
ssot_keys: [image.sidecars, build.bake]
related_ws: [WS-CAT, WS-MDRIVE]
supersedes: []
superseded_by: []
---

# ADR-0014: The bootc-install bare-metal leg: bootc install to-disk --transport oci

## Status

Proposed — 2026-07-28. Implementation PLANNED to complete offline bare-metal installation capability across USB and Ventoy deployment surfaces.

## Context

MiOS utilizes `bootc` for transactional OS updates and base system image management. While existing scripts (`automation/build-mios.sh`, `installation/mios-install.sh`) handle system conversion (`to-existing-root`) and updates (`mios-update`), they lack an offline bare-metal installer path for blank hardware.

Installing directly onto blank disks without Internet connectivity requires sourcing the container image from a local OCI tarball rather than an online container registry.

## Decision

Formalize and implement the three bare-metal installation legs for `bootc`:

1. **Three Installation Legs**:
   - **`to-existing-root`** (Conversion): Replaces an existing running system's rootfs with the MiOS container image.
   - **`to-disk`** (Blank Hardware): Installs the MiOS image directly onto an unpartitioned or blank target disk.
   - **`to-filesystem`** (Kickstart / Custom Partitions): Sinks the container payload into pre-formatted target filesystems (used during Anaconda/Kickstart `%post`).

2. **Offline OCI Transport Requirement**:
   - Sources the target image via `--transport oci` / `oci-archive` from the local MiOS-Data OCI payload tarball on USB/Ventoy media.
   - Guarantees fully offline deployment capability on blank hardware without external network egress.

## Rationale

- Fills the architectural gap between online container updates and offline bare-metal provisioning.
- Adheres to Law 12 (BAKE-NOT-FETCH) by embedding all required installation payload layers on local media.
- Provides consistent partitioning and bootloader setup across physical hardware targets.

## Alternatives

- **Online-Only Registry Installs**: Fails in air-gapped or low-connectivity environments.
- **Traditional Anaconda ISO Only**: Increases build maintenance overhead by maintaining separate non-container installer payloads.

## Consequences

### Positive
- Enables offline installation onto blank physical servers and workstations.
- Standardizes bare-metal deployment on official upstream `bootc` commands.

### Negative
- Requires larger USB/Ventoy image bundles containing the full OCI transport tar.

## Implementation

- Will be integrated into `installation/mios-install.sh` under the `bootc` target.
- Leverages Kickstart configuration in `usr/share/mios/ventoy/mios-kickstart.cfg`.

## References

- [ADR-0005: Sovereign run-off-M](file:///C:/MiOS/usr/share/doc/mios/adr/0005-sovereign-run-off-m-drive.md)
- [ADR-0008: MiOS-Cat unified entry point](file:///C:/MiOS/usr/share/doc/mios/adr/0008-mios-cat-unified-entry-and-minification.md)
- [Architectural Laws 3, 4, 12](file:///C:/MiOS/usr/share/mios/mios.toml)
