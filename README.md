# MiOS: Immutable OCI-Native Linux Distribution

MiOS is an open-source, user-defined, immutable Linux distribution packaged as a bootable OCI image. It utilizes a native Linux Filesystem Hierarchy Standard (FHS) repository structure designed for read-only root overlay patterns via `bootc` and `ostree`.

---

## 🚀 Ignition Workflow

To ignite a MiOS root overlay on a target system (optimized for Fedora), use the following one-liner:

```bash
# 1. Download and ignite the MiOS overlay
sudo curl -fsSL https://raw.githubusercontent.com/Kabuki94/MiOS/main/mios.sh -o /usr/bin/mios.sh && sudo chmod +x /usr/bin/mios.sh && sudo /usr/bin/mios.sh
```

### What happens during Ignition:
1. **FHS Mapping:** The MiOS repository structure is natively overlaid onto the host system's root (`/`).
2. **Environment Initialization:** AI environment components, system tools, and build scripts are placed into standard Linux paths.
3. **AI Self-Initialization:** The `/v1` directory is populated with OpenAI API-compliant manifests, enabling local inference servers (vLLM, LocalAI) to auto-initialize.
4. **Build Readiness:** The system is immediately ready to build, test, and deploy MiOS OCI images.

---

## 📂 Repository Structure (FHS Native)

The repository strictly follows the Linux Filesystem Hierarchy Standard to ensure seamless integration as a system overlay:

- **/usr/lib/mios/automation/**: Master build runner (`build.sh`) and numbered phase scripts.
- **/usr/lib/mios/tools/**: Internal engineering utilities and libraries.
- **/usr/bin/**: User-facing MiOS command-line tools.
- **/etc/mios/**: System configuration templates and environment overrides.
- **/var/lib/mios/**: Build artifacts, OCI image layers, and persistent state.
- **/v1/**: OpenAI API-compliant discovery root for local AI services.

---

## 🤖 AI-Native Integration

MiOS is architected for "AI-First" operations, providing a standardized interface for local FOSS AI agents:

- **/v1/models**: JSON manifest for all available local models.
- **/v1/mcp**: Configuration for Model Context Protocol (MCP) servers.
- **/v1/knowledge.json.gz**: A high-density, compressed RAG snapshot of all MiOS documentation and engineering context.

---

## 🏗 Architectural Deep-Dive

### Immutable Core (bootc & ostree)
MiOS leverages `bootc` to deliver a mathematically verifiable OS. The root filesystem is immutable, with state persistence managed via `ostree` overlays on `/var`. This ensures that every boot starts from a known-good cryptographic state, while allowing for dynamic AI model management.

### Self-Initializing AI Gateway
By consolidating AI metadata into `/v1`, MiOS provides a "Zero-Config" entry point for local inference. 
- **LocalAI** acts as the universal API shim, discovering model definitions in `/usr/share/mios/ai/models/`.
- **vLLM** provides high-throughput execution for large-scale models, bridged to the unified OpenAI-compatible API surface.

For more details, see [BOOTC-AI-PATTERNS.md](/usr/share/doc/mios/engineering/BOOTC-AI-PATTERNS.md).

---

## 🛠 Building MiOS

Once overlaid, you can build the MiOS OCI image directly from the root:

```bash
# Build the MiOS OCI image using the native Containerfile
sudo podman build -t mios:latest -f /Containerfile .
```

---

### 🌐 Project Resources
- **Repository:** [https://github.com/Kabuki94/MiOS](https://github.com/Kabuki94/MiOS)
- **License:** Apache-2.0
- **Version:** v0.1.4

---
*MiOS: The Operating System as an OCI Payload.*
