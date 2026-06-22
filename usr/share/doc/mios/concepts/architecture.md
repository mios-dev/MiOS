<!-- AI-hint: Defines the MiOS system architecture end-to-end -- the bootc/OCI image structure and lifecycle, CDI-based GPU acceleration, zero-trust security posture, the FHS-compliant filesystem layout, and the local agentic-AI surface (inference lanes -> agent gateway -> pgvector memory -> MCP/A2A).
     AI-related: mios-gpu, mios-llm-light, mios-llm-heavy, mios-pgvector, hermes-agent.service, mios-agent-pipe.service, localhost:8642, localhost:8640, localhost:11450 -->
# 'MiOS' Architecture

## What MiOS is

'MiOS' (pronounced "MyOS") is an **immutable, container-image-shaped Linux
workstation** that boots like an OS, upgrades like a `git pull`, and rolls back
like a Ctrl-Z. It is Fedora underneath -- a `bootc`-managed OCI image built
`FROM` Universal Blue's `ucore-hci` -- with a curated workstation layer on top
for people who use their machines for AI, virtualization, and clusters.

It is also a **local, self-replicating agentic AI OS**: every layer of the
system -- the build pipeline that produces the image, the inference engines, the
agent orchestrator, the memory store, and the security posture -- is wired
together so an on-box agent can observe, reason about, and act on the machine
entirely offline, with no vendor lock-in. There is one OpenAI-compatible brain
behind one endpoint, and every tool on the system talks to it.

This document is the **layout-and-architecture reference**: how the OCI image is
shaped, how `bootc` governs its lifecycle, how the filesystem is partitioned by
FHS character, how hardware is delegated to VMs and containers, and how the AI
surface fits on top. Its purpose is to let a reader (human or agent) reason about
*where things live and why* before touching them. For the build-pipeline
mechanics see `guides/engineering.md`; for the threat model see
`guides/security.md`; for the full AI API see `reference/api.md`.

## Pillars

The whole system rests on three load-bearing properties. Every other design
choice traces back to one of these.

1. **Transactional integrity** -- the system core is a content-addressed OCI
   image managed by `bootc` (<https://bootc-dev.github.io/bootc/>). Atomic
   upgrade and rollback via `bootc upgrade` / `bootc rollback`. A release is a
   new image; a bad release is one `bootc rollback` away. This is what makes the
   AI plane safe to evolve aggressively -- a regression is reversible at the OS
   layer.
2. **Hardware acceleration** -- universal CDI (Container Device Interface,
   <https://github.com/cncf-tags/container-device-interface>) for NVIDIA,
   AMD ROCm/KFD, and Intel iGPU. CDI specs are generated under `/var/run/cdi/`,
   with admin overrides under `/etc/cdi/` (declared in
   `usr/lib/tmpfiles.d/mios-gpu.conf`). The same CDI plumbing that lets a Windows
   VM see a passed-through GPU also lets the inference containers offload to it.
3. **Zero-trust execution** -- `fapolicyd` deny-by-default, SELinux enforcing,
   USBGuard, CrowdSec sovereign-mode IPS, and kernel-lockdown integrity. Because
   the AI plane can act on the machine, the security plane is not optional. See
   `guides/security.md`.

## Base image -- uCore HCI

'MiOS' builds `FROM ghcr.io/ublue-os/ucore-hci:stable-nvidia` (`MIOS_BASE_IMAGE`).
uCore HCI is a Universal Blue derivative of Fedora CoreOS targeting
hyperconverged infrastructure:

| Layer | What it provides |
|---|---|
| Fedora CoreOS foundation | Immutable ostree rootfs, composefs `/usr`, SELinux enforcing, podman, ZFS kernel modules |
| uCore additions | cockpit, firewalld, tailscale, mergerfs, samba, NFS |
| HCI additions | libvirt/KVM, QEMU, VFIO-PCI tooling, virtiofs |
| NVIDIA variant (`stable-nvidia`) | Proprietary driver akmods pre-built and MOK-signed; NVIDIA Container Toolkit |
| Stable stream kernel | LTS Linux 6.12 -- server-grade stability, consistent ABI across updates |

'MiOS' adds, on top of this base: a GNOME 50 desktop (Phosh tablet/RDP
fallback), Looking Glass B7, KVM passthrough, k3s, Ceph, the full local AI
surface (inference lanes + agent orchestrator + pgvector memory), and
defense-in-depth hardening.

Upstream: <https://github.com/ublue-os/ucore>

## From source tree to running host

The architecture is best understood as one pipeline, build to boot:

1. **Repo root IS the system root.** The `usr/`, `etc/`, `srv/`, `var/`
   directories in `mios.git` mirror exactly where files land on a booted system
   -- no `system_files/` indirection. What you browse is what gets baked.
2. **Build.** A single-stage `Containerfile` runs every `automation/[NN]-*.sh`
   script in numeric order (packages, SELinux, CDI specs, UKI, Quadlet render,
   model bakes). The overlay step `automation/08-system-files-overlay.sh` applies
   the source tree onto the image; the final `RUN bootc container lint` enforces
   Architectural Law 4. The result is one content-addressed OCI image.
3. **Distribute.** That image is published (`ghcr.io/mios-dev/mios:latest`) and
   materialized into whichever artifact the target needs -- RAW disk, ISO, qcow2,
   Hyper-V VHDX, or WSL2 tar.
4. **Boot + Day-2 lifecycle.** `bootc switch` / `bootc upgrade` deploy the image;
   `bootc rollback` reverts it. The filesystem dispositions below decide what
   survives that lifecycle.

## Filesystem layout (FHS 3.0 + bootc)

Spec: <https://refspecs.linuxfoundation.org/FHS_3.0/>.

The bootc disposition reflects FHS 3.0's intent: `/usr` is explicitly
"shareable, read-only" in the spec -- the composefs/ostree model enforces this
at the kernel level. `/etc` is the host-specific config surface; bootc applies a
3-way merge (image default + previous state + admin edits) on upgrade so local
changes survive. `/var` is never touched by an upgrade. This is the mechanism
behind the "upgrade like a git pull, roll back like a Ctrl-Z" property.

| Path | FHS character | bootc disposition | Source-of-truth in repo |
|---|---|---|---|
| `/usr` | Read-only, shareable | Immutable composefs mount; change = new OCI image | `usr/` overlaid by `automation/08-system-files-overlay.sh` |
| `/etc` | Host-specific config | 3-way merge overlay; admin edits survive upgrades | `etc/` |
| `/var` | Mutable, persistent | Fully writable; never replaced on upgrade | `usr/lib/tmpfiles.d/mios*.conf` (LAW 2) |
| `/srv` | Data served by the system | Persistent; AI model weights, Ceph data | `usr/lib/tmpfiles.d/mios.conf` |
| `/run` | Ephemeral runtime (FHS 3.0) | tmpfs; cleared at boot; never in image layers | -- |
| `/home` | User home directories | Persistent via `/var/home/<user>` + symlink | `usr/lib/sysusers.d/` |

Build-time writes to `/var/` are forbidden (LAW 2). The overlay step at
`automation/08-system-files-overlay.sh:49-67` writes home dotfiles to
`/etc/skel/` and lets `systemd-sysusers` populate `/var/home/<user>/` at first
boot. Persistent agent state -- the PostgreSQL+pgvector data dir, the llama.cpp
KV slot store, AI memory and scratch -- all lives under `/var` and `/srv` so it
outlives every image upgrade.

## Hardware delegation

This is Pillar 2 in practice: a single CDI/VFIO plumbing layer serves both the
VM-passthrough path (hand a GPU to a guest) and the container path (let the
inference lanes offload to the same GPU).

Default GPU passthrough targets are detected at runtime via
`automation/34-gpu-detect.sh`, which writes `/run/mios/gpu-passthrough.status`
(earlier revisions of this doc hard-coded PCI IDs such as `10de:2204,10de:1aef`;
runtime detection replaced that).

Virtualization: KVM/QEMU + libvirt (`automation/12-virt.sh`), VFIO-PCI
passthrough kargs (`usr/lib/bootc/kargs.d/`), KVMFR shared-memory built in-image
(`automation/52-bake-kvmfr.sh`), and the Looking Glass B7 client built in-image
(`automation/53-bake-lookingglass-client.sh`). Hand a discrete GPU to a Windows
VM and game on it with near-native latency; the iGPU/host keeps the desktop.

## AI surface

The AI surface is the second half of what MiOS *is*: a local agentic AI OS. It
is organized as **inference lanes** (the raw model backends) sitting behind an
**agent orchestrator** (the brain that classifies, decomposes, dispatches, and
synthesizes), backed by a **unified memory store** (PostgreSQL + pgvector), and
exposed through **open agentic standards** (MCP for tools, A2A for agents). Every
agent and tool on the system resolves its endpoint from `MIOS_AI_ENDPOINT` --
there are no vendor-hardcoded URLs anywhere (Architectural Law 5).

### The single endpoint contract

`MIOS_AI_ENDPOINT` is the one OpenAI-v1-compatible endpoint every agent, CLI, and
editor client targets. The live operator-facing gateway is **MiOS-Hermes** at
`http://localhost:8642/v1`. The endpoint implements the OpenAI v1 REST protocol
-- core surfaces: `GET /v1/models`, `POST /v1/chat/completions` (streaming SSE
supported), `POST /v1/embeddings`. Auth: `Authorization: Bearer $MIOS_AI_KEY`
(an empty key is accepted by the local stack). Tool calling (`tools` array,
`finish_reason: tool_calls`) is supported for capable models. Because the
protocol is the contract, any OpenAI-API-compatible client talks to the same
brain with no lock-in.

### Inference lanes

Inference is served by **function-named** engines (the unit/service identity is
the MiOS function, not the upstream tool name). All speak the OpenAI-compatible
API; the underlying engines are FOSS.

| Lane (unit) | Endpoint | Engine | Role / models |
|---|---|---|---|
| **`mios-llm-light`** | `:11450` | llama.cpp via the upstream llama-swap proxy image (`ghcr.io/mostlygeek/llama-swap`) | **Primary** everyday lane. Auto-swaps a `llama-server` per requested model behind one `/v1` endpoint, with per-conversation KV-paging to disk (`--slot-save-path`). Serves the chat/reasoning models, the `mios-opencode` coder model, AND embeddings (`nomic-embed-text`, OpenAI-compat `/v1/embeddings`). Config: `usr/share/mios/llamacpp/mios-llm-light.yaml`. dGPU (CDI). |
| **`mios-llm-heavy`** | `:11441` | SGLang | Heavy GPU lane, served-name `mios-heavy`. HiCache CPU KV-offload, OpenAI `/v1`. **Gated / off by default** (VRAM). |
| **`mios-llm-heavy-alt`** | `:11440` | vLLM | Alternate heavy lane (PagedAttention + prefix cache). Mutually exclusive with `mios-llm-heavy` on a shared GPU. **Gated / off by default** (VRAM). |
| **`mios-llm-worker@`** | (per-instance) | llama.cpp | Single-model swarm workers for fan-out. |

`mios-llm-light` is the linchpin: it restores on-demand multi-model auto-swap for
one-model-per-process llama.cpp behind a single endpoint, and each `llama-server`
can checkpoint/restore a conversation's KV cache to disk -- the fleet-wide
context manager. The heavy lanes are VRAM-gated and join the swarm via
health-gated `[nodes.*]` entries only when enabled.

### Agent orchestration

The lanes are raw backends; the **agent plane** is what turns a user prompt into
grounded, tool-using work:

| Service (unit) | Port | Role |
|---|---|---|
| **MiOS-Agent-Pipe** (`mios-agent-pipe.service`) | `:8640` | The orchestrator. Classifies each request, refines it, decomposes substantive asks into concurrent sub-tasks across lanes/agents, runs the tool-loop, then synthesizes + polishes. Fronts Hermes for every gateway (OWUI, Discord, future Slack/Telegram). |
| **MiOS-Prefilter** | `:8641` | Injects `tool_choice=delegate_task` on fan-outable prompts, then forwards to Hermes. |
| **MiOS-Hermes** (`hermes-agent.service`) | `:8642` | OpenAI-compat agent gateway -- sessions, native tool-calling, browser/CDP + skills. The canonical `MIOS_AI_ENDPOINT` front door. |
| **MiOS-OpenCode** gateway | :8633 | opencode -> OpenAI /v1 shim; built-but-gated / partial / introspection-only council peer the orchestrator dispatches code/doc work to (see aios-engineering-blueprint.md). Loopback only. |
| **MiOS-OWUI** (Open WebUI) | `:3030` | Browser front-end; its `OPENAI_API_BASE_URL` points at the agent plane. |
| **MiOS-Search** (SearXNG) | `:8888` | Privacy-respecting metasearch backing the `web_search` tool. |

The end-to-end chat path: a gateway (OWUI/Discord) hits the agent-pipe (`:8640`),
which refines + routes the request, dispatches to Hermes (`:8642`) and council
peers (each backed by an inference lane), runs the tool-loop, persists the
gained knowledge, and returns a synthesized answer.

### Memory + state -- PostgreSQL + pgvector

The unified agent-plane datastore is **PostgreSQL + pgvector** (`mios-pgvector`
container, `:5432`, uid 826). One engine serves relational + JSONB (document) +
vector (pgvector HNSW) memory -- the standard "back to SQL" agent-memory stack.
The schema (`usr/share/mios/postgres/schema-init.sql`) defines `agent_memory`,
`event`, `tool_call`, `session`, `skill`, `scratch`, `knowledge`, `sys_env`,
`kanban`, `directory_entry`, `person`, `agent_keypair`, and more. Agents read and
write it through `mios-pg-query` (a pure-Python loopback client) / `mios-db --pg`.
Embeddings written here come from the `nomic-embed-text` lane on
`mios-llm-light`, closing the RAG loop entirely on-box.

### Discovery + federation (MCP / A2A)

| Concern | Mechanism |
|---|---|
| Tool discovery | MCP -- `usr/share/mios/ai/v1/mcp.json`; the universal MiOS verb/skill/recipe surface is both served and consumed |
| Agent discovery | A2A -- the agent plane publishes a peer card and can delegate sub-tasks to peer agents |
| System prompt | `usr/share/mios/ai/system.md` (canonical), `etc/mios/ai/system-prompt.md` (host override) |

This is the seam by which MiOS becomes *self-replicating* across a fleet: peer
MiOS nodes discover each other's tools (MCP) and agents (A2A) and delegate work,
rather than relying on bespoke point-to-point plumbing.

> **Naming note (migration history).** Earlier revisions described inference as
> Ollama (`:11434`) + Ollama-CPU, with SurrealDB for state and Qdrant for
> vectors. Those are **fully retired**: inference + embeddings run on
> `mios-llm-light` (`:11450`), state + vectors run on PostgreSQL+pgvector. The
> upstream `mios-llm-light` image and the Ollama-/OpenAI-compatible *API* remain
> legitimate external references -- only the MiOS unit identities changed.
> Likewise the old `cloudws-*` project name is retired; every shipped artifact is
> `mios-<component>`.

## Architectural Laws

Six laws are enforced by build-time lint and `automation/99-postcheck.sh`; a
violation fails the build/audit. They are the contract that keeps the layout
above coherent across upgrades.

1. **USR-OVER-ETC** -- static config lives in `/usr/lib/<component>.d/`; `/etc/`
   is admin-override only.
2. **NO-MKDIR-IN-VAR** -- every `/var/` path is declared via
   `usr/lib/tmpfiles.d/*.conf`; never written at build time.
3. **BOUND-IMAGES** -- every Quadlet image is symlinked into
   `/usr/lib/bootc/bound-images.d/` and baked into `/usr/lib/containers/storage`
   so it ships *with* the host.
4. **BOOTC-CONTAINER-LINT** -- the final `RUN` of the `Containerfile`. Fail the
   lint, fail the build.
5. **UNIFIED-AI-REDIRECTS** -- every agent and tool targets `MIOS_AI_ENDPOINT`.
   No vendor-hardcoded URLs.
6. **UNPRIVILEGED-QUADLETS** -- every Quadlet declares `User=`, `Group=`,
   `Delegate=yes`. Documented exceptions (rationale in their unit headers):
   `mios-ceph`, `mios-k3s`, `mios-forgejo-runner`, `mios-llm-heavy` (the upstream
   SGLang image must run as root).

## References

- bootc: <https://github.com/bootc-dev/bootc>
- bootc-image-builder: <https://github.com/osbuild/bootc-image-builder>
- Universal Blue uCore HCI: <https://github.com/ublue-os/ucore>
- rechunk: <https://github.com/hhd-dev/rechunk>
- cosign: <https://github.com/sigstore/cosign>
- mios-llm-light (upstream inference proxy): <https://github.com/mostlygeek/llama-swap>
- pgvector: <https://github.com/pgvector/pgvector>
