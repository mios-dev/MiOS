# INDEX.md — MiOS Universal Agent Hub (SSOT)

```json:knowledge
{
  "summary": "The SINGLE SOURCE OF TRUTH for MiOS. Architectural laws, agent behavior, and API surface contracts in a unified OpenAI-compliant manifest.",
  "logic_type": "documentation",
  "tags": [
    "MiOS",
    "AI",
    "Agent Hub",
    "Index",
    "OpenAI",
    "SSOT"
  ],
  "relations": {
    "depends_on": [
      ".env.mios",
      "ai-context.json"
    ],
    "impacts": [
      "ARCHITECTURE.md",
      "ENGINEERING.md",
      "llms.txt",
      "llms-full.txt",
      "system-prompt.md",
      ".cursorrules",
      ".clinerules",
      ".github/ai-instructions.md"
    ]
  },
  "version": "0.2.0",
  "last_rag_sync": "2026-04-29T23:06:38.455497"
}
```

> **DELEGATED AI FILES:**
> - **.cursorrules**: Rules for VS Code Cursor.
> - **.clinerules**: Rules for Cline/Roo-Code.
> - **.github/ai-instructions.md**: Rules for GitHub Agents.
> - **system-prompt.md**: Authoritative Persona & Identity.
> - **llms.txt**: High-level AI ingestion index.
> - **llms-full.txt**: Flattened repository context.

---

## 🏗️ Project Profile
MiOS is a **bootc-based, self-building, immutable workstation OS** on Fedora Rawhide. It uses a single OCI image to cover all roles: Desktop, K3s, VFIO, and WSL2.

---

## 🤖 AI Agent Surface Contract (OpenAI Native)
MiOS is OpenAI-API native. All agents MUST target the local proxy at `http://localhost:8080/v1`.

| Endpoint | Method | Purpose | Deployed Filesystem Mirror |
|---|---|---|---|
| /v1/chat/completions | POST | Primary Chat Interface | - |
| /v1/models | GET | Model Discovery | /usr/share/mios/ai/v1/models.json |
| /v1/mcp | FS | MCP Registry | /usr/share/mios/ai/mcp/config.json |
| /v1/embeddings | POST | Vector Search | - |

---

## ⚖️ Immutable Appliance Laws (Day 0)
These laws are absolute. Violations cause state drift and build failure.

1. **USR-OVER-ETC**: Never write static config to `/etc` at build time. Use `/usr/lib/<component>.d/`.
2. **NO-MKDIR-IN-VAR**: Declare all `/var` dirs via `tmpfiles.d`.
3. **BOUND-IMAGES**: All primary Quadlet sidecar containers must be symlinked into `/usr/lib/bootc/bound-images.d/`.
4. **BOOTC-CONTAINER-LINT**: `RUN bootc container lint` must be the final instruction in every Containerfile.
5. **UNIFIED-AI-REDIRECTS**: Use agnostic environment variables (MIOS_AI_KEY, MIOS_AI_MODEL) targeting `http://localhost:8080/v1`.

---

## 🛠️ Unified Specification Files
- **[ARCHITECTURE.md](./ARCHITECTURE.md)**: Hardware, Filesystem, and Virtualization.
- **[ENGINEERING.md](./ENGINEERING.md)**: Security, Build Modes, and Automation.

---

## 📂 Repository Directory Map (Rootfs-Native)

| Path | Purpose | Manifest |
|---|---|---|
| `usr/` | System Binaries & Templates | `usr/manifest.json` |
| `etc/` | Host Overrides | `etc/manifest.json` |
| `var/` | Mutable State Templates | `var/manifest.json` |
| `automation/` | Build Pipeline | `automation/manifest.json` |
| `tools/` | Utility Toolchain | `tools/manifest.json` |
| `specs/` | Research & Blueprints | `specs/manifest.json` |

---
*Copyright (c) 2026 MiOS Project. Day 0 Ready.*
