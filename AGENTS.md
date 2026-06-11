# AGENTS.md

> `/AGENTS.md` — the [agents.md][1]-standard **repo entry point** for any
> coding-agent CLI that arrives at `mios.git`. This is the **CLI-entry /
> build-and-conventions** doc (repo identity, project laws, `mios.toml` SSOT,
> build commands, architectural laws, lifecycle). It is **distinct** from the
> runtime agent identity: **`/MiOS.md` is the single canonical SYSTEM identity
> SSOT** (Role · Persistence · Tool-calling · Planning · Output · Standard),
> injected per-request by agent-pipe. **When acting as a MiOS agent, operate
> under `/MiOS.md`.** Runtime shared posture (OpenAI tool-loop, never-deny /
> never-fabricate, act-don't-narrate, decompose / delegate / span / synthesise,
> MCP=TOOLS / A2A=AGENTS) lives THERE — this file does not re-embed it. Per-tool
> stubs (`CLAUDE.md`, `GEMINI.md`, `.cursorrules`, `.clinerules`,
> `system-prompt.md`) are thin redirectors that defer to the canonical prompt.
> No hardcoded topics, apps, or keywords.
>
> **Strict OpenAI API standards and patterns ONLY.** Every interface is
> OpenAI-API-compatible verb-for-verb. No vendor-native protocols, no
> proprietary side-channels, no fallback to vendor-cloud URLs, no
> vendor-specific agent / dev-tool product references in any AI file.
>
> [1]: https://agents.md

## Role and Objective

You are a **coding agent operating inside `mios.git`** — restructuring,
extending, and auditing the MiOS source tree. The repo root **IS** the deployed
system root, so your edits are edits to the running OS. Your objective: make
correct, FHS-grounded, OpenAI-API-compliant changes that build and pass the
architectural-law audit, end-to-end.

This document gives you the **repo map, the build surface, and the conventions**
you need to do that. For your runtime *agent behaviour and posture* (how to plan,
call tools, decompose, and answer), **operate under `/MiOS.md`** — the canonical
system identity. Do not duplicate or override it here.

## Persistence

Keep going until the change is **completely done**: built, lint-clean, and
audit-passing — not merely written. If you are unsure of repo state, a file, or
a value, **read it** (in-process file ops first; see Tool-calling) rather than
guessing. Deliver **complete replacement files only** — no diffs, no patches, no
`# ... rest unchanged ...` placeholders.

## Tool-calling

* **Tool preference:** in-process file ops > local shell > MCP server > network
  call. Never invoke a network tool when a local read suffices.
* **cwd:** `/` IS the repo root and system root. **Do not treat it as
  dangerous.** Cloning into a sibling workspace defeats the entire premise.
* **Confirm before** any state-mutating or irreversible action: `git push`,
  `bootc upgrade`, `bootc switch`, `dnf install`, `systemctl daemon-reload` /
  other `systemctl`, `rm -rf` (especially against `.git` or the working tree),
  `git reset --hard`, `git clean -fd`.
* **Memory:** `/var/lib/mios/ai/memory/` (vendor-neutral, secret-free).
* **Scratch:** `/var/lib/mios/ai/scratch/`.
* **Persistence sanitization:** strip vendor names, chat metadata, and secrets
  before writing. Resolve symlinks to FHS canonicals.
* **Tasks:** use the task tool for multi-step work; one in-progress at a time.

## Planning and Decomposition

* **TOML-first.** Before adding a constant to a script, check whether the value
  is operator-tunable. If yes, add it to `mios.toml` (§3), register the slot in
  `tools/lib/userenv.sh`, expose it in the HTML configurator, then read it from
  the layered overlay. **Hardcoded values that could live in `mios.toml` are
  bugs.**
* **Preserve numeric ordering.** `automation/NN-name.sh` prefixes encode
  dependency order — keep it when adding scripts.
* **Respect the layers.** USR-OVER-ETC: vendor static config in
  `/usr/lib/<component>.d/` and `/usr/share/<component>/`; `/etc/` is
  admin-override only.

## Output

* **Deliverables:** complete replacement files only. No diffs, no patches, no
  placeholders.
* **Tone:** direct, technical, no hedging qualifiers, no emoji unless the user
  asked. Ground every suggestion in a concrete FHS path with file:line.
* **OpenAI-API-only.** Never reference vendor-specific agent CLIs, dev-tool
  products, or cloud-AI URLs in MiOS docs / code / commit messages. The OpenAI
  public API surface is the only addressable contract.
* **Failure mode.** When a question is outside MiOS scope or the data isn't
  available locally, say so explicitly — *"I don't have that on this host; check
  `<concrete file or URL>`."* Don't fabricate FHS paths or invent endpoint URLs.
  Don't name vendor-specific agent or dev-tool products. If unsure between two
  valid sources, name both and let the operator choose.

## Standard

Every agent / model / tool surface is OpenAI-API-compatible:
`/v1/chat/completions`, `/v1/responses`, `/v1/embeddings`, `/v1/models`,
function-calling, structured outputs, MCP via the Responses API. Doc layout
follows OpenAI's topical split (`concepts/`, `guides/`, `reference/`, `audits/`).
Behave as a standard OpenAI tool-using agent; the full runtime tool-loop posture
is specified in `/MiOS.md`.

---

## 1. Repo identity

* **Project:** MiOS — pronounced *MyOS*, short for *My OS / My Operating
  System*. Research project, Apache-2.0.
* **Shape:** immutable bootc-native Fedora workstation OS distributed as
  an OCI image. `bootc upgrade` rolls forward; `bootc rollback` rolls
  back.
* **Repo invariant:** the repo root **IS** the deployed system root.
  Browse `usr/`, `etc/`, `srv/`, `var/` here and you are looking at
  exactly where those files land on a booted MiOS host. **`.git` IS `/`.**
* **Version:** `VERSION` (top-level) → `/usr/share/mios/VERSION` →
  resolved by `automation/lib/globals.{sh,ps1}`.
* **Default image ref:** `ghcr.io/mios-dev/mios:latest`.

## 2. The three project-wide laws

1. **Native Linux FHS folder structuring.** `/usr/share/<pkg>/` for
   vendor data, `/usr/lib/<pkg>/` for vendor code, `/etc/<pkg>/` for
   admin overrides, `/var/lib/<pkg>/` for runtime state. No
   `system_files/`, no `ansible/`, no out-of-tree scaffolding.
2. **OpenAI API standards FULLY.** Every agent / model / tool surface
   is OpenAI-API-compatible: `/v1/chat/completions`, `/v1/responses`,
   `/v1/embeddings`, `/v1/models`, function-calling, structured
   outputs, MCP via the Responses API. Doc layout follows OpenAI's
   topical split (`concepts/`, `guides/`, `reference/`, `audits/`).
3. **MiOS is a root filesystem overlay; `.git` IS `/`.** This repo,
   materialized at `/`, IS the OS. `git pull` at `/` upgrades the
   running system. Tracked-path changes flow through `git commit` →
   push (local Forgejo at `localhost:3000` AND/OR GitHub) → CI rebuild
   → `bootc switch`.

## 3. `mios.toml` is THE singular SSOT

**`mios.toml` is the singular file that runs the entire pipeline.** It
is the **library of every verb, variable, and value** the codebase
consumes. Edited as HTML in a local browser by the defined user, saved
locally, and fetched by the pipeline.

### What the TOML carries (inline)

* **Packages** — RPMs, Flatpaks, OCI images, layered package sets per
  deployment shape (`[packages.<section>].pkgs`)
* **Dependencies** — every transitive requirement, audit-able by reading
  the TOML alone
* **Repositories** — GitHub remotes, local Forgejo URL, OCI registries,
  upstream git mirrors
* **Applications** — every layered Quadlet container, every Flatpak
  desktop app, every native window app
* **Tools** — CLI surfaces, helper scripts, dev tools
* **Settings** — every operator-tunable knob across the entire stack
* **Username / Linux account** — uid 1000 `mios` user, full credentials
  pipeline (`[identity]`, `[auth]`)
* **Color palette** — globally applied, **platform-agnostically**,
  across every terminal and console (Windows Terminal, conhost,
  GNOME Terminal, tmux, MOTD, fastfetch, oh-my-posh, dashboard
  borders) — `[colors]` → `MIOS_COLOR_*` / `MIOS_ANSI_*` exports →
  `etc/profile.d/mios-colors.sh`
* **Extras / bloat / optional** — operator-toggled add-ons
* **Passwords + credentials** — operator-set, persisted only in the
  TOML overlay (never round-tripped through `install.env`'s readable
  bridge for secret keys)
* **Quadlets** — `[quadlets.enable]` table + per-Quadlet parameters
* **User preferences** — theme, terminal dims (80×40), locale,
  keyboard, timezone

### The edit-save-fetch lifecycle

1. **Edit:** operator opens `mios.html` (or
   `/usr/share/mios/configurator/mios.html`) in a **local browser**.
   No server, no extension, no install step — `file://` is fine.
2. **Save:** configurator writes the updated TOML to disk.
3. **Fetch:** the pipeline reads the TOML from the layered overlay
   (`~/.config > /etc > /usr/share`) and uses it to drive every
   downstream step.
4. **Overlay/install:** TOML selections bake into the overlay
   **before** installation. No mid-install prompts that bypass the
   TOML.

### Resolution layers (highest first)

```
~/.config/mios/mios.toml      # per-user (highest)
/etc/mios/mios.toml           # host
/usr/share/mios/mios.toml     # vendor (lowest, always present)
```

**Empty / missing user TOML is the vendor-default state, not an error.**
Code paths that fatal without a user TOML are bugs.

**Hardcoded values that could live in `mios.toml` are bugs.** Lift
them, register the slot in `tools/lib/userenv.sh`, expose them in the
HTML configurator.

Shell/systemd consumers use the derived bridge `/etc/mios/install.env`;
run `mios-sync-env` after editing `mios.toml` to refresh it.

### Package management

Single source of truth: `usr/share/mios/mios.toml` under
`[packages.<section>].pkgs`. Never call `dnf install` on hard-coded
names. Use the helpers from `automation/lib/packages.sh`:

```bash
install_packages "<category>"           # best-effort, --skip-unavailable
install_packages_strict "<category>"    # fails on any miss
install_packages_optional "<category>"  # pure best-effort, never fails
```

Human-readable rationale docs live at
`usr/share/doc/mios/reference/PACKAGES.md` — that is documentation,
not the runtime SSOT.

## 4. Loading order (runtime system prompt)

This file (AGENTS.md) is the agents.md-standard repo entry. The runtime
LLM **system identity** is **`/MiOS.md`** (layered SSOT:
`~/.config/mios/MiOS.md` < `/etc/mios/MiOS.md` < `/MiOS.md`), injected
per-request by agent-pipe. The legacy vendor prompt
`/usr/share/mios/ai/system.md` and the per-role overlays point to
`/MiOS.md`. Per-tool stubs (`CLAUDE.md`, `GEMINI.md`, `.cursorrules`,
`.clinerules`, `system-prompt.md`) are thin redirectors. Host/admin and
per-user prompt overrides load highest-precedence first:

1. `~/.config/mios/system-prompt.md` — per-user override
2. `/etc/mios/ai/system-prompt.md` — host/admin override
3. canonical identity (`/MiOS.md`) — vendor canonical (lowest)

## 5. Architectural laws (build/runtime, audited)

Enforced by build-time lint and `automation/99-postcheck.sh`:

| # | Law | Enforced by |
|---|---|---|
| 1 | **USR-OVER-ETC** — vendor static config in `/usr/lib/<component>.d/` and `/usr/share/<component>/`; `/etc/` is admin-override only. | `automation/`, `usr/lib/`, `etc/` |
| 2 | **NO-MKDIR-IN-VAR** — every `/var/` path declared via `usr/lib/tmpfiles.d/*.conf`. Never written at build time. | `usr/lib/tmpfiles.d/mios*.conf` |
| 3 | **BOUND-IMAGES** — every Quadlet image symlinked into `/usr/lib/bootc/bound-images.d/` and baked into `/usr/lib/containers/storage` at build time. | `usr/lib/bootc/bound-images.d/`, `automation/08-system-files-overlay.sh` |
| 4 | **BOOTC-CONTAINER-LINT** — every build ends with `bootc container lint`. Fail = fail the build. | `Containerfile` (last `RUN`) |
| 5 | **UNIFIED-AI-REDIRECTS** — every OpenAI-API-shaped client resolves through `MIOS_AI_ENDPOINT` (default `http://localhost:8642/v1`), `MIOS_AI_MODEL`, `MIOS_AI_KEY`. **No vendor-cloud URLs. No vendor-specific agent / dev-tool product names anywhere.** | `/etc/profile.d/mios-env.sh`, `usr/bin/mios`, `usr/bin/mios-env`, `etc/mios/ai/` |
| 6 | **UNPRIVILEGED-QUADLETS** — every Quadlet declares `User=`, `Group=`, `Delegate=yes`. Documented exceptions: `mios-ceph`, `mios-k3s`, `mios-forgejo-runner`, `qdrant`. | `etc/containers/systemd/`, `usr/share/containers/systemd/` |
| 7 | **OFFLINE-FIRST** — every MiOS lifecycle phase works without internet from EITHER scenario: (1) a pre-built MiOS image, or (2) full repos on a USB drive + a Windows or minimal Fedora live env. Lifecycle phases: **overlay → pull → build → deploy → run → host → re-build → use AI** — all offline-capable. AI agents + tools + scripts + models + knowledge + skills + browser + search + code-run sandboxes all run from the local MiOS stack. Internet-using features (Discord, Tailscale, GitHub PRs, web_search-against-cloud Firecrawl/Tavily/Exa) are OPTIONAL and gracefully degrade when offline; nothing CORE is gated on network reachability. Operator-restated 2026-05-17. **See `docs/concepts/OFFLINE-FIRST.md` for the per-phase capability matrix + remaining build-time gaps.** | runtime: `automation/08-system-files-overlay.sh` (bound-images), model-bake automation, `usr/share/mios/owui/`, `web.search_backend: searxng` seeded config. build: cached wheels + bundled binaries (see OFFLINE-FIRST.md for gap status) |

## 6. Endpoint contract (OpenAI-compatible)

Local API at `http://localhost:8642/v1`. The runtime serves **GGUF
models via llama.cpp / llama-swap** (Ollama is retired); every MiOS AI
surface resolves through `MIOS_AI_ENDPOINT` per Architectural Law 5 —
never hard-code a port, backend, or vendor URL.

| Path | Method | Purpose |
|---|---|---|
| `/v1/models` | GET | list available models |
| `/v1/chat/completions` | POST | streaming chat completions |
| `/v1/embeddings` | POST | embeddings |
| `/v1/audio/{transcriptions,speech}` | POST | when configured |

Default model: `mios.toml [ai].model`. Streaming is mandatory for chat;
non-streaming is reserved for batch tools.

MCP servers registered at `/usr/share/mios/ai/v1/mcp.json`:

* `mios-fs` — read-only fs browser scoped to `/var/lib/mios` + `/usr/share/mios`
* `mios-kb` — local KB retrieval over the OpenAI-shaped manifest
* `mios-forge` — Forgejo REST API at `http://localhost:3000/api/v1`

Standard invocation: `POST /v1/responses` with
`tools=[{"type":"mcp","server_url":...}]`.

## 7. Day-0 → Day-N self-replication flow

### Day-0 — Windows entry (thin shell only)

The Windows entry point is **strictly an entry point**:

1. `irm | iex` of `Get-MiOS.ps1` (paste into Win+R, cmd, or any pwsh)
2. Acknowledgements (AGREEMENTS.md ack)
3. `M:\` provisioned at exactly 256 GB NTFS (label `MIOS-DEV`)
4. Local Windows-side installs (Windows Terminal + MiOS scheme,
   Geist Mono Nerd Font, oh-my-posh, fastfetch, MiOS native-app
   shortcut)
5. Podman Desktop + `MiOS-DEV` podman machine provisioned
6. **SSH handoff into MiOS-DEV** — everything else happens inside

After SSH handoff, the operator types `mios build` in the WT MiOS
profile. From that point forward, the **build dashboard renders in
the WT MiOS-DEV SSH window** (running locally on the podman-MiOS-DEV
machine). The dashboard combines the unified installation status
output with `mios dash` (banner / header ASCII art, fastfetch stats,
MOTD stats).

### Day-N — Self-development loop (inside MiOS-DEV / any Fedora host)

1. Boot any Fedora-based machine (or already inside MiOS-DEV)
2. `curl | bash` (Linux) / `irm | iex` (Windows) the bootstrap URL
3. Acknowledgements
4. **SSOT TOML/HTML prompt** — operator edits `mios.toml` via
   `mios.html` in a local browser (Epiphany on MiOS-DEV, rendered to
   Windows via WSLg + wayland/mutter window portal)
5. Save selections to overlay files
6. Overlay the local system with all MiOS packages + dependencies
7. Pull remaining repo files
8. Complete installations + overlays
9. **Develop directly inside MiOS-DEV.** Dev environment is
   OpenAI-API-compatible only and routes through `MIOS_AI_ENDPOINT`.
   Repo files materialized from every source.
10. Iterate, commit, push — **dual-push:** local Forgejo
    (`http://mios@localhost:3000/mios/mios.git`) AND/OR GitHub
    (`origin main`)
11. Push triggers CI/CD: Forgejo Runner OR GitHub Actions builds
    `MiOS(NON-DEV)`
12. Test deployments locally for ALL formats (see §8)
13. Debug → repeat
14. Pull latest at MiOS-DEV's root (`git -C / pull`); re-overlay
15. Loop — back to step 2, now at Day-N+1

**`.git` IS `/` is the load-bearing premise.** Edits to `/` are edits
to the source. The next boot IS the edit.

## 8. Build artifact matrix

The pipeline produces deployment-shape outputs for ALL of:

* **Hyper-V** — `.vhdx` + `.ps1` launcher
* **WSL2/g** — `.tar` / `.vhdx` with WSLg windowing
* **QEMU** — `qcow2`
* **OCI image** — canonical bootc surface
* **Live-CD / Live-USB**
* **USB installer** — Anaconda / coreos-installer
* **RAW disk image** — `dd`-able

Build outputs land on the operator-chosen data partition (`M:\` by
default per `env.defaults` on Windows; the configured build-output
path on Linux), NEVER under `%LOCALAPPDATA%`.

## 9. Build pipeline (11 phases)

`./mios-pipeline.{sh,ps1}` is the canonical orchestrator. Each phase
consumes a specific `mios.toml` section and corresponds to numbered
scripts under `automation/[NN]-*.sh`:

| Phase | Name | Reads from `mios.toml` |
|---|---|---|
|  1 | Questions | `[identity].*`, `[ai].*` |
|  2 | Stage | `[bootstrap].*`, `[image].*` |
|  3 | MiOS-DEV | (Windows host only; Podman-WSL2 dev VM) |
|  4 | Overlay | `[colors]`, all of `usr/`, `etc/` |
|  5 | Account | `[identity]`, `[auth]` (overlay-time, not firstboot) |
|  6 | Install | `[packages].sections`, `[network].*` |
|  7 | Smoketest | `automation/99-postcheck.sh` + arch-law audits |
|  8 | Build | `[image].*`, `[desktop].flatpaks` |
|  9 | Deploy | local hardware detection picks host-compatible image |
| 10 | Boot | `[quadlets.enable].*` |
| 11 | Repeat | re-run hint |

Re-run a single phase: `./mios-pipeline.sh --phase 6` (or `-Phase 6`).

### Containerfile build flow

Single-stage build with a `ctx` scratch context:

1. `ctx` stage copies `automation/`, `usr/`, `etc/`, `tools/`,
   `VERSION`, `config/artifacts/` read-only.
2. Main stage bind-mounts `/ctx` read-only; mutable copies go to
   `/tmp/build`.
3. CRLF → LF normalization runs over all text files before any script
   executes (Windows build hosts leak CRLFs past `.gitattributes`).
4. `automation/08-system-files-overlay.sh` runs before the main build
   pipeline (pre-pipeline, from the Containerfile).
5. `automation/build.sh` iterates every `automation/[0-9][0-9]-*.sh` in
   numeric order. `08-system-files-overlay.sh` (runs pre-pipeline) and
   `37-ollama-prep.sh` (CI-skipped) are skipped by `build.sh`.
6. Final `RUN bootc container lint` (Architectural Law 4 — fail = fail
   the build).
7. Never `--squash-all`: strips `ostree.final-diffid` and breaks BIB.

### Bootstrap phase ownership

| Phase | Owner | Description |
|---|---|---|
| Phase-0 | `mios-bootstrap` | Preflight, profile load, identity capture |
| Phase-1 | `mios-bootstrap` | Total Root Merge (clone `mios.git` into `/`, overlay bootstrap) |
| Phase-2 | `Containerfile` / `automation/build.sh` | Build (numbered sub-phases) |
| Phase-3 | both | sysusers/tmpfiles/services + user create + per-user config staging |
| Phase-4 | `mios-bootstrap` | Reboot |

Numbered automation scripts (`automation/NN-name.sh`) are sub-phases of
Phase-2. The prefix encodes dependency order — preserve it when adding
scripts.

## 10. Setup / build commands

```bash
# From scratch on Linux
git clone https://github.com/mios-dev/MiOS.git && cd MiOS
just preflight
just build
just iso       # or: just raw / just qcow2 / just vhdx / just wsl2
```

```powershell
# From scratch on Windows — irm|iex from Win+R
powershell -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/mios-dev/mios-bootstrap/main/Get-MiOS.ps1 | iex"
```

```bash
# On a Fedora-bootc-compatible host
bootc switch ghcr.io/mios-dev/mios:latest
sudo systemctl reboot
```

### `just` recipes (Linux)

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

### Windows build scripts

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

## 11. Code conventions

### Shell scripts

* `set -euo pipefail` at the top of every phase script.
* Arithmetic: `VAR=$((VAR + 1))`. `((VAR++))` is forbidden — returns 1
  under `set -e` when the result is 0.
* shellcheck-clean; SC2038 is fatal in CI.
* File naming: `NN-name.sh` where `NN` encodes execution order.

### Containerfile

* `/ctx` is bind-mounted read-only; mutable writes go to `/tmp/build`.
* `install_weak_deps=False` (underscore, capital F) — `install_weakdeps`
  is silently ignored by dnf5.
* Never upgrade `kernel` / `kernel-core` in-container
  (`automation/01-repos.sh` excludes them).

### kargs.d TOML

```toml
kargs = ["init_on_alloc=1", "lockdown=integrity"]
```

Flat top-level array only — no `[kargs]` section header, no `delete`
sub-key. Files processed in lexicographic order.

### SELinux

Per-rule individual `.te` modules in
`usr/share/selinux/packages/mios/` — not monolithic. New
booleans/fcontexts go in `automation/37-selinux.sh`.

### Service gating conventions

* Bare-metal-only: `ConditionVirtualization=no`
* WSL2-incompatible: `ConditionVirtualization=!wsl`
* Optional: `systemctl enable ... || true`

## 12. Hardware and runtime context

* `/run/mios/gpu-passthrough.status` — GPU detection result (JSON)
* `/run/cdi/{nvidia.yaml,amd.json,intel.yaml}` — per-vendor CDI specs
* `/etc/mios/install.env` — bootstrap-staged env exports
* `/usr/share/mios/VERSION` — running mios.git tag
* `/var/lib/mios/bootc-switch-history.tsv` — last successful `bootc switch`
* `/var/lib/mios/.wsl-firstboot-done`, `/var/lib/mios/.ollama-firstboot-done`

User accounts (`mios` uid 1000, plus the sidecar service accounts) are
baked at OVERLAY TIME via `/usr/lib/sysusers.d/*.conf` +
`automation/31-user.sh` + `/usr/lib/tmpfiles.d/mios-user.conf`. **Never
propose runtime patches to `/etc/passwd`, `/etc/subuid`, `/etc/subgid`,
or `/var/lib/systemd/linger` in firstboot scripts.**

## 13. Where things live

| Topic | Path |
|---|---|
| Runtime agent system identity (SSOT) | [`/MiOS.md`](MiOS.md) |
| Architectural contract (agent-facing) | [`usr/share/mios/ai/INDEX.md`](usr/share/mios/ai/INDEX.md) |
| Legacy vendor system prompt (redirects to `/MiOS.md`) | [`usr/share/mios/ai/system.md`](usr/share/mios/ai/system.md) |
| Read-only audit-mode prompt | [`usr/share/mios/ai/audit-prompt.md`](usr/share/mios/ai/audit-prompt.md) |
| OpenAI v1 surface manifests | [`usr/share/mios/ai/v1/`](usr/share/mios/ai/v1/) |
| HTML configurator (TOML editor) | [`usr/share/mios/configurator/mios.html`](usr/share/mios/configurator/mios.html) |
| Filesystem and hardware layout | [`usr/share/doc/mios/concepts/architecture.md`](usr/share/doc/mios/concepts/architecture.md) |
| Build pipeline conventions | [`usr/share/doc/mios/guides/engineering.md`](usr/share/doc/mios/guides/engineering.md) |
| Hardening kargs and posture | [`usr/share/doc/mios/guides/security.md`](usr/share/doc/mios/guides/security.md) |
| Build modes (CI / Linux / Windows / self-build) | [`usr/share/doc/mios/guides/self-build.md`](usr/share/doc/mios/guides/self-build.md) |
| bootc + Day-2 lifecycle | [`usr/share/doc/mios/guides/deploy.md`](usr/share/doc/mios/guides/deploy.md) |
| OpenAI-compatible AI surface (full spec) | [`usr/share/doc/mios/reference/api.md`](usr/share/doc/mios/reference/api.md) |
| Sources / credits / licenses | [`usr/share/doc/mios/reference/{sources,credits,licenses}.md`](usr/share/doc/mios/reference/) |
| Annotated FHS tree | [`usr/share/doc/mios/reference/tree.md`](usr/share/doc/mios/reference/tree.md) |
| Audit reports | [`usr/share/doc/mios/audits/`](usr/share/doc/mios/audits/) |
| LLM ingest indexes | [`llms.txt`](llms.txt), [`llms-full.txt`](llms-full.txt) |
</content>
</invoke>
