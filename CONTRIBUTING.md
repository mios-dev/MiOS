<!-- AI-hint: Defines project-wide contribution rules, build constraints (USR-OVER-ETC, no-bloat, the six Architectural Laws), and the mandatory build/lint workflow contributors and agents follow to keep the MiOS image deterministic, atomic, and self-contained. Use this when preparing a PR: where files go, how to build/lint, and what a contribution must satisfy.
     AI-related: mios-build-local, mios-dev, mios-bootstrap, automation/build.sh, usr/share/mios/ai/INDEX.md, usr/share/mios/mios.toml -->
# Contributing to 'MiOS'

## What you are contributing to

MiOS is one thing built two ways at once: an **immutable, bootc/OCI-shaped
Fedora workstation** (the whole OS is a single container image — boot it,
`bootc upgrade` it like a `git pull`, `bootc rollback` it like a Ctrl-Z) that is
*also* a **local, self-replicating, agentic AI operating system**. The same image
that ships GNOME/Wayland, NVIDIA+ROCm+iGPU via CDI, KVM/libvirt with VFIO
passthrough, and a k3s+Ceph one-node-cluster path also ships a full local agent
stack behind one OpenAI-compatible endpoint.

That dual nature is why this repo is laid out the way it is, and why the rules
below are non-negotiable: **the repo root IS the deployed system root.** The
`Containerfile` bakes `usr/`, `etc/`, `srv/`, `var/` exactly where they land on a
booted host; the build pipeline assembles the image; the bootc lifecycle carries
it forward (`build pipeline → OCI image → bootc upgrade/rollback`). When you edit
a file here you are editing the OS — including the AI plane (the inference lanes,
the agent orchestrator, the pgvector memory) that are just more numbered steps in
the same pipeline.

**The purpose of this document** is to tell you how to contribute to that image
without breaking the contract that makes the dual promise honest: the six
Architectural Laws, the build-up discipline, and a build/lint workflow that ends
in a clean `bootc container lint`. Read it before you open a PR.

## Project rules

- **Single source of truth: `usr/share/mios/ai/INDEX.md` + `usr/share/mios/mios.toml`.**
  Every package belongs in `mios.toml [packages.<section>].pkgs`,
  every architectural rule in `usr/share/mios/ai/INDEX.md`. Other docs
  cite, never duplicate. Human-readable package documentation lives at
  `usr/share/doc/mios/reference/PACKAGES.md` -- it is documentation, not
  the runtime SSOT. Everything operator-tunable (packages, ports, AI
  lanes, services, agent behaviour) flows from `mios.toml`; never hardcode
  a literal that belongs there.
- **USR-OVER-ETC, NO-MKDIR-IN-VAR, BOUND-IMAGES, BOOTC-CONTAINER-LINT,
  UNIFIED-AI-REDIRECTS, UNPRIVILEGED-QUADLETS** -- the six Architectural
  Laws; see `usr/share/mios/ai/INDEX.md` §3. They are the contract that lets
  MiOS be both immutable and agentic at once: Laws 1-4 keep the image
  deterministic, atomic, and self-contained so bootc can upgrade/roll it back;
  Laws 5-6 keep the AI plane unified and least-privileged so the agent stack
  stays portable and sandboxed. Violating any of the six is a build/audit fail.
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

The deliverable of a build is the OCI image (and, optionally, disk artifacts cut
from it) — the same image the bootc lifecycle then deploys and rolls back.
Everything from `just preflight` to `just iso` is "produce the MiOS image"; the
Architectural Laws are the contract that image must satisfy, enforced by the
final `bootc container lint`.

Linux:

```bash
just preflight   # System prereq check
just build       # Build the OCI image (bootc container lint runs as the final step)
just lint        # Re-run bootc container lint on the built image
just rechunk     # Optimized Day-2 deltas
just raw         # RAW disk image via BIB
just iso         # Anaconda ISO via BIB
just sbom        # CycloneDX SBOM via syft
```

(`just --list` shows every target, including the other disk artifacts — `qcow2`,
`vhdx`, `wsl2`, `all`.)

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
- File naming: `NN-name.sh` where NN encodes execution order (it is a sub-phase
  of the numbered build pipeline — the prefix is dependency order).

### Containerfile

- `/ctx` is bind-mounted read-only from the `ctx` stage. Mutating writes
  go to `/tmp/build`.
- `SYSTEMD_OFFLINE=1` and `container=podman` to prevent scriptlet hangs
  (set automatically by Podman; do not override).
- Final RUN must be `bootc container lint` (Architectural Law 4).

### System files

- Immutable config: `/usr/lib/`.
- Admin-overridable config: `/etc/` (only when upstream contract demands
  /etc/, e.g., yum repos, nvidia-container-toolkit).
- The `usr/`, `etc/`, `home/`, `srv/` directories at repo root mirror the
  deployed root; the overlay is applied by
  `automation/08-system-files-overlay.sh`.

### Quadlets (container units)

- Every Quadlet declares `User=`, `Group=`, `Delegate=yes` (Law 6,
  UNPRIVILEGED-QUADLETS). Documented exceptions carry their rationale in
  the unit header.
- Every Quadlet image is symlinked into `/usr/lib/bootc/bound-images.d/`
  and baked into local storage at build time (Law 3, BOUND-IMAGES) so the
  whole stack — including the AI containers — ships *inside* the image.
- AI/agent units resolve their model endpoint from `MIOS_AI_ENDPOINT`
  (Law 5, UNIFIED-AI-REDIRECTS); never hard-code a port or vendor URL.

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
4. If you added or changed a port, AI lane, or service, do it in
   `usr/share/mios/mios.toml` — that is the SSOT every consumer derives from.
5. If user-facing, bump `VERSION`.
6. Open a PR against `main`.

## Issue templates

- Bug Report -- for broken behavior.
- Feature Request -- for new functionality.
- Security -- see `SECURITY.md` for private disclosure.

## License

Contributions are accepted under the project license (Apache-2.0,
`LICENSE`).

## Upstream references

These are external tools and standards MiOS integrates with — legitimate
upstream references, kept current:

- bootc: <https://github.com/containers/bootc>
- bootc-image-builder: <https://github.com/osbuild/bootc-image-builder>
- bootc docs: <https://bootc-dev.github.io/bootc/>
- Universal Blue (uCore base): <https://github.com/ublue-os/main>
- uupd: <https://github.com/ublue-os/uupd>
- rechunk: <https://github.com/hhd-dev/rechunk>
- cosign: <https://github.com/sigstore/cosign>
- the upstream llama-swap proxy (the proxy image fronting the `mios-llm-light`
  inference lane; the lanes speak the OpenAI/Ollama-compatible API):
  <https://github.com/mostlygeek/llama-swap>
- bootstrap repo (user-facing installer): <https://github.com/mios-dev/mios-bootstrap>
