<!-- 🌐 MiOS Artifact | Proprietor: MiOS Project | https://github.com/mios-project/mios -->
# 🧬 MiOS Technology & Architectural Patterns

```json:knowledge
{
  "summary": "Unified mapping of technologies, implementation patterns, and historical context.",
  "logic_type": "blueprint",
  "tags": [
    "technology",
    "patterns",
    "mapping",
    "SSOT"
  ],
  "version": "1.0.0"
}
```

This document serves as the **AI-Native Map** for MiOS, connecting specific technologies to their implementation scripts, configuration paths, and architectural intent.

---

## 🏗️ Core OS & Immutability
| Technology | Pattern | implementation / Source |
| :--- | :--- | :--- |
| **bootc** | OCI-native bootable containers | `Containerfile`, `usr/lib/bootc/` |
| **composefs** | Read-only rootfs + deduplication | `automation/40-composefs-verity.sh` |
| **ostree** | Atomic updates & rollback | `automation/99-cleanup.sh` |
| **systemd-sysext** | Dynamic system extensions | `specs/knowledge/archive/*-sysext-*` |

## 🛡️ Security & Hardening
| Technology | Pattern | implementation / Source |
| :--- | :--- | :--- |
| **Kernel Hardening** | Kargs + Sysctl precedence | `usr/lib/bootc/kargs.d/`, `usr/lib/sysctl.d/` |
| **CrowdSec** | Behavior-based IPS | `automation/33-firewall.sh`, `PACKAGES.md` |
| **fapolicyd** | Execution whitelisting | `automation/20-fapolicyd-trust.sh` |
| **USBGuard** | USB physical security | `automation/47-hardening.sh` |
| **Secure Boot** | MOK-signed proprietary modules | `automation/generate-mok-key.sh`, `automation/enroll-mok.sh` |

## ⚡ Virtualization & GPU
| Technology | Pattern | implementation / Source |
| :--- | :--- | :--- |
| **VFIO** | Dynamic PCIe GPU passthrough | `usr/bin/mios-vfio-toggle`, `usr/lib/bootc/kargs.d/20-vfio.toml` |
| **Looking Glass** | KVMFR shared memory output | `automation/52-bake-kvmfr.sh`, `automation/53-bake-lookingglass-client.sh` |
| **CDI** | Container Device Interface | `automation/45-nvidia-cdi-refresh.sh` |
| **Waydroid** | LXC-based Android containers | `automation/35-waydroid.toml` (kargs), `PACKAGES.md` |

## ☁️ Cloud & Orchestration
| Technology | Pattern | implementation / Source |
| :--- | :--- | :--- |
| **K3s** | Lightweight Kubernetes | `automation/13-ceph-k3s.sh`, `usr/lib/greenboot/check/wanted.d/60-k3s.sh` |
| **Ceph** | Distributed RADOS storage | `automation/13-ceph-k3s.sh`, `usr/share/containers/systemd/ceph-radosgw.container` |
| **Quadlet** | Systemd-native Podman containers | `usr/share/containers/systemd/*.container` |

## 🤖 AI & Tooling
| Technology | Pattern | implementation / Source |
| :--- | :--- | :--- |
| **MCP** | Model Context Protocol | `specs/engineering/2026-04-27-Artifact-ENG-004-AI-Tool-Interface.md` |
| **UKB/RAG** | Unified Knowledge Base (JSON.gz) | `tools/generate-unified-knowledge.py`, `artifacts/repo-rag-snapshot.json.gz` |
| **JSON CLI** | Machine-readable tool output | `usr/bin/mios-update`, `usr/bin/mios-status`, `usr/bin/mios-vfio-*` |

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->
