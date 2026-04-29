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

# 🤖 MiOS AI Integration


This document outlines the AI shell assistant and local LLM integration within MiOS.

## 🚀 Overview
MiOS features a modern, local-first AI stack designed for high-performance coding, system automation, and mathematical reasoning. The stack is fully containerized and integrated directly into the system shell.

## 🛠️ Core Components

### 1. Ollama (Local LLM Backend)
**Ollama** runs as a containerized service managed by systemd Quadlets.
- **Service Name:** `ollama.service`
- **Model Path:** `/var/lib/ollama` (Persistent)
- **API Endpoint:** `http://localhost:11434`
- **Acceleration:** Automatic NVIDIA GPU passthrough (via `nvidia-container-toolkit`).

### 2. AIChat & AIChat-NG (Shell Assistants)
Two powerful Rust-based CLI tools function as the primary interfaces for the LLM stack.
- **`aichat`**: The standard all-in-one LLM CLI.
- **`aichat-ng`**: An enhanced fork featuring response editing and optimized Ollama support.

## 🧠 Model Standards
The system defaults to high-performance, open-license models:
- **Default Coding Model:** `deepseek-coder-v2:lite` (Apache 2.0)
  - *Optimized for:* Windows PowerShell, Linux Bash, Python, and C++.
  - *Configuration:* Pre-pulled and embedded during local builds.
- **Recommended Math Model:** `qwen2.5` (Apache 2.0)
  - *Optimized for:* Algorithmic reasoning and logic.

## ⌨️ Usage & Management

### MiOS CLI Commands
The `mios` tool provides simplified management for the AI stack:
- `mios ai`: Display status and version information.
- `mios ai-logs`: View real-time logs from the Ollama backend.
- `mios ai-pull <model>`: Download new models (defaults to `deepseek-coder-v2:lite`).

### Shell Integration
Both `aichat` and `aichat-ng` are pre-configured to use the local Ollama instance.
- Run `aichat "How do I list listening ports in PowerShell?"` for instant command generation.
- Run `aichat-ng` to enter an interactive REPL session with persistent history.

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-project/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->
