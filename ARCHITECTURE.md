# MiOS ARCHITECTURE — System Blueprint (Day 0)

```json:knowledge
{
  "summary": "Consolidated architectural specification for MiOS. Hardware, Filesystem, and AI Interface SSOT.",
  "logic_type": "blueprint",
  "tags": ["MiOS", "Architecture", "Day-0", "SSOT"],
  "version": "v0.1.4"
}
```

## 🏗️ Core Pillars
MiOS is a container-native workstation engineered for high-performance virtualization and local Generative AI development.

1. **Transactional Integrity**: The system core is cryptographically sealed and managed via `bootc`.
2. **Hardware Agnosticism**: Universal acceleration for primary GPU vendors (NVIDIA, AMD, Intel).
3. **Zero-Trust Boundary**: Mandatory execution control and kernel-level isolation.

---

## 💾 Filesystem Hierarchy (FHS 3.0 + bootc)
MiOS mirrors the standard Linux FHS within its OCI root.

| Path | Type | Intent |
| :--- | :--- | :--- |
| `/usr` | Immutable | System Binaries, Libraries, and Static Config. |
| `/etc` | Persistent | Host-specific overrides. |
| `/var` | Persistent | System state and User home directories. |
| `/srv` | Persistent | Sidecar service data (Models, Databases). |

### ⚖️ Immutability Mandate
Build-time overlays into `/var` are architectural violations. All `/var` state must be declared via `tmpfiles.d` to ensure atomic, reproducible deployments.

---

## 🖥️ Hardware Delegation

### 🎮 Universal Acceleration
Standardized CDI (Container Device Interface) and ROCm/Arc drivers ensure local AI tools access native hardware performance.
- **Hardware Targeting**: Primary GPU IDs `10de:2204,10de:1aef`.

### ⚡ Virtualization
Tier-1 Hypervisor capabilities (KVM/QEMU) are native to the system core, supporting VFIO-PCI passthrough and shared memory (KVMFR) buffers.

---

## 🤖 AI Interface Surface
The system architecture exposes a local OpenAI-compatible API surface for autonomous management and user interaction.

| Service | Protocol | Access Point |
| :--- | :--- | :--- |
| **Inference** | REST | `http://localhost:8080/v1` |
| **Discovery** | MCP | `/usr/share/mios/ai/mcp/` |
| **Metadata** | JSON | `/usr/share/mios/ai/v1/` |

---
*Copyright (c) 2026 MiOS. Pure FOSS. Zero Day Ready.*
