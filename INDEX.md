# MiOS System Interface — OpenAI-Native Surface (v0.1.4)

```json:knowledge
{
  "summary": "The SINGLE SOURCE OF TRUTH for MiOS. Architectural laws and API surface contracts in a unified OpenAI-compliant manifest.",
  "logic_type": "specification",
  "tags": ["MiOS", "OpenAI", "SSOT"],
  "relations": {
    "depends_on": [".env.mios"],
    "impacts": [
      "ARCHITECTURE.md",
      "ENGINEERING.md",
      "system-prompt.md"
    ]
  },
  "version": "v0.1.4"
}
```

## 1. System Profile
MiOS is an immutable, AI-native workstation operating system. It exposes a standardized surface for autonomous agents to interact with system resources via OpenAI-compatible APIs.

---

## 2. API Surface (OpenAI Native)
All system agents target the local proxy at `http://localhost:8080/v1`.

| Path | Method | Purpose | Deployed Path |
|---|---|---|---|
| `/v1/chat/completions` | POST | Primary System Interaction | - |
| `/v1/models` | GET | Inventory Discovery | `/usr/share/mios/ai/v1/models.json` |
| `/v1/mcp` | FS | Context Registry | `/usr/share/mios/ai/v1/mcp.json` |

---

## 3. Operational Invariants
1. **USR-OVER-ETC**: Persistent defaults reside in `/usr/lib/`.
2. **STATELÉSS-VAR**: Mutable state is declared via `tmpfiles.d`.
3. **UNPRIVILEGED-EXECUTION**: All agent containers execute without root privileges.
4. **BOOTC-LIFECYCLE**: System updates are managed via OCI image commits.

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
