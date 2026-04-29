<!-- 🌐 MiOS Artifact | Proprietor: MiOS Project | https://github.com/mios-project/mios -->
# 🌐 MiOS
```json:knowledge
{
  "summary": "Standardized AI tool interface for MiOS CLI commands.",
  "logic_type": "documentation",
  "tags": [
    "MiOS",
    "engineering",
    "AI",
    "API"
  ],
  "relations": {
    "depends_on": [
      "/.well-known/ai-tools.json"
    ],
    "impacts": [
      "/usr/bin/mios-update"
    ]
  }
}
```
> **Proprietor:** MiOS Project
> **Infrastructure:** Self-Building Infrastructure (Personal Property)
> **License:** Licensed as personal property to MiOS Project
> **Source Reference:** MiOS-Core-v0.1.1
---

# 🔌 Programmable AI Tool Interface

MiOS implements the **OpenAI Function Calling** and **Model Context Protocol (MCP)** standards to allow FOSS-aligned AI agents (Ollama, LocalAI, LiteLLM) to natively interact with system management tools.

## 🛠️ Implementation Architecture

To ensure "Native to FOSS AI API patterns," MiOS provides:
1.  **JSON Schema Definitions:** Located at `/.well-known/ai-tools.json`, these schemas define the parameters and expected outputs for MiOS CLI tools.
2.  **MCP Integration:** MiOS tools are designed for ingestion by **MCP Servers**, which have become the industry standard in 2026 for connecting LLMs to external systems.
3.  **Structured CLI Output:** Core tools (e.g., `mios-update`) support a `--json` flag to return machine-readable data, eliminating interactive prompts or decorative text that breaks LLM tool-calling logic.

## 🤖 Supported Tools

### 1. `mios_update`
- **CLI Command:** `mios-update --json [--check-only]`
- **Description:** Checks for or applies system updates via `bootc`.
- **Output Schema:**
  ```json
  {
    "status": "up_to_date | staged | error",
    "current_image": "ghcr.io/...",
    "message": "Human-readable status message"
  }
  ```

## 🔌 Integration Guide (LiteLLM/LocalAI)

To expose MiOS tools to your local LLM, configure your proxy to map the function names in `ai-tools.json` to the corresponding shell commands.

### Example Tool Definition (Python/OpenAI SDK)
```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "mios_update",
            "description": "Update the MiOS workstation",
            "parameters": { ... }
        }
    }
]
```

### Execution Mapping
- **Input:** Agent calls `mios_update(check_only=true)`
- **Mapping:** Proxy executes `sudo /usr/bin/mios-update --json --check-only`
- **Return:** Proxy feeds the JSON stdout back to the LLM.

## 📝 Conclusion
By adhering to OpenAI-compatible schemas, MiOS allows any standard AI agent to manage the workstation autonomously while preserving architectural purity and FOSS alignment.

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-project/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->
