<!-- 🌐 MiOS Artifact | Proprietor: MiOS Project | https://github.com/mios-project/mios -->
# 🐧 Linux-Native Memory Standards

```json:knowledge
{
  "summary": "Standardization of cognitive and historical memory storage using Linux-native filesystem patterns.",
  "logic_type": "blueprint",
  "tags": [
    "standards",
    "memory",
    "FOSS",
    "API-native",
    "Linux-native"
  ],
  "version": "1.0.0"
}
```

## 🏗️ Architectural Pattern: `var/lib` for Cognitive State
MiOS adopts the standard Linux Filesystem Hierarchy (FHS) for AI agent state and repository history. 

### 1. Structured Episodic Memory (The Journal)
- **Path:** `var/lib/mios/memory/journal/`
- **Format:** `vN.jsonl` (JSON Lines)
- **Standard:** Every entry is a discrete JSON object containing a schema-validated version, timestamp, agent identity, and semantic data payload (thought, action, result).

### 2. Semantic Data Persistence
Historical artifacts, research, and technical mappings are treated as **System State**.
- **Source:** Managed in `specs/` (The "usr/lib" equivalent for documentation).
- **Runtime:** Synchronized into `var/lib/mios/memory/` for live AI ingestion.

## 🤖 AI API Standardization
To ensure MiOS is "Open-Source AI API native," all memory stores MUST be:
1.  **Parseable:** No decorative headers or fluff text in the primary data store.
2.  **Schema-Aligned:** Consistent naming conventions across all JSON/JSONL artifacts.
3.  **Streamable:** JSONL format allows agents to ingest history without loading the entire file into context.

## 🛠️ Tooling Integration
The `tools/journal-sync.py` utility maintains consistency between the human-readable Markdown views and the machine-native JSONL stores.

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->
