<!-- 🌐 MiOS Artifact | Proprietor: MiOS Project | https://github.com/mios-project/mios -->
# 🌐 MiOS
```json:knowledge
{
  "summary": "> **Proprietor:** MiOS Project",
  "logic_type": "documentation",
  "tags": [
    "MiOS",
    "knowledge"
  ],
  "relations": {
    "depends_on": [
      ".env.mios"
    ],
    "impacts": []
  }
}
```
> **Proprietor:** MiOS Project
> **Infrastructure:** Self-Building Infrastructure (Personal Property)
> **License:** Licensed as personal property to MiOS Project
> **Source Reference:** MiOS-Core-v0.1.1
---

# Upstream bootc Ecosystem Research (2025–2026)

This document summarizes the latest architectural shifts in the Fedora bootc ecosystem and Universal Blue (uCore), mapping upstream trajectories to missing implementations in MiOS.

## 1. The Native `composefs` Backend Transition
The most significant upstream technical change is the deprecation of the `ostree` backend in favor of a "pure" **native composefs** backend.
*   **Current State:** `bootc` currently imports OCI layers into an `/sysroot/ostree` repository and dynamically generates a `composefs` image for the root filesystem.
*   **Future State (Fedora 44 / 2026):** `bootc` will use `/sysroot/composefs` directly. The OS boots directly from a Merkle-tree-based filesystem image pointing to a content-addressed object store. 
*   **Benefits:** Eliminates the `ostree` abstraction layer, guarantees strict read-only immutability, and provides native cryptographic integrity via `fs-verity`.

**MiOS Gap:** We have enabled `composefs.enabled = verity` in `prepare-root.conf`, which is good preparation. However, we must explicitly test our build targets against `--composefs-native` installation flags as `bootc-image-builder` and `bootc install` mature, to ensure our `` overlays do not violate native composefs assumptions.

## 2. Unified Kernel Images (UKI)
Integrated closely with the composefs-native transition is the shift to **Unified Kernel Images (UKI)**.
*   **What it is:** Bundling the kernel, initramfs, and kernel command line into a single, signed EFI binary.
*   **Why it matters:** UKI establishes a continuous Secure Boot chain of trust from UEFI firmware directly into the `composefs` Merkle tree.

**MiOS Gap:** We currently use `systemd-boot-unsigned` as a placeholder. We need to implement a full UKI generation step during our OCI build (or rely on `ucore-hci` if they implement it upstream), ensuring our custom kernel arguments (currently in `kargs.d/`) are cleanly injected into the UKI before signing.

## 3. Fedora CoreOS (FCOS) Exclusive OCI Delivery
By Fedora 43/44, Fedora CoreOS is planned to be delivered **exclusively as OCI images**, completely disabling traditional ostree repository pulls. FCOS is becoming a specialized "flavor" of `bootc`.
*   **Impact:** The `ucore-hci` base we rely on will transition to this model natively.

**MiOS Gap:** We are already aligned with this (MiOS builds itself entirely from OCI via `podman build`). However, we should monitor how upstream FCOS handles Ignition vs. cloud-init under pure OCI delivery. Currently, MiOS handles first-boot provisioning via custom `systemd` scripts (e.g., `mios-wsl-firstboot`). We should evaluate adopting standard `bootc` ignition-injection patterns if they become the upstream standard.

## 4. Hardlinking under `/usr`
Fedora 44 plans to hardlink identical files under `/usr` by default to drastically reduce image size.

**MiOS Gap:** Our `08-system-files-overlay.sh` uses `tar` pipes to copy overlays. We must ensure that our overlay mechanisms do not break hardlinks or dramatically inflate layer sizes when the base image introduces global hardlinking.

## Strategic Roadmap for MiOS
To keep progressing, we must prioritize the following missing implementations:
1.  **Test the `--composefs-native` flag:** Evaluate building RAW/VHDX targets with `bootc-image-builder` forcing the new backend.
2.  **UKI Architecture:** Research how to bundle our custom `kargs.d/` and NVIDIA `akmod` kernel modules into a Unified Kernel Image.
3.  **Monitor systemd-remount-fs:** We currently mask `systemd-remount-fs.service` due to an F42+ interop bug with composefs. We must track upstream `systemd` and `composefs` repositories to unmask this service once the bug is resolved.

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-project/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->
