<!-- 🌐 MiOS Artifact | Proprietor: MiOS Project | https://github.com/mios-project/mios -->
# 🌐 MiOS
```json:knowledge
{
  "summary": "> **Proprietor:** MiOS Project",
  "logic_type": "documentation",
  "tags": [
    "MiOS",
    "engineering"
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

# 🧪 MiOS System Validation

```json
{
  "tools": "tmt (Test Management Tool)",
  "infrastructure": "Testing Farm / virtual.testcloud",
  "method": "Ephemeral OCI Validation"
}
```

---

## 🛠️ Validation Suites

### 🩺 Smoke Testing
Basic system integrity and service readiness checks.

```json
{
  "plan": "evals/tmt/plans/smoke.fmf",
  "checks": [
    "fs-verity-integrity",
    "systemd-initialization",
    "network-bridge-readiness"
  ]
}
```

### 🎮 Virtualization Stabiliy
Verifying the integrity of the KVM/VFIO stack.

| Test | Objective | Target |
| :--- | :--- | :--- |
| **IOMMU Audit** | Verify valid group isolation | `mios-vfio-check` |
| **KVMFR Hook** | Shared memory allocation check | `/dev/shm/looking-glass` |
| **GDM Readiness** | Wayland compositor boot success | `graphical.target` |

---

## 📋 Software Bill of Materials (SBOM)

MiOS generates signed manifests for every build.

1. **Formats:** `CycloneDX`, `SPDX`.
2. **Records:** Built via GitHub Actions with OIDC identity verification.
3. **Storage:** Artifacts attached to GHCR image metadata.

---

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-project/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->
