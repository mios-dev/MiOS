<!-- 🌐 MiOS Artifact | Proprietor: MiOS Project | https://github.com/mios-project/mios -->
# 🌐 MiOS — AI-Native Architectural Patterns

```json:knowledge
{
  "summary": "Formalization of AI-native structures, protocols, and synchronization patterns.",
  "logic_type": "blueprint",
  "tags": [
    "AI",
    "MCP",
    "RAG",
    "UKB",
    "Mirror-Law"
  ],
  "version": "1.0.0"
}
```

## 🧠 The Cognitive Mirror Pattern
The MiOS repository operates as a single cognitive space shared by multiple AI agents (both cloud-based and FOSS models).

### Core Protocols
1. **The Mirror Law:** All agents MUST read from and write to the shared episodic memory (`specs/memory/journal.md`).
2. **Episodic vs. Semantic:**
   - **Episodic (Journal):** Transient session logs, thoughts, and immediate actions.
   - **Semantic (Specs):** Permanent architectural blueprints, engineering patterns, and validated knowledge.
3. **Synchronization:** Handoffs occur via the journal, ensuring the "Brain" is never split across agent sessions.

## 🗂️ Unified Knowledge Base (UKB)
MiOS implements a FOSS-native, AI-parseable knowledge structure.

### Structure: `artifacts/repo-rag-snapshot.json.gz`
A compressed JSON structure optimized for RAG (Retrieval-Augmented Generation) and full-repo context ingestion.

| Component | Description |
| :--- | :--- |
| **Metadata** | Project versioning, timestamp, and FOSS compliance tags. |
| **Semantic Index** | Categorized map of Blueprints, Patterns, and Automation logic. |
| **Knowledge Nodes** | Flat array of redacted file contents with category and technology tags. |

### Generation
The UKB is auto-generated via `tools/generate-unified-knowledge.py` during build and initialization phases.

## 🛠️ MCP (Model Context Protocol) Integration
MiOS tools are being mapped to the Model Context Protocol for universal tool-calling.

- **MCP Backend:** `mios-mcp.service` (Local engine).
- **Discovery:** `.well-known/ai-tools.json` provides a manifest of available agentic tools.
- **Standards:** All MiOS CLI tools (`mios-*`) are designed to be idempotent and return machine-readable (JSON) output when requested.

## 📄 AI-Native File Formats
1. **llms.txt:** Root-level entry point for AI crawlers and LLM context loaders.
2. **json:knowledge blocks:** Embedded JSON metadata within Markdown files for high-fidelity parsing.
3. **Manifests:** Directory-level `manifest.json` files for structural discovery.

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->
