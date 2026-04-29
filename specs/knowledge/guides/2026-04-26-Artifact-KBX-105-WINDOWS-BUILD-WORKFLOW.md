<!-- 🌐 MiOS Artifact | Proprietor: MiOS Project | https://github.com/mios-fss/mios -->
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
> **Source Reference:** MiOS-Core-v0.1.4
---

# 🪟 Windows 11 Build & Deployment Workflow
> **Proprietor:** MiOS Project
> **Infrastructure:** Self-Building Infrastructure (Personal Property)
> **License:** Licensed as personal property to MiOS Project
> **Source Reference:** MiOS-Core-v0.1.4
---

## 🚀 Overview
MiOS is optimized for development and synthesis on **Windows 11** using **Podman Desktop** and **WSL2**. This workflow utilizes a specialized PowerShell orchestration layer to handle everything from repository fetching to multi-artifact deployment (RAW, VHDX, ISO, WSL).

---

## 🛠️ Prerequisites
1.  **Windows 11** (Pro or Enterprise recommended for Hyper-V features).
2.  **Podman Desktop** installed and initialized.
3.  **WSL2** enabled (`wsl --install`).
4.  **PowerShell 7+** (pwsh).
5.  **Git for Windows**.

---

## 🔄 The "One-Click" Workflow

### 1. Fetch & Initialize
The easiest way to start is using the `install.ps1` script directly from the upstream repository. This handles the git fetch and environment pre-flight.

```powershell
# From an Administrator PowerShell prompt:
irm https://raw.githubusercontent.com/MiOS-FSS/MiOS-bootstrap/main/bootstrap.ps1 | iex
```

### 2. Pre-flight Check
Before building, run the pre-flight script to ensure your Windows environment is ready (CPU/RAM allocation, Podman socket availability, etc.).

```powershell
./preflight.ps1
```

### 3. Build & Orchestrate (`mios-build-local.ps1`)
The `mios-build-local.ps1` script is the primary master orchestrator. It manages a dedicated `mios-builder` Podman machine to ensure build-time performance and isolation.

**What it does:**
-   **Phase 1:** Creates/Updates the `mios-builder` machine (Rootful, Max Resources).
-   **Phase 2:** Executes `podman build` within the isolated machine.
-   **Phase 3:** Invokes `bootc-image-builder` (BIB) to generate artifacts.
-   **Phase 4:** Deploys artifacts to `./mios-deploy-out/`.

**Commands:**
```powershell
# Interactive Build Menu
./mios-build-local.ps1

# Non-interactive Local Build
./mios-build-local.ps1 -Workflow "Local Build"
```

---

## 🏗️ Building in WSL2/g
If you prefer to work entirely within a WSL2 environment:

1.  **Clone the Repo:** `git clone https://github.com/mios-fss/mios.git`
2.  **Use the Justfile:**
    ```bash
    just build    # OCI Image only
    just wsl      # Generate WSL2 Tarball
    just all      # Full artifact synthesis
    ```

---

## 📦 Deployment Artifacts
Upon completion, the Windows workflow populates `.\mios-deploy-out\` with:
-   `mios-bootable.raw`: For bare-metal flashing.
-   `mios-hyperv.vhdx`: For immediate use in Hyper-V Manager.
-   `mios-wsl.tar`: Importable via `wsl --import`.
-   `mios-installer.iso`: Bootable Anaconda installer.

---

## 🩺 Diagnostic Logging
Every Windows-side action is logged with high-resolution timestamps.
-   **Build Logs:** Captured in `/usr/lib/mios/logs/` inside the image.
-   **Orchestration Logs:** Outputted to the PowerShell console and mirrored in the project root during execution.

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-fss/mios](https://github.com/mios-fss/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-fss/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-fss/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->
