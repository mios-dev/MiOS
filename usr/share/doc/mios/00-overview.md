# 'MiOS' Overview

> Source: `README.md`, `INDEX.md` §1, `ARCHITECTURE.md` §Pillars, `llms.txt`,
> at `github.com/mios-dev/'MiOS'` (v0.2.2).

'MiOS' is a user-defined, customisable Linux distribution: an immutable,
bootc-managed Fedora workstation OS distributed as an OCI image at
`ghcr.io/mios-dev/mios:latest`. Its mission is FOSS-aligned: a local
OpenAI-compatible AI surface, transactional system upgrades, hardware
acceleration, and a defense-in-depth security posture.

## Three pillars

1. **Transactional integrity.** The system core is a content-addressed OCI
   image managed by `bootc`. Atomic upgrade and rollback via
   `bootc upgrade` / `bootc rollback`. composefs (`/usr` immutable) plus
   ostree (`/sysroot` deployments) provide content-addressed
   deduplication and verified boot.
2. **Hardware acceleration.** Universal CDI (Container Device Interface,
   `github.com/cncf-tags/container-device-interface`) for NVIDIA, AMD
   ROCm/KFD, and Intel iGPU. CDI specs generated under `/var/run/cdi/`,
   admin overrides under `/etc/cdi/`, declared in
   `usr/lib/tmpfiles.d/mios-gpu.conf`. KVMFR and Looking Glass B7 baked
   in-image via `automation/52-bake-kvmfr.sh` and
   `automation/53-bake-lookingglass-client.sh`.
3. **Zero-trust execution.** `fapolicyd` deny-by-default, SELinux
   enforcing, USBGuard ready, CrowdSec sovereign-mode IPS, kernel-lockdown
   integrity. See `80-security.md`.

## Base image — uCore HCI

'MiOS' builds `FROM ghcr.io/ublue-os/ucore-hci:stable-nvidia`
(`MIOS_BASE_IMAGE`). uCore HCI is a Universal Blue derivative of Fedora
CoreOS targeting hyperconverged infrastructure:

| Layer | What it provides |
| --- | --- |
| Fedora CoreOS foundation | Immutable ostree rootfs, composefs `/usr`, SELinux enforcing, podman, ZFS kernel modules |
| uCore additions | cockpit, firewalld, tailscale, mergerfs, samba, NFS |
| HCI additions | libvirt/KVM, QEMU, VFIO-PCI tooling, virtiofs |
| NVIDIA variant (`stable-nvidia`) | Proprietary driver akmods pre-built and MOK-signed; NVIDIA Container Toolkit |
| Stable stream kernel | LTS Linux 6.12 — server-grade stability, consistent ABI across updates |

'MiOS' adds GNOME 50, Looking Glass B7, KVM passthrough, k3s, Ceph, the
local AI surface, and defense-in-depth hardening on top.

Upstream: `github.com/ublue-os/ucore`.

## Repo == system root

`usr/`, `etc/`, `home/`, `srv/`, `v1/` in the repo mirror the deployed
image 1:1. There is **no separate `system_files/` directory** — overlay
edits target real on-disk paths directly. The `Containerfile`'s `ctx`
scratch stage copies these directories into `/ctx`, then the main build
bind-mounts `/ctx` read-only and copies a writable working set to
`/tmp/build` for phase scripts to mutate.

## Two-repo split

- `github.com/mios-dev/'MiOS'` — **system layer** (this repo). Owns the
  Containerfile, automation phase scripts, FHS overlay, system docs, CI.
- `github.com/mios-dev/mios-bootstrap` — **user-facing installer**. Owns
  Phase-0 preflight + identity capture, Phase-1 Total Root Merge, Phase-4
  reboot. End users do not clone the system layer directly.

## Day-2 lifecycle

```
sudo bootc upgrade && sudo systemctl reboot   # pull and stage next image
sudo bootc switch <ref>                       # move to a different tag
sudo bootc rollback                           # undo most recent upgrade
```

Cosign keyless verification before deploy:

```
cosign verify \
  --certificate-identity-regexp="https://github.com/mios-dev/mios" \
  --certificate-oidc-issuer="https://token.actions.githubusercontent.com" \
  ghcr.io/mios-dev/mios:latest
```
