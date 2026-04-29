<!-- 🌐 MiOS Artifact | Proprietor: MiOS Project | https://github.com/mios-project/mios -->
# 🧠 MiOS Cognitive Journal (Episodic Memory)

```json:knowledge
{
  "summary": "Human-readable interface for the structured episodic memory store.",
  "logic_type": "memory",
  "tags": [
    "journal",
    "episodic",
    "API-native"
  ],
  "storage": "var/lib/mios/memory/journal/v1.jsonl",
  "format": "JSONL (API-Native / FOSS AI Standard)"
}
```

> **IMPORTANT:** This file is a rendered view of the **Single Source of Truth** for MiOS episodic memory, located at `var/lib/mios/memory/journal/v1.jsonl`. 
> 
> For AI agents, it is recommended to parse the JSONL store directly for high-fidelity context ingestion.

---

## 🏛️ Structured Memory Patterns
MiOS uses a Linux-native filesystem pattern for its cognitive history, following the standard log-rotation and data-storage conventions found in enterprise Linux environments.

| Tier | Path | Purpose |
| :--- | :--- | :--- |
| **Data Store** | `var/lib/mios/memory/journal/v1.jsonl` | API-Native append-only JSON stream. |
| **Interface** | `specs/memory/journal.md` | Human-readable navigation and context. |
| **Sync** | `tools/journal-sync.py` | Bi-directional synchronization between formats. |

---

## 📅 Recent Entries (Rendered)

### [2026-04-27 05:20:00 UTC] [AI: Native CLI]
- **Type:** KNOWLEDGE MAPPING & FLATTENING
- **Thought:** Fulfilled the directive to flatten historical knowledge into an AI-native, FOSS-compliant structure.
- **Action:** Created `specs/engineering/2026-04-27-Artifact-ENG-005-Technology-Patterns.md` as an AI-Native map of repository technologies.
- **Result:** Completed historical knowledge flattening directive.

### [2026-04-27 04:55:00 UTC] [AI: Native CLI]
- **Type:** BUILD FIX — GITHUB ACTIONS SYNC
- **Thought:** Investigated GitHub Actions build failure where `home/` and `var/` directories were missing from the build context.
- **Action:** Created `.gitkeep` files in user-space subdirectories.
- **Result:** Build context integrity restored for remote runners.

... [Historical entries moved to structured JSONL store] ...

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->

### [2026-04-27 05:40:00 UTC] [AI: Native CLI]
- **Type:** ARCHITECTURE — STRUCTURED MEMORY
- **Thought:** Refactored journaling to be API-native, programmatically parseable, and Linux-native.
- **Action:** Created `var/lib/mios/memory/journal/v1.jsonl` as the machine-native episodic store.
- **Action:** Created `tools/journal-sync.py` to migrate legacy Markdown to JSONL.
- **Action:** Documented `specs/core/2026-04-27-Artifact-COR-006-Linux-Native-Memory-Standards.md`.
- **Result:** Cognitive history is now structured for high-fidelity AI API ingestion while adhering to Linux FHS (`var/lib`).
