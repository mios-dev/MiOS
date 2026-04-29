# MiOS Universal Agent Hub — API Surface (Day 0)

```json:knowledge
{
  "summary": "The SINGLE SOURCE OF TRUTH for MiOS. Architectural laws, agent behavior, and API surface contracts in a unified OpenAI-compliant manifest.",
  "logic_type": "documentation",
  "tags": ["MiOS", "AI", "Agent Hub", "Index", "OpenAI", "SSOT"],
  "relations": {
    "depends_on": [".env.mios"],
    "impacts": [
      "ARCHITECTURE.md",
      "ENGINEERING.md",
      "system-prompt.md",
      "llms.txt"
    ]
  },
  "version": "v0.1.4"
}
```

## 🏗️ System Profile
MiOS is an immutable, AI-native workstation operating system. It provides a standardized surface for autonomous agents to interact with system resources via OpenAI-compatible APIs.

---

## 🤖 AI Agent Surface Contract (OpenAI Native)
All agents MUST target the local proxy at `http://localhost:8080/v1`.

| Endpoint | Method | Purpose | Deployed Path |
|---|---|---|---|
| /v1/chat/completions | POST | Primary System Chat | - |
| /v1/models | GET | Hardware/Model Discovery | /usr/share/mios/ai/v1/models.json |
| /v1/mcp | FS | Model Context Protocol Hub | /usr/share/mios/ai/mcp/config.json |
| /v1/embeddings | POST | Semantic Search (Local) | - |

---

## ⚖️ Immutable Appliance Laws
These laws define the system's operational boundaries. Violations cause state drift and are architectural failures.

1. **USR-OVER-ETC**: All static configuration must reside in `/usr/lib/`. `/etc/` is reserved strictly for host-specific administrator overrides.
2. **NO-MKDIR-IN-VAR**: Persistence in `/var/` is managed exclusively via `tmpfiles.d` declarations.
3. **UNPRIVILEGED-QUADLETS**: Containerized sidecars MUST execute as unprivileged users with cgroup delegation enabled.
4. **BOOTC-NATIVE**: System updates and configuration are cryptographically signed and managed via `bootc`.

---

## 📂 Environment Map (Indexed Verbs)

| Variable | Verb | Scope | Purpose |
|---|---|---|---|
| `MIOS_AI_KEY` | `SET_KEY` | AI | API Key for local inference. |
| `MIOS_AI_MODEL` | `SET_MODEL` | AI | Target model for system operations. |
| `MIOS_BASE_IMAGE` | `GET_BASE` | SYS | Root OCI image reference. |
| `MIOS_LOCAL_TAG` | `SET_TAG` | SYS | Local image identifier. |

---
*Copyright (c) 2026 MiOS. Pure FOSS. Zero Day Ready.*
