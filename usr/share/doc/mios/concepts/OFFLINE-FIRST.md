<!-- AI-hint: Defines MiOS's offline-first capability matrix — maps each lifecycle phase (overlay, pull, build, deploy, run, host, re-build, use-AI) to its network requirement, proving the whole bootc/OCI workstation + local agentic AI OS can be deployed, run, and self-rebuilt fully offline / air-gapped. Lists the remaining build-time fetch gaps to vendor.
     AI-related: mios-bootstrap, mios-sys-agent, mios-llm-light, mios-pgvector, /usr/share/mios/llamacpp/mios-llm-light.yaml, automation/build.sh -->
# Law-adjacent — OFFLINE-FIRST capability matrix

> Operator directive 2026-05-17: "if a user had; 1. a MiOS Image to
> deploy, or 2. full repos offline on a usb drive, a windows or
> minimal fedora live environment — users can overlay, pull, build,
> deploy, run, host, re-build, use AI — ALL OFFLINE!!!"

## Purpose — why offline-first is load-bearing for MiOS

MiOS is one thing built two ways at once: an **immutable, bootc/OCI Fedora
workstation** (the whole OS is a single container image you `bootc upgrade` like a
`git pull` and `bootc rollback` like a Ctrl-Z) that is *also* a **local,
self-replicating, agentic AI operating system** — a full agent stack behind one
OpenAI-compatible endpoint. Both halves are designed to need **zero vendor cloud**.

Offline-first is the property that makes that dual nature real rather than
marketing: an operator with nothing but the image (or the repos) and a power
outlet can stand up, run, and *re-derive* the entire system — desktop, services,
and AI brain — with the network unplugged. The build pipeline assembles the OCI
image, the bootc lifecycle carries it forward, and the local inference lanes +
agent-pipe + pgvector memory generate and remember without ever leaving the box.
This doc is the **audit ledger** for that promise: per lifecycle phase, what
works fully offline TODAY and what still touches the network, with the fix needed
to close each gap (track each in a PR). A passing offline build is the canonical
proof of compliance.

## Scenarios

| Scenario | What the operator has | What they're doing |
|---|---|---|
| **1. Pre-built image** | A finished MiOS bootc OCI image (`localhost/mios:<tag>` or `.qcow2`/`.iso`/`.vhdx`/WSL2 artifact) | Boots the image, runs services + AI |
| **2. Full repos offline** | `mios.git` + `mios-bootstrap.git` checked out on USB, a Windows host or minimal Fedora live env with `podman` + `bootc` | Overlays repos, builds the image locally, deploys, runs, re-builds |

Both scenarios MUST work with the host's network unplugged.

## Per-phase capability matrix

The phases below mirror the system's own lifecycle: **overlay → pull → build**
produce the image (Phase-0..2 of the build pipeline); **deploy → run → host**
are the bootc lifecycle on a target; **re-build → use-AI** are the
self-replicating + agentic halves operating on-box.

| Phase | Scenario 1 (image) | Scenario 2 (build) | Notes |
|---|---|---|---|
| **overlay** (apply repo files to `/`) | n/a | ✅ offline | Plain `install`/`cp` from the USB (`automation/08-system-files-overlay.sh`); the repo root IS the system root, no network needed |
| **pull** (acquire deps + sources) | n/a (image already has) | ⚠️ partial | dnf packages come from the OCI base layer (works if the base layer is cached); `automation/05-enable-external-repos.sh` + `09-fonts.sh` + `10-gnome.sh` + `13-ceph-k3s.sh` + `19-k3s-selinux.sh` + `38-hermes-agent.sh` + `38-llamacpp-prep.sh` / `38-vllm-prep.sh` hit github.com / pypi.org / flathub.org / model registries. **Gap.** |
| **build** (`bib`/`podman build` the OCI image) | n/a | ⚠️ partial | Bound-images law (3) symlinks Quadlet image refs into `/usr/lib/bootc/bound-images.d/` and bakes them into `/usr/lib/containers/storage` so the FINAL image carries them, but the BUILD step still pulls from the registry to populate. A pre-pulled local registry mirror closes this. |
| **deploy** (`bootc switch`/`bootc upgrade` to the new image) | ✅ offline | ✅ offline | bootc reads from the local image store; no network if the image is local |
| **run** (boot + start services) | ✅ offline | ✅ offline | All systemd units + Quadlets reference images from the local store via `bound-images.d/` (Law 3) |
| **host** (serve OWUI, Hermes, the inference lanes, SearXNG, Cockpit, k3s) | ✅ offline | ✅ offline | Every port binds localhost-or-LAN: OWUI `:3030`, agent-pipe `:8640`, Hermes `:8642`, prefilter `:8641`, `mios-llm-light` `:11450`, `mios-llm-heavy` `:11441`, opencode-gateway `:8633`, pgvector `:5432`, SearXNG `:8888`, Cockpit `:9090`, k3s `:6443`. No vendor cloud calls. |
| **re-build** (re-overlay + re-build after a code edit) | ✅ offline (if only `automation/*-render-*.sh` re-run) | ⚠️ partial | Same gap as "pull" — if the edit touches a script that re-fetches an external dep, the re-build needs that dep cached. This is the self-replicating half: the running OS can re-derive its own next image on-box. |
| **use AI** (chat, refine, council/swarm, tool calls, memory) | ✅ offline | ✅ offline | Models baked via `automation/38-llamacpp-prep.sh`; **`mios-llm-light` (`:11450`)** is the primary inference lane — `llama.cpp` behind the upstream `mios-llm-light` proxy image (`ghcr.io/mostlygeek/llama-swap`), multi-model auto-swap + KV-cache paging — and also serves **embeddings** (`nomic-embed-text`, OpenAI-compat `/v1/embeddings`). Heavy GPU lanes `mios-llm-heavy` (SGLang `:11441`) / `mios-llm-heavy-alt` (vLLM `:11440`) are gated/off-by-default. Hermes config seeds its endpoint from `MIOS_AI_ENDPOINT` (Law 5, default `http://localhost:8080/v1`) with `web.search_backend: searxng` (local `:8888`). Agent memory/knowledge/RAG live in **PostgreSQL + pgvector** (`mios-pgvector`, `:5432`). Skills + `system.md`/SOUL on disk. Internet-using tools (Discord, Firecrawl) are OPTIONAL valves. |

## Remaining build-time gaps (Scenario 2)

These files reach the internet at build time. Each blocks a fully-offline
scenario-2 build. Tracking the work needed to vendor:

| File | What it fetches | Vendor as |
|---|---|---|
| `automation/05-enable-external-repos.sh` | `terra.repo` from github.com | Bundle `usr/share/mios/repos/terra.repo` |
| `automation/09-fonts.sh` | Geist + Nerd-Fonts archives from github.com | `usr/share/mios/vendored/fonts/{geist,nerd}.tar.xz` (LFS or bundled) |
| `automation/10-gnome.sh` | Bibata cursor + flathub remote URL | Bundle `usr/share/mios/vendored/bibata-*.tar.xz`; ship a local flathub mirror image |
| `automation/13-ceph-k3s.sh` | k3s binary + checksums from github.com | Bundle `usr/share/mios/vendored/k3s/k3s-<tag>` |
| `automation/19-k3s-selinux.sh` | k3s-selinux git clone | Bundle as a tarball in `usr/share/mios/vendored/k3s-selinux-<tag>.tar.xz` |
| `automation/38-hermes-agent.sh` | hermes-agent git + pip deps (aiohttp, websockets, discord.py) | Vendor wheels in `usr/share/mios/vendored/wheels/`; use `pip install --no-index --find-links=...` |
| `automation/38-llamacpp-prep.sh` | GGUF model blobs + the upstream llama-swap proxy image | Bundle GGUFs under `usr/share/mios/vendored/models/` (or a pre-populated `/models` layer); pre-pull the upstream mios-llm-light image into the local store |
| (any) | dnf packages from Fedora mirrors | Already mostly cached by the bootc base layer; for full offline, ship a local rpm mirror image |

## How to know if a build is fully offline

```
# from inside the build context, before `bib build` / `just build`:
nmcli connection down "<your wifi>"  # cut the network
sudo podman build ...                 # if this succeeds, build is offline-safe
```

A passing offline build run is the canonical proof of compliance. The `bib build`
step itself is offline-safe (it reads from the local podman store); the question
is whether the IMAGE LAYERS the build references were already pulled before the
network cut.

## Audit (live, this host, 2026-05-17 — pre-migration snapshot)

Runtime audit script: `/var/lib/mios/ai/scratch/audit-offline.sh`.
All core services reachable on localhost; tier models loaded; Hermes
provider/search/browser all local; SOUL + skills + `mios-*` verbs present; zero
cloud API keys configured; Quadlet images symlinked into
`/usr/lib/bootc/bound-images.d/`.

> **Migration note (2026-06-13):** this audit predates the inference/datastore
> migration. The offline conclusions still hold; only the components changed.
> Inference + embeddings now run on **`mios-llm-light` (`:11450`, llama.cpp via
> the upstream llama-swap proxy)** with gated heavy lanes (`mios-llm-heavy` SGLang `:11441`,
> `mios-llm-heavy-alt` vLLM `:11440`) — Ollama is **removed** (it survives only as
> an upstream API-compat reference, since the lanes speak the OpenAI/Ollama-
> compatible API). The agent datastore is **PostgreSQL + pgvector**
> (`mios-pgvector`, `:5432`) — SurrealDB and Qdrant are **removed**. Re-run
> `audit-offline.sh` against these endpoints for a current snapshot.

**Runtime + use-AI phases: 100% offline-capable.**
**Build phase: needs the gaps above closed for true offline-from-USB.**
