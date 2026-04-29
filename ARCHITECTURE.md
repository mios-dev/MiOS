# MiOS ARCHITECTURE — Unified Blueprint (Day 0)

```json:knowledge
{
  "summary": "Consolidated architectural specification for MiOS. Hardware, Filesystem, and Virtualization SSOT.",
  "logic_type": "blueprint",
  "tags": ["MiOS", "Architecture", "Day-0", "SSOT"],
  "version": "1.0.0"
}
```

## 🏗️ Core Pillars
MiOS is a container-native, immutable workstation engineered for high-performance virtualization and Generative AI development.

1. **Transactional Immutability**: The userspace is a cryptographically sealed OCI image.
2. **Hardware Agnosticism**: Unified support for Intel, AMD, and NVIDIA silicon.
3. **Zero-Trust Security**: Strict execution whitelisting and kernel-level hardening.

---

## 💾 Filesystem Hierarchy (FHS 3.0 + bootc)
MiOS follows a rootfs-native repository structure.

| Path | Type | Persistence | Purpose |
| :--- | :--- | :--- | :--- |
| `/usr` | `composefs` | Immutable | Core OS Binaries & Libraries |
| `/etc` | `overlay` | Persistent | Admin Overrides (USR-OVER-ETC Law) |
| `/var` | `ext4/btrfs` | Persistent | User Data & System State |
| `/home` | `symlink` | Persistent | Points to `/var/home` |

### ⚖️ Immutable Appliance Laws
- **USR-OVER-ETC**: Never write static config to `/etc` at build time. Use `/usr/lib/<component>.d/`.
- **NO-MKDIR-IN-VAR**: All `/var` directories must be declared via `tmpfiles.d`.

---

## 🖥️ Hardware & Virtualization

### 🎮 Graphics Acceleration
Native-tier performance via:
- **NVIDIA**: Open-source GSP modules with CDI (Container Device Interface) support.
- **AMD**: KFD/ROCm native support.
- **Intel**: Arc/Xe native support.

### ⚡ Virtualization Mastery
The system operates as a Tier-1 hypervisor (KVM/QEMU).
- **VFIO-PCI**: Dynamic GPU passthrough for Guest VMs.
- **Looking Glass**: Shared Memory (KVMFR) for low-latency VM display.
- **CPU Pinning**: Core shielding for X3D/Hybrid core isolation.

---

## ⚡ Kernel & Performance
- **Scheduler**: BORE (Burst-Oriented Response Enhancer).
- **Tickrate**: 1000Hz.
- **Memory**: zram (zstd compressed) with le9uo anti-thrashing patches.
- **I/O**: BFQ for slow disks, Kyber for NVMe.

---

## 📦 Deployment Matrix
| Target | Format | Delivery |
| :--- | :--- | :--- |
| **Bare Metal** | `RAW` | ISO / Disk Flash |
| **Hyper-V** | `VHDX` | Gen2 VM |
| **WSL2** | `Tarball` | WSL Import |
| **OCI** | `Image` | `ghcr.io/kabuki94/mios` |

---
*Copyright (c) 2026 MiOS Project. Licensed as personal property.*
