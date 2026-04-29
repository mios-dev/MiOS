<!-- 🌐 MiOS Artifact | Proprietor: MiOS Project | https://github.com/mios-project/mios -->
# 🌐 MiOS
```json:knowledge
{
  "summary": "> **Proprietor:** MiOS Project",
  "logic_type": "documentation",
  "tags": [
    "MiOS",
    "core"
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

# 📋 MiOS Feature Index

```json
{
  "status": "Verified",
  "data_source": "specs/engineering/2026-04-26-Artifact-ENG-001-Packages.md"
}
```

---

## 📦 Core System

### 🧱 System Foundation
The immutable core is built for stability and cryptographic assurance.

```json
{
  "base": "Fedora Rawhide (fc45)",
  "package_manager": "DNF5",
  "init": "Systemd (PID 1)",
  "updater": "uupd (Staged delivery)"
}
```

### 🖥️ Desktop Ecosystem
Modern Wayland-only GNOME environment.

| Component | Standard |
| :--- | :--- |
| **Compositor** | `Mutter 50 (Wayland)` |
| **Toolkit** | `GTK 4.22` |
| **Typography** | `Geist (Vercel)` |
| **Theming** | `Adaptive Dark Mode` |

---

## 🛠️ Workstation Toolkit

### 🏗️ Development Sandboxes
Mutable environments within the immutable host.

{
    "sandboxing": {
      "engine": "Distrobox / Podman",
      "gui_forwarding": "Wayland socket mapping",
      "persistence": "Home directory integration"
    }
  }
}
```

---

## 🛠️ Toolchain Index

| Binary | Purpose | Path |
| :--- | :--- | :--- |
| **`mios`** | Master CLI entry point | `/usr/bin/mios` |
| **`mios-backup`** | State & persistent data backup | `/usr/bin/mios-backup` |
| **`mios-update`** | Staged bootc image transactions | `/usr/bin/mios-update` |
| **`mios-status`** | Real-time role & service telemetry | `/usr/bin/mios-status` |
| **`mios-vfio-check`** | IOMMU and passthrough diagnostics | `/usr/bin/mios-vfio-check` |
| **`mios-vfio-toggle`** | Dynamic GPU isolation (no-reboot) | `/usr/bin/mios-vfio-toggle` |
| **`mios-rebuild`** | In-place OS self-replication | `/usr/bin/mios-rebuild` |
| **`ujust`** | Unified Blue build & config recipes | `/usr/bin/ujust` |
| **`iommu-groups`** | Raw hardware isolation reporting | `/usr/bin/iommu-groups` |

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
