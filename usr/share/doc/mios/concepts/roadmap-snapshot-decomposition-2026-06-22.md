<!-- AI-hint: Research-backed decomposition of a historical MiOS roadmap snapshot into a minified executive summary and detailed current-architecture documentation. Reconciles the snapshot against current MiOS architectural laws, mios.toml SSOT, bootc lifecycle, local AI endpoint, pgvector memory plane, and offline-first constraints.
     AI-related: /MiOS.md, /usr/share/mios/mios.toml, /usr/share/doc/mios/concepts/architecture.md, /usr/share/doc/mios/concepts/aios-engineering-blueprint.md, /usr/share/doc/mios/concepts/OFFLINE-FIRST.md, /usr/share/doc/mios/reference/api.md -->
# MiOS Roadmap Snapshot Decomposition -- 2026-06-22

## Status

This document decomposes a 2025-2026 roadmap snapshot into current MiOS
architecture documentation. Treat the snapshot as **historical input**, not as a
source of truth. The current source of truth is:

- runtime identity: `/MiOS.md`
- repo/build contract: `/AGENTS.md`
- system configuration: `usr/share/mios/mios.toml`
- architecture: `usr/share/doc/mios/concepts/architecture.md`
- engineering rules: `usr/share/doc/mios/guides/engineering.md`
- OpenAI-compatible API surface: `usr/share/doc/mios/reference/api.md`

The snapshot is useful because it captures the product shape: immutable
workstation, container-first services, virtualization, local AI, and
self-rebuild. It is not authoritative where it conflicts with the current
architectural laws.

## Minified Executive Summary

MiOS is an immutable Fedora bootc workstation and a local agentic AI operating
system shipped as one OCI image. The repo root mirrors the deployed root
filesystem: edits under `usr/`, `etc/`, and related FHS paths become OS content
in the next image. `bootc switch`, `bootc upgrade`, and `bootc rollback` carry the
host across versions atomically.

The system has two equal faces. The workstation face provides GNOME/Wayland,
Podman Quadlets, KVM/libvirt, VFIO/Looking Glass, CDI GPU delegation, k3s, Ceph,
security hardening, and deployable artifacts such as ISO, RAW, qcow2, VHDX, WSL2
rootfs, and OCI images. The AI face provides one OpenAI-compatible local endpoint,
local inference lanes, an agent orchestrator, MCP tools, A2A peer delegation, and
PostgreSQL + pgvector memory.

The current design is TOML-first. `usr/share/mios/mios.toml` is the package,
ports, services, identity, AI-lane, endpoint, and operator-settings SSOT.
`PACKAGES.md` is rationale documentation only. Hard-coded install lists,
hard-coded AI ports, and values that bypass TOML are architecture bugs.

The pasted snapshot contains several retired assumptions. Do not use
`PACKAGES.md` as the build schema. Do not squash all OCI layers. Do not re-add
retired inference or datastore components. Do not add vendor-specific agent
product references to MiOS docs, code, prompts, or commit messages. The current
standard is OpenAI API compatibility, function-named MiOS units, local-first
operation, and offline-capable rebuild.

## Current Architecture, Detailed

### 1. Bootc / OCI operating system

MiOS is built as a bootable OCI image. Upstream bootc describes the model as
transactional in-place operating-system updates using OCI container images; the
container image carries the bootable userspace and kernel, while systemd remains
PID 1 on the target host. MiOS uses that model directly: `Containerfile` builds
the image, `bootc container lint` gates it, and bootc deploys it.

The runtime filesystem follows the bootc/FHS split:

| Path | Role | MiOS rule |
|---|---|---|
| `/usr` | vendor, static, shareable, read-only OS content | shipped in the image; static config belongs under `/usr/lib/<component>.d/` or `/usr/share/<component>/` |
| `/etc` | host/admin override surface | shipped defaults merge with local admin edits across upgrades |
| `/var` | persistent runtime state | never created by build-time `mkdir`; declare via `usr/lib/tmpfiles.d/*.conf` |
| `/run` | ephemeral runtime state | tmpfs only; never baked |
| `/srv` | served system data | persistent data such as models and service payloads |

composefs is the integrity layer for the read-only system tree. The composefs
project combines overlayfs, EROFS, and optional fs-verity to provide verified,
read-only filesystem trees. MiOS enables this through
`usr/lib/ostree/prepare-root.conf`, so the image-provided system can be verified
before userspace consumes it.

### 2. Build pipeline and SSOT

The build pipeline is deterministic and repo-native:

1. `Containerfile` copies the build context into `/ctx` and mutable working
   copies into `/tmp/build`.
2. `automation/08-system-files-overlay.sh` applies the rootfs overlay.
3. `automation/build.sh` runs numbered `automation/NN-*.sh` sub-phases in order.
4. `bootc container lint` validates the image.
5. `just` recipes use bootc-image-builder or local export flows to materialize
   deployment artifacts.

`usr/share/mios/mios.toml` is the authoritative schema for packages, ports,
services, sidecar images, AI lanes, identity, credentials flow, colors, and
operator preferences. Package scripts must use `automation/lib/packages.sh`:

- `install_packages "<category>"`
- `install_packages_strict "<category>"`
- `install_packages_optional "<category>"`

`usr/share/doc/mios/reference/PACKAGES.md` explains why packages exist; it does
not drive installs. This corrects the snapshot's older `PACKAGES.md` claim.

OCI layer squashing is also corrected: MiOS must not use `--squash-all` because
bootc/BIB need image metadata such as `ostree.final-diffid`. Day-2 delta size is
handled through the current rechunk flow, not through destructive flattening.

### 3. Artifact generation

The canonical artifact is the OCI image. Disk and installer outputs are
projections of that image:

| Artifact | Current path |
|---|---|
| OCI image | `just build` |
| RAW disk | `just raw` |
| Anaconda installer ISO | `just iso` |
| QEMU qcow2 | `just qcow2` |
| Hyper-V VHDX | `just vhdx` (`vhd` from BIB, then `qemu-img` conversion) |
| WSL2 rootfs | `just wsl2` (`podman export`, not a BIB type) |
| all local targets | `just all` |

Upstream bootc-image-builder supports image types such as `ami`,
`anaconda-iso`, `bootc-installer`, `gce`, `qcow2`, `raw`, `vhd`, and `vmdk`.
MiOS only documents and automates the targets it currently owns.

### 4. Container and service orchestration

Podman is the local container engine. Upstream Podman is a daemonless container
engine, and its Quadlet generator converts declarative `.container`, `.volume`,
`.network`, `.pod`, `.kube`, `.image`, and related files into systemd units.

MiOS uses Quadlets for local sidecars and enforces:

- every Quadlet image is bound into `/usr/lib/bootc/bound-images.d/`
- every non-exempt Quadlet declares `User=`, `Group=`, and `Delegate=yes`
- vendor Quadlets live under `/usr/share/containers/systemd/`
- admin overrides live under `/etc/containers/systemd/`

k3s provides the lightweight Kubernetes surface. Upstream k3s is a compliant
Kubernetes distribution distributed as a single binary or minimal container
image, with an embedded SQLite default datastore and HA options using embedded
etcd or external databases. MiOS uses it for local cluster workflows without
making the workstation depend on a remote control plane.

### 5. Virtualization, Android compatibility, and GPU delegation

MiOS includes KVM/QEMU/libvirt for first-class VM workflows, VFIO for PCI/GPU
passthrough, virtiofs for host-guest filesystem sharing, and Looking Glass for
low-latency guest display integration.

GPU delegation is unified around runtime detection and CDI:

- `/run/mios/gpu-passthrough.status` records detected passthrough state
- `/run/cdi/` carries generated vendor CDI specs
- `/etc/cdi/` is the admin override surface
- AI inference containers and VM workflows share the same GPU delegation posture

Waydroid remains a container-based Android-on-Linux option when kernel,
Wayland, LXC, binder, and GPU support line up. Upstream Waydroid describes the
model as a full Android system running in a Linux container on Wayland, using
Linux namespaces and LXC/binder access to needed hardware.

### 6. Storage fabric

The roadmap's storage idea maps to the current MiOS position: Ceph is available
as the local storage fabric for block, object, and file workflows, but it must
remain a domain service with its own lifecycle rather than being folded into the
agent datastore.

Ceph's upstream documentation defines it as one unified object, block, and file
storage system. Ceph block devices are thin-provisioned, resizable, striped over
OSDs, and integrate with KVM/libvirt/QEMU. Object storage exposes S3/Swift-style
interfaces. In MiOS terms:

- Ceph RBD fits VM and persistent block use cases.
- Ceph object storage fits backup, artifact, and disaster-recovery use cases.
- PostgreSQL + pgvector remains the agent-plane datastore; it is not replaced by
  Ceph.

### 7. AI operating-system plane

MiOS's AI plane is local-first and OpenAI-compatible. The architectural rule is
simple: every agent, model client, and tool resolves through `MIOS_AI_ENDPOINT`,
`MIOS_AI_MODEL`, and `MIOS_AI_KEY`. Hard-coded model ports or cloud endpoints are
bugs.

Current functional layers:

| Layer | MiOS component |
|---|---|
| Front door | `mios-agent-pipe` (`:8640`) as orchestrator front door |
| Agent/tool-loop gateway | MiOS-Hermes (`:8642`) as dispatched leaf/gateway |
| Prefilter | MiOS-Prefilter (`:8641`) for fan-outable prompts |
| Primary inference | `mios-llm-light` (`:11450`) for everyday chat, coding, and embeddings |
| Heavy inference | `mios-llm-heavy` (`:11441`) and `mios-llm-heavy-alt` (`:11440`), gated/off by default |
| OpenAI client surface | `/v1/models`, `/v1/chat/completions`, `/v1/embeddings`, tool calls |
| Browser UI | `mios-open-webui` (`:3030`) |
| Search | `mios-searxng` (`:8888`) |
| Memory | `mios-pgvector` (`:5432`) |

The OS-to-AI metaphor in the snapshot maps cleanly when kept concrete:

| Snapshot metaphor | Current MiOS implementation |
|---|---|
| kernel -> LLM core | `mios-agent-pipe` orchestrator and MiOS-Hermes gateway |
| scheduler | routing, priority, hop-budget, DAG/swarm dispatch modules |
| RAM -> context window | context packing, token-budget handling, KV slot save/restore |
| filesystem -> vector/RAG memory | PostgreSQL + pgvector schema and local embeddings |
| applications -> agents/tools | MCP tools, function-named MiOS verbs, A2A peers |
| UI -> natural language | OpenAI-compatible endpoint plus local browser UI |

### 8. Agent memory and state

The current datastore is PostgreSQL + pgvector. This replaced older
split-database/vector-store assumptions. One OSI-FOSS engine now carries:

- `agent_memory`
- `event`
- `tool_call`
- `session`
- `skill`
- `scratch`
- `knowledge`
- `sys_env`
- `kanban`
- identity, key, directory, and relationship tables

Embeddings are produced by the local embeddings lane through the OpenAI
`/v1/embeddings` surface and stored in `vector(768)` columns with pgvector HNSW
indexes. The schema is `usr/share/mios/postgres/schema-init.sql`.

### 9. Security posture

MiOS security is not bolted on after the AI plane; it is a precondition for a
local system that can act on its host. The posture includes:

- SELinux enforcing
- fapolicyd deny-by-default policy work
- USBGuard
- CrowdSec
- kernel lockdown integrity
- MOK-signed modules where required
- tmpfiles/sysusers-owned runtime state
- unprivileged-by-default Quadlets
- HITL gates for higher-risk agent actions
- local-first OpenAI-compatible routing rather than hidden vendor endpoints

Security changes must land in the appropriate FHS layer. Static policy belongs
under `/usr/share/selinux/packages/mios/` or `/usr/lib/...`; admin overrides
belong under `/etc`; runtime state belongs under `/var`.

### 10. Offline-first lifecycle

MiOS's offline-first law is stronger than "can run without internet." The goal
is that an operator with a prebuilt image, or full repos on removable media plus
a Windows or minimal Fedora environment, can overlay, pull from local stores,
build, deploy, run, host, rebuild, and use AI offline.

Current status:

| Phase | Status |
|---|---|
| deploy prebuilt image | offline-capable |
| run desktop/services | offline-capable |
| use local AI | offline-capable |
| bootc upgrade from local image store | offline-capable |
| rebuild from full local cache | offline-capable if RPMs, container images, wheels, models, and source tarballs are cached |
| rebuild from internet-free uncached host | gap remains; see `OFFLINE-FIRST.md` |

The remaining gaps are build-time fetches: external repos, font archives,
Flatpak metadata, k3s/k3s-selinux sources, Python wheels, model blobs, and
container images unless pre-vendored or mirrored.

## Snapshot Reconciliation

| Snapshot claim | Current MiOS position |
|---|---|
| `PACKAGES.md` is the declarative build schema | Incorrect. `usr/share/mios/mios.toml` is the SSOT; `PACKAGES.md` is rationale docs. |
| OCI builds use `--squash-all` | Incorrect. Squashing is forbidden because it strips metadata bootc/BIB need. |
| `/` is immutable | Clarify. `/usr` is immutable/read-only; `/etc` is merged host config; `/var` is persistent mutable state. |
| `/home` is symlinked to `/var/home` | Correct shape; user state is persistent and generated through sysusers/tmpfiles/account setup. |
| Podman microservices are managed by Quadlets | Correct, with MiOS-specific unprivileged and bound-image laws. |
| k3s is the local Kubernetes layer | Correct, but MiOS treats it as optional/local infrastructure, not a hard dependency for the base workstation. |
| Ceph provides storage fabric | Correct as a storage service; not the agent datastore. |
| AI memory is vector storage/RAG | Correct concept; current implementation is PostgreSQL + pgvector, not a separate vector appliance. |
| AI endpoint is a single natural-language control plane | Correct concept; the enforceable contract is OpenAI API compatibility through `MIOS_AI_ENDPOINT`. |
| Vendor-specific agent/editor products are part of the control plane | Incorrect for MiOS docs/code. Use OpenAI-compatible API language only. |
| Older datastore/inference components remain active | Incorrect. Current active components are `mios-llm-light`, optional heavy lanes, and PostgreSQL + pgvector. |
| WSL2, NUT, sysext, and k3s upgrade issues are known | Keep as issue categories only when tied to current repo code or a tracked work item. Do not treat historical notes as live defects without local verification. |

## Documentation Decomposition

Use this decomposition to split future work without mixing concerns:

| Document | Scope |
|---|---|
| `concepts/architecture.md` | canonical bootc/FHS/hardware/AI architecture |
| `guides/engineering.md` | build pipeline rules, automation conventions, package SSOT, lint gates |
| `guides/deploy.md` | bootc switch/upgrade/rollback, artifact installation, Day-2 lifecycle |
| `guides/security.md` | SELinux, fapolicyd, USBGuard, CrowdSec, lockdown, signing |
| `reference/api.md` | OpenAI-compatible endpoints, models, tools, auth, streaming |
| `concepts/OFFLINE-FIRST.md` | offline capability matrix and build-time fetch gaps |
| `concepts/aios-engineering-blueprint.md` | agent-kernel modules, memory/orchestration/security/eval gap register |
| this document | historical snapshot decomposition and correction ledger |

## Research Sources

Local MiOS sources:

- `/AGENTS.md`
- `/MiOS.md`
- `usr/share/doc/mios/concepts/architecture.md`
- `usr/share/doc/mios/guides/engineering.md`
- `usr/share/doc/mios/concepts/OFFLINE-FIRST.md`
- `usr/share/doc/mios/concepts/aios-engineering-blueprint.md`
- `usr/share/doc/mios/concepts/postgres-pgvector-unification.md`
- `usr/share/doc/mios/upstream/{bootc,bib,composefs,podman,k3s-cockpit}.md`

External sources checked on 2026-06-22:

- bootc documentation: <https://bootc.dev/bootc/>
- bootc-image-builder / Image Builder documentation: <https://osbuild.org/docs/bootc/>
- Podman manual: <https://docs.podman.io/en/latest/markdown/podman.1.html>
- Podman Quadlet manual: <https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html>
- k3s documentation: <https://docs.k3s.io/>
- k3s architecture: <https://docs.k3s.io/architecture>
- composefs README: <https://github.com/composefs/composefs>
- Waydroid project documentation: <https://waydro.id/>
- Ceph documentation: <https://docs.ceph.com/en/latest/>
- Ceph block device documentation: <https://docs.ceph.com/en/latest/rbd/>
