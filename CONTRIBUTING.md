# Contributing to 'MiOS'

## Project rules

- **Single source of truth: `usr/share/mios/ai/INDEX.md` + `usr/share/mios/mios.toml`.**
  Every package belongs in `mios.toml [packages.<section>].pkgs`,
  every architectural rule in `usr/share/mios/ai/INDEX.md`. Other docs
  cite, never duplicate. Human-readable package documentation lives at
  `usr/share/doc/mios/reference/PACKAGES.md` -- it is documentation, not
  the runtime SSOT.
- **USR-OVER-ETC, NO-MKDIR-IN-VAR, BOUND-IMAGES, BOOTC-CONTAINER-LINT,
  UNIFIED-AI-REDIRECTS, UNPRIVILEGED-QUADLETS** -- see `usr/share/mios/ai/INDEX.md` §3.
  Violating any of the six is a build/audit fail.
- **Pure build-up.** Only the ~25 GNOME packages required for the desktop
  ship. No `dnf remove` bloat blocks. User-facing apps are Flatpaks; RPMs
  are restricted to kernel modules, drivers, virtualization, container
  runtime, system tools, and GNOME infrastructure.
- **Nothing gets removed without permission.** If a file or package
  exists in the repo, do not delete it in a PR without prior discussion.
- **Complete files only.** No diffs, patches, fragments, or
  "paste this into X" instructions. Every contribution is a drop-in
  replacement.

## Prerequisites

- Podman (rootful, for bootc image builds)
- 8 GB RAM, 250 GB disk on the builder
- Windows: PowerShell 7+ and WSL2

## Building

Linux:

```bash
just preflight   # System prereq check
just build       # Build the OCI image
just lint        # Re-run bootc container lint on the built image
just rechunk     # Optimized Day-2 deltas
just raw         # RAW disk image via BIB
just iso         # Anaconda ISO via BIB
just sbom        # CycloneDX SBOM via syft
```

Windows:

```powershell
.\preflight.ps1
.\mios-build-local.ps1
```

The PowerShell orchestrator handles Podman machine creation, credential
injection, image build, rechunk, disk-image generation, GHCR push, and
cleanup.

## Code conventions

### Shell scripts

- `set -euo pipefail`. `automation/build.sh` runs with `-e` and toggles
  `set +e` only around the per-phase invocation
  (`automation/build.sh:234-237`); phase scripts themselves are strict.
- Arithmetic: `VAR=$((VAR + 1))`. Never `((VAR++))`.
- Use `install_packages` / `install_packages_strict` /
  `install_packages_optional` from `automation/lib/packages.sh`. Never
  call `dnf install` on hard-coded names.
- File naming: `NN-name.sh` where NN encodes execution order.

### Containerfile

- `/ctx` is bind-mounted read-only from the `ctx` stage. Mutating writes
  go to `/tmp/build`.
- `SYSTEMD_OFFLINE=1` and `container=podman` to prevent scriptlet hangs
  (set automatically by Podman; do not override).
- Final RUN must be `bootc container lint`.

### System files

- Immutable config: `/usr/lib/`.
- Admin-overridable config: `/etc/` (only when upstream contract demands
  /etc/, e.g., yum repos, nvidia-container-toolkit).
- The `usr/`, `etc/`, `home/`, `srv/` directories at repo root mirror the
  deployed root; the overlay is applied by
  `automation/08-system-files-overlay.sh`.

### SELinux

- Per-rule individual `.te` modules, not monolithic.
- New booleans/fcontexts go in the `semanage` block of
  `automation/37-selinux.sh`.

### Services

- Bare-metal-only: `ConditionVirtualization=no` drop-in.
- WSL2-incompatible: `ConditionVirtualization=!wsl`.
- Optional: `systemctl enable ... || true`.

## Submitting changes

1. Branch from `main`.
2. Local validation: `just build` (Containerfile lint runs as final RUN).
3. If you added or changed packages, edit `usr/share/mios/mios.toml`
   under the matching `[packages.<section>]` table (the configurator
   HTML at `usr/share/mios/configurator/mios.html` is the WYSIWYG
   editor for the same file). Update `usr/share/doc/mios/reference/PACKAGES.md`
   in the same PR if the prose rationale changes.
4. If user-facing, bump `VERSION`.
5. Open a PR against `main`.

## Issue templates

- Bug Report -- for broken behavior.
- Feature Request -- for new functionality.
- Security -- see `SECURITY.md` for private disclosure.

## License

Contributions are accepted under the project license (Apache-2.0,
`LICENSE`).

## Upstream references

- bootc: <https://github.com/containers/bootc>
- bootc-image-builder: <https://github.com/osbuild/bootc-image-builder>
- bootc docs: <https://bootc-dev.github.io/bootc/>
- Universal Blue (uCore base): <https://github.com/ublue-os/main>
- uupd: <https://github.com/ublue-os/uupd>
- rechunk: <https://github.com/hhd-dev/rechunk>
- cosign: <https://github.com/sigstore/cosign>
- bootstrap repo (user-facing installer): <https://github.com/mios-dev/mios-bootstrap>
