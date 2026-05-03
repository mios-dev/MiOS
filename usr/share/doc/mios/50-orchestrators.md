# Build Orchestrators -- `Justfile` (Linux) and `mios-build-local.ps1` (Windows)

> Source: `Justfile`, `mios-build-local.ps1`, `SELF-BUILD.md`,
> `DEPLOY.md`.

## Linux -- `just`

The `Justfile` exposes the canonical build targets:

| Target | What it does |
| --- | --- |
| `just preflight` | System prereq check (`tools/preflight.sh`). |
| `just flight-status` | Show variable mappings (`tools/flight-control.sh`). |
| `just build` | `podman build --no-cache` with `--build-arg` for `BASE_IMAGE`, `MIOS_FLATPAKS`, `MIOS_USER`, `MIOS_HOSTNAME`. Output: `localhost/mios:latest`. |
| `just build-logged` | Same, with unified log to `logs/build-<UTC>.log`. |
| `just build-verbose` | Same, no redirection. |
| `just lint` | `podman run --rm --entrypoint /usr/bin/bootc <local> container lint`. (The Containerfile's final RUN already runs lint at build time; this re-runs it on the built image.) |
| `just rechunk` | `bootc-base-imagectl rechunk --max-layers 67` for 5-10× smaller Day-2 deltas, then re-tag. |
| `just raw` | BIB → 80GiB ext4 RAW (`config/artifacts/bib.toml` + `--type raw`). |
| `just iso` | BIB → Anaconda installer ISO (`config/artifacts/iso.toml` + `--type iso`). **Only mount `iso.toml`** -- mounting both `bib.toml` and `iso.toml` crashes BIB with "found config.json and also config.toml". |
| `just qcow2` | BIB → QEMU qcow2. **Requires** `MIOS_USER_PASSWORD_HASH` env var (and optionally `MIOS_SSH_PUBKEY`); the recipe `sed`-substitutes them into a temp copy of `config/artifacts/qcow2.toml`. |
| `just vhdx` | BIB → `.vhd` (VPC format), then `qemu-img convert -f vpc -O vhdx`. Same env vars as `qcow2`. |
| `just wsl2` | BIB → `tar.gz` for `wsl --import`. |
| `just sbom` | `anchore/syft` → CycloneDX-JSON at `artifacts/sbom/mios-sbom.json`. |
| `just all-bootstrap` | `build` → `rechunk` → log artifacts to bootstrap repo via `tools/log-to-bootstrap.sh`. |
| `just init-user-space` | XDG-compliant user config (`tools/init-user-space.sh`). |
| `just show-env` | Dump loaded `MIOS_*` env vars. |
| `just edit-env` / `edit-images` / `edit-build` / `edit-flatpaks` | Edit per-user TOML/list configs under `~/.config/mios/`. |

## Justfile env vars

| Variable | Default | Purpose |
| --- | --- | --- |
| `MIOS_BASE_IMAGE` | `ghcr.io/ublue-os/ucore-hci:stable-nvidia` | OCI base image (Justfile:45). |
| `MIOS_LOCAL_TAG` | `localhost/mios:latest` | Local image tag (Justfile:13). |
| `MIOS_USER` | `mios` | Default account baked into the image (Containerfile:26). |
| `MIOS_HOSTNAME` | `mios` | Default hostname (Containerfile:27). |
| `MIOS_FLATPAKS` | (empty) | Comma-separated Flatpak refs (Containerfile:28). |
| `MIOS_USER_PASSWORD_HASH` | required for qcow2/vhdx | `openssl passwd -6 'yourpass'`. |
| `MIOS_SSH_PUBKEY` | optional | SSH public key to bake. |
| `MIOS_BIB_IMAGE` | `quay.io/centos-bootc/bootc-image-builder:latest` | BIB image. |
| `MIOS_REGISTRY_DEFAULT` | `ghcr.io/MiOS-DEV/mios` | Push target (note: image refs are case-insensitive in OCI; lowercase `ghcr.io/mios-dev/mios` is canonical). |

## Windows -- `mios-build-local.ps1`

Five-phase orchestrator:

1. **Prompt** for username, password, LUKS passphrase, registry credentials.
2. **Builder machine** -- create the `mios-builder` Podman machine (rootful, all cores, all RAM, 250 GB disk).
3. **Build** -- inject credentials, run `podman build`, `rechunk`, restore placeholders.
4. **Disk images** -- generate via BIB: RAW, VHDX, WSL2 tarball, Anaconda ISO.
5. **Push** -- push to GHCR, mark package public, restore the default Podman machine, print a report.

Companion Windows scripts:

| File | Purpose |
| --- | --- |
| `preflight.ps1` | System prereq check (Git, Podman Desktop, WSL2). |
| `push-to-github.ps1` | Standalone GHCR push helper. |
| `Get-MiOS.ps1` | Pull the latest signed image. |
| `install.ps1` | User-facing installer (delegates to `mios-bootstrap`). |

## Build modes (SELF-BUILD.md)

- **Mode 0 -- Bootstrap** (initial install, fresh Linux): `curl ... install.sh`.
- **Mode 1 -- CI/CD** (production): `.github/workflows/mios-ci.yml` builds, rechunks on tag, signs keyless with cosign, pushes on tag and `main`.
- **Mode 2 -- Windows local**: `.\mios-build-local.ps1`.
- **Mode 3 -- Linux local**: `just build` etc.
- **Mode 4 -- Self-build** (running 'MiOS' builds the next 'MiOS'):

  ```bash
  git clone https://github.com/mios-dev/MiOS.git && cd 'MiOS'
  sudo podman build --no-cache --build-arg MIOS_USER=mios --build-arg MIOS_HOSTNAME=mios -t localhost/mios:dev .
  sudo podman run --rm --entrypoint /usr/bin/bootc localhost/mios:dev container lint
  sudo bootc-base-imagectl rechunk --max-layers 67 \
      localhost/mios:dev localhost/mios:rechunked
  sudo bootc switch --transport containers-storage localhost/mios:rechunked
  sudo systemctl reboot
  ```
- **Mode 5 -- Ignition appliance**: `config/ignition/` Butane configs compiled with `butane` to `.ign` for fully automated builds on a fresh Fedora CoreOS or Fedora Server instance.

## Build requirements

| Resource | Minimum | Recommended |
| --- | --- | --- |
| CPU cores | 4 | 8+ |
| RAM | 8 GB | 16+ GB |
| Disk (builder) | 100 GB | 250 GB |
| Network | required (RPM + base image pulls) | fast for ~2-4 GB of RPM downloads |

`dnf5` cache mounts in the `Containerfile` (`--mount=type=cache,...`) make
subsequent rebuilds 5-10× faster.
