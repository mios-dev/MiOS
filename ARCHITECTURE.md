# MiOS Architecture

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

## Filesystem layout (FHS 3.0 + bootc)

Spec: <https://refspecs.linuxfoundation.org/FHS_3.0/>.

| Path | Type | Source-of-truth in repo |
|---|---|---|
| `/usr` | Immutable image content | `usr/` (overlaid by `automation/08-system-files-overlay.sh`) |
| `/etc` | Persistent admin-override surface; build-time writes are upstream-contract only | `etc/` |
| `/var` | Persistent state; declared via `tmpfiles.d` | `usr/lib/tmpfiles.d/mios*.conf` |
| `/srv` | Sidecar service data (models, databases) | `srv/`, `usr/lib/tmpfiles.d/mios.conf` |

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

| Service | Protocol | Path |
|---|---|---|
| Inference | OpenAI-compatible REST | `http://localhost:8080/v1` (LocalAI Quadlet `etc/containers/systemd/mios-ai.container`) |
| Discovery | MCP | `usr/share/mios/ai/v1/mcp.json` |
| Metadata | JSON | `usr/share/mios/ai/v1/models.json` |
| System prompt | markdown | `usr/share/mios/ai/system.md` (canonical), `etc/mios/ai/system-prompt.md` (host override) |

References:
- bootc: <https://github.com/containers/bootc>
- bootc-image-builder: <https://github.com/osbuild/bootc-image-builder>
- Universal Blue (uCore base): <https://github.com/ublue-os/main>
- rechunk: <https://github.com/hhd-dev/rechunk>
- cosign: <https://github.com/sigstore/cosign>
- LocalAI: <https://github.com/mudler/LocalAI>
