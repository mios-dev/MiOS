<!-- AI-hint: Documentation for the KVMFR kernel module and Looking Glass B7 client baked into the MiOS image — the shared-memory framebuffer relay that lets the host display a VFIO-passed-through guest GPU's output at near-zero latency, plus its build, runtime-enable, and SELinux integration. -->
# Looking Glass B7 + KVMFR

> **Where this fits in MiOS.** MiOS is one image built two ways at once: an
> immutable bootc/OCI Fedora workstation *and* a local, self-replicating agentic
> AI OS. Both halves lean on the same hardware-delegation plumbing — a single
> CDI/VFIO layer that can hand a real GPU to a guest VM (this doc's topic) or let
> the local inference lanes offload to that same GPU. This doc covers the *VM
> display* side of that plumbing: how a guest's framebuffer gets back onto the
> operator's screen without crossing the network. KVMFR + Looking Glass is baked
> into the image at build time (Architectural Law 3, BOUND/BAKED images), so the
> capability ships in the OS rather than being assembled at runtime.
>
> Source of truth: `usr/share/doc/mios/concepts/architecture.md`
> §Hardware-delegation, `automation/52-bake-kvmfr.sh`,
> `automation/53-bake-lookingglass-client.sh`, and the runtime units listed below.

## What it solves

VFIO GPU passthrough hands a real, discrete GPU to a guest VM (for example, a
Windows VM that games on the 4090 at near-native latency while the iGPU/host
keeps the desktop). Once the GPU is *inside* the guest, the host still needs to
*display* that guest's framebuffer back to the user — mouse, keyboard, video —
without routing pixels through the network stack (VNC/RDP/SPICE add latency and
re-encode the frame). Looking Glass + KVMFR is the canonical low-latency answer:

- **KVMFR** (Kernel Module for Video Frame Relay) is a kernel module exposing a
  shared-memory device (`/dev/kvmfr0`) that both host and guest can write
  framebuffer data into.
- **Looking Glass** is a host-side viewer that reads from that shared memory at
  near-zero latency and paints the guest's display in a local window.

The result is a passthrough'd GPU whose output appears in an ordinary host
window with minimal added latency — passthrough gaming/workstation use without a
second monitor or a KVM switch.

## Project

- Looking Glass: <https://looking-glass.io/>
- Repo: <https://github.com/gnif/LookingGlass>

Per MiOS dependency policy, every dependency tracks the latest release from its
source. Looking Glass ships letter-numbered release branches (B6, B7, …);
`53-bake-lookingglass-client.sh` resolves the highest `B*` branch at build time
rather than pinning a literal version, so "B7" here is the current branch, not a
hard-coded one.

## How MiOS builds it (build time)

Both pieces are produced during the Containerfile build (no runtime compile);
this is the "bake it into the image" half of Law 3.

- **`automation/52-bake-kvmfr.sh`** installs `akmod-kvmfr` (from the
  `hikariknight/looking-glass-kvmfr` COPR), builds the kvmfr kmod against the
  `ucore-hci` kernel shipped in the base image (`akmods --force --kernels $KVER`),
  and bakes the result into `/usr/lib/modules/$KVER/extra/kvmfr/kvmfr.ko`. When
  the ublue/akmods MOK private key is present it signs the module so it loads
  under `lockdown=integrity`; otherwise users enroll the MOK and the module uses
  the public cert shipped by `ublue-os-akmods-addons`. The script follows the
  project principle of never upgrading the base kernel in-container: if no exact
  `kernel-devel-$KVER` is available it **skips** the kvmfr bake (and logs the
  on-host enable steps) rather than failing the build — Looking Glass still runs
  in IVSHMEM-only mode without kvmfr.
- **`automation/53-bake-lookingglass-client.sh`** builds the B7 client
  (`cmake`/`make`, PipeWire + libdecor enabled) and installs
  `/usr/bin/looking-glass-client` plus a `looking-glass.desktop` entry. In
  practice `automation/12-virt.sh` already builds the client as part of the
  virtualization stack (and then strips the toolchain to shrink the image), so
  `53-*` short-circuits with success when the binary is already present; it only
  rebuilds if the binary is missing and the toolchain is still available.

## How MiOS runs it (runtime, opt-in)

The display path is **disabled by default** and opt-in per host — passthrough is
a hardware-specific operator decision, so MiOS ships the capability inert:

- **`mios-kvmfr-load.service`** (`ConditionVirtualization=!container`, ordered
  `After=systemd-modules-load.service` / `Before=libvirtd.service`) loads the
  module (`modprobe kvmfr`) and sets ownership on the device
  (`chgrp kvm /dev/kvmfr0`, `chmod 0660`). It is shipped with an empty
  `WantedBy=` (disabled); the documented enable path is
  `ujust mios-looking-glass-enable`.
- **`usr/lib/modprobe.d/kvmfr.conf`** sizes the shared-memory region
  (`options kvmfr static_size_mb=128` — 128 MB is enough for 4K SDR; raise it for
  ultrawide or HDR).
- **`usr/lib/udev/rules.d/99-kvmfr.rules`** grants the `kvm` group read/write to
  the kvmfr character device (`MODE="0660"`, `TAG+="uaccess"`), so a libvirt/QEMU
  guest running as a `kvm`-group member can map the buffer without elevation.

## SELinux integration

So a *confined* guest can write the shared-memory device without dropping SELinux
to permissive, MiOS ships a custom `mios_kvmfr` policy module. It is generated by
`automation/37-selinux.sh` (MiOS keeps SELinux policy as per-rule modules
assembled at build time, not as loose `.te` files under
`usr/share/selinux/packages/mios/`). The module allows the sVirt guest domain to
operate the kvmfr character device:

```
module mios_kvmfr 1.0;
require { type svirt_t; type device_t; class chr_file { open read write map getattr }; }
allow svirt_t device_t:chr_file { open read write map getattr };
```

This keeps the passthrough path inside enforcing mode, consistent with MiOS's
least-privilege posture.

## Cross-refs

- `usr/share/doc/mios/concepts/architecture.md` §Hardware-delegation — VFIO/CDI
  plumbing, runtime GPU-passthrough target detection (`34-gpu-detect.sh`), and
  where Looking Glass sits in the whole system.
- `usr/lib/bootc/kargs.d/` — the VFIO-PCI passthrough + IOMMU kernel arguments
  (the kargs the architecture/security docs describe; processed lexicographically).
- `usr/share/doc/mios/guides/security.md` — `lockdown=integrity`, MOK signing,
  and the SELinux/secure-boot context the signed kvmfr module relies on.
- `usr/share/doc/mios/upstream/nvidia.md` — NVIDIA/CDI GPU stack (the other
  consumer of the same hardware-delegation layer).
- `usr/share/doc/mios/upstream/selinux.md` — how MiOS assembles its SELinux
  policy modules.
