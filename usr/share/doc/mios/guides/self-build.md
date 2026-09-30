<!-- AI-hint: Documentation for the MiOS self-build lifecycle, detailing the build chain, CI/CD workflows, and local build modes (Bootstrap, CI/CD, Windows, Linux/Justfile, in-place self-build, Ignition appliance) for generating the MiOS OCI image and the disk images cut from it.
     AI-related: mios-dev, mios-bootstrap, mios-ci, mios-build-local, mios-builder, mios-build-driver, mios-installer -->
# Self-build guide

## What this is, and why it matters

MiOS is one thing built two ways at once: an **immutable, bootc/OCI-shaped
Fedora workstation** (the whole OS is a single container image — boot it,
`bootc upgrade` it like a `git pull`, `bootc rollback` it like a Ctrl-Z) that is
*also* a **local, self-replicating agentic AI operating system**. The same image
that ships the GNOME/Wayland desktop, GPU wiring (NVIDIA + ROCm + iGPU via CDI),
KVM/libvirt VFIO passthrough, and the k3s + Ceph one-node-cluster path also ships
the full local agent stack — inference lanes, the agent-pipe orchestrator,
MiOS-Hermes, PostgreSQL+pgvector memory — behind one OpenAI-compatible endpoint.

"Self-replicating" is the literal property this guide documents: because the
whole OS is a single rebuildable OCI image, the default package configuration
retains the compiler, source, container and verification tools for producing its
next generation. Disk artifacts use the configured `bootc-image-builder` OCI
image through Podman; a host command with that name is not a prerequisite.
The build pipeline is the front half of the system lifecycle —
**build pipeline → OCI image → bootc lifecycle on the host** — and self-build is
the loop that closes it: `MiOS vN` builds `MiOS vN+1`, then deploys it atomically
and can roll it back. This doc is the operator/builder reference for every way
that loop can be driven.

Source of truth: `Containerfile`, `Justfile`, and
`/usr/share/mios/mios.toml`. `[packages.self-build]` declares image, repository
and verification tools and composes `[packages.build-toolchain]` through
`requires_sections`. `[packages.devcontainer]` consumes the same shared groups.
`/usr/share/doc/mios/reference/PACKAGES.md` explains the package policy; it does
not supply a fallback package catalog. See the deeper build-pipeline
rules in [`engineering.md`](engineering.md) and the deploy/Day-2 side in
[`deploy.md`](deploy.md).

## Build chain

```
'MiOS' vN (running) → podman build → 'MiOS' vN+1 (OCI image)
                                         ↓
                              rechunk → cosign keyless sign → push to GHCR
                                         ↓
                              bootc upgrade → reboot → 'MiOS' vN+1 (running)
```

The image is the deliverable; the disk artifacts (RAW / ISO / qcow2 / VHDX /
WSL2 tarball) are cut *from* that same image by `bootc-image-builder`. Whatever
mode you use, the final `RUN bootc container lint` (Architectural Law 4) must
pass or the build fails — that is what keeps each generation deterministic and
deployable.

## Modes

### Mode 0 -- Bootstrap (initial install, fresh Linux)

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/mios-dev/mios-bootstrap/main/install.sh)"
```

Runs the bootstrap installer from `mios-bootstrap.git`. On a non-bootc
host it clones this repo and runs `install.sh` to lay down the FHS
overlay (the repo root IS the deployed system root — `usr/`, `etc/`, `srv/`,
`var/` land exactly where you see them); on a bootc-managed Fedora host it runs
`bootc switch ghcr.io/mios-dev/mios:latest`.

### Mode 1 -- CI/CD (recommended for production)

`.github/workflows/mios-ci.yml` builds, rechunks (on tag push), signs
(keyless cosign), and pushes the image on every tag and on `main`.
End users receive updates via the bootc lifecycle:

```bash
sudo bootc upgrade && sudo systemctl reboot
```

### Mode 2 -- Windows local build

Use the [bootstrap entry and installation guide](https://github.com/mios-dev/mios-bootstrap/blob/main/usr/share/doc/mios-bootstrap/guides/bootstrap_install.md).
Windows provisions the host and hands builds to `podman-MiOS-DEV`. The resource
budget comes from the resolved TOML. Operator selections belong in the TOML
overlay before the build starts. `mios-build-local.ps1` is a compatibility
redirector, not a separate builder or resource policy.

### Mode 3 -- Linux local build (Justfile)

```bash
just build           # OCI image (runs bootc container lint as final step)
just rechunk         # Optimized Day-2 deltas
just lint            # Re-run bootc container lint
just raw             # RAW disk image
just iso             # Anaconda installer ISO
just qcow2 / vhdx / wsl2   # Other formats (need MIOS_USER_PASSWORD_HASH)
just sbom            # CycloneDX SBOM
just all-bootstrap   # build + rechunk + log to bootstrap repo
```

`just --list` shows every target; `Justfile` is the source of truth for the
Linux side, `mios-build-local.ps1` is the Windows equivalent.

### Mode 4 -- Self-build (running 'MiOS' builds next 'MiOS')

The development substrate rebuilds the image from its full source checkout.
Run the build in MiOS-DEV:

```bash
git clone https://github.com/mios-dev/mios.git
cd mios
just preflight
just build
just lint
```

`just rechunk` runs the configured containerized rechunk step. Review the build
log, image and selected artifact before using the [deployment lifecycle](deploy.md)
to switch a bootc host. Building an image and deploying it are separate actions.

### Mode 5 -- Ignition appliance

`config/ignition/` holds Butane configs for fully automated builds on a
fresh Fedora CoreOS or Fedora Server instance. Compile `.bu` →
`.ign` with Butane (<https://coreos.github.io/butane/>), provision the
target with the resulting `.ign`. On first boot it installs `git podman
just`, clones 'MiOS', and produces a live installer ISO at
`/usr/src/mios/output/mios-installer.iso`.

## Bootstrapping the first image

The build chain is self-replicating once a 'MiOS' image exists, but the very
first generation is built from the upstream base — no prior 'MiOS' image needed:

1. Install Podman on any Linux (Fedora, Debian/Ubuntu) or use Podman
   Desktop on Windows.
2. Clone the repo and run `podman build` (or `mios-build-local.ps1` on
   Windows).
3. The Containerfile pulls
   `ghcr.io/ublue-os/ucore-hci:stable-nvidia` as the base (the `mios.toml`
   `[image].base` default; `[image].base_no_nvidia` =
   `ghcr.io/ublue-os/ucore-hci:stable` for non-NVIDIA hosts) -- no prior
   'MiOS' image needed.
4. Deploy the result to the target (bare metal via ISO, Hyper-V via
   VHDX, etc.).
5. Subsequent builds can run from inside the deployed 'MiOS' (Mode 4).

## Dependency retention and verification

`[packages.self-build].retain_toolchain = true` is the default. The cleanup
phase preserves the selected dependency closure rather than removing tools
whose package group happens to end in `-build`. Setting retention to false is
an explicit choice to create an image that needs a separate development builder.
Core and development profiles must install the selected self-build dependencies
even when the virtualization phase is absent.

Rust target standard libraries and a matching linker remain prerequisites for
cross compilation; installing Cargo alone does not provision every target.
Use the checked-in toolchain and build configuration inside MiOS-DEV. The shared
agent requirements are installed into `/usr/lib/mios/agents/.venv`; system Python
consumers obtain their dependencies from the declared RPM groups.

Run these read-only checks from a full checkout inside MiOS-DEV:

```bash
command -v podman buildah skopeo bootc git just cargo rustc make cmake
podman info
df -h /var/lib/containers
just preflight
```

Then run the selected image build and its runtime checks. A declared package
list or successful resolver test does not establish that a full deployed image
has built and can rebuild itself. Retain the build log and report missing RPMs,
target libraries, repository access or service prerequisites as failures.

## Build requirements

| Resource | Minimum | Recommended |
|---|---|---|
| CPU cores | 4 | 8+ |
| RAM | 8 GB | 16+ GB |
| Disk (builder) | 100 GB | 250 GB |
| Network | Required (RPM + base image pulls) | Fast for ~2-4 GB of RPM downloads |

dnf5 cache mounts (`Containerfile` `--mount=type=cache,...`) make
subsequent rebuilds 5-10× faster.

## Future work: image-builder-cli

`bootc-image-builder` (BIB) is the current disk-image generator.
`image-builder-cli` (<https://github.com/osbuild/image-builder-cli>) is
under evaluation as a successor -- adds first-class SBOM generation and
cross-architecture support. `image-versions.yml` has commented-out
entries for `image_builder_cli_digest` ready for Renovate tracking.

## References

- bootc: <https://github.com/containers/bootc>
- bootc-image-builder: <https://github.com/osbuild/bootc-image-builder>
- rechunk: <https://github.com/hhd-dev/rechunk>
- cosign: <https://github.com/sigstore/cosign>
- Bootstrap repo: <https://github.com/mios-dev/mios-bootstrap>
