<!-- AI-hint: Provides the core MiOS knowledge base and architectural facts (hardware, stack, and infrastructure) for grounding agent reasoning and ensuring technical accuracy across the system.
     AI-related: /usr/share/mios/ai/system.md, /etc/mios/MiOS.md, /usr/share/mios/mios.toml, /etc/mios/mios.toml, /usr/lib/mios/agents/opencode/bin/, mios-agent-pipe, hermes-agent, mios-delegation-prefilter, mios-opencode-gateway, mios-searxng, mios-open-webui, mios-bootstrap -->
> _FHS: `/usr/share/mios/ai/system.md` — canonical MiOS AI grounding /
> knowledge base (the CONTEXT layer). This is NOT the identity SSOT: the agent
> identity, posture, and tool/agent doctrine live in `/MiOS.md` (layered
> `~/.config/mios/MiOS.md` < `/etc/mios/MiOS.md` < `/MiOS.md`), injected once per
> request by agent-pipe. This file supplies the grounded MiOS facts an agent
> reasons over — host architecture, the agent-stack seams, build invariants,
> stack, and the host-owner identity source. No hardcoded topics, apps, or
> keywords._

# MiOS Grounding / Knowledge Base

**Operate under `/MiOS.md`.** That file is the single canonical system identity:
your role as a node in a federated AIOS, persistence, the MCP=TOOLS / A2A=AGENTS
doctrine, decompose / delegate / span / synthesise, never-deny / never-fabricate
/ act-don't-narrate, and the OpenAI tool-calling loop. Do not duplicate or
override it. The sections below are the **CONTEXT/KB** you ground answers in.

# Context

## What "MiOS" is

MiOS is a fully self-replicating, immutable Linux distribution built on **Fedora
Rawhide**, delivered as a **bootc-managed OCI image** atop
`ghcr.io/ublue-os/ucore-hci:stable-nvidia`. "MiOS Agent" is the umbrella name for
the federation of cooperating processes that serve agent traffic on a MiOS host
(the seams are listed below).

- **Canonical hardware:** AMD Ryzen 9 9950X3D + NVIDIA RTX 4090.
- **Deployment surfaces:** bare metal, Hyper-V VHDX, WSL2/WSLg, QEMU,
  Live-CD/USB, USB installer, raw OCI image.
- **API uniformity:** every model, tool, and agent endpoint exposes a uniform
  **OpenAI-API** surface (function-calling, structured outputs, the tool-calling
  loop). Production code paths are never provider-specific
  (Architectural Law UNIFIED-AI-REDIRECTS — every agent/tool targets
  `MIOS_AI_ENDPOINT`, default `http://localhost:8080/v1`; no vendor-hardcoded
  URLs).
- **Host-owner identity** is read from `[identity]` in
  `/usr/share/mios/mios.toml` (layered with `/etc/mios/mios.toml` and
  `~/.config/mios/mios.toml`). Read the reader's identity from there — they are
  technically fluent; skip basics, lead with the answer.

## Agent stack (the seams "MiOS Agent" hides)

Runtime is **llama.cpp serving GGUF models** (fronted by the upstream mios-llm-light
proxy) behind the OpenAI-compat
endpoint; identity is injected per-request by agent-pipe (not baked into any
model). The orchestrator seat AND the single OpenAI-compatible front door is
**MiOS-Agent-Pipe** (`:8640`, served model "MiOS-Agent"): every gateway (OWUI,
Discord/CLI, Slack) funnels through it, where it refines intent, routes by where
the answer comes from, then runs the matching path — trivial chat, OS-control
fast-path, a native single-agent tool-loop, a multi-task/verb-DAG, council
fan-out across lanes, or A2A/MCP federation — and finishes with critic/polish
plus a real Sources list. **MiOS-Hermes** is NOT the orchestrator; it is a leaf
the pipe fronts and dispatches to (an OpenAI-compat agent gateway / tool-loop)
with fanout off to avoid recursion. Non-trivial code work is dispatched to the
MiOS-OpenCoder peer as a co-equal OpenAI `/v1` council peer (NOT spawned over
ACP); web research goes via `web_search`, which routes through the local SearXNG.

| Role               | Process                                                                              | Port     | Purpose                                                                       |
|--------------------|-------------------------------------------------------------------------------------|----------|------------------------------------------------------------------------------|
| **MiOS-Agent-Pipe**| `mios-agent-pipe.service`                                                            | `:8640`  | The front door AND orchestrator — refine + route + council/swarm fan-out + critic/polish; every gateway funnels through it; fronts Hermes and the lanes |
| **MiOS-Hermes**    | `hermes-agent.service` (host-direct)                                                 | `:8642`  | OpenAI-compat agent gateway / tool-loop the pipe fronts — sessions, tool-calling, skills, browser/CDP loop |
| **MiOS-Prefilter** | `mios-delegation-prefilter.service`                                                  | `:8641`  | HTTP forwarder; injects `tool_choice=delegate_task` on fan-outable prompts    |
| **MiOS-Inference** | `mios-llm-light` (llama.cpp, fronted by the upstream llama-swap proxy) primary + `mios-llm-heavy`/`-heavy-alt` (SGLang/vLLM) heavy lanes | `:11450` | GGUF models + embeddings (`nomic-embed-text`) behind the unified `MIOS_AI_ENDPOINT`; lanes across CPU / iGPU / dGPU / heavy |
| **MiOS-Memory**    | `mios-pgvector` (PostgreSQL + pgvector)                                              | `:5432`  | Unified agent datastore — memory, sessions, events, skills, knowledge/RAG vectors |
| **MiOS-Delegate**  | light-lane children via `delegate_task`                                              | (in-proc)| CPU/iGPU-side fanout pool (bounded concurrency + depth)                       |
| **MiOS-OpenCoder** | `mios-opencode-gateway.service` (`opencode` at `/usr/lib/mios/agents/opencode/bin/`) | `:8633`  | Coding specialist — first-class OpenAI `/v1` council peer dispatched by the orchestrator |
| **MiOS-Search**    | `mios-searxng.service` (Quadlet)                                                     | `:8888`  | Local SearXNG; backs `web_search` + OWUI's web-augmentation                   |
| **MiOS-OWUI**      | `mios-open-webui.service` (Quadlet)                                                  | `:3030`  | Browser front-end                                                             |

## First Principle: Self-Replication

MiOS is fully self-replicating. **MiOS-DEV** is the mutable testbed AND the
canonical source-of-self. The Windows entry point is a thin shim that SSHes into
the MiOS-DEV Podman machine to present a unified build dashboard. MiOS builds the
next MiOS forever (Day-0 → Day-1 → Day-N).

### Day-N loop

1. Bootstrap (`mios-bootstrap`) produces a minimal MiOS-DEV runtime.
2. MiOS-DEV is the mutable canonical source-of-self.
3. From MiOS-DEV, the Justfile invokes BIB → next bootc OCI image.
4. Image is signed, pushed to GHCR (or local registry), tagged.
5. Running MiOS systems (including MiOS-DEV itself) `bootc upgrade` to the new
   image. The loop repeats.

## Repo-IS-Root contract

- The MiOS git working tree's top-level directory IS the OS root.
- There is NO `system_files/` directory. There never will be.
- The `.git` directory functions as a root-level overlay: `./[ROOT]/.git`.
- Two repos — `MiOS` and `mios-bootstrap` — share one filesystem with different
  `.gitignore`-as-whitelist subsets. Each repo "sees" only its whitelist;
  commits to one never pollute the other.

## Architecture invariants (NEVER violate)

- Repo root IS system root — no `system_files/`.
- `Containerfile` is single-stage with a `ctx` scratch context.
- Build orchestrator is `Justfile` at the repo root (not numbered top-level
  scripts).
- ~48 phase scripts exist (under `usr/libexec/mios/phases/`) and are invoked from
  the Justfile.
- `PACKAGES.md` lives at `usr/share/mios/PACKAGES.md` and uses fenced
  ` ```packages-<category> ` blocks. Package installs flow through this file — no
  inline `dnf install` in the Containerfile or phase scripts.
- `lockdown=integrity` (NOT `confidentiality`). Confidentiality is for
  special-purpose appliances and breaks hibernation; integrity gives
  kernel-integrity without breaking legitimate workflows.
- `init_on_alloc=0`, `init_on_free=0`, `page_alloc.shuffle=0` — NVIDIA CUDA fails
  to initialize with these on (NVIDIA Grace tuning guide; CachyOS, Arch, NVIDIA
  dev-forum reports).
- NEVER `--squash-all`: it strips `ostree.final-diffid` and breaks BIB.
- `((VAR++))` must be `VAR=$((VAR + 1))` under `set -e` — `((VAR++))` returns 1 on
  first increment of an unset variable, killing the script.
- `repo_gpgcheck=0` in any added dnf repo (gpgcheck=1 is fine, but we don't sign
  repodata).
- xRDP MUST use Xorg backend via `xorgxrdp-glamor` and `lib=libxup.so` in
  `/etc/xrdp/xrdp.ini`. Never Xvnc.
- GTK theming: set `ADW_DEBUG_COLOR_SCHEME=prefer-dark` + dconf only; NEVER set
  `GTK_THEME=Adwaita-dark` (wrong API for libadwaita apps, breaks per-app
  themes).
- `ceph-bootstrap.service` uses `ConditionVirtualization=no` (documented
  antonym), NOT `!container` (does not cover Hyper-V or KVM bare-metal).
- kargs.d TOML: flat `kargs = [...]` array only — no `[kargs]` section headers.
  Per bootc upstream the schema is exactly `kargs = [...]` + optional
  `match-architectures = [...]`.
- ucore-hci ships `/usr/local` as a symlink to `/var/usrlocal` — use a two-stage
  tar pipeline; never `cp -a` (dereferences and writes to `/var`).
- Every image is fully self-building — no seed/full split; all GPU vendors
  (NVIDIA, AMD, Intel) supported unconditionally.
- OS is **Fedora Rawhide** (Fedora 44 released 2026-04-28; Rawhide is tracking
  toward F45).
- `install_weak_deps=False` in dnf5 syntax (underscore, capital F).
- Skel population MUST occur BEFORE `useradd -m`.
- Build-time writes to user home dirs require an explicit unconditional
  `chown -R user:user /home/user` pass at the end.

## Stack

- **Build:** bootc, ostree, composefs, bootc-image-builder (BIB), Podman
  (rootful), Justfile, dnf5.
- **AI / inference:** the local LLM engines are tier-named by role:
  **`mios-llm-light`** (llama.cpp via the upstream llama-swap proxy, :11450) is the primary lane —
  it serves the everyday GGUF models, the coder model, embeddings (`nomic-embed-text`,
  OpenAI-compat `/v1/embeddings`), AND a vision VLM (`qwen3-vl`), hot-swapping on
  demand; **`mios-llm-heavy`**
  (SGLang, :11441, served-name `mios-heavy`) is the heavy GPU lane with
  **`mios-llm-heavy-alt`** (vLLM) the gated alternate, and **`mios-llm-worker@`** for
  single-model swarm fan-out. All sit behind the OpenAI-compat `MIOS_AI_ENDPOINT`.
  The front door AND orchestrator is **MiOS-Agent-Pipe**
  (`mios-agent-pipe.service` :8640) — every gateway funnels through it; it fronts
  **MiOS-Hermes** (`hermes-agent.service` :8642), an OpenAI-compat agent gateway /
  tool-loop it dispatches to. **MiOS-Prefilter** (:8641) injects
  `tool_choice=delegate_task` on fan-outable prompts; **MiOS-OpenCoder**
  (`mios-opencode-gateway.service` :8633) is a first-class `/v1` council peer. The unified agent datastore is
  **PostgreSQL + pgvector** (`mios-pgvector`) — memory, sessions, events, skills,
  knowledge/RAG vectors. Optional drop-in alternatives (LocalAI, LiteLLM) flip on
  in `mios.toml [ai]`.
- **Container / orchestration:** Podman Quadlets, K3s, Ceph, Pacemaker/Corosync,
  CrowdSec (sovereign mode).
- **Dev environment:** OpenHands integrated inside MiOS-DEV; Forgejo for local
  Git hosting; Cockpit; Apache Guacamole.
- **Virtualization:** KVM/VFIO, Looking Glass B7, Waydroid, xRDP
  (Xorg/xorgxrdp-glamor), Hyper-V, WSL2/WSLg.
- **Security:** SELinux (enforcing), fapolicyd, USBGuard, firewalld,
  composefs/fs-verity, CrowdSec sovereign mode, kernel `lockdown=integrity`.

## Operational grounding rules

- File paths are quoted with a leading `/`.
- Modifications go through the bootc image first; runtime writes to `/usr` fail
  with EIO (composefs/fsverity-protected).
- Build issues: `mios build status` and `journalctl -u mios-build@*.service` are
  the canonical checks.
- Kernel arguments live in `/usr/lib/bootc/kargs.d/`; never invented.
- Agent-level introspection: `mios agent` subcommands.
