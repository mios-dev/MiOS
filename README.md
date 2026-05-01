# MiOS

Immutable, bootc-native Fedora workstation OS distributed as an OCI
image. Local OpenAI-compatible AI surface, FOSS-aligned.

- **Version:** v0.2.0 (`VERSION`)
- **Image:** `ghcr.io/mios-dev/mios:latest`
- **Bootstrap (user-facing installer):** <https://github.com/mios-dev/mios-bootstrap>

## What lives here

This repo is the **system layer**. It contains:

- Build infrastructure: `Containerfile`, `Justfile`, `build-mios.sh`,
  `mios-build-local.ps1`, `preflight.ps1`, `push-to-github.ps1`.
- Build pipeline: `automation/build.sh` orchestrates 50+ numbered phase
  scripts under `automation/`.
- FHS overlay: `usr/`, `etc/`, `home/`, `srv/`, `v1/` mirror the
  deployed image root 1:1.
- System docs: `INDEX.md`, `ARCHITECTURE.md`, `ENGINEERING.md`,
  `SECURITY.md`, `SELF-BUILD.md`, `DEPLOY.md`, `CONTRIBUTING.md`.
- CI: `.github/workflows/mios-ci.yml`.

User-facing install, dotfiles, env templates, and the interactive setup
wizard live in `mios-bootstrap`. End users do not clone this repo
directly.

## Install

**Windows 11** (Podman Desktop + WSL2):

```powershell
irm https://raw.githubusercontent.com/mios-dev/mios-bootstrap/main/install.ps1 | iex
```

Installs as a Windows application (`%LOCALAPPDATA%\Programs\MiOS\`), clones both repos,
registers in Add/Remove Programs, creates Start Menu shortcuts, and auto-configures WSL2.
Requires [Git](https://git-scm.com/download/win), [Podman Desktop](https://podman-desktop.io), and WSL2.

**Linux** (Fedora bootc):

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/mios-dev/mios-bootstrap/main/install.sh)"
```

On a bootc-managed Fedora host this resolves to `bootc switch
ghcr.io/mios-dev/mios:latest`. On an FHS host it clones this repo and
runs `install.sh` for the FHS overlay. See `DEPLOY.md`.

## Build

```bash
just preflight      # System prereq check
just build          # OCI image
just lint           # bootc container lint (re-run on built image)
just rechunk        # Optimized Day-2 deltas
just raw            # 80 GiB RAW disk image
just iso            # Anaconda installer ISO
just qcow2          # QEMU qcow2 disk image (needs MIOS_USER_PASSWORD_HASH)
just vhdx           # Hyper-V VHDX disk image (needs MIOS_USER_PASSWORD_HASH)
just wsl2           # WSL2 tar.gz for wsl --import
just sbom           # CycloneDX SBOM
just all-bootstrap  # build + rechunk + log artifacts to bootstrap repo
```

Windows: `.\preflight.ps1 ; .\mios-build-local.ps1`. See `SELF-BUILD.md`.

## Architecture

Single source of truth: `INDEX.md`. Build pipeline and code conventions:
`ENGINEERING.md`. Filesystem and hardware: `ARCHITECTURE.md`. Security
posture: `SECURITY.md`. Agent contract: `usr/share/mios/ai/system.md`
(canonical), `CLAUDE.md` / `GEMINI.md` / `AGENTS.md` (per-tool stubs).

## License

Apache-2.0 (`LICENSE`). Bundled-component licenses in `LICENSES.md`.
