<!-- AI-hint: Defines the three bootc installation legs (to-existing-root, to-disk, to-filesystem) and requires offline --transport oci deployment for bare-metal installs from MiOS USB drives; read before modifying bootc installation targets. -->
<!-- AI-related: automation/build-mios.sh, installation/mios-install.sh, usr/share/mios/ventoy/mios-kickstart.cfg -->
---
adr: 0014
title: "The bootc-install bare-metal leg: bootc install to-disk --transport oci"
status: proposed
date: 2026-07-28
deciders: [operator, ai-pair]
tags: [bootc, bare-metal, offline, oci-archive, deployment]
laws: [3, 4, 12]
ssot_keys: [image.sidecars, build.bake]
related_ws: [WS-CAT, WS-MDRIVE]
supersedes: []
superseded_by: []
---

# ADR-0014: The bootc-install bare-metal leg — bootc install to-disk --transport oci

## Status

Proposed — 2026-07-28. Architectural design for offline bare-metal installation of the MiOS OCI bootc container image onto target hardware.

## Context

MiOS uses Red Hat `bootc` for transactional, container-based operating system deployment. Currently:
- In-place system conversion (`bootc install to-existing-root`) is supported for existing Linux systems.
- Image upgrades (`bootc upgrade` / `mios-update`) pull container layers over the network for running hosts.

However, deploying MiOS onto a **blank bare-metal machine** without internet connectivity poses an architectural challenge:
1. Standard `bootc install to-disk` attempts to pull image manifests from remote registries (e.g., GitHub Container Registry `ghcr.io`).
2. Live installation drives (such as `MiOS-Cat` USB drives) operate in air-gapped or offline environments during first-boot recovery and field installation.
3. The system requires an explicit, documented contract for installing the pinned bootc OCI container image directly from local media without remote registry dependencies.

## Decision

Define and adopt three distinct `bootc` installation legs, enforcing offline `--transport oci` capability for bare-metal deployment:

1. **Leg 1: `to-existing-root` (In-Place Conversion)**: Converts an already-running Linux system into a MiOS bootc container instance.
2. **Leg 2: `to-disk` (Blank Hardware Installation)**: Installs MiOS onto a blank target disk from a bootable USB drive using local `--transport oci` / `--transport oci-archive` sourcing:
   ```bash
   bootc install to-disk --transport oci /mnt/media/mios-oci-tar:latest /dev/nvme0n1
   ```
3. **Leg 3: `to-filesystem` (Automated Anaconda / Kickstart %post)**: Executes inside Kickstart / Anaconda installer scripts (`mios-kickstart.cfg`) to format partitions and unpack the OCI image to target mountpoints.

Key Requirements:
- The `MiOS-Cat` USB build pipeline must stage the complete `mios:latest` container image as an offline OCI archive (`.tar` / directory) on the Ventoy partition.
- `mios-install` CLI must surface `bootc-install-disk` as a target resolving to Leg 2.

## Rationale

- **Air-Gapped Sovereignty**: Ensures MiOS can be installed on remote or offline hardware without requiring GitHub Container Registry connectivity.
- **Identical Deployment Parity**: Guarantees that bare-metal installations deploy the exact same immutable OCI layers compiled during image build.
- **Clear Separation of Install Modes**: Eliminates ambiguity between converting existing systems vs. provisioning new hardware.

## Alternatives

- **Network-Only Installation**: Require active internet connectivity during bare-metal setup. *Rejected*: Violates air-gapped sovereignty requirements and fails when installing on offline hardware.
- **Traditional Package-Based Anaconda Install**: Use standard RPM packages instead of `bootc`. *Rejected*: Violates the immutable OCI container architecture of MiOS (Law 4).

## Consequences

### Positive
- Reliable offline installation on blank machines directly from `MiOS-Cat` USB media.
- Zero dependency on remote container registries during initial bare-metal provisioning.

### Negative
- Requires staging ~5–10 GB OCI container tarballs on the USB installation drive.

## Implementation

- Update `MiOS-Cat` builder to export the compiled OCI container image as an OCI archive tar.
- Add `resolve_bootc_disk` handler to `installation/mios-install.sh`.
- Update `usr/share/mios/ventoy/mios-kickstart.cfg` to use local `--transport oci` paths.

## References

- [ADR-0005: Sovereign run-off-M: Hyper-V VHDX deployment](file:///C:/MiOS/usr/share/doc/mios/adr/0005-sovereign-run-off-m-drive.md)
- [ADR-0008: MiOS-Cat unified entry point + repo minification](file:///C:/MiOS/usr/share/doc/mios/adr/0008-mios-cat-unified-entry-and-minification.md)
- `automation/build-mios.sh`
- `installation/mios-install.sh`
