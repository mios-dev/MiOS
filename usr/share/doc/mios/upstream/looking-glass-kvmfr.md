# Looking Glass B7 + KVMFR

> MiOS bakes the KVMFR shared-memory kernel module and the Looking
> Glass B7 client into the image at build time. Source:
> `ARCHITECTURE.md` §Hardware-delegation,
> `automation/52-bake-kvmfr.sh`, `automation/53-bake-lookingglass-client.sh`.

## What it solves

VFIO GPU passthrough sends a real GPU to a guest VM. The host then
needs to *display* the guest's framebuffer back to the user (mouse,
keyboard, video) without going through the network stack. Looking
Glass + KVMFR is the canonical low-latency answer:

- KVMFR (Kernel Module for Video Frame Relay) is a kernel module
  exposing a shared-memory device that both host and guest can write
  framebuffer data into
- Looking Glass is a host-side viewer that reads from that shared
  memory at near-zero latency

## Project

- Looking Glass: <https://looking-glass.io/>
- Repo: <https://github.com/gnif/LookingGlass>

## How MiOS builds it

`automation/52-bake-kvmfr.sh` builds the KVMFR DKMS module against the
running kernel (in-image) and signs it with the MOK chain so it loads
under `lockdown=integrity`. `automation/53-bake-lookingglass-client.sh`
compiles the B7 client and stages it under `/usr/bin/looking-glass-client`.

## SELinux integration

The custom `mios_kvmfr` SELinux module (in
`usr/share/selinux/packages/mios/`) labels the KVMFR device file
appropriately so a confined guest can write to it without going to
permissive mode.

## Cross-refs

- `usr/share/doc/mios/40-kargs.md` (VFIO + iommu kargs)
- `usr/share/doc/mios/upstream/nvidia.md`
- `usr/share/doc/mios/upstream/selinux.md`
