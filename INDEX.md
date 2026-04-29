<!-- [NET] MiOS Artifact | Proprietor: MiOS-DEV | https://github.com/MiOS-DEV/MiOS-bootstrap -->
# INDEX.md — MiOS Universal Agent Hub (SSOT)

```json:knowledge
{
  "summary": "The SINGLE SOURCE OF TRUTH for MiOS. Consolidates architectural laws, agent behavior, build-time rules, and API surface contracts into a unified OpenAI API compliant manifest.",
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
      "AGENTS.md",
      "AI-AGENT-GUIDE.md",
      "system-prompt.md",
      ".cursorrules",
      ".clinerules",
      ".github/ai-instructions.md"
    ]
  },
  "last_rag_sync": "2026-04-29T20:00:00Z",
  "version": "0.2.0"
}
```

> **DEPRECATION NOTICE:** AGENTS.md and AI-AGENT-GUIDE.md are legacy snapshots. 
> This file is the **only authoritative source** for MiOS architecture, laws, and agent behavior.

## [NET] Live Documentation (CHECK FIRST)

**IMPORTANT:** This INDEX.md is a snapshot. **ALWAYS check the Wiki for current/updated information:**
- **Wiki Home:** https://github.com/MiOS-DEV/MiOS-bootstrap/wiki
- **Purpose:** PRIMARY source for current tasks, research patterns, and build logs.

---

## 🏗 Project Profile

MiOS is a **bootc-based, self-building, immutable workstation OS** on Fedora Rawhide.
One OCI image covers all hardware roles: desktop, k3s/HA, GPU passthrough (VFIO), WSL2.
Sole proprietor: **MiOS-DEV**. Target: AMD Ryzen 9 9950X3D + NVIDIA RTX 4090.

---

## 🤖 AI Agent Surface Contract (OpenAI Native)

MiOS is OpenAI-API native. All agents MUST target the local proxy at http://localhost:8080/v1.

| Endpoint | Method | Purpose | Deployed Filesystem Mirror |
|---|---|---|---|
| /v1/chat/completions | POST | Primary Chat Interface | - |
| /v1/models | GET | Model Discovery | /usr/share/mios/ai/v1/models.json |
| /v1/mcp | FS | MCP Registry | /usr/share/mios/ai/mcp/config.json |
| /v1/embeddings | POST | Vector Search | - |

**Inference Backend:** LocalAI (default), swappable with Ollama, vLLM, or llama.cpp.

---

## ⚖️ Immutable Appliance Laws

These laws are absolute. Violations cause state drift and CI failure.

1. **USR-OVER-ETC:** Never write static config to /etc/ at build time. Use /usr/lib/<component>.d/. /etc/ is for admin overrides only.
2. **NO-MKDIR-IN-VAR:** Never mkdir /var/... in build scripts. Declare all /var dirs via tmpfiles.d (d or C directives) or StateDirectory= in unit files.
3. **MANAGED-SELINUX:** semodule -i in a Containerfile RUN layer is the primary method for custom modules.
4. **BOUND-IMAGES:** All primary Quadlet sidecar containers must be symlinked into /usr/lib/bootc/bound-images.d/ for atomic updates.
5. **BOOT-SHIELDING:** Use excludepkgs="shim-*,kernel*" as a regression guard in dnf operations.
6. **NOVA-CORE-BLACKLIST:** Blacklist both nouveau AND nova_core on Fedora 44+ (kernel 6.15+).
7. **BOOTC-CONTAINER-LINT:** RUN bootc container lint MUST be the final instruction in every Containerfile.
8. **NO-DNF-UPGRADE-UNCONDITIONAL:** Never RUN dnf -y upgrade without specifying package names.
9. **UNIFIED-AI-REDIRECTS:** Use agnostic environment variables (MIOS_AI_KEY, MIOS_AI_MODEL) targeting http://localhost:8080/v1.

---

## 🛠 Hard Rules (Build-Breaking)

### kargs.d TOML
- **Valid:** kargs = ["key=value", "flag"]
- **Never:** [kargs] section headers, delete =, or [[kargs]]. Deletion is a CLI-only flag.

### Bash
- set -euo pipefail in all scripts.
- VAR=$((VAR + 1)) always — never ((VAR++)).
- Never dnf install kernel inside the container.
- Never --squash-all on podman build (destroys bootc delta structure).
- Quote all variables; use read -r.

### GNOME / Theming
- Never GTK_THEME=Adwaita:dark. Use ADW_DEBUG_COLOR_SCHEME=prefer-dark and dconf color-scheme='prefer-dark'.
- /etc/dconf/profile/user and /etc/dconf/profile/gdm must exist.
- xorgxrdp-glamor only (xorgxrdp conflicts).

### NVIDIA / VM Gating
- NVIDIA blacklisted by default; unblacklisted only on bare metal via 34-gpu-detect.sh.
- Blacklist nova_core on kernel 6.15+.

### PowerShell
- Never Invoke-Expression on downloaded content.
- Push scripts must clone the existing repo — never git init.

---

## 📂 Repository Directory Map (Rootfs-Native)

| Path | Purpose | Manifest |
|---|---|---|
| usr/ | System Binaries (Immutable) | usr/manifest.json |
| etc/ | System Configuration (Templates) | etc/manifest.json |
| var/ | Mutable System State (Templates) | var/manifest.json |
| specs/ | Architectural Blueprints & Research | specs/manifest.json |
| automation/ | Build & Configuration Automation | automation/manifest.json |
| srv/ai/ | Writable AI State (Weights/MCP) | - |

---

## 🧠 Shared Memory System

| Path | Purpose |
|---|---|
| .ai/foundation/memories/journal.md | Episodic memory — timestamped log of all AI actions. |
| .ai/foundation/memory/ | Semantic memory — named .md files per topic. |
| .ai/foundation/shared-tmp/ | Scratchpad — transient cross-agent data. |

---

## 🤝 Deliverable Contract

Complete replacement files only. No patches. No diffs. PII and vendor branding MUST be scrubbed.

<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS-DEV -->
