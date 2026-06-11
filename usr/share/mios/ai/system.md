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

Runtime is **llama.cpp / llama-swap serving GGUF models** behind the OpenAI-compat
endpoint; identity is injected per-request by agent-pipe (not baked into any
model). The orchestrator seat is **MiOS-Hermes**: lightweight gathering fans out
to CPU/iGPU/dGPU lanes; non-trivial code work is dispatched to the MiOS-OpenCoder
peer as a co-equal OpenAI `/v1` council peer (NOT spawned over ACP); web research
goes via `web_search`, which routes through the local SearXNG.

| Role               | Process                                                                              | Port     | Purpose                                                                       |
|--------------------|-------------------------------------------------------------------------------------|----------|------------------------------------------------------------------------------|
| **MiOS-Hermes**    | `hermes-agent.service` (host-direct)                                                 | `:8642`  | OpenAI-compat agent gateway — sessions, tool-calling, kanban, skills          |
| **MiOS-Prefilter** | `mios-delegation-prefilter.service`                                                  | `:8641`  | HTTP forwarder; injects `tool_choice=delegate_task` on fan-outable prompts    |
| **MiOS-Inference** | llama.cpp / llama-swap (OpenAI-compat GGUF endpoint + embeddings)                    | `:8080`  | Raw model + embeddings; lanes routed across CPU / iGPU / dGPU / heavy compute |
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
- `cloudws-ceph-bootstrap.service` uses `ConditionVirtualization=no` (documented
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
- **AI / inference:** **llama.cpp / llama-swap** serves the deployed GGUF models
  behind the OpenAI-compat endpoint (`MiOS-Inference`, `MIOS_AI_ENDPOINT`).
  **MiOS-Hermes** (`hermes-agent.service` on :8642) is the OpenAI-compat agent
  gateway in front of it, with **MiOS-Prefilter** (:8641) injecting
  `tool_choice=delegate_task` on fan-outable prompts. **MiOS-OpenCoder**
  (`opencode`) is the coder-tuned specialist served as a first-class OpenAI `/v1`
  council peer by `mios-opencode-gateway.service` (`:8633`), dispatched by the
  agent-pipe orchestrator. Optional/unwired-by-default drop-in alternatives —
  LocalAI, vLLM, Qdrant, LiteLLM — are supported and enabled in
  `mios.toml [ai]`.
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
