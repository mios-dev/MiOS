# MiOS

> Immutable, bootc-native workstation OS. Self-hosted, OpenAI-API native,
> aligned to FOSS standards. Monorepo for the system layer.

**Version:** v0.2.0
**Image:** `ghcr.io/MiOS-DEV/mios:latest`
**Bootstrap (installer):** https://github.com/MiOS-DEV/MiOS-bootstrap

---

## What lives here

This repository is the **system layer** of MiOS. It contains:

- **Build infrastructure** -- `Containerfile`, `Justfile`, `build-mios.sh`,
  `mios-build-local.ps1`, `preflight.ps1`, `push-to-github.ps1`, all the
  scripts and config that build the bootc OCI image.
- **System-side installer** -- `install.sh` applies the FHS overlay to a
  non-bootc Fedora host. (On bootc-managed hosts, use `bootc switch` instead.)
- **FHS overlay** -- `usr/`, `etc/`, `var/`, `srv/`, `v1/` are the
  files baked into the deployed image. The repository's working tree mirrors
  the deployed root.
- **System docs** -- `INDEX.md`, `AGENTS.md`, `SECURITY.md`, `SELF-BUILD.md`,
  `DEPLOY.md`.
- **CI** -- `.github/workflows/mios-ci.yml` builds the image on every push.

## What does NOT live here

User-facing installation, dotfiles, env templates, and the interactive setup
wizard live in **MiOS-bootstrap**. End users never clone this repo directly;
they run the bootstrap installer, which (on FHS hosts) clones MiOS automatically
to apply the system overlay.

## Installation flows

### Bootc-managed Fedora host (preferred)

End users run:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/MiOS-DEV/MiOS-bootstrap/main/install.sh)"
```

The bootstrap installer prompts for username, hostname, password, etc. (all
defaulting to `mios`), then runs `bootc switch ghcr.io/MiOS-DEV/mios:latest`.
Reboot to activate.

### FHS Fedora Server host

The same bootstrap one-liner. On a non-bootc host, bootstrap clones this repo
and runs `install.sh` to lay down the FHS overlay.

### Local build

For developers working on MiOS itself:

```powershell
# Windows host
.\\mios-build-local.ps1
```

```bash
# Linux host
./build-mios.sh
```

Both orchestrators read defaults from `image-versions.yml` and the user's
`/etc/mios/install.env` (written by bootstrap).

## Architecture

Single source of truth: [INDEX.md](INDEX.md). Agent contract for the deployed
system: [AGENTS.md](AGENTS.md).

## License

Apache-2.0. See [LICENSE](LICENSE) and [LICENSES.md](LICENSES.md) for vendored
component licenses.
