# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Canonical agent prompt: `/usr/share/mios/ai/system.md` (deployed from `mios-bootstrap`).
> Loading order: `/usr/share/mios/ai/system.md` → `/etc/mios/ai/system-prompt.md` (host override) → `~/.config/mios/system-prompt.md` (user override).

## What this repo is

MiOS is an immutable, `bootc`-managed Fedora-derived workstation OS distributed as an OCI image. The repo root **is** the deployed system root: `usr/`, `etc/`, `srv/`, `var/`, `proc/`, `opt/` at the top level mirror their FHS-3.0 destinations. There is no `system_files/` indirection; `automation/08-system-files-overlay.sh` overlays them into the image.

The published image is `ghcr.io/mios-dev/mios:latest` and is built `FROM ghcr.io/ublue-os/ucore-hci:stable-nvidia` (set via `MIOS_BASE_IMAGE`).

## Build commands

Linux orchestrator is `Justfile`; Windows orchestrator is `mios-build-local.ps1`. Do not invent a "cloud-ws.ps1" or four-stage pipeline — neither exists.

```bash
just preflight    # System prereq check (tools/preflight.sh)
just build        # Build OCI image -> localhost/mios:latest
just lint         # Re-run `bootc container lint` on the built image
just rechunk      # Optimize Day-2 deltas (rechunk into versioned tag)
just raw          # RAW disk image via BIB
just iso          # Anaconda installer ISO via BIB
just qcow2        # Requires MIOS_USER_PASSWORD_HASH env (openssl passwd -6)
just vhdx         # Hyper-V VHDX (same env requirement)
just wsl2         # WSL2 tarball
just sbom         # CycloneDX SBOM via syft
just artifact     # Refresh AI manifests, UKB, and Wiki docs
just all-bootstrap # build + rechunk + log to bootstrap repo
```

Windows: `.\preflight.ps1` then `.\mios-build-local.ps1` (rootful Podman machine, credential injection, BIB, GHCR push, cleanup).

The `Containerfile` already runs `bootc container lint` as its final RUN — `just build` is itself the lint gate.

## Phase-2 build pipeline (the `automation/` directory)

`Containerfile` triggers `automation/build.sh`, which iterates every `automation/[0-9][0-9]-*.sh` in lexicographic numeric order. **Sub-phase numbering encodes dependency order and must be preserved when adding new scripts.** Per-script failures are captured in `FAIL_LOG`/`WARN_LOG` (set +e wrapper around each invocation, `automation/build.sh:234-237`) — the orchestrator does not abort. Critical packages are post-validated via `rpm -q` against `packages-critical` from `PACKAGES.md`.

Skipped under the in-Containerfile build:
- `08-system-files-overlay.sh` — runs pre-pipeline directly from `Containerfile`
- `37-ollama-prep.sh` — CI-skipped

The full pipeline spans five phases owned by two repos:

| Phase | Owner | Description |
|---|---|---|
| 0 | `mios-bootstrap.git/install.sh` | Preflight + profile load + identity capture |
| 1 | `mios-bootstrap.git/install.sh` | Total Root Merge of `mios.git` and `mios-bootstrap.git` to `/` |
| 2 | `Containerfile` + `automation/build.sh` | Build (this repo) |
| 3 | `mios.git/install.sh` + bootstrap profile staging | sysusers/tmpfiles + user create + per-user `~/.config/mios/{profile.toml,system-prompt.md}` |
| 4 | `mios-bootstrap.git/install.sh` | Reboot prompt |

## Architectural Laws (non-negotiable, build/audit-fail on violation)

1. **USR-OVER-ETC** — static config in `/usr/lib/<component>.d/`; `/etc/` is admin-override only. Documented exceptions are upstream-contract surfaces (`/etc/yum.repos.d/`, `/etc/nvidia-container-toolkit/`).
2. **NO-MKDIR-IN-VAR** — every `/var/` path declared via `usr/lib/tmpfiles.d/*.conf`. **Never write to `/var/` at build time.** bootc forbids it; lint will fail.
3. **BOUND-IMAGES** — every Quadlet image symlinked into `/usr/lib/bootc/bound-images.d/`. Binder loop: `automation/08-system-files-overlay.sh:74-86`.
4. **BOOTC-CONTAINER-LINT** — must be the final `RUN` of `Containerfile`. No `--squash-all` (strips OCI metadata bootc needs).
5. **UNIFIED-AI-REDIRECTS** — all agents target `MIOS_AI_ENDPOINT` (`http://localhost:8080/v1`). Vendor-hardcoded URLs are forbidden. Endpoint served by `etc/containers/systemd/mios-ai.container`.
6. **UNPRIVILEGED-QUADLETS** — every Quadlet declares `User=`, `Group=`, `Delegate=yes`. Documented root exceptions: `mios-ceph`, `mios-k3s` (file headers explain why).

## Package management

Single source of truth: `usr/share/mios/PACKAGES.md`. Every RPM lives in a fenced ` ```packages-<category>` block parsed by `automation/lib/packages.sh:get_packages` (regex `/^```packages-${category}$/,/^```$/`). **Never call `dnf install` on hard-coded names.** Use:

- `install_packages "<category>"` — best-effort, `--skip-unavailable`
- `install_packages_strict "<category>"` — fails the script on any miss
- `install_packages_optional "<category>"` — pure best-effort, never fails

Kernel rule: only add `kernel-modules-extra`, `kernel-devel`, `kernel-headers`, `kernel-tools`. Never upgrade `kernel`/`kernel-core` in-container — `automation/01-repos.sh` excludes them. dnf option spelling is `install_weak_deps=False` (underscore); `install_weakdeps` is silently ignored by dnf5.

## Containerfile shape

Single-stage main image with a `ctx` scratch context that bind-mounts read-only at `/ctx`. Mutating writes go to `/tmp/build`. The `Containerfile` pre-pipeline `RUN` installs `packages-base` (security stack) before `automation/build.sh` runs.

## Shell conventions

- `set -euo pipefail` at the top of every phase script.
- Arithmetic: `VAR=$((VAR + 1))`. **`((VAR++))` is forbidden** — under `set -e` it exits 1 when the result is 0.
- shellcheck-clean. SC2038 is fatal in CI (`.github/workflows/mios-ci.yml`).
- File naming: `NN-name.sh` where NN encodes execution order.

## Kargs format

`usr/lib/bootc/kargs.d/*.toml` uses a flat top-level array; bootc rejects anything else:

```toml
kargs = ["init_on_alloc=1", "lockdown=integrity"]
```

No `[kargs]` section header, no `delete` sub-key. Files processed in lexicographic order; earlier entries cannot be removed by later files in the same image — use runtime `bootc kargs --delete` for removal.

Note: `lockdown=integrity` (not `confidentiality`). `init_on_alloc=1`, `init_on_free=1`, `page_alloc.shuffle=1` are **disabled** in MiOS due to NVIDIA/CUDA incompatibility.

## Service gating

- Bare-metal-only services: `ConditionVirtualization=no` drop-in.
- WSL2-incompatible: `ConditionVirtualization=!wsl`.
- Optional: `systemctl enable ... || true`.

Every boolean in `usr/share/mios/profile.toml` ships **`true`**; the system never disables a component via static config — Quadlet `Condition*` directives short-circuit incompatible units silently.

## Claude Code operating context

- **cwd:** `/` is both the repo root and the deployed system root — do not treat it as dangerous.
- **Confirm before:** `git push`, `bootc upgrade`, `dnf install`, `systemctl`, `rm -rf`.
- **Deliverables:** complete replacement files only — no diffs, no patches, no "paste this into X" fragments. Nothing in the repo gets removed without prior discussion.
- **Memory:** `/var/lib/mios/ai/memory/`
- **Scratch:** `/var/lib/mios/ai/scratch/`
- **Tasks:** use the task tool for multi-step work; one in-progress at a time.

## Cross-references

- Architectural laws and API surface: `INDEX.md`
- Filesystem and hardware layout: `ARCHITECTURE.md`
- Engineering standards (this file's authoritative source for build rules): `ENGINEERING.md`
- Build modes: `SELF-BUILD.md`
- Deployment and Day-2 lifecycle: `DEPLOY.md`
- Security posture and hardening kargs: `SECURITY.md`
- Contribution conventions: `CONTRIBUTING.md`
