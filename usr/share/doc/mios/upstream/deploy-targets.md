<!-- AI-hint: Documentation of MiOS deployment-target methods (bootc host, Hyper-V Gen2, QEMU/KVM, WSL2, Anaconda ISO, RAW disk), detailing the Justfile build recipes and per-artifact config requirements that turn the single OCI image into a bootable system; use to guide automated deployment workflows.
     AI-related: mios-dev, usr/lib/bootc/kargs.d/10-mios-console.toml, config/artifacts -->
# Deployment Targets — bootc / Hyper-V / WSL2 / QEMU / ISO / RAW

> **Purpose.** MiOS is one thing built two ways at once: an immutable
> bootc/OCI-shaped Fedora workstation *and* a local, self-replicating agentic
> AI operating system. Both halves ship inside a single OCI image
> (`ghcr.io/mios-dev/mios:latest`). This doc is about the *last mile* — how that
> one image becomes a running machine on whatever substrate you have: a
> bootc-managed bare-metal host, a Hyper-V Gen 2 VM, QEMU/KVM, a WSL2 distro, an
> installer ISO, or a RAW disk. Pick the target that fits; the system you get is
> the same image either way.
>
> Where this sits in the lifecycle: **build pipeline → OCI image → disk
> artifact → boot → bootc Day-2 lifecycle.** The build pipeline (`just build`)
> produces the image; `bootc-image-builder` (BIB) cuts disk artifacts from it
> (see `upstream/bib.md`); the targets below boot one of those; and from then on
> `bootc upgrade` / `bootc rollback` carry the host forward like `git pull` /
> Ctrl-Z. The same artifact that brings up GNOME/Wayland also brings up the
> local inference lanes (`mios-llm-light` on `:11450` and the gated heavy GPU
> lanes), the agent-pipe/Hermes orchestration, and the PostgreSQL+pgvector
> memory — there is no separate "AI install" step.
>
> Source: `usr/share/doc/mios/guides/deploy.md`, `Justfile` (recipes `raw`,
> `iso`, `qcow2`, `vhdx`, `wsl2`), `config/artifacts/*.toml`.

## Bootc-managed Fedora host (preferred)

The native target. No disk artifact needed — a Fedora-bootc-compatible host
pulls the OCI image directly and switches its own root onto it.

```bash
sudo bootc switch ghcr.io/mios-dev/mios:latest && sudo systemctl reboot

# Day-2
sudo bootc upgrade && sudo systemctl reboot
sudo bootc switch <ref>     # change tag
sudo bootc rollback         # undo last upgrade
```

This is the form every other target converges to: once any of the artifacts
below boots, the deployed system is bootc-managed and upgrades/rolls back the
same way.

## Hyper-V Gen 2 (Windows)

1. Build the VHDX: `just vhdx` (requires `MIOS_USER_PASSWORD_HASH` **and**
   `MIOS_SSH_PUBKEY` — see [Password hash & SSH key](#password-hash--ssh-key)).
   BIB emits a VPC `.vhd`; the recipe converts it to `.vhdx` via `qemu-img`.
2. In Hyper-V Manager: New VM, Generation 2, attach `output/*.vhdx`.
3. **Enable Secure Boot** with the **Microsoft UEFI CA** template (not the
   "Microsoft Windows" template — the latter rejects the Linux shim).
4. The first-boot console fix is already baked: `plymouth.enable=0` ships in
   `usr/lib/bootc/kargs.d/10-mios-console.toml`, because Plymouth otherwise
   steals the framebuffer and makes Hyper-V/QEMU/serial boot invisible. (Console
   verbosity kargs are in `00-mios.toml` + `10-mios-verbose.toml`.)

## QEMU/KVM

```bash
just qcow2   # requires MIOS_USER_PASSWORD_HASH and MIOS_SSH_PUBKEY
qemu-system-x86_64 -enable-kvm -m 16G -smp 8 \
  -drive file=output/*.qcow2,if=virtio \
  -bios /usr/share/edk2/ovmf/OVMF_CODE.fd \
  -nic user,model=virtio
```

For libvirt: `virt-install --import --osinfo fedora-bootc --disk path=output/*.qcow2 ...`

This is the quickest local round-trip for validating an image — the same qcow2
is what MiOS itself uses for its VFIO/Looking-Glass virtualization story, so a
QEMU boot exercises the immutable host end-to-end before you commit it to metal.

## WSL2

```powershell
just wsl2   # on a Linux build host -> output/wsl2/mios-rootfs.tar.gz
wsl --import MiOS C:\WSL\MiOS .\output\wsl2\mios-rootfs.tar.gz
wsl -d MiOS
```

BIB has no native `wsl2` type, so the `wsl2` recipe exports the OCI image's
rootfs directly (`podman create` + `podman export | gzip`) into
`output/wsl2/mios-rootfs.tar.gz` for `wsl --import`.

WSL2 caveats:

- The Windows-hosted kernel ignores the image's `kargs.d` (Hyper-V owns the
  kernel), so kernel-side tweaks like the Plymouth/console fix above are moot
  here.
- Set `systemd=true` in the imported instance's `/etc/wsl.conf` (MiOS ships
  this already) so the agent stack's systemd units start.
- bootc commands work inside the distro, but `bootc switch` requires writing the
  new rootfs back into the WSL distribution — so the bootstrap installer
  re-imports a fresh rootfs rather than doing a `bootc switch`-in-place.

The WSL2 path is the primary target the Windows bootstrap (`Get-MiOS.ps1`) drops
the build into, alongside a VHDX, ISO, and qcow2 — pick whichever fits the host.

## Anaconda installer ISO

```bash
just iso
```

Boot the resulting `output/*.iso` (USB or physical media), run the Anaconda
installer, reboot. On first boot the deployed system runs `bootc upgrade` to
align with the remote `:latest` tag, so the installed host immediately tracks
the published image.

> The `iso` recipe mounts **only** `config/artifacts/iso.toml`; mounting a
> second BIB config crashes BIB with `found config.json and also config.toml`.
> Details in `upstream/bib.md`.

## RAW

`just raw` produces an 80 GiB ext4 RAW disk image (from
`config/artifacts/bib.toml`). Useful for:

- `dd if=output/*.raw of=/dev/sdX` to a physical USB or disk
- Flashing to an SBC or appliance
- Cloud import (most clouds accept RAW + a custom kernel)

## Password hash & SSH key

The `qcow2` and `vhdx` recipes need a login credential baked in, since (unlike
the ISO path) there is no interactive installer to create the user. Both
`sed`-substitute env vars into a `mktemp`-staged copy of the artifact TOML at
build time, keeping secrets out of the committed configs:

- `MIOS_USER_PASSWORD_HASH` (from `openssl passwd -6 'pass'`) replaces the
  placeholder `$6$REPLACEME_WITH_SHA512_HASH$REPLACEME`.
- `MIOS_SSH_PUBKEY` (an ed25519 public key, for sudo-less remote management)
  replaces `AAAA_REPLACE_WITH_REAL_PUBKEY`.

The `raw`, `iso`, and `wsl2` recipes do not require these.

## Cross-refs

- `usr/share/doc/mios/upstream/bib.md` — bootc-image-builder: output types, the
  ISO config gotcha, and the VHDX `.vhd`→`.vhdx` conversion idiom.
- `usr/share/doc/mios/guides/deploy.md` — bootc + Day-2 lifecycle in depth.
- `usr/share/doc/mios/guides/security.md` — hardening kargs and posture (FIPS,
  VFIO, lockdown), companion to the console kargs referenced above.
- `Justfile` — the source of truth for the build/artifact recipes.
