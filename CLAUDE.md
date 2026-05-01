# CLAUDE.md

This file is the agent-CLI entry point for this repository. Tool resolution
relies on the literal filename — the prose below is intentionally vendor-
agnostic.

## Authoritative prompt

This file is a **redirector stub**. The canonical agent prompt for MiOS-DEV
is `/usr/share/mios/ai/system.md`, with `/etc/mios/ai/system-prompt.md`
applied as a host-local override and `~/.config/mios/system-prompt.md` as
per-user override (see resolution order in `system-prompt.md`). A copy of
the canonical prompt lives at `/system.md` in the repo root for off-host
use. Load that first; the rest of this file is agent-CLI-specific delta
plus repo orientation.

## What this repo is

MiOS is an immutable, bootc-native Fedora workstation OS distributed as an
OCI image (`ghcr.io/mios-dev/mios:latest`). This repo is the **system layer**:
the `Containerfile`, `Justfile`, build orchestrators, the `automation/`
pipeline, and the FHS overlay (`usr/`, `etc/`, `home/`, `srv/`, `v1/`) that is
baked into the image. End-user installation lives in a separate repo,
`mios-bootstrap`. See README.md and INDEX.md.

The repo's working tree mirrors the deployed root filesystem — paths in this
tree are FHS paths in the running OS (`/usr/lib/...`, `/etc/containers/...`).

## Common commands

Build orchestration is via `just` (Linux) or `mios-build-local.ps1` (Windows
PowerShell 7+ with WSL2/Podman). Both read defaults from `image-versions.yml`
and XDG-located TOMLs under `~/.config/mios/`.

```bash
just preflight        # System prereq check (tools/preflight.sh)
just build            # podman build → localhost/mios:latest
just build-logged     # Build with tee'd log under logs/
just rechunk          # bootc-base-imagectl rechunk for small Day-2 deltas
just raw              # 80 GiB RAW disk image via bootc-image-builder (BIB)
just iso              # Anaconda installer ISO via BIB
just qcow2 / vhdx / wsl2   # Other disk formats (need MIOS_USER_PASSWORD_HASH)
just sbom             # CycloneDX SBOM via syft
just artifact         # Refresh AI manifests, knowledge, wiki (automation/ai-bootstrap.sh)
just init-user-space  # Lay down ~/.config/mios/{env,images,build}.toml
just show-env         # Print loaded MIOS_* vars
```

`just lint` is referenced in CONTRIBUTING.md but the `lint` target is not
defined in the current Justfile — `bootc container lint` runs as the final
`RUN` of `Containerfile`, so a successful `just build` is the lint gate.

There is no test suite. Validation gates: `automation/99-postcheck.sh` (run
inside the image build), `bootc container lint` (last Containerfile RUN), and
the GitHub Actions smoke-test (PR-only `podman build` in `.github/workflows/mios-ci.yml`).

For a single pipeline phase during local iteration, run the script directly,
not the orchestrator:

```bash
bash automation/<NN>-<name>.sh   # e.g. automation/37-selinux.sh
```

Day-2 (deployed host): `sudo bootc upgrade && sudo systemctl reboot`,
`sudo bootc switch <ref>`, `sudo bootc rollback`, `mios <prompt>`.

## Architecture (the parts that span multiple files)

### Global pipeline phases

The full bootstrap → install pipeline is partitioned into five global phases.
Every doc, log line, and orchestrator script in either repo refers to these
by number:

| Phase | Owner | Purpose |
|---|---|---|
| **Phase-0** | `mios-bootstrap.git/install.sh` | Preflight, profile load, host-kind detection, interactive identity capture. |
| **Phase-1** | `mios-bootstrap.git/install.sh` (`trigger_mios_install`) | Total Root Merge — clone `mios.git` into `/`, copy bootstrap overlays (etc/, usr/, var/, profile/) on top. |
| **Phase-2** | `Containerfile` + `automation/build.sh` (or FHS package install) | Build the running system. The numbered `automation/[0-9][0-9]-*.sh` scripts are *sub-phases* of Phase-2. |
| **Phase-3** | `mios.git/install.sh` + `mios-bootstrap.git/install.sh` (`apply_user_profile`, `deploy_system_prompt`, `stage_user_profile_artifacts`) | systemd-sysusers, systemd-tmpfiles, daemon-reload, services; create the Linux user; stage `~/.config/mios/{profile.toml,system-prompt.md}` and host `/etc/mios/ai/system-prompt.md`. |
| **Phase-4** | `mios-bootstrap.git/install.sh` (`reboot_prompt`) | Interactive `systemctl reboot`. |

### The build pipeline (Phase-2 sub-phases)

`Containerfile` is small. Its single big `RUN` calls
`automation/08-system-files-overlay.sh` (overlay apply) then
`automation/build.sh` — the master orchestrator that iterates every
`automation/[0-9][0-9]-*.sh` in numeric order. The numbering is internal to
Phase-2 and encodes dependencies (repos → kernel → overlay → stack install →
service config → user/GPU → AI/SELinux/polish → supply chain → finalize →
from-source kmods → validate). Do not renumber without understanding the
dependency. Skipped under build: `08-system-files-overlay.sh` (runs
pre-pipeline from Containerfile), `37-ollama-prep.sh` (CI-skipped).

Every script sources `automation/lib/{common,packages,masking}.sh`. The
masking library filters secrets out of build logs; output is teed through
`mask_filter` at the top of `build.sh`.

### PACKAGES.md is the only place packages live

`usr/share/mios/PACKAGES.md` is the single source of truth for every RPM
installed into the image. Scripts pull packages by category via
`get_packages` / `install_packages` / `install_packages_strict` from
`automation/lib/packages.sh`, which extracts content of fenced code blocks
tagged ` ```packages-<category> `. Never `dnf install` a package outside
this system; add it to the appropriate fenced block in PACKAGES.md instead.

### FHS overlay convention

Files under `usr/`, `etc/`, `home/`, `srv/`, `v1/` in this repo correspond
1:1 to paths in the deployed image. Editing `usr/lib/systemd/system/foo.service`
in this repo edits `/usr/lib/systemd/system/foo.service` in the next image.
Overlay copy happens in `automation/08-system-files-overlay.sh`.

### Quadlet sidecars + bound images

Sidecar containers (LocalAI, Ceph, k3s) ship as Quadlet `.container` units
under `etc/containers/systemd/` on the network `mios.network` (10.89.0.0/24).
Each Quadlet's image must be symlinked into `/usr/lib/bootc/bound-images.d/`
so bootc pre-pulls it offline.

### Dual-repo split

This repo (`mios.git`) and `mios-bootstrap.git` resolve to the same physical
root on the dev host but each gitignore whitelists a *different subset*. The
`.gitignore` here is a **whitelist inverter** — `/*` ignores everything,
then `!/path` re-includes the system-overlay subset.

| Path on deployed system | Owner repo | Purpose |
|---|---|---|
| `/usr/share/mios/profile.toml` | `mios.git` | vendor profile defaults (immutable) |
| `/usr/share/mios/env.defaults` | `mios.git` | vendor env defaults |
| `/usr/share/mios/ai/system.md` | `mios.git` | canonical agent prompt |
| `/etc/mios/profile.toml` | `mios-bootstrap.git` | host/admin profile overrides |
| `/etc/mios/install.env` | `mios-bootstrap.git` | runtime identity (written at install) |
| `/etc/mios/ai/system-prompt.md` | `mios-bootstrap.git` | host AI prompt override |
| `/etc/skel/.config/mios/profile.toml` | `mios-bootstrap.git` | per-user TOML template |
| `/etc/skel/.config/mios/system-prompt.md` | `mios-bootstrap.git` | per-user AI prompt template |

When committing to `mios.git`, verify each path matches a whitelist
negation; an untracked file outside the whitelist is correct gitignore
behavior, not "a file to add". User-installer files (`/etc/mios/*`,
`/etc/skel/.config/mios/*`, knowledge graphs) belong in
`mios-bootstrap.git`, not here.

## Defaults policy

Every boolean feature flag in the profile (`[quadlets.enable]`, `[ai]`,
`[network]`, `[bootstrap]`) ships **`true`**. The system does NOT
disable a component via static config. When a component is incompatible
with the host (wrong virtualization layer, missing required path,
missing hardware), systemd `Condition*` directives in the corresponding
Quadlet/service short-circuit it at boot/pre-boot and the unit silently
no-ops. Operators can still set a flag to `false` to force-disable.
See `INDEX.md` §5 for the gating table.

## Architectural laws (from INDEX.md / .cursorrules — non-negotiable)

1. **USR-OVER-ETC** — static config goes in `/usr/lib/<component>.d/`.
   `/etc/` is for admin overrides only. Exception: `/etc/mios/install.env`
   written at first boot.
2. **NO-MKDIR-IN-VAR** — declare every `/var/` path via `usr/lib/tmpfiles.d/`.
   No build-time `/var/` overlays, no `mkdir -p /var/...` in scripts.
3. **BOUND-IMAGES** — Quadlet container images symlinked into
   `/usr/lib/bootc/bound-images.d/`.
4. **BOOTC-CONTAINER-LINT** — must be the final instruction in `Containerfile`.
5. **UNIFIED-AI-REDIRECTS** — agnostic env vars (`MIOS_AI_KEY`,
   `MIOS_AI_MODEL`, `MIOS_AI_ENDPOINT`) targeting `http://localhost:8080/v1`.
   No vendor-specific defaults anywhere.
6. **UNPRIVILEGED-QUADLETS** — every Quadlet defines `User=`, `Group=`,
   `Delegate=yes`. Exception: `mios-k3s.container` may be `Privileged=true`.

## Conventions worth knowing before editing

- Bash scripts: `set -euo pipefail`. `build.sh` itself runs with `-euo pipefail`
  too, but flips `set +e` around each per-script invocation
  (`automation/build.sh:234-237`) so individual phase failures are captured
  in `FAIL_LOG`/`WARN_LOG` rather than aborting the orchestrator.
  Use `VAR=$((VAR + 1))`, never `((VAR++))` — the latter exits 1 when the
  result is 0 and dies under `set -e`.
- Numbered script naming `NN-name.sh` — NN encodes ordering.
- `kargs.d/*.toml` uses a flat top-level `kargs = [...]` array — no
  `[kargs]` section header, no `delete` sub-key. bootc rejects anything else.
- Do not upgrade `kernel` / `kernel-core` inside the build; only add
  `kernel-modules-extra`, `kernel-devel`, `kernel-headers`, `kernel-tools`.
- No `--squash-all` on `podman build` — strips OCI metadata bootc needs.
- `dnf5` option is `install_weak_deps=False` (underscore). The dnf4 form
  `install_weakdeps` is silently ignored.
- `/etc/skel/.bashrc` must be written before `useradd -m`.
- Theme: do not set `GTK_THEME=Adwaita-dark`. Use
  `ADW_DEBUG_COLOR_SCHEME=prefer-dark` and dconf `color-scheme='prefer-dark'`.
- Deliverables: complete replacement files only — no diffs, no patches, no
  "edit this section" snippets.

## Sanitization

Per the canonical prompt §6, anything you persist to `/usr/share/mios/ai/`,
`/etc/mios/ai/`, or any pushed path must be sanitized to OpenAI API-compliant
minimal form: no corporate vendor names in prose (protocol names like
"OpenAI v1 API" stay), no chat metadata, no tool-call envelopes, no foreign
sandbox paths (`/mnt/user-data/`, `/home/claude/`, `/repo/`). Upstream
package names, FHS paths, source code, and protocol endpoints survive
unchanged.

## Agent-CLI deltas

- **Task tracking:** track multi-step audits, refactors, and migrations
  with the agent's task tool. One in-progress at a time; mark completed
  immediately on finish.
- **File-creation defaults:** new scratch files default to
  `/var/lib/mios/ai/scratch/` unless the user specifies a path or the work
  targets the system overlay.
- **Confirm before mutating shared state:** never run `git push`,
  `bootc upgrade`, `dnf install`, `systemctl`, or `rm -rf` without explicit
  user confirmation per invocation.
- **Memory:** per-session learnings go to `/var/lib/mios/ai/memory/`.
  Read the canonical prompt §12 (immutable records, supersedes-only updates)
  before writing.
- **Document-format skills:** docx/pptx/xlsx generation skills are not
  needed for routine work here; skip unless explicitly requested.
