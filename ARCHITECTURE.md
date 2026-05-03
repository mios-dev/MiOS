# 'MiOS' Architecture

## Pillars

1. **Transactional integrity** — system core is a content-addressed OCI image
   managed by `bootc` (<https://bootc-dev.github.io/bootc/>). Atomic upgrade
   and rollback via `bootc upgrade` / `bootc rollback`.
2. **Hardware acceleration** — universal CDI (Container Device Interface,
   <https://github.com/cncf-tags/container-device-interface>) for NVIDIA,
   AMD ROCm/KFD, and Intel iGPU. CDI specs generated under `/var/run/cdi/`,
   admin overrides under `/etc/cdi/` (declared in
   `usr/lib/tmpfiles.d/mios-gpu.conf`).
3. **Zero-trust execution** — `fapolicyd` deny-by-default, SELinux enforcing,
   USBGuard, CrowdSec sovereign-mode IPS, kernel-lockdown integrity. See
   `SECURITY.md`.

## Base image — uCore HCI

'MiOS' builds `FROM ghcr.io/ublue-os/ucore-hci:stable-nvidia` (`MIOS_BASE_IMAGE`).
uCore HCI is a Universal Blue derivative of Fedora CoreOS targeting
hyperconverged infrastructure:

| Layer | What it provides |
|---|---|
| Fedora CoreOS foundation | Immutable ostree rootfs, composefs `/usr`, SELinux enforcing, podman, ZFS kernel modules |
| uCore additions | cockpit, firewalld, tailscale, mergerfs, samba, NFS |
| HCI additions | libvirt/KVM, QEMU, VFIO-PCI tooling, virtiofs |
| NVIDIA variant (`stable-nvidia`) | Proprietary driver akmods pre-built and MOK-signed; NVIDIA Container Toolkit |
| Stable stream kernel | LTS Linux 6.12 — server-grade stability, consistent ABI across updates |

'MiOS' adds: GNOME 50 desktop, Looking Glass B7, KVM passthrough, k3s, Ceph,
full AI surface, and defense-in-depth hardening on top.

Upstream: <https://github.com/ublue-os/ucore>

## Filesystem layout (FHS 3.0 + bootc)

Spec: <https://refspecs.linuxfoundation.org/FHS_3.0/>.

bootc disposition reflects FHS 3.0's intent: `/usr` is explicitly
"shareable, read-only" in the spec — the composefs/ostree model enforces this
at the kernel level. `/etc` is the host-specific config surface; bootc applies
a 3-way merge (image default + previous state + admin edits) on upgrade so
local changes survive. `/var` is never touched by an upgrade.

| Path | FHS character | bootc disposition | Source-of-truth in repo |
|---|---|---|---|
| `/usr` | Read-only, shareable | Immutable composefs mount; change = new OCI image | `usr/` overlaid by `automation/08-system-files-overlay.sh` |
| `/etc` | Host-specific config | 3-way merge overlay; admin edits survive upgrades | `etc/` |
| `/var` | Mutable, persistent | Fully writable; never replaced on upgrade | `usr/lib/tmpfiles.d/mios*.conf` (LAW 2) |
| `/srv` | Data served by the system | Persistent; AI model weights, Ceph data | `usr/lib/tmpfiles.d/mios.conf` |
| `/run` | Ephemeral runtime (FHS 3.0) | tmpfs; cleared at boot; never in image layers | — |
| `/home` | User home directories | Persistent via `/var/home/<user>` + symlink | `usr/lib/sysusers.d/` |

Build-time writes to `/var/` are forbidden (LAW 2). The overlay step at
`automation/08-system-files-overlay.sh:49-67` writes home dotfiles to
`/etc/skel/` and lets `systemd-sysusers` populate `/var/home/<user>/` at
first boot.

## Hardware delegation

Default GPU passthrough targets (`ARCHITECTURE.md` previously hard-coded
`10de:2204,10de:1aef`; current behavior detects at runtime via
`automation/34-gpu-detect.sh` and writes `/run/mios/gpu-passthrough.status`).

Virtualization: KVM/QEMU + libvirt (`automation/12-virt.sh`), VFIO-PCI
passthrough kargs (`usr/lib/bootc/kargs.d/`), KVMFR shared-memory built
in-image (`automation/52-bake-kvmfr.sh`), Looking Glass B7 client built
in-image (`automation/53-bake-lookingglass-client.sh`).

## AI surface

All agents and tooling target `MIOS_AI_ENDPOINT` (`http://localhost:8080/v1`).
The endpoint implements the OpenAI v1 REST protocol — core surfaces:
`GET /v1/models`, `POST /v1/chat/completions` (streaming SSE supported),
`POST /v1/embeddings`. Auth: `Authorization: Bearer $MIOS_AI_KEY` (empty key
accepted by the local stack). Tool calling (`tools` array,
`finish_reason: tool_calls`) is supported for capable models.

| Service | Protocol | Path |
|---|---|---|
| Inference | OpenAI v1 REST | `MIOS_AI_ENDPOINT` (`http://localhost:8080/v1`) — Quadlet `etc/containers/systemd/mios-ai.container` |
| Discovery | MCP | `usr/share/mios/ai/v1/mcp.json` |
| Metadata | JSON | `usr/share/mios/ai/v1/models.json` |
| System prompt | markdown | `usr/share/mios/ai/system.md` (canonical), `etc/mios/ai/system-prompt.md` (host override) |

References:
- bootc: <https://github.com/bootc-dev/bootc>
- bootc-image-builder: <https://github.com/osbuild/bootc-image-builder>
- Universal Blue uCore HCI: <https://github.com/ublue-os/ucore>
- rechunk: <https://github.com/hhd-dev/rechunk>
- cosign: <https://github.com/sigstore/cosign>
