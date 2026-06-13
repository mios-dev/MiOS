<!-- AI-hint: Documents the ucore-hci upstream base image lineage and specifications — the FCOS/uCore/HCI/NVIDIA foundation MiOS builds FROM. Explains what the base image provides (immutable ostree+composefs, podman, KVM/QEMU/VFIO, MOK-signed NVIDIA akmods), which tags MiOS tracks, and how this base enables the whole-system MiOS stack (bootc lifecycle, GPU-fed inference lanes, agent plane). Use to understand the bottom of the image lineage and why this base was chosen. -->
# ucore-hci — MiOS Base Image

> **Purpose.** This is the image MiOS builds `FROM`. Everything MiOS *is* — an
> immutable, `bootc`/OCI-shaped Fedora workstation that is *also* a local,
> self-replicating agentic AI OS — is layered on top of `ucore-hci`. This doc
> explains what that base provides, why it was chosen, and how its
> capabilities feed the rest of the MiOS system.
>
> `ARG BASE_IMAGE=ghcr.io/ublue-os/ucore-hci:stable-nvidia` in `Containerfile`;
> the same value is the `MIOS_BASE_IMAGE` default referenced by the build
> recipes in `Justfile`.
> Source: `usr/share/doc/mios/concepts/architecture.md` §Base-image, `Containerfile:4`.

## Why this base (its role in the whole system)

MiOS does not reinvent the immutable-OS plumbing — it inherits it. `ucore-hci`
hands MiOS three things the rest of the system depends on:

1. **The immutable substrate** — an ostree/composefs read-only `/usr`, podman,
   and SELinux enforcing. This is what makes the MiOS Architectural Laws
   enforceable (Law 1 USR-OVER-ETC, Law 2 NO-MKDIR-IN-VAR) and what lets the
   whole OS ship as one OCI image that `bootc upgrade`s like a `git pull` and
   `bootc rollback`s like a Ctrl-Z.
2. **The virtualization stack** — libvirt/KVM, QEMU, and VFIO-PCI tooling, so
   MiOS can pass a discrete GPU to a guest (Looking Glass B7) without rebuilding
   the kernel or fighting drivers.
3. **MOK-signed NVIDIA akmods** — pre-built, Secure-Boot-signed proprietary
   driver modules. This is what allows the MiOS inference lanes (the GPU-fed
   `mios-llm-*` services) and the passthrough VMs to each claim hardware on a
   locked-down host.

In short: `ucore-hci` provides the deterministic, GPU-capable, immutable base;
MiOS adds the workstation desktop, the local AI surface, and defense-in-depth on
top. The base is the bottom of the lineage below.

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
                                  the local OpenAI-compatible AI surface,
                                  defense-in-depth
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

These are the capabilities the MiOS layer builds upon: the immutable rootfs
underpins the bootc lifecycle, the HCI virtualization tooling underpins the
KVM/Looking-Glass passthrough path, and the NVIDIA toolkit underpins the
GPU-fed inference lanes wired up through CDI (see `upstream/cdi.md`).

## Tags MiOS tracks

- `:stable-nvidia` — primary base for MiOS (proprietary NVIDIA, open kernel modules where supported)
- `:stable-nvidia-lts` — alternative for older GPUs needing the 580 LTS proprietary stream (Maxwell/Pascal)
- `:stable` — non-NVIDIA path for AMD-only or Intel-only hosts (not the default; override `MIOS_BASE_IMAGE`)

The base image is itself a tunable: `MIOS_BASE_IMAGE` flows from `mios.toml`
through the build, so swapping the NVIDIA stream or dropping to the non-NVIDIA
`:stable` tag is a one-line override, never a code edit.

## Multi-arch posture

ucore is multi-arch (linux/amd64 + linux/arm64) since 2025-11-08. ZFS
landed in base 2025-06-12 (older `:*-zfs` variants are deprecated).
MiOS currently ships amd64 only — the `mios_build` tool's `platforms`
parameter accepts `linux/arm64` for forward compat.

## Sibling images (related distros)

ucore-hci is one spin in the Universal Blue family; MiOS chose it because it is
the only sibling that combines hyperconverged virtualization tooling with the
signed NVIDIA driver stream the AI lanes need.

| Image | Spin | Use case |
| --- | --- | --- |
| Bluefin | GNOME developer workstation | dev containers, conventional desktop |
| Aurora | KDE | KDE-preferred workstation |
| Bazzite | Gaming/handheld | Steam Deck-class HTPC |
| ucore | Server/HCI | self-hosted infrastructure |
| **ucore-hci** | **HCI + NVIDIA** | **MiOS base** |

## Cross-refs

- `usr/share/doc/mios/upstream/fedora-bootc.md` — the bootc lifecycle this base feeds
- `usr/share/doc/mios/upstream/related-distros.md` — the Universal Blue family
- `usr/share/doc/mios/upstream/nvidia.md` — the MOK-signed driver path
- `usr/share/doc/mios/upstream/cdi.md` — how the base GPU is exposed to the AI lanes/VMs
- `usr/share/doc/mios/concepts/architecture.md` §Base-image — the MiOS layer on top
