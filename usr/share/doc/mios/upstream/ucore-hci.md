# ucore-hci — MiOS Base Image

> The image MiOS builds `FROM`. `ARG BASE_IMAGE=ghcr.io/ublue-os/ucore-hci:stable-nvidia`
> in `Containerfile`; default `MIOS_BASE_IMAGE` in `Justfile:45`.
> Source: `ARCHITECTURE.md` §Base-image, `Containerfile:1`.

## Lineage

```
Fedora CoreOS (FCOS)
   ↓
ucore                          ← ublue-os/ucore: FCOS + batteries
   ↓
ucore-hci                      ← + libvirt/KVM/QEMU/VFIO-PCI/virtiofs
   ↓
ucore-hci:stable-nvidia        ← + NVIDIA proprietary akmods (MOK-signed)
   ↓
MiOS                           ← + GNOME 50, Looking Glass B7, k3s, Ceph,
                                  LocalAI surface, defense-in-depth
```

- ublue-os org: <https://github.com/ublue-os>
- ucore project: <https://github.com/ublue-os/ucore>
- ccos (CentOS sibling): <https://github.com/ublue-os/ccos>

## What ucore-hci provides

| Layer | Components |
| --- | --- |
| Fedora CoreOS foundation | Immutable ostree rootfs, composefs `/usr`, SELinux enforcing, podman, ZFS kernel modules |
| ucore additions | cockpit, firewalld, tailscale, mergerfs, samba, NFS |
| HCI additions | libvirt/KVM, QEMU, VFIO-PCI tooling, virtiofs |
| NVIDIA variant (`:stable-nvidia`) | Proprietary driver akmods pre-built and **MOK-signed**; NVIDIA Container Toolkit |
| Stable-stream kernel | LTS Linux 6.12 — server-grade stability, consistent ABI across updates |

## Tags MiOS tracks

- `:stable-nvidia` — primary base for MiOS (proprietary NVIDIA, open kernel modules where supported)
- `:stable-nvidia-lts` — alternative for older GPUs needing the 580 LTS proprietary stream (Maxwell/Pascal)
- `:stable` — non-NVIDIA path for AMD-only or Intel-only hosts (not the default; override `MIOS_BASE_IMAGE`)

## Multi-arch posture

ucore is multi-arch (linux/amd64 + linux/arm64) since 2025-11-08. ZFS
landed in base 2025-06-12 (older `:*-zfs` variants are deprecated).
MiOS currently ships amd64 only — the `mios_build` tool's `platforms`
parameter accepts `linux/arm64` for forward compat.

## Sibling images (related distros)

| Image | Spin | Use case |
| --- | --- | --- |
| Bluefin | GNOME developer workstation | dev containers, conventional desktop |
| Aurora | KDE | KDE-preferred workstation |
| Bazzite | Gaming/handheld | Steam Deck-class HTPC |
| ucore | Server/HCI | self-hosted infrastructure |
| **ucore-hci** | **HCI + NVIDIA** | **MiOS base** |

## Cross-refs

- `usr/share/doc/mios/upstream/fedora-bootc.md`
- `usr/share/doc/mios/upstream/related-distros.md`
- `usr/share/doc/mios/upstream/nvidia.md`
- `ARCHITECTURE.md` §Base-image-uCore-HCI
