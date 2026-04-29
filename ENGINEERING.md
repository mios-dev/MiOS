# MiOS ENGINEERING — Unified Standards (Day 0)

```json:knowledge
{
  "summary": "Consolidated engineering standards, build modes, and security specifications for MiOS.",
  "logic_type": "engineering",
  "tags": ["MiOS", "Engineering", "Security", "Build", "AI"],
  "version": "1.0.0"
}
```

## 🛡️ Security Framework

### 🧠 Execution Control
Strict binary whitelisting via `fapolicyd` (deny-by-default).
- **Authorized paths**: `/usr/bin`, `/usr/lib`, `/usr/local/bin`.
- **Trust Boundary**: `allow perm=execute : ftype=application/x-executable trust=1`.

### 🔒 Kernel Hardening (29-Parameter Standard)
- `slab_nomerge`: Prevents heap layout manipulation.
- `init_on_alloc=1 / init_on_free=1`: Memory zeroing.
- `lockdown=integrity`: Protects kernel integrity.
- `iommu=force`: Hardware-level DMA isolation.
- **VFIO Isolation**: Early-boot binding for IDs `10de:2204,10de:1aef`.

---

## 🏗️ Build Architecture

### 🔄 The Self-Build Loop
MiOS is a self-replicating OS. A running MiOS instance can build its own successor using Podman/Buildah without host-level dependencies.
```
Running MiOS → Podman Build → New OCI Image → bootc switch → Reboot → New OS
```

### 🛠️ Build Modes
1. **CI/CD**: Automated GitHub Actions build/sign/push.
2. **Local (Linux)**: Orchestrated via `Justfile` (`just build`).
3. **Local (Windows)**: Orchestrated via `mios-build-local.ps1`.
4. **Self-Build**: Running MiOS executes `podman build`.

---

## 🤖 AI Integration & Tooling

### 🔌 Programmable Interface
MiOS implements **OpenAI Function Calling** and **Model Context Protocol (MCP)** standards.
- **SSOT Hub**: `INDEX.md` and `llms.txt`.
- **Local API**: `http://localhost:8080/v1` (LocalAI/Ollama).
- **Structured Output**: Core tools support `--json` for direct agent interaction.

### 🛠️ Core Toolchain
- `mios-update`: Atomic OS transactions via `bootc`.
- `mios-status`: Real-time system telemetry.
- `mios-vfio-toggle`: Dynamic GPU isolation.
- `mios-backup`: Persistent state retention (`/var` and `/etc`).

---

## 📜 Automation Pipeline (Numbered)
The build process executes a sequential pipeline in `automation/`:
- **01-08**: Core Repos, Kernel, and Filesystem Overlay.
- **10-13**: GNOME, Hardware Drivers, and Virt/Storage (Ceph/K3s).
- **20-26**: Services, Security (fapolicyd/SELinux), and Remote Desktop.
- **30-39**: Localization, Users, Hostname, and Desktop Polish.
- **40-49**: Integrity (Composefs), Policy (Cosign), and Finalization.

---
*Copyright (c) 2026 MiOS Project. Licensed as personal property.*
