# Self-build guide

MiOS is self-replicating: the published image contains every tool
(`podman`, `buildah`, `bootc`, `bootc-image-builder`) needed to produce
its own next generation. Source: `Containerfile`, `Justfile`,
`usr/share/mios/PACKAGES.md` `packages-self-build`.

## Build chain

```
MiOS vN (running) → podman build → MiOS vN+1 (OCI image)
                                         ↓
                              rechunk → cosign keyless sign → push to GHCR
                                         ↓
                              bootc upgrade → reboot → MiOS vN+1 (running)
```

## Modes

### Mode 0 — Bootstrap (initial install, fresh Linux)

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/mios-dev/mios-bootstrap/main/install.sh)"
```

Runs the bootstrap installer from `mios-bootstrap.git`. On a non-bootc
host it clones this repo and runs `install.sh` to lay down the FHS
overlay; on a bootc-managed Fedora host it runs
`bootc switch ghcr.io/mios-dev/mios:latest`.

### Mode 1 — CI/CD (recommended for production)

`.github/workflows/mios-ci.yml` builds, rechunks (on tag push), signs
(keyless cosign), and pushes the image on every tag and on `main`.
End users receive updates via:

```bash
sudo bootc upgrade && sudo systemctl reboot
```

### Mode 2 — Windows local build

```powershell
.\mios-build-local.ps1
```

Five-phase orchestrator (`mios-build-local.ps1`):

1. Prompt for username, password, LUKS passphrase, registry credentials.
2. Create the `mios-builder` Podman machine (rootful, all cores, all
   RAM, 250 GB disk).
3. Inject credentials, run `podman build`, rechunk, restore
   placeholders.
4. Generate disk images via BIB (RAW, VHDX, WSL2 tarball, Anaconda ISO).
5. Push to GHCR, mark package public; restore default Podman machine;
   print report.

### Mode 3 — Linux local build (Justfile)

```bash
just build           # OCI image
just rechunk         # Optimized Day-2 deltas
just lint            # Re-run bootc container lint
just raw             # RAW disk image
just iso             # Anaconda installer ISO
just qcow2 / vhdx / wsl2   # Other formats (need MIOS_USER_PASSWORD_HASH)
just sbom            # CycloneDX SBOM
just all-bootstrap   # build + rechunk + log to bootstrap repo
```

### Mode 4 — Self-build (running MiOS builds next MiOS)

```bash
git clone https://github.com/mios-dev/mios.git
cd mios
sudo podman build --no-cache \
    --build-arg MIOS_USER=mios \
    --build-arg MIOS_HOSTNAME=mios \
    -t localhost/mios:dev .
sudo podman run --rm --entrypoint /usr/bin/bootc localhost/mios:dev container lint
sudo bootc-base-imagectl rechunk --max-layers 67 \
    localhost/mios:dev localhost/mios:rechunked
sudo bootc switch --transport containers-storage localhost/mios:rechunked
sudo systemctl reboot
```

### Mode 5 — Ignition appliance

`config/ignition/` holds Butane configs for fully automated builds on a
fresh Fedora CoreOS or Fedora Server instance. Compile `.bu` →
`.ign` with Butane (<https://coreos.github.io/butane/>), provision the
target with the resulting `.ign`. On first boot it installs `git podman
just`, clones MiOS, and produces a live installer ISO at
`/usr/src/mios/output/mios-installer.iso`.

## Bootstrapping the first image

If no MiOS image exists yet:

1. Install Podman on any Linux (Fedora, Debian/Ubuntu) or use Podman
   Desktop on Windows.
2. Clone the repo and run `podman build` (or `mios-build-local.ps1` on
   Windows).
3. The Containerfile pulls
   `ghcr.io/ublue-os/ucore-hci:stable-nvidia` as the base — no prior
   MiOS image needed.
4. Deploy the result to the target (bare metal via ISO, Hyper-V via
   VHDX, etc.).
5. Subsequent builds can run from inside the deployed MiOS (Mode 4).

## Verifying self-build capability

```bash
which podman buildah bootc bootc-image-builder
sudo podman info | grep -E "rootless|graphRoot"
df -h /var/lib/containers
sudo podman build --no-cache -t test-build . && echo "Self-build: OK"
sudo podman rmi test-build
```

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
under evaluation as a successor — adds first-class SBOM generation and
cross-architecture support. `image-versions.yml` has commented-out
entries for `image_builder_cli_digest` ready for Renovate tracking.

## References

- bootc: <https://github.com/containers/bootc>
- bootc-image-builder: <https://github.com/osbuild/bootc-image-builder>
- rechunk: <https://github.com/hhd-dev/rechunk>
- cosign: <https://github.com/sigstore/cosign>
- Bootstrap repo: <https://github.com/mios-dev/mios-bootstrap>
