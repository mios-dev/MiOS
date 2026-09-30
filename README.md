<!-- AI-hint: Project overview, technical specification, and system architecture for MiOS, an immutable container-image-based Linux workstation and sovereign local agentic AI operating system; defines the core identity, end-to-end build pipeline, OCI image lifecycle, bootc deployment, local inference lanes, agent orchestration, pgvector memory datastore, licensing, architectural laws, and engineering remediation.
     AI-related: /usr/libexec/mios/mios-build-driver, /usr/share/mios/configurator/, /usr/share/mios/mios.toml, /usr/share/mios/ai/, /usr/share/mios/ai/system.md, /usr/share/mios/llamacpp/mios-llm-light.yaml, mios-build-driver, mios-dev, mios-bootstrap, mios-build-local, mios-llm-light, mios-pgvector, mios-ceph -->
# MiOS: Immutable Container-Based Linux Workstation & Agentic Operating System

> **Architectural Specification & Scope:** Refer to [`usr/share/doc/mios/manual/thesis.md`](usr/share/doc/mios/manual/thesis.md) for the foundational design principles, execution scope, and the demarcation between deployment targets (bare-metal, virtualization) and development runtimes (Hyper-V, QEMU, WSL2).

**Phonetic Identification:** Pronounced `/maɪ.oʊ.ɛs/` (*"MyOS"*), derived as an acronym for *My Operating System*. The capitalization is a stylistic identifier and denotes no corporate or organizational entity.

**Project Classification:** MiOS is an open-source systems engineering research platform (Apache-2.0). Artifacts are synthesized from declarative build scripts, container specifications, and structured configuration manifests.

**Legal and Runtime Agreements:** Execution of any entry point (`just <target>`, `install.sh`, `install.ps1`, `Get-MiOS.ps1`, `bootstrap.{sh,ps1}`, `/usr/bin/mios-*`, or `bootc` management commands) constitutes acceptance of [`AGREEMENTS.md`](./AGREEMENTS.md), upstream software licenses ([`usr/share/doc/mios/reference/licenses.md`](usr/share/doc/mios/reference/licenses.md)), and the project attribution registry ([`usr/share/doc/mios/reference/credits.md`](usr/share/doc/mios/reference/credits.md)). Upstream trademarks and system components remain property of their respective maintainers.

---

## 1. System Overview

MiOS is an immutable, container-encapsulated Linux operating system built upon Fedora CoreOS / Universal Blue (`ucore-hci`) primitives via `bootc`. It converges a hardware-accelerated workstation with an isolated, locally hosted, OpenAI-API-compatible agentic AI operating infrastructure.

The runtime root filesystem (`/usr`) is deployed as an atomic, read-only `composefs` mount backed by `fs-verity` cryptographic verification. Operating system upgrades and rollbacks operate as atomic OCI image state transactions executed via `bootc`.

Concurrently, MiOS packages a fully localized, sovereign cognitive runtime plane directly into the base image. The AI sub-layer provides local Large Language Model (LLM) inference lanes, OpenAI-compatible ingress proxies, a deterministic multi-agent orchestration engine, and a PostgreSQL + pgvector persistent memory store. All intelligence services execute on local host hardware, operate unprivileged under dedicated system accounts, and require no egress to third-party cloud infrastructure.

### Canonical Image Reference

    ghcr.io/mios-dev/mios:latest

---

## 2. Structural Evolution and Specification Remediation

Operating system documentation often degenerates into non-technical promotional language, utilizing anthropomorphic analogies and imprecise abstractions that obscure underlying systems architecture. In earlier iterations of the MiOS documentation, imperative package management failure modes were described through unstable structural metaphors such as collapsing towers, daemon supervision was characterized as passive custodial babysitting, and the computational environment was described as an autonomous entity capable of subjective self-reasoning. Such phrasing obscures the deterministic engineering mechanics governing image assembly, cryptographic attestation, process lifecycle containment, and hardware boundary isolation.

A rigorous systems engineering specification demands that these concepts be redefined through precise operational taxonomy. Imperative package managers do not suffer from emotional uncertainty; they exhibit non-deterministic state drift, unresolvable transactional dependency graphs, and partial filesystem mutations when interrupted during pre-install or post-install scriptlet execution. Similarly, containerized inference runtimes and relational memory backends do not constitute a biological cognitive core; they function as isolated, user-space daemons communicating across POSIX loopback sockets, constrained by cgroups v2 resource envelopes, and governed by deterministic inter-process communication protocols.

The transition to a sterile, specification-compliant documentation model replaces subjective rhetoric with verifiable technical parameters. Operating system components are categorized strictly by filesystem immutability classes, Open Container Initiative (OCI) image layer hierarchies, systemd unit generation mechanics, and hardware abstraction layer interfaces.

### Technical Taxonomy & Remediation Matrix

| Legacy Colloquial Description | Technical Systems Engineering Definition | Concrete Subsystem Realization |
|---|---|---|
| Distro updates evolving like unstable block towers | Non-deterministic state divergence and broken dependency trees in mutable package managers | Declarative OCI image compilation via buildah/podman and atomic image deployment |
| Upgrades functioning like version control pulls | Atomic rootfs commit deployment using OSTree and composefs storage backends | `bootc upgrade` executing cryptographic digest validation against remote container registries |
| Operating system rolling back like a keystroke undo | Reversible bootloader targeting of immutable deployment trees via bls entries | `bootc rollback` swapping OSTree commit stubs prior to kernel initialization |
| Shipped inference daemons avoiding continuous babysitting | Supervised, unprivileged container lifecycles bound to system initialization | Declarative Podman Quadlet generation with automated restart policies under systemd |
| System operating as an integrated cognitive brain | Multi-tiered RPC pipeline routing OpenAI-compatible JSON payloads to local inference engines | Fast-swapping reverse proxy (llama-swap) dispatching execution to llama.cpp, vLLM, or SGLang |
| Dedicated gaming virtual machines with discrete GPUs | Direct hardware virtualization via kernel stub driver rebinding and VFIO memory mappings | `vfio-pci` kernel command-line device reservation coupled with KVM/QEMU and Looking Glass shared memory |

---

## 3. Host Lifecycle and Immutable Filesystem Topology

MiOS is built upon an image-mode operating system paradigm derived from Fedora CoreOS and Universal Blue's `ucore-hci`, managed natively via Red Hat's `bootc` utility. Rather than assembling the operating system on the target node via sequential, non-deterministic package installations, the entire operating system image is compiled inside a container runtime environment, validated against structural container linters, and distributed as an OCI artifact. This model enforces absolute parity between development, testing, and production bare-metal hosts.

The host storage hierarchy segregates binary objects, node configurations, and persistent state across distinct mount boundaries governed by composefs and OSTree technologies. At system initialization, the initramfs executes `ostree-prepare-root`, reading configuration directives from `/usr/lib/ostree/prepare-root.conf`. When composefs is enabled, the runtime verifies the fs-verity cryptographic digest of the root directory descriptor against the underlying OSTree object repository located in `/ostree/repo/objects`. The resulting filesystem tree mounts `/usr` as a strictly read-only, content-addressable block device.

System configuration within `/etc` retains mutability to support host-specific network bindings, authentication secrets, and hardware customizations. When an administrator executes `bootc upgrade`, the deployment client pulls the target container layers, unpacks the content into the OSTree store, and initiates a three-way merge across `/etc`. Modifications originating from the new container image are applied unless explicitly overridden by active local configurations, preventing administrative drift from silently corrupting updated base services.

All persistent host state, user data, virtualization disk images, and container storage volumes are isolated within `/var`. The root filesystem enforces a strict structural rule prohibiting arbitrary directory creation within `/var` during image assembly. Directories required by container engines, monitoring services, or agent datastores are declared via configuration files within `/usr/lib/tmpfiles.d/*.conf`. During systemd initialization, `systemd-tmpfiles-setup.service` parses these manifests and materializes required paths, permissions, and access-control lists directly on the persistent partition, guaranteeing that the immutable base image remains completely decoupled from node-specific runtime state.

### Filesystem Immutability and Lifecycle Specifications

| Filesystem Path | Immutability Class | Backing Technology | Lifecycle Update / Rollback Dynamic |
|---|---|---|---|
| `/usr` | Read-only | `composefs` over OSTree object store | Atomic replacement via digest switch; bit-for-bit identical to registry image |
| `/etc` | Read-write | Standard POSIX filesystem overlay | Three-way merge preserved across image switches; retains administrative overrides |
| `/var` | Read-write | Dedicated persistent partition | Decoupled from container image lifecycle; survives all OS upgrades and rollbacks |
| `/opt` | Read-only | Redirected or nested within `/usr` | Static component of the vendor base image; immutable at runtime |
| `/sys`, `/proc`, `/dev` | Virtual / Synthetic | Linux Kernel pseudo-filesystems | Dynamically instantiated by the kernel; non-persistent |

The build execution pipeline is implemented via a sequential file tree structure. The upstream Git repository root maps directly to the root of the deployed filesystem (`.git` IS `/`), eliminating intermediate build abstractions or indirection scripts. Build orchestration is driven by a master Containerfile that processes numbered automation scripts (`automation/[00-99]-*.sh`) in sequential order. Each step executes within an isolated container build layer, executing deterministic tasks such as package installation, SELinux policy compilation, UKI image rendering, and Container Device Interface (CDI) manifest generation. System assembly concludes with the execution of `bootc container lint`, which enforces adherence to image-mode filesystem standards before publishing the container image to the target registry.

---

## 4. The Architectural Laws

System contributions, automated builds, and image modifications must strictly comply with the architectural law registry. The canonical source is `usr/share/mios/mios.toml` under `[laws]` -- the single registry of the id, slug, and enforcement-target mapping -- with `automation/98-drift-checks.sh` and `automation/99-postcheck.sh` executing the checks at build time (a failing law aborts the build) and `mios-gate law-enforcers` verifying that every registered enforcement target resolves to live code. The v0.3.0 registry defines sixteen laws:

| # | Invariant Identifier | Architectural Enforcement Mandate |
|---|---|---|
| **1** | `USR-OVER-ETC` | All static vendor assets, service definitions, and configurations must reside exclusively in `/usr/lib/<component>.d/` or `/usr/share/`. The `/etc/` directory is reserved strictly for local administrator overrides. |
| **2** | `NO-MKDIR-IN-VAR` | The `/var/` directory hierarchy must never be modified or populated at image build time. All runtime directories in `/var/` must be declared declaratively via `usr/lib/tmpfiles.d/*.conf`. |
| **3** | `BOUND-IMAGES` | Container images referenced by system Quadlets must be staged and symlinked into `/usr/lib/bootc/bound-images.d/` to guarantee offline image survival and atomic co-deployment with the host. |
| **4** | `BOOTC-CONTAINER-LINT` | The final layer of every container build must pass `bootc container lint` with exit code 0. Architectural validation failures immediately abort the build pipeline. |
| **5** | `UNIFIED-AI-REDIRECTS` | Every agent, tool, script, and web console must address the AI plane strictly through `MIOS_AI_ENDPOINT`, `MIOS_AI_MODEL`, and `MIOS_AI_KEY`. Hardcoded external endpoints, vendor URLs, or bypassing loopback proxies is forbidden. |
| **6** | `UNPRIVILEGED-QUADLETS` | System Quadlets must declare non-root service credentials (`User=`, `Group=`, `Delegate=yes`). Root execution exists only for the exceptions registered in `[security.privileged_quadlets]`, with the audit rationale in each unit's header. |
| **7** | `NO-HARDCODE` | No operator-tunable value -- model identifiers, ports, versions, dates -- may be hardcoded. All such values resolve through the `mios.toml` configuration cascade; hand-pinned version literals fail the build (SBOM-not-hardcode / float-latest, ADR-0003 and ADR-0012). |
| **8** | `SSOT-PROJECTION` | Files derived from `mios.toml` are generated artifacts and are drift-gated. Every generator must be registered in `[laws.projection_registry]`. |
| **9** | `ONE-CANONICAL-NAME` | Every referenced `MIOS_*` variable must close against the set the system emits (`referenced ⊆ emitted`), enforced by the variable-closure ledger. |
| **10** | `BARE-SAFE-ENV` | The baked `install.env` render must be bare `KEY=value`, secret-free, and clean under `set -u`, proven by a `system-sync-env --dry-run` execution at postcheck. |
| **11** | `SECRETS-NEVER-IN-ENV` | Secret keys registered in `[security.secret_keys]` must never be materialized into environment files; secret-bearing files ship with `0600` permissions. |
| **12** | `BAKE-NOT-FETCH` | Artifacts are baked into the image at build time under bake-DAG integrity checks; the first-boot path degrades open instead of fetching from the network. This law carries the offline-first guarantee. |
| **13** | `NATIVE-DROPINS` | The native resolvers (`mios-resolver`, `miosd`) and the shell/Python fallback resolvers must remain in proven twin parity under differential fixtures. |
| **14** | `TARGET-LANGUAGES` | Automation consolidates on the declared target languages. Legacy C# survives only through the `[laws.target_languages]` grandfather registry. |
| **15** | `DOUBLE-REPO-TRIPLE-CHECK` | Changes touching surfaces shared between `mios.git` and `mios-bootstrap.git` are verified in both repositories; cross-repo parity is drift-checked. |
| **16** | `ONE-TEMPLATE-PER-TYPE` | Exactly one template exists per file type, projected from the SSOT and validated by `check-template-conformance` (ADR-0011). |

The generated, always-current law-to-enforcer table ships in [`llms.txt`](llms.txt); the decision record behind each law is indexed in [`ADR.md`](ADR.md) from the ADRs baked at `usr/share/doc/mios/adr/`.

---

## 5. Workstation Subsystems & Virtualization

    +-----------------------------------------------------------------------------------+
    |                                  MiOS Host OS                                     |
    +------------------------------------+----------------------------------------------+
    |     Workstation / Infrastructure   |              Local AI Plane                  |
    |  - GNOME 50 (Wayland) + Phosh      |  - Local Inference (llama.cpp, vLLM, SGLang) |
    |  - KVM/QEMU + libvirt + VFIO-PCI   |  - Unified Endpoint: MIOS_AI_ENDPOINT        |
    |  - Looking Glass B7 (KVMFR DMA)    |  - Orchestrator (agent-pipe) + Hermes Gateway|
    |  - Container Device Interface (CDI)|  - Memory: PostgreSQL 16 + pgvector          |
    |  - k3s Kubernetes + Ceph Storage   |  - Tool Interfaces: MCP Servers + A2A Bus    |
    |  - Kernel Lockdown + SELinux       |  - Strict JSON Schemas + Rust Keyring Guard  |
    +------------------------------------+----------------------------------------------+
    |            Immutable Core: Fedora bootc + composefs (Read-Only /usr)              |
    +-----------------------------------------------------------------------------------+

### 5.1 Display Server & Desktop Environment
* **Primary Desktop:** GNOME 50 running natively under Wayland.
* **Secondary / Mobile Shell:** Phosh integration for high-DPI tablets, touch panels, and remote desktop protocol (RDP) headless sessions.
* **Mobile Terminal Optimization:** iOS Blink Shell compatibility via `Shift+Tab` backtab pass-through, `extkeys` protocol, and touch shortcuts defined in `usr/share/mios/tmux/blink-mobile-keys.tmux.conf`.

### 5.2 Hardware Acceleration & CDI Plumbing
* **Multi-Vendor Support:** Native integration for NVIDIA (CUDA/NVENC), AMD (ROCm/HIP), and Intel (oneAPI/iGPU).
* **Container Device Interface (CDI):** Hardware device nodes, capability flags, and driver libraries are dynamically mapped into unprivileged containers via generated CDI definitions (`/etc/cdi/` and `/var/run/cdi/`), eliminating host-level `--device` mapping flags.

### 5.3 Hardware Virtualization & Shared-Memory Display
* **Hypervisor Layer:** Type-1 KVM virtualization orchestrated via QEMU and `libvirt`.
* **I/O Virtualization:** Pre-staged kernel command-line arguments (`usr/lib/bootc/kargs.d/`) configuring IOMMU groups (`intel_iommu=on` or `amd_iommu=on`) and `vfio-pci` stubbing for discrete PCIe GPU passthrough prior to host graphics driver initialization.
* **Low-Latency Inter-VM Frame Relay:** Image-baked Looking Glass B7 client integration utilizing the KVMFR shared-memory kernel driver (`/dev/kvmfr0`) for high-throughput zero-copy frame retrieval from passthrough virtual machines.

### 5.4 Cross-Platform Subsystems & Progress Tracking
MiOS engineering addresses specific integration and lifecycle constraints within hybrid virtualization environments:
* **Pre-Logon Service Execution (WSL Issue #11280):** Implemented pre-logon system service management using custom autounattend routines, allowing MiOS container services and systemd initialization units to execute prior to interactive Windows desktop sign-in.
* **Wayland & Display Propagation (WSL Issue #12436):** Introduced environmental variable propagation hooks within user session managers. Capturing active `DISPLAY` and `WAYLAND_DISPLAY` runtime socket references and exporting them directly into systemd user activation environments guarantees that graphical background daemons launch within WSLg without socket failures.

### 5.5 Hyperconverged Edge Clustering
* **Containerized Kubernetes:** Single-node or edge-clustered `k3s` integration deployed via managed systemd Quadlet definitions.
* **Distributed Storage:** `mios-ceph` micro-cluster storage fabric packaged directly within the host OCI image, providing block and object storage without re-imaging.

### 5.6 Defense-in-Depth Security Baseline
* **Mandatory Access Control:** SELinux targeted policy operating strictly in `Enforcing` mode.
* **Execution Whitelisting:** `fapolicyd` configured in deny-by-default mode for untrusted binaries outside verified composefs paths.
* **Peripheral Access Control:** `USBGuard` daemon restricting unauthorized USB interface descriptors and keystroke-injection vectors.
* **Kernel & Module Sealing:** Linux Kernel Lockdown in `integrity` mode, Machine Owner Key (MOK) cryptographic module signing, and read-only kernel sysctls.
* **Network & Host IPS:** CrowdSec deployed in sovereign localized mode.
* **Rust Native Boundaries:** Tokenized system execution and secret ingestion handled through static Rust binaries (`tools/native/`) leveraging Linux Kernel Keyrings and direct `execve` boundaries.

---

## 6. Podman Quadlet Service Topology & Logically Bound Container Management

Microservices and local runtime infrastructure running on MiOS are declared via Podman Quadlets rather than monolithic compose files or external container orchestration daemons. Quadlets extend the systemd unit model by introducing container-specific declarative tables (`[Container]`, `[Image]`, `[Network]`, `[Volume]`) into `.container` specification files. During host boot or when triggering `systemctl daemon-reload`, the Quadlet generator parses files situated in `/usr/share/containers/systemd/` and dynamically synthesizes standard systemd service units, directly mapping container lifecycles to the host process tree.

To ensure that the local operational stack functions completely offline and remains immune to remote registry outages, MiOS uses bootc logically bound images. Rather than relying on floating images that must be retrieved over the network at first execution via `podman pull`, logically bound images are coupled directly to the host operating system lifecycle. Quadlet container definitions situated in `/usr/share/containers/systemd/` are symlinked into `/usr/lib/bootc/bound-images.d/`.

During base image compilation or host transitions executed via `bootc upgrade`, the bootc engine parses these symlinks, identifies the container images declared within the `Image=` fields, and pulls the target image layers directly into a dedicated, host-managed storage repository at `/usr/lib/bootc/storage`. To instruct Podman to resolve images from this immutable store without duplicating layers into `/var/lib/containers`, each Quadlet specification includes the parameter:

    GlobalArgs=--storage-opt=additionalimagestore=/usr/lib/bootc/storage

Logically bound images are updated atomically with the base operating system. If a host update is rolled back via `bootc rollback`, the corresponding logically bound container images associated with that rollback target are retained and instantly reactivated, preventing version skew between the host operating system and its application microservices. Image pruning is managed by bootc; when a Quadlet reference is dropped from `/usr/lib/bootc/bound-images.d/`, the unreferenced image layers inside `/usr/lib/bootc/storage` are marked for garbage collection.

Privilege escalation within containerized workloads is restricted by system security policy. All standard service Quadlets declare non-root user execution envelopes via `User=` and `Group=` directives, accompanied by cgroup control delegation via `Delegate=yes`. Root execution is permissible only for the exceptions registered in `[security.privileged_quadlets]` -- the Ceph/RadosGW storage fabric, `mios-k3s`, the Forgejo runner, the PXE hub, the webtools pod, Redis, the heavy GPU lanes, and the coderun sandbox -- each carrying its audit rationale in the unit file header.

### Quadlet Service Specification Table

| Quadlet Unit File | Upstream Image Reference | Port Key & Bindings | Memory & Resource Constraints | Privilege & Capability Isolation |
|---|---|---|---|---|
| `mios-llm-light.container` | `ghcr.io/mostlygeek/llama-swap:cuda` | `llm_light` (8500) | Dynamic VRAM management; CPU fallback thread limits | Unprivileged UID; CDI passthrough for GPU compute |
| `mios-llm-heavy.container` | `docker.io/vllm/vllm-openai:latest` | `vllm` (8520) | Gated activation; multi-GPU tensor parallel allocation | Unprivileged UID; direct device allocation |
| `mios-pgvector.container` | `docker.io/pgvector/pgvector:latest` | `pgvector` (8600 host / 5432 in-container) | Shared memory allocation; persistent volume mount | Dedicated database system user; no network egress |
| `mios-agent-pipe.container` | `mios-agent-pipe:latest` | `agent_pipe` (8700) | Low latency, stateless async task router | Unprivileged UID; network loopback binding only |
| `mios-hermes.container` | `mios-hermes:latest` | `hermes` (8720) | Tool execution loop; process sandbox boundaries | Rootless execution; drop all Linux capabilities |
| `mios-searxng.container` | `docker.io/searxng/searxng:latest` | `searxng` (8800) | Read-only local network search aggregator | Dedicated non-login service user; isolated egress |
| `mios-k3s.container` | `docker.io/rancher/k3s:${MIOS_VERSION_K3S}` | `k3s_api` (8450) | Host resource reservation; cluster control plane | Privileged container; required host namespace access |
| `mios-ceph.container` | `quay.io/ceph/ceph:${MIOS_VERSION_CEPH}` | `radosgw` (8470) / `ceph_dashboard` (8460) | Block storage management; cluster data replication | Privileged container; host block device manipulation |

---

## 7. Local AI Architecture (The Cognitive Substrate)

All internal AI components, developer utilities, and user tools communicate with a single loopback target defined by the environment variable `MIOS_AI_ENDPOINT` (default: `http://localhost:8700/v1`, resolved from the SSOT `agent_pipe` port).

    +------------------------------------------------------------------------------------+
    |                                Client Applications                                 |
    |       (Open WebUI :8200, CLI Tools, Emacs, Neovim, External OpenAI Clients)        |
    +-----------------------------------------+------------------------------------------+
                                              |
                                              v  MIOS_AI_ENDPOINT (:8700/v1)
    +------------------------------------------------------------------------------------+
    |                             Agent Orchestration Layer                              |
    |  +------------------------------------------------------------------------------+  |
    |  | mios-agent-pipe (:8700): Dynamic Router, Decomposer & Dispatch Gateway      |  |
    |  +------------------------------------------------------------------------------+  |
    |  | mios-hermes (:8720): OpenAI Agent Gateway (Session State, Tool-Loop, Skills) |  |
    |  +------------------------------------------------------------------------------+  |
    |  | mios-prefilter (:8710): Static Prompt Analysis & Fan-Out Decomposition Hinting|  |
    +-----------------------------------------+------------------------------------------+
                                              |
                       +----------------------+----------------------+
                       |                                             |
                       v                                             v
    +------------------------------------+        +--------------------------------------+
    |          Inference Lanes           |        |           Tool & Data Plane          |
    |  - mios-llm-light (:8500):         |        |  - Datastore: mios-pgvector (:8600)  |
    |    llama.cpp + llama-swap proxy;   |        |    Relational memory, sessions, tool |
    |    text generation & nomic-embed-  |        |    logs, vector semantic recall      |
    |    text embeddings                 |        |  - Protocols: Model Context Protocol |
    |  - mios-llm-heavy (:8520):         |        |    (MCP) tool servers + A2A bus      |
    |    vLLM engine (VRAM-gated)        |        |  - Search: Local SearXNG instance    |
    |  - mios-llm-heavy-alt (:8530):     |        |  - Code Mode: opencode-gateway       |
    |    SGLang engine (VRAM-gated)      |        |    isolated execution council        |
    +------------------------------------+        +--------------------------------------+

### 7.1 Inference Routing Lanes
System inference lanes are cataloged by operational function rather than upstream binary names:
* **Primary Lane (`mios-llm-light`, Port: `8500`):** Multi-model inference engine based on `llama.cpp` managed by the `llama-swap` proxy container (`ghcr.io/mostlygeek/llama-swap:cuda`). Automatically loads, swaps, and evicts model weights based on demand; pages inactive context slots to disk; serves text generation, code assistance (`mios-opencode`), and high-throughput vector embeddings via `nomic-embed-text` (`/v1/embeddings`). Model configuration is defined in [`usr/share/mios/llamacpp/mios-llm-light.yaml`](usr/share/mios/llamacpp/mios-llm-light.yaml).
* **High-Throughput GPU Lane (`mios-llm-heavy`, Port: `8520`):** vLLM inference backend optimized for large parameter weights, continuous batching, and tensor parallelism. Inactive by default; enabled via configuration when host VRAM meets allocation thresholds.
* **Alternative GPU Lane (`mios-llm-heavy-alt`, Port: `8530`):** SGLang inference backend providing RadixAttention cache optimizations for complex multi-turn reasoning workflows.
* **Worker Swarm Nodes (`mios-llm-worker@`):** Template-instantiated systemd services allocating dedicated single-model workers across distributed compute devices.

### 7.2 Agent Orchestration Pipeline
* **`mios-agent-pipe` (Port: `8700`):** Core routing and dispatch intermediary connecting client interfaces (Open WebUI, messaging shims, shell completions) to downstream execution units. Handles prompt triage, task decomposition, and inter-service fan-out.
* **`mios-hermes` (Port: `8720`):** Primary agent state machine implementing the OpenAI tool-calling loop, active execution sessions, dynamic skill loading, and OS-control operations.
* **`mios-prefilter` (Port: `8710`):** Low-overhead prompt analyzer injecting contextual hints and pipeline routing metadata prior to primary inference.

### 7.3 Unified Memory & Persistence
* **Datastore (`mios-pgvector`, Port: `8600` host / `5432` in-container):** Centralized PostgreSQL 16 instance utilizing the `pgvector` extension. Houses system-wide episodic agent memory, conversation session trees, structured tool telemetry, execution scratchpads, and the canonical `knowledge` vector base.
* **Vector Embeddings:** Ingestion vectors are generated locally via `nomic-embed-text` through the primary inference lane, enforcing cryptographic data sovereignty.

### 7.4 Tool Execution, Discovery & Federation
* **Model Context Protocol (MCP):** Unified schema standard exposing system diagnostics, file system access, and package automation to local agents via JSON-RPC primitives over stdio and HTTP.
* **Agent-to-Agent (A2A) Interface:** Federated discovery and delegation protocol permitting decoupled local agents to negotiate and dispatch tasks to peer units.
* **Local Web Search:** Privacy-preserving retrieval engine backed by an in-image SearXNG instance (SSOT port key `searxng`, 8800), preventing parameter leakage to external commercial search engines.
* **Dynamic Code Execution:** Host mutations and untrusted script execution are routed through `opencode-gateway` into isolated, Landlock- and seccomp-restricted sandboxes.
* **AI Metadata Discovery System:** During image assembly, `/usr/libexec/mios/mios-ai-metadata.py` indexes file-level metadata tags (`AI-hint`, `AI-related`, `AI-functions`) into `/usr/share/mios/ai/v1/metadata.json` for deterministic tool discovery.

### 7.5 Safety Boundaries and Isolation Layers
1. **Strict JSON Schema Validation:** Schemas declared in `/usr/lib/mios/schemas/` enforce strict validation (`strict: true`, `additionalProperties: false`), preventing argument hallucination and malformed JSON payloads.
2. **TypeScript Type Discrimination:** Discriminated unions defined in `/usr/lib/mios/ts/` enforce type safety across agent messaging channels and routing layers.
3. **Rust Static Mediation Binaries:** Host-mutating operations are mediated by statically compiled Rust binaries located in `tools/native/`. These binaries bypass standard shell interpreters, enforcing strict tokenized parsing via POSIX `execve` system calls to eliminate prompt-injection-driven command injection.
4. **Kernel Keyring Secret Isolation:** Administrative credentials, API keys, and sensitive tokens are retained within the Linux Kernel Keyring (`keyctl`) and exposed to authorized sub-processes via inherited file descriptors, preventing credential exfiltration into agent context windows.

---

## 8. The "Repo-as-Root" Invariant & FHS Mapping

MiOS enforces a strict 1:1 structural equivalence: **the Git repository root is the deployed filesystem root (`.git` IS `/`)**.

    / (Repository Root & System Target)
    ├── usr/
    │   ├── lib/
    │   │   ├── bootc/kargs.d/             # Statically staged kernel arguments (IOMMU, VFIO, Lockdown)
    │   │   ├── bootc/bound-images.d/      # Symlinks defining logically bound container workloads
    │   │   ├── mios/schemas/              # Strict OpenAI JSON Schema definitions
    │   │   ├── mios/ts/                   # TypeScript type-safe discriminated union manifests
    │   │   └── systemd/system/            # Vendor systemd units and timer profiles
    │   ├── libexec/mios/                  # Internal executable helper scripts and pipeline drivers
    │   └── share/
    │       ├── containers/systemd/        # System-level Podman Quadlet definitions
    │       ├── doc/mios/                  # Comprehensive system documentation
    │       └── mios/
    │           ├── ai/                    # Agent prompts, models.json, mcp.json, tool registries
    │           ├── configurator/          # mios.html standalone graphical configuration interface
    │           ├── llamacpp/              # Inference routing maps and hardware model tables
    │           └── mios.toml              # Single Source of Truth (SSOT) default configuration
    ├── etc/
    │   └── mios/                          # Administrator host-specific overrides
    ├── var/
    │   └── lib/                           # Mutable persistent application directories (declared via tmpfiles.d)
    └── automation/                        # Numeric multi-phase image build automation scripts ([NN]-*.sh)

No intermediate staging directories, external templating engines, or non-FHS build wrappers are used. Changes checked into paths under `usr/` or `etc/` compile directly to those exact targets within the OCI container image.

---

## 9. System Configuration & Governance

System parameters are declared across a hierarchical three-layer override model evaluated at boot and runtime:

    [Vendor Baseline]          -->  [Host Configuration]  -->  [User Configuration]
    /usr/share/mios/mios.toml       /etc/mios/mios.toml        ~/.config/mios/mios.toml
    (Immutable Image Root)          (Machine Specific)         (Per-User Profile)

The vendor file `/usr/share/mios/mios.toml` serves as the Single Source of Truth (SSOT). Users customize their deployments by generating `~/.config/mios/mios.toml`:

    [user]
    name     = "operator"
    hostname = "workstation-node"

    [ai]
    model              = "granite4.1:8b"
    endpoint           = "http://localhost:8700/v1"
    key                = ""
    system_prompt_file = "~/.config/mios/system-prompt.md"

    [flatpaks]
    install = [
      "org.mozilla.firefox",
      "org.videolan.VLC"
    ]

    [env]
    EDITOR = "nvim"
    PAGER  = "less"

### CLI Governance Utilities
* `just init-user-space`: Copies the vendor template to `~/.config/mios/mios.toml`.
* `just edit`: Opens the active configuration in the system `$EDITOR`.
* `just show-env`: Resolves the layered TOML properties and outputs the active system environment variables.
* `sudo mios sync-env`: Regenerates `/etc/mios/install.env` from the resolved `mios.toml` values to align systemd daemon runtimes.

---

## 10. Build Pipeline & Deployment

### 10.1 Deployment to Existing bootc Hosts

To rebase an existing Fedora bootc installation onto MiOS:

    sudo bootc switch ghcr.io/mios-dev/mios:latest
    sudo systemctl reboot

### 10.2 Windows Bootstrap (Provisioning Host)

To provision a local development machine, configure virtual disk allocations, setup WSL2/Hyper-V, and initiate container compilation from Windows:

    powershell -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/mios-dev/mios-bootstrap/main/Get-MiOS.ps1 | iex"

The script executes the following stages:
1. Validates host CPU virtualization flags, RAM capacity, and storage blocks.
2. Allocates partition `M:\` (size resolved from the `mios.toml` `[bootstrap.host_storage]` defaults, ~256 GB NTFS) dedicated to the build root.
3. Provisions the container runtime engine and stages the `MiOS-DEV` builder environment.
4. Clones `mios.git` and `mios-bootstrap.git`, then chains into `/usr/libexec/mios/mios-build-driver` for the OCI build.
5. Outputs raw disk images (`.raw`, `.vhdx`), an Anaconda installer `.iso`, and WSL2 rootfs archives.

### 10.3 Linux Native Compilation & Image Output

Linux builds require a functional `podman` installation and the `just` command runner:

    # Clone source repository
    git clone https://github.com/mios-dev/MiOS.git
    cd MiOS

    # Validate build requirements and container dependencies
    just preflight

    # Execute OCI container image build
    just build

    # Generate deployment artifacts
    just iso     # Bootable installation media
    just qcow2   # KVM / OpenStack image
    just vhdx    # Hyper-V virtual disk
    just wsl2    # WSL2 sideload distribution

The compilation process is managed by `automation/` shell scripts running in strict numeric sequence (`00-mios-pre-bootc.sh` through `99-postcheck.sh`) inside an isolated Buildah/Podman context.

---

## 11. Repository Documentation Index

All documentation conforms to the standard Linux FHS hierarchy under `/usr/share/doc/mios/` and utilizes structured categorization:

| Target File | System Domain & Scope |
|---|---|
| [`usr/share/mios/ai/INDEX.md`](usr/share/mios/ai/INDEX.md) | Canonical contract for AI architecture, ports, and OpenAI compatibility. |
| [`usr/share/mios/ai/system.md`](usr/share/mios/ai/system.md) | Canonical baseline system prompt for internal agents. |
| [`usr/share/mios/ai/v1/models.json`](usr/share/mios/ai/v1/models.json) | Local `/v1/models` manifest cataloging active inference identifiers. |
| [`usr/share/mios/ai/v1/mcp.json`](usr/share/mios/ai/v1/mcp.json) | Registry of active Model Context Protocol (MCP) server endpoints. |
| [`usr/lib/mios/schemas/`](usr/lib/mios/schemas/) | Strict JSON Schema definitions (`strict: true`) for tool inputs and outputs. |
| [`usr/lib/mios/ts/`](usr/lib/mios/ts/) | TypeScript type declarations and discriminated unions for agent actions. |
| [`usr/share/doc/mios/concepts/architecture.md`](usr/share/doc/mios/concepts/architecture.md) | Detailed filesystem, process isolation, and hardware topology. |
| [`usr/share/doc/mios/guides/engineering.md`](usr/share/doc/mios/guides/engineering.md) | Script conventions, coding standards, and build pipeline rules. |
| [`usr/share/doc/mios/guides/security.md`](usr/share/doc/mios/guides/security.md) | Kernel lockdown parameters, SELinux policies, and fapolicyd whitelists. |
| [`usr/share/doc/mios/guides/self-build.md`](usr/share/doc/mios/guides/self-build.md) | Day-0 through Day-N autonomous image build and self-replication procedures. |
| [`usr/share/doc/mios/guides/deploy.md`](usr/share/doc/mios/guides/deploy.md) | `bootc` transactional operations, rollback hooks, and update policies. |
| [`usr/share/doc/mios/reference/api.md`](usr/share/doc/mios/reference/api.md) | Detailed specification of the local OpenAI REST endpoints. |
| [`usr/share/doc/mios/reference/PACKAGES.md`](usr/share/doc/mios/reference/PACKAGES.md) | Exhaustive catalog of package dependencies and architectural rationales. |
| [`usr/share/doc/mios/reference/licenses.md`](usr/share/doc/mios/reference/licenses.md) | Comprehensive upstream component licensing inventory. |

Machine-readable documentation summaries are maintained in [`llms.txt`](llms.txt) and [`llms-full.txt`](llms-full.txt). Tool discovery entry points ([`AGENTS.md`](AGENTS.md), [`CLAUDE.md`](CLAUDE.md), [`GEMINI.md`](GEMINI.md)) map directly to `/usr/share/mios/ai/system.md`.

---

## 12. Development Status & Milestone Tracking

* **Baseline Version:** `v0.3.0` (Active Development).
* **Base Platform:** Fedora CoreOS / uCore-HCI baseline (`bootc`).
* **CI Quality Gate:** Strict compliance enforcement via `bootc container lint`, `shellcheck`, and `99-postcheck.sh`.
* **State of Migration:** Legacy datastores (Qdrant, SurrealDB) and standalone Ollama daemon instances have been retired. Active services use PostgreSQL 16 + `pgvector` (`mios-pgvector`) and `llama-swap`/`llama.cpp` (`mios-llm-light`). All tool routing interfaces conform strictly to the Model Context Protocol (MCP) and the OpenAI API schema.

Contributions must adhere to the engineering standards codified in [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

## 13. License & Legal Attribution

MiOS is distributed under the **Apache License, Version 2.0**. Refer to the [`LICENSE`](LICENSE) file for terms of use. Upstream software components bundled within the generated container image remain governed by their respective individual licenses as cataloged in [`usr/share/doc/mios/reference/licenses.md`](usr/share/doc/mios/reference/licenses.md).

`'MiOS'` is a project identification mark; the lowercase identifier `mios` is reserved for technical nomenclature including system paths, binary names, package keys, and environment variables.
