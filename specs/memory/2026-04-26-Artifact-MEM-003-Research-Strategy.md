<!-- 🌐 MiOS Artifact | Proprietor: MiOS Project | https://github.com/mios-project/mios -->
# 🌐 MiOS
```json:knowledge
{
  "summary": "> **Proprietor:** MiOS Project",
  "logic_type": "documentation",
  "tags": [
    "MiOS",
    "memory"
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

# Research and Remediation Plan for Missing Components and Issues

### Overview
This document outlines the comprehensive research and remediation plan for the 13 missing components and architectural discrepancies identified during the project audit.

---

## Phases

### Phase 1: Identification
- **Milestone:** Complete identification of all missing components.
- **Deliverables:** Detailed list of missing components (Completed).
- **Research Tasks:**
  1. Review existing documentation and package manifests.
  2. Audit system scripts and container definitions.

### Phase 2: Research
- **Milestone:** Conduct research for each missing component.
- **Deliverables:** Research findings documents for each component.
- **Research Tasks:**
  1. Identify upstream Fedora/bootc references.
  2. Analyze solutions from Universal Blue and similar projects.

### Phase 3: Remediation
- **Milestone:** Remediate issues based on research findings.
- **Deliverables:** Implemented solutions for all components.
- **Research Tasks:**
  1. Develop initial script/manifest solutions.
  2. Test and validate across hardware targets.

---

## Kanban Board

| Task / Component | Status | Milestone | Deliverables | Upstream References |
|------------------|--------|-----------|--------------|---------------------|
| **1. Ceph & K3s Storage** | Done | Remediation | Remove 'planned' tag from scripts | N/A |
| **2. K3s SELinux** | Done | Remediation | Compile `.pp` policy from source during OCI build | k3s-io/k3s-selinux |
| **3. Pacemaker HA VM Gating** | Done | Remediation | Deploy PCS remote via Podman Quadlet | Fedora Pacemaker Docs |
| **4. ComposeFS Verity Bug** | Done | Remediation | Migrate all root mount options to `kargs` | systemd/composefs issues |
| **5. Unified Kernel Image (UKI)** | Done | Remediation | Draft `ukify` script post-akmod compilation | bootc UKI roadmap |
| **6. FreeIPA/SSSD Automation** | Done | Remediation | Zero-touch systemd oneshot w/ credential shredding | FreeIPA Client Docs |
| **7. Fapolicyd Alternatives** | Done | Remediation | Configure Fapolicyd with fs-verity trust backend | Fedora Security / fapolicyd |
| **8. Cosign Verification** | Done | Remediation | Implemented via native `/etc/containers/policy.json` | sigstore/cosign / bootc |
| **9. Podman-Docker Symlink** | Done | Remediation | Swapped podman-docker for moby-engine in OCI build | ublue-os/ucore |
| **10. Intel Compute Stack** | Done | Remediation | Validate Battlemage `xe` driver bind via `kargs` | Fedora/Intel Compute |
| **11. Utility Packages Addition** | Done | Remediation | Add ntfs-3g, strace, lsof, etc. | PACKAGES-AUDIT.md |
| **12. NVIDIA Waydroid 3D** | Done | Remediation | Implement SwiftShader systemd drop-in | Waydroid/NVIDIA docs |
| **13. RTX 50-Series VFIO Bug** | Done | Remediation | Draft libvirt FLR hook / GSP firmware toggle | VFIO / NVIDIA Open kmods |
| **14. Hyper-V GPU-PV (dxgkrnl)** | Done | Remediation | Implement guest driver copy shim script | Microsoft/LKML |
| **15. Wayland RDP VSOCK** | In Progress | Remediation | Optimize GRD proxy via systemd drop-ins | GNOME Upstream |
| **16. SR-IOV Persistence** | Done | Remediation | Implement systemd oneshot service | systemd/bootc |
| **17. Universal CDI** | Done | Remediation | Implement vendor-agnostic generator | Podman CDI |

---

### Conclusion
This plan aims to trace and rectify all missing components and issues affecting the MiOS project. Tracking progress through the Kanban matrix will ensure transparency and accountability throughout the process.

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-project/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->
