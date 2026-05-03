# Deployment Targets -- Hyper-V / WSL2 / QEMU / ISO / RAW

> 'MiOS' produces one OCI image and several disk-image artifacts via BIB.
> Source: `DEPLOY.md`, `Justfile` (recipes `raw`, `iso`, `qcow2`, `vhdx`,
> `wsl2`), `config/artifacts/*.toml`.

## Bootc-managed Fedora host (preferred)

```bash
sudo bootc switch ghcr.io/mios-dev/mios:latest && sudo systemctl reboot

# Day-2
sudo bootc upgrade && sudo systemctl reboot
sudo bootc switch <ref>     # change tag
sudo bootc rollback         # undo last upgrade
```

## Hyper-V Gen 2 (Windows)

1. Build the VHDX: `just vhdx` (requires `MIOS_USER_PASSWORD_HASH`)
2. In Hyper-V Manager: New VM, Generation 2, attach `output/*.vhdx`
3. **Enable Secure Boot** with the **Microsoft UEFI CA** template (not
   "Microsoft Windows" template -- the latter rejects Linux shim)
4. First-boot Plymouth fix is already baked via
   `usr/lib/bootc/kargs.d/05-mios-plymouth.toml`
   (`plymouth.enable=0 rd.plymouth=0`)

## QEMU/KVM

```bash
just qcow2
qemu-system-x86_64 -enable-kvm -m 16G -smp 8 \
  -drive file=output/*.qcow2,if=virtio \
  -bios /usr/share/edk2/ovmf/OVMF_CODE.fd \
  -nic user,model=virtio
```

For libvirt: `virt-install --import --osinfo fedora-bootc --disk path=output/*.qcow2 ...`

## WSL2

```powershell
just wsl2  # on a Linux build host
wsl --import 'MiOS' C:\WSL\'MiOS' .\output\disk.wsl2
wsl -d 'MiOS'
```

WSL2 caveats:

- The Windows-hosted kernel ignores the image's kargs.d
- Set `systemd=true` in the imported instance's `/etc/wsl.conf` ('MiOS'
  ships this already)
- bootc commands work, but `bootc switch` requires writing the new
  rootfs back into the WSL distribution -- the bootstrap installer
  re-imports rather than `bootc switch`-in-place

## Anaconda installer ISO

```bash
just iso
```

Boot the resulting `output/*.iso` (USB or physical media), run the
Anaconda installer, reboot. On first boot the deployed system runs
`bootc upgrade` to align with the remote `:latest` tag.

## RAW

`just raw` produces an 80 GiB ext4 RAW disk image. Useful for:

- `dd if=output/*.raw of=/dev/sdX` to a physical USB
- Flashing to an SBC or appliance
- Cloud import (most clouds accept RAW + custom kernel)

## Cross-refs

- `usr/share/doc/mios/upstream/bib.md`
- `usr/share/doc/mios/90-deploy.md`
- `usr/share/doc/mios/40-kargs.md` (Plymouth fix, FIPS, VFIO)
