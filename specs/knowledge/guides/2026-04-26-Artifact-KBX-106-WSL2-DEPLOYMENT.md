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

# 🛡️ WSL2 Deployment & Security Guide

This document outlines the requirements and security considerations for deploying MiOS as a WSL2 distribution.

## 🚨 SECURITY ADVISORY: CVE-2026-32178

A critical vulnerability (**CVE-2026-32178**) affecting the .NET runtime used in the WSL host has been identified. This vulnerability allows for SMTP header injection via `System.Net.Mail`.

### 🛠️ Required Mitigation
To ensure the security of your MiOS deployment on Windows, you **MUST** upgrade your WSL host to version **0.1.1 or higher**.

**Check your version:**
```powershell
wsl --version
```

**Upgrade command:**
```powershell
wsl --update
```

---

## 🚀 Deployment Workflow

MiOS is optimized for WSL2 through a specialized synthesis process that generates a compatible rootfs tarball.

### 1. Generate WSL Artifact
Use the root `Justfile` to synthesize the WSL tarball:
```bash
just wsl
```
This generates `artifacts/mios-wsl.tar`.

### 2. Import into Windows
On your Windows host, import the tarball as a new distribution:
```powershell
wsl --import MiOS C:\WSL\MiOS .\artifacts\mios-wsl.tar
```

### 3. Initialize
Launch MiOS and follow the first-boot initialization prompts:
```powershell
wsl -d MiOS
```

---

## 🔧 WSL2 Optimization

### Memory & CPU Scaling
MiOS automatically requests optimal resources in WSL2. You can further customize this in your `%USERPROFILE%\.wslconfig`:

```ini
[wsl2]
memory=16GB
processors=8
```

### Podman Integration
MiOS in WSL2 is pre-configured to handle Podman-native workloads. The `mios-builder` machine logic in `mios-build-local.ps1` ensures that build-time isolation is maintained even when running inside a Windows host.

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-project/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->
