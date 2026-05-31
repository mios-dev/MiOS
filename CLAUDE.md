# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Canonical agent prompt: `/usr/share/mios/ai/system.md` (deployed from `mios-bootstrap`).

## Loading order

1. Load `/usr/share/mios/ai/system.md`.
2. Apply `/etc/mios/ai/system-prompt.md` if present (host override).
3. Apply `~/.config/mios/system-prompt.md` if present (user override).

## Claude Code deltas

* **cwd:** `/` is the repo root and system root — do not treat it as dangerous.
* **Confirm before:** `git push`, `bootc upgrade`, `dnf install`, `systemctl`, `rm -rf`.
* **Deliverables:** complete replacement files only — no diffs, no patches.
* **Memory:** `/var/lib/mios/ai/memory/`
* **Scratch:** `/var/lib/mios/ai/scratch/`
* **Tasks:** use the task tool for multi-step work; one in-progress at a time.

## Build commands

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
| `MIOS_OLLAMA_BAKE_MODELS` | CSV of models baked into the image at build time |
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

| Phase | Owner | Description |
|---|---|---|
| Phase-0 | `mios-bootstrap` | Preflight, profile load, identity capture |
| Phase-1 | `mios-bootstrap` | Total Root Merge (clone `mios.git` into `/`, overlay bootstrap) |
| Phase-2 | `Containerfile` / `automation/build.sh` | Build (numbered sub-phases) |
| Phase-3 | both | sysusers/tmpfiles/services + user create + per-user config staging |
| Phase-4 | `mios-bootstrap` | Reboot |

Numbered automation scripts (`automation/NN-name.sh`) are sub-phases of Phase-2. The prefix encodes dependency order — preserve it when adding scripts. `08-system-files-overlay.sh` and `37-ollama-prep.sh` are skipped by `build.sh` (the former runs pre-pipeline from the Containerfile; the latter is CI-skipped).

### Architectural laws (non-negotiable; violations fail the build/audit)

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

Three-layer override (highest wins):

```
~/.config/mios/mios.toml     # per-user
/etc/mios/mios.toml          # host/admin (written by bootstrap)
/usr/share/mios/mios.toml    # vendor defaults (immutable, shipped in image)
```

Shell/systemd consumers use the derived bridge `/etc/mios/install.env`; run `mios-sync-env` after editing `mios.toml` to refresh it. The static configurator UI at `/usr/share/mios/configurator/index.html` is a browser-local TOML editor for the same file.

### AI stack

| Service | Port | Role |
|---|---|---|
| MiOS-Hermes (`hermes-agent.service`) | `:8642` | OpenAI-compat agent gateway — sessions, tool-calling, skills |
| MiOS-Prefilter | `:8641` | Injects `tool_choice=delegate_task` on fan-outable prompts, forwards to Hermes |
| MiOS-Inference (`ollama.service`) | `:11434` | Raw model + embeddings |
| MiOS-OWUI | `:3030` | Browser front-end (Open WebUI) |
| MiOS-Search | `:8888` | SearXNG — backs `web_search` tool |

All agents resolve the endpoint from `MIOS_AI_ENDPOINT`; never hard-code a port or vendor URL. Optional inference backends (LocalAI, vLLM, llama.cpp, Qdrant, LiteLLM) are off by default — flip them on in `mios.toml [ai]`.

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
