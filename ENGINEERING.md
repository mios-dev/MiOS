# MiOS ENGINEERING — Unified Standards (Day 0)

```json:knowledge
{
  "summary": "Consolidated engineering standards, security specifications, and AI integration patterns for MiOS.",
  "logic_type": "engineering",
  "tags": ["MiOS", "Engineering", "Security", "AI"],
  "version": "v0.1.4"
}
```

## 🛡️ Security Framework

### 🧠 Execution Control
Strict binary whitelisting via `fapolicyd` (deny-by-default).
- **Authorized paths**: `/usr/bin`, `/usr/lib`, `/usr/local/bin`.
- **Trust Boundary**: `allow perm=execute : ftype=application/x-executable trust=1`.

### 🔒 Kernel Hardening
The system implements a hardened kernel posture including:
- Memory zeroing (`init_on_alloc=1`).
- Integrity lockdown (`lockdown=integrity`).
- Early-boot VFIO binding for hardware isolation.

---

## 🤖 AI Integration & Patterns

### 🔌 Programmable Interface
MiOS implements **OpenAI API** and **Model Context Protocol (MCP)** standards as its primary management plane.
- **Local Proxy**: `http://localhost:8080/v1` (LocalAI/Ollama).
- **Structured Telemetry**: Core system tools provide `--json` output for high-fidelity agent ingestion.

### 🛠️ Core Patterns
- **Cognitive Mirror**: Agents record significant actions in the episodic journal (`usr/share/mios/memory/v1.jsonl`).
- **Declarative State**: System state is managed via `tmpfiles.d` and `sysusers.d`.
- **Unprivileged sidecars**: All sidecar containers execute as unprivileged service accounts.

---

## 🛠️ System Toolchain (Indexed Verbs)

| Tool | Verb | Intent |
| :--- | :--- | :--- |
| `bootc` | `UPGRADE_CORE` | Transactional system updates. |
| `podman` | `RUN_SIDECAR` | Orchestrate unprivileged sidecars. |
| `mios-status` | `GET_STATE` | Retrieve system-wide telemetry. |

---
*Copyright (c) 2026 MiOS. Pure FOSS. Zero Day Ready.*
