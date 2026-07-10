<!-- AI-hint: Claude Code entry point for mios.git — the MiOS SYSTEM repo (the OCI/bootc image source), where the repo root IS the deployed system root. Use this to navigate the build pipeline (Containerfile -> automation/NN-*.sh), the mios.toml SSOT, the six architectural laws, the local AI plane, and the `just` build surface. Defers to AGENTS.md / /usr/share/mios/ai/system.md for runtime agent identity.
     AI-related: usr/share/mios/mios.toml, usr/share/mios/ai/system.md, usr/share/mios/ai/INDEX.md, automation/lib/packages.sh, automation/99-postcheck.sh, usr/lib/bootc/kargs.d/, usr/share/mios/llamacpp/mios-llm-light.yaml, http://localhost:8080/v1 -->
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Canonical agent prompt: `AGENTS.md` (this repo's agents.md-standard entry) → `/usr/share/mios/ai/system.md` (deployed vendor canonical). This file covers only the Claude-Code-specific deltas for working on the source tree.

## What this repo is

This is **`mios.git`** (`github.com/mios-dev/MiOS`) — the **system FHS overlay** of MiOS, an immutable, `bootc`/OCI-shaped Fedora workstation that is *also* a local, self-hosted agentic AI OS. The entire OS is one rebuildable container image (`ghcr.io/mios-dev/mios:latest`): boot it, `bootc upgrade` it like a `git pull`, `bootc rollback` it like a Ctrl-Z.

**The repo root IS the deployed system root.** `usr/`, `etc/`, `srv/`, `var/` here land at exactly those paths on a booted host — no `system_files/` indirection, no Ansible. Browse `usr/` on GitHub and you're looking at `/usr` on the machine. When you edit a file here you are editing the OS.

This repo defines *what the OS is*. The sibling **`mios-bootstrap.git`** (interactive installer + user-editable overlay; also cloned locally at `C:\mios-bootstrap`) defines *how an operator gets onto it and tunes it*. **Never double-track paths across the two repos** — `mios.git` owns the FHS overlay, Containerfile, systemd units, Quadlets, kernel args, tmpfiles, sysusers; `mios-bootstrap.git` owns installer scripts and the user profile layer.

> Note: several top-level scripts here (`Get-MiOS.ps1`, `build-mios.*`, `bootstrap.*`, `install.*`, `mios.toml`) are bootstrap-owned files that also appear in this working tree. The canonical Linux build surface for *this* repo is the `justfile` + `Containerfile` + `automation/`; treat those as the source of truth.

## The build pipeline (the core mental model)

The image is built by a single `Containerfile` that runs **every script in `automation/NN-*.sh` in numeric order**. Each script does one thing (install packages, configure SELinux, render the UKI, generate Quadlets, generate CDI specs…); the numeric prefix encodes execution order. To add a build step, drop a new `45-myfeature.sh` next to its peers — do not thread it through some central dispatcher.

```
Containerfile  →  automation/01-*.sh … 99-postcheck.sh  →  OCI image  →  bootc lifecycle on host
```

Shared build helpers live in `automation/lib/` (`common.sh`, `packages.sh`, `paths.sh`, `globals.sh`, `masking.sh`). `automation/99-postcheck.sh` is the final gate that enforces the architectural laws.

## `mios.toml` — the singular SSOT

`usr/share/mios/mios.toml` is the runtime source of truth for every operator-tunable value: packages, ports, AI lanes, models, services. Packages resolve from `[packages.<section>].pkgs`, parsed by `automation/lib/packages.sh`. **A hardcoded constant that belongs in the TOML is a bug** — lift it into `mios.toml`, expose it in the configurator (`/usr/share/mios/configurator/`), and read it back through the layered overlay.

Three-layer resolution (highest wins): `~/.config/mios/mios.toml` (per-user) → `/etc/mios/…` (host/admin) → `/usr/share/mios/mios.toml` (vendor default). Empty strings do **not** override non-empty values below them.

## Common commands (`just` is the Linux SSOT)

The `justfile` is the source of truth for the Linux build; `just --list` shows every target.

```bash
just preflight        # host readiness checks (tools/preflight.sh)
just build            # podman build the OCI image (runs preflight + flight-status first)
just lint             # bootc container lint against the freshly built image
just drift-gate       # source-tree fitness functions — NO built image needed; safe on every PR
just iso              # build + emit installer ISO   (also: raw / qcow2 / vhdx / wsl2)
just all              # build + every artifact format
just init-user-space  # seed ~/.config/mios/mios.toml from the vendor template
just show-env         # print resolved MIOS_* environment
just edit             # open the user mios.toml in $EDITOR
```

Windows equivalent of the Linux build: `mios-build-local.ps1`. On a provisioned Windows host the operator drives builds through the `mios` verb dispatcher (`mios build`, `mios dev`), which hands off into the `MiOS-DEV` podman machine — **all builds run inside `MiOS-DEV`, never on the Windows host directly.**

### Tests / lint (run these before proposing a build)

`just drift-gate` is the fast pre-image check and bundles the two test suites:
1. **SSOT-render conformance** — `bash automation/38-ssot-lint.sh` (asserts every `${MIOS_*}` Quadlet placeholder is wired on both ends).
2. **agent-pipe unit tests** — `test_mios_*.py` under `usr/lib/mios/agent-pipe/`, run via `python3` (prefers the `.venv` at `/usr/lib/mios/agents/.venv/bin/python3` if present).

Run a single agent-pipe test directly:
```bash
cd usr/lib/mios/agent-pipe && python3 test_mios_<name>.py
```
Additional standalone dispatcher/extraction tests live in `tests/` (`test-*.py`, `test-*.sh`) — run each file directly.

## The six architectural laws (enforced by lint + `automation/99-postcheck.sh`)

Every change must obey these; a failing law fails the build:

1. **USR-OVER-ETC** — static config lives in `/usr/lib/<component>.d/`; `/etc/` is for admin overrides only.
2. **NO-MKDIR-IN-VAR** — every `/var/` path is declared via `usr/lib/tmpfiles.d/*.conf`, never `mkdir`'d at build time.
3. **BOUND-IMAGES** — every Quadlet image is symlinked into `/usr/lib/bootc/bound-images.d/` so it ships *with* the host.
4. **BOOTC-CONTAINER-LINT** — every build ends with `bootc container lint`; fail the lint, fail the build.
5. **UNIFIED-AI-REDIRECTS** — every agent and tool targets `MIOS_AI_ENDPOINT` (`http://localhost:8080/v1`). No vendor-hardcoded cloud URLs, no vendor-specific agent/product names in code, docs, or commit messages.
6. **UNPRIVILEGED-QUADLETS** — every Quadlet declares `User=`, `Group=`, `Delegate=yes`. Documented exceptions only: `mios-ceph`, `mios-k3s`.

Quadlets are generated, not hand-edited into final form — see `automation/14-generate-quadlets.sh` and `15-render-quadlets.sh`. Kernel args ship in `usr/lib/bootc/kargs.d/`.

## The local AI plane

The "self-hosted agent OS" half ships *inside* the image and is reachable through one OpenAI-compatible front door: **`http://localhost:8080/v1`** (named by `MIOS_AI_ENDPOINT`). Lanes are named by *function*, not upstream tool:

| Component | Port | Role |
|---|---|---|
| `mios-llm-light` | `:8450` | **Primary** lane — `llama.cpp` behind the `llama-swap` proxy; auto-swaps chat/reasoning models, serves embeddings (`nomic-embed-text`) + the `mios-opencode` coder model. Model map: `usr/share/mios/llamacpp/mios-llm-light.yaml` |
| `mios-llm-heavy` / `-alt` | `:8441` / `:8442` | Heavy GPU lanes (vLLM `:8441` / SGLang `:8442`) — **gated off by default** on VRAM grounds |
| agent-pipe | `:8640` | Router/dispatch gateway every front-end talks to; decomposes + fans out to agents, calls tools |
| MiOS-Hermes | `:8642` | OpenAI-compatible agent gateway — owns sessions, the tool-loop, skills, browser control |
| prefilter | `:8641` | Injects fan-out hints on decomposable prompts |
| `mios-pgvector` | `:8432` | Unified agent datastore (PostgreSQL + pgvector): memory, events, tool calls, sessions, skills, and a `knowledge` table with vector recall |
| SearXNG | `:8899` | Local search backing `web_search` |
| opencode-gateway | `:8633` | Serves the coder peer as a `/v1` council member |

Throughline: **inference lanes → agent-pipe/Hermes orchestration → pgvector memory → MCP/A2A tools**. The full contract is `usr/share/doc/mios/reference/api.md`; the agent-facing architectural contract is `usr/share/mios/ai/INDEX.md`.

## Claude Code deltas

- **cwd:** on a deployed host `/` IS both the repo root and the system root. Bootstrap/dev files map directly to FHS destinations. Don't treat `/` as inherently dangerous.
- **Confirm before:** `git push`, `bootc switch`, `bootc upgrade`, `dnf install`, `systemctl`, `rm -rf`, `git reset --hard`, `git clean -fd`, `wsl --unregister`, `podman machine rm`, `Remove-Partition`.
- **Deliverables:** complete replacement files only — no diffs, no `# ... rest unchanged ...` placeholders.
- **Memory:** `/var/lib/mios/ai/memory/` · **Scratch:** `/var/lib/mios/ai/scratch/` (both runtime-only, not committed).
- The repo-root agent files (`MiOS.md`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`) are **baked into the image** (`Containerfile` copies them to `/ctx/rootmd/`) and are the deployed agent identity contract — editing this file edits a shipped OS artifact.

## Conventions

- **Latest packages** — default to newest stable upstream when pinning RPMs, OCI tags, or base images; bump conservative pins forward on next touch unless held for a documented reason.
- **OpenAI-API-only** — the OpenAI public surface (`/v1/chat/completions`, `/v1/responses`, `/v1/embeddings`, `/v1/models`, function-calling, MCP via Responses API) is the only addressable AI contract.
- **Every artifact is tracked** — generated files get a `.gitignore` whitelist line, staged and committed; `git pull` must restore full context.
- **Persistence sanitization** — before writing to memory/scratch, strip vendor-specific names and chat metadata, reduce paths to FHS canonicals, never persist secrets.

See `CONTRIBUTING.md` for contribution conventions and `usr/share/doc/mios/guides/engineering.md` for the full build-pipeline + shell rules.
