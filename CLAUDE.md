<!-- AI-hint: Per-tool operating overlay for the Claude Code CLI working on the MiOS repo (which IS the system root). Defines build commands, the build-pipeline/Architectural-Law contract, repo conventions, and the operator's binding session rules; defers core runtime identity to /MiOS.md.
     AI-related: /etc/mios/MiOS.md, /etc/mios/mios.toml, /usr/share/mios/mios.toml, /etc/mios/install.env, /usr/share/mios/configurator/index.html, /usr/share/mios/llamacpp/llama-swap.yaml, mios-build-local, mios-bootstrap, mios-ceph, mios-k3s, mios-forgejo-runner -->
# CLAUDE.md

> _`/CLAUDE.md` — per-tool stub for **Claude Code** (claude.ai/code) working on
> the MiOS repo. **Runtime identity SSOT is [`/MiOS.md`](MiOS.md)** — operate
> under it. This file carries ONLY the Claude-Code-specific deltas: build/loading
> commands, repo conventions, and the operator's binding session rules. It does
> NOT redefine identity, posture, or tool-calling — those live in `/MiOS.md`
> (layered `~/.config/mios/MiOS.md` < `/etc/mios/MiOS.md` < `/MiOS.md`). No
> hardcoded topics, apps, or keywords._

## What MiOS is (so this overlay makes sense)

MiOS is one thing built two ways at once: an **immutable, bootc/OCI-shaped
Fedora workstation** (the whole OS is a single container image — boot it,
`bootc upgrade` it like a `git pull`, `bootc rollback` it like a Ctrl-Z) that is
*also* a **local, self-replicating, agentic AI operating system**. The same image
that ships GNOME/Wayland, NVIDIA+ROCm+iGPU via CDI, KVM/libvirt with VFIO
passthrough, and a k3s+Ceph one-node-cluster path also ships a full local agent
stack behind one OpenAI-compatible endpoint.

That dual nature is why this repo is laid out the way it is, and why the laws
below are non-negotiable: **the repo root IS the deployed system root.** The
`Containerfile` bakes `usr/`, `etc/`, `srv/`, `var/` exactly where they land on
a booted host, the build pipeline assembles the image, and the bootc lifecycle
carries it forward. When you edit a file here you are editing the OS.

Claude Code's job in that whole is narrow and load-bearing: **build, lint, and
extend the image and its code paths** — not to operate the running machine. The
sections below tell you how to build it, the contract you must not break, and
the operator rules that bound a Claude session.

## Role and Objective

Provide guidance to Claude Code when working with code in this repository (the
repo root IS the system root). Your runtime identity, persistence, tool-calling,
planning/decomposition, output, and standards posture are defined in
**[`/MiOS.md`](MiOS.md)** — follow it. Everything below is the Claude-Code
operating overlay: where things are, how to build, and how to behave in a Claude
session.

## Persistence

Operate under `/MiOS.md` (keep going until the request is completely resolved;
use a tool to find out rather than guess; decide → act → verify). The
Claude-Code addition: prefer **complete replacement files** over diffs, and drive
multi-step work through the task tool with **one in-progress task at a time**.

## Tool-calling

Operate under `/MiOS.md` for the agentic tool-loop (global tool access, MCP for
TOOLS / A2A for AGENTS, never deny/never fabricate, real calls only).
Claude-Code deltas:

- **cwd:** `/` is the repo root and system root — do **not** treat it as
  dangerous.
- **Confirm before:** `git push`, `bootc upgrade`, `dnf install`, `systemctl`,
  `rm -rf`.
- **Memory:** `/var/lib/mios/ai/memory/`
- **Scratch:** `/var/lib/mios/ai/scratch/`
- **Tasks:** use the task tool for multi-step work; one in-progress at a time.

## Planning and Decomposition

Operate under `/MiOS.md` (plan before each call, reflect after; decompose
multi-faceted requests; sequence dependent steps in one loop). For build work,
respect the numbered pipeline order described under **Architecture** below —
phase/sub-phase prefixes encode dependency order.

## Output

Operate under `/MiOS.md` (answer from tool results and given context; act, do not
narrate). **Deliverables:** complete replacement files only — no diffs, no
patches.

---

# Claude Code Deltas (build · architecture · conventions)

## Build commands

The deliverable of a build is the OCI image (and, optionally, disk artifacts cut
from it). Everything from `just preflight` to `just iso` is "produce the MiOS
image"; the Architectural Laws below are the contract that image must satisfy.

### Linux

```bash
just preflight          # system prereq check
just build              # build OCI image (runs bootc container lint as final step)
just lint               # re-run bootc container lint on the built image
just artifact           # refresh AI manifests before a build
just rechunk            # optimized Day-2 delta layers
just raw                # RAW disk image via BIB
just iso                # Anaconda installer ISO
just qcow2              # QEMU disk image (needs MIOS_USER_PASSWORD_HASH, MIOS_SSH_PUBKEY)
just vhdx               # Hyper-V VHDX (needs MIOS_USER_PASSWORD_HASH, MIOS_SSH_PUBKEY)
just wsl2               # WSL2 tar.gz
just all                # every artifact in one shot
just verify-images      # smoke-test all output/ artifacts
just sbom               # CycloneDX SBOM via syft
just init-user-space    # seed ~/.config/mios/mios.toml from vendor template
just show-env           # print resolved MIOS_* surface
just edit               # open mios.toml in $EDITOR
```

### Windows

```powershell
.\preflight.ps1
.\mios-build-local.ps1   # full OCI build + rechunk + disk images + GHCR push
```

### Key build-time env vars

| Variable | Purpose |
|---|---|
| `MIOS_BASE_IMAGE` | OCI base (default `ghcr.io/ublue-os/ucore-hci:stable-nvidia`) |
| `MIOS_LOCAL_TAG` | Local image tag (default `localhost/mios:latest`) |
| `MIOS_USER` / `MIOS_HOSTNAME` | Default account/hostname baked into the image |
| `MIOS_USER_PASSWORD_HASH` | SHA-512 hash (`openssl passwd -6 'pw'`) — required for qcow2/vhdx |
| `MIOS_SSH_PUBKEY` | ed25519 pubkey — required for qcow2/vhdx |

## Architecture

### Repo root IS system root

There is no `system_files/` indirection. The `usr/`, `etc/`, `srv/`, `var/` directories at repo root mirror exactly where files land on a booted system. `automation/08-system-files-overlay.sh` applies the overlay during the Containerfile's main `RUN`.

### Containerfile

Single-stage build with a `ctx` scratch context:
1. `ctx` stage copies `automation/`, `usr/`, `etc/`, `tools/`, `VERSION`, `config/artifacts/` read-only.
2. Main stage bind-mounts `/ctx` read-only; mutable copies go to `/tmp/build`.
3. CRLF → LF normalization runs over all text files before any script executes (Windows build hosts leak CRLFs past `.gitattributes`).
4. `automation/08-system-files-overlay.sh` runs before the main build pipeline.
5. `automation/build.sh` iterates every `automation/[0-9][0-9]-*.sh` in numeric order.
6. Final `RUN bootc container lint` (Architectural Law 4 — fail = fail the build).
7. Never `--squash-all`: strips `ostree.final-diffid` and breaks BIB.

### Build pipeline phases

The image you build is consumed by the bootc lifecycle: Phase-0..4 produce it,
then a host `bootc switch`/`upgrade` deploys it and `bootc rollback` reverts it.
Keeping the phases ordered is what makes that lifecycle reproducible.

| Phase | Owner | Description |
|---|---|---|
| Phase-0 | `mios-bootstrap` | Preflight, profile load, identity capture |
| Phase-1 | `mios-bootstrap` | Total Root Merge (clone `mios.git` into `/`, overlay bootstrap) |
| Phase-2 | `Containerfile` / `automation/build.sh` | Build (numbered sub-phases) |
| Phase-3 | both | sysusers/tmpfiles/services + user create + per-user config staging |
| Phase-4 | `mios-bootstrap` | Reboot |

Numbered automation scripts (`automation/NN-name.sh`) are sub-phases of Phase-2. The prefix encodes dependency order — preserve it when adding scripts. `08-system-files-overlay.sh` is skipped by `build.sh` (it runs pre-pipeline from the Containerfile).

### Architectural laws (non-negotiable; violations fail the build/audit)

These six laws are the contract that lets MiOS be both immutable and agentic at
once. Laws 1–4 keep the image deterministic, atomic, and self-contained so bootc
can upgrade/roll it back; Laws 5–6 keep the AI plane unified and least-privileged
so the agent stack stays portable and sandboxed.

| # | Law |
|---|---|
| 1 | **USR-OVER-ETC** — static config in `/usr/lib/<component>.d/`; `/etc/` is admin-override only. |
| 2 | **NO-MKDIR-IN-VAR** — every `/var/` path declared via `usr/lib/tmpfiles.d/*.conf`; never written at build time. |
| 3 | **BOUND-IMAGES** — every Quadlet image symlinked into `/usr/lib/bootc/bound-images.d/` and baked into `/usr/lib/containers/storage` at build time. |
| 4 | **BOOTC-CONTAINER-LINT** — final `RUN` of `Containerfile`. Fail = fail the build. |
| 5 | **UNIFIED-AI-REDIRECTS** — every agent/tool targets `MIOS_AI_ENDPOINT` (default `http://localhost:8080/v1`). No vendor-hardcoded URLs. |
| 6 | **UNPRIVILEGED-QUADLETS** — every Quadlet declares `User=`, `Group=`, `Delegate=yes`. Exceptions: `mios-ceph`, `mios-k3s`, `mios-forgejo-runner` (rationale in their headers). |

### Package management

Single source of truth: `usr/share/mios/mios.toml` under `[packages.<section>].pkgs`. Never call `dnf install` on hard-coded names. Use the helpers from `automation/lib/packages.sh`:

```bash
install_packages "<category>"           # best-effort, --skip-unavailable
install_packages_strict "<category>"    # fails on any miss
install_packages_optional "<category>"  # pure best-effort, never fails
```

Human-readable rationale docs live at `usr/share/doc/mios/reference/PACKAGES.md` — that is documentation, not the runtime SSOT.

### Configuration SSOT — `mios.toml`

Everything operator-tunable — packages, ports, AI lanes, services, agent
behaviour — flows from one file with a three-layer override (highest wins):

```
~/.config/mios/mios.toml     # per-user
/etc/mios/mios.toml          # host/admin (written by bootstrap)
/usr/share/mios/mios.toml    # vendor defaults (immutable, shipped in image)
```

Shell/systemd consumers use the derived bridge `/etc/mios/install.env`; run `mios-sync-env` after editing `mios.toml` to refresh it. The static configurator UI at `/usr/share/mios/configurator/index.html` is a browser-local TOML editor for the same file.

### AI stack — the local, OpenAI-compatible brain

This is the "agentic AI OS" half of MiOS. A user request flows from a front-end
(OWUI, the Discord gateway, the `mios` CLI) into the **agent-pipe** orchestrator,
which refines it, fans it out across a council/swarm, and dispatches tool/verb
calls; **MiOS-Hermes** is the OpenAI-compatible gateway and tool-loop agent;
**pgvector** is the unified agent memory (tiered memory, knowledge, sessions,
skills, RAG embeddings); the **inference lanes** below do the actual generation
and embeddings. MCP exposes the tool surface and A2A federates peer agents.

| Service | Unit | Port | Role |
|---|---|---|---|
| MiOS-Agent-Pipe | `mios-agent-pipe.service` | `:8640` | Standalone orchestrator — router + refine + council/swarm fan-out + critic/polish; fronts Hermes for every gateway |
| MiOS-Hermes | `hermes-agent.service` | `:8642` | OpenAI-compat agent gateway — sessions, tool-calling, skills, browser/CDP tool loop |
| MiOS-Prefilter | `mios-delegation-prefilter.service` | `:8641` | Injects `tool_choice=delegate_task` on fan-outable prompts, forwards to Hermes |
| MiOS-LLM-Light | `mios-llm-light.service` | `:11450` | **Primary** local inference — llama.cpp behind the `llama-swap` proxy image; multi-model auto-swap + KV-cache paging; serves everyday models, the `mios-opencode` coder model, **and embeddings** (`nomic-embed-text`, OpenAI-compat `/v1/embeddings`). Config: `usr/share/mios/llamacpp/llama-swap.yaml` |
| MiOS-LLM-Heavy | `mios-llm-heavy.service` | `:11441` | Heavy GPU lane (SGLang, served-name `mios-heavy`, HiCache CPU KV-offload). Gated/off-by-default (VRAM) |
| MiOS-LLM-Heavy-Alt | `mios-llm-heavy-alt.service` | `:11440` | Alternate heavy lane (vLLM, PagedAttention+APC). Gated/off-by-default (VRAM) |
| MiOS-LLM-Worker | `mios-llm-worker@.service` | — | Single-model swarm workers (templated; for the dGPU swarm topology) |
| MiOS-OpenCode | `mios-opencode-gateway.service` | `:8633` | opencode → OpenAI `/v1` gateway shim; makes opencode a real council peer (loopback) |
| MiOS-OWUI | `mios-open-webui.service` | `:3030` | Browser front-end (Open WebUI) |
| MiOS-Search | `mios-searxng.service` | `:8888` | SearXNG — backs the `web_search` tool |
| MiOS-PGVector | `mios-pgvector.service` | `:5432` | PostgreSQL + pgvector — unified agent datastore (agent_memory, event, tool_call, session, skill, scratch, knowledge, sys_env, kanban, …). Accessed via `mios-pg-query` / `mios-db --pg` |

All agents resolve the endpoint from `MIOS_AI_ENDPOINT` (Law 5); never hard-code a
port or vendor URL. `llama-swap` is the upstream proxy image
(`ghcr.io/mostlygeek/llama-swap`) and the engines speak the OpenAI/Ollama-
compatible API — those are legitimate upstream references; the MiOS *unit
identity* is `mios-llm-light`. The heavy lanes (`mios-llm-heavy`,
`mios-llm-heavy-alt`) are gated in `mios.toml` and stay inert until enabled and
reachable (`health_gate`).

### Service gating conventions

- Bare-metal-only: `ConditionVirtualization=no`
- WSL2-incompatible: `ConditionVirtualization=!wsl`
- Optional: `systemctl enable ... || true`

## Code conventions

### Shell scripts

- `set -euo pipefail` at the top of every phase script.
- Arithmetic: `VAR=$((VAR + 1))`. `((VAR++))` is forbidden — returns 1 under `set -e` when result is 0.
- shellcheck-clean; SC2038 is fatal in CI.
- File naming: `NN-name.sh` where NN encodes execution order.

### Containerfile

- `/ctx` is bind-mounted read-only; mutable writes go to `/tmp/build`.
- `install_weak_deps=False` (underscore, capital F) — `install_weakdeps` is silently ignored by dnf5.
- Never upgrade `kernel`/`kernel-core` in-container (`automation/01-repos.sh` excludes them).

### kargs.d TOML

```toml
kargs = ["init_on_alloc=1", "lockdown=integrity"]
```

Flat top-level array only — no `[kargs]` section header, no `delete` sub-key. Files processed in lexicographic order.

### SELinux

Per-rule individual `.te` modules in `usr/share/selinux/packages/mios/` — not monolithic. New booleans/fcontexts go in `automation/37-selinux.sh`.

## Operator behavioural rules (binding on every Claude session)

These are Claude-Code session constraints — they bound what **this assistant**
may do, and are distinct from (and additive to) the runtime agent posture in
`/MiOS.md`. They follow directly from MiOS's design: Claude builds the image and
its code paths; the *running* MiOS agent stack is what operates the machine.

### NO live launches — implement code, never run apps interactively

Claude is **infrastructure**, not a runtime convenience. When the operator asks for something operational (open Chrome, launch a game, post to a channel, navigate a URL), the answer is to **fix or extend the code path** so the MiOS-Agent stack does it locally — NOT to invoke the launch via Bash/PowerShell/`mios-launch` from this assistant's tools.

Exceptions:
* **Read-only state checks** (Get-Process, journalctl reads, `mios-doctor`, `mios-find` which resolves-without-running, `mios-apps`, CDP `/json/version` probes, file inspections) are fine — anything whose effect is purely observational.
* **One-time API probes** for verifying a service binding (curl to Discord `/users/@me`, CDP `/json/version`, OWUI `/api/v1/functions/`) are fine — they touch external APIs but don't put windows on the operator's screen.

Forbidden:
* Anything whose effect is the operator seeing a NEW window, sound, notification, or app on their machine. The operator has stated this in caps multiple times ("I DON'T WANT YOU TO EVER LAUNCH THE APPS FOR ME!!!"). For verifying launch-chain changes, inspect the broker socket / journal / script source WITHOUT triggering the launch. Tell the operator "shipped; try X in OWUI" and let them verify visibly themselves.

### NO context injection — env discovery via tool calls only

The agent (MiOS-Hermes) learns its environment by **calling tools** (`mios-env-probe`, `mios-apps`, `skill_view name=mios-environment`, the native `mios_verbs.*` surface) — NEVER via a `pre_llm_call` hook that auto-prepends env text to the user message.

When working on Hermes config / hooks / plugins: do not add `pre_llm_call` shapes that return `{"context": "..."}`. If env awareness needs reinforcing, do it in SOUL.md prose telling the agent WHEN to invoke env-discovery tools — not by pre-injecting their output.
