# Podman, buildah, skopeo, Quadlets

> Used in MiOS for: image build (`podman build` from `Justfile:build`),
> sidecar orchestration (Quadlet units in `etc/containers/systemd/` and
> `usr/share/containers/systemd/`), Windows builder (`mios-build-local.ps1`
> creates a rootful `mios-builder` Podman machine).

## Projects

- Podman: <https://github.com/containers/podman> · docs <https://docs.podman.io/>
- buildah: <https://github.com/containers/buildah>
- skopeo: <https://github.com/containers/skopeo>
- Quadlet (systemd integration): <https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html>

## Build invariants for bootc images

| Rule | Why | Where |
| --- | --- | --- |
| **No `--squash-all`** | Strips OCI metadata bootc needs (`ostree.final-diffid`); breaks layer reuse for `bootc upgrade` deltas | `usr/share/doc/mios/guides/engineering.md` §Containerfile-conventions |
| `--no-cache` for production builds | Predictable, reproducible | `Justfile:build` and `mios-build-local.ps1` |
| Bind-mount build context | Keep `/ctx` read-only, mutate at `/tmp/build` | `Containerfile` `ctx` scratch stage |
| BuildKit cache mounts for dnf | 5–10× faster rebuilds without layer bloat | `Containerfile` `--mount=type=cache,...` |
| Multi-arch via `podman manifest` | `manifest create` + `manifest add` + `manifest push --all` | future `mios_build` `platforms` parameter |

## Quadlets — the systemd-podman bridge

A Quadlet is a systemd unit that podman generates from a `.container`,
`.volume`, `.network`, or `.kube` file. MiOS uses Quadlets for every
image-delivered service.

- Vendor-shipped Quadlets: `usr/share/containers/systemd/`
- Host-overridable Quadlets: `etc/containers/systemd/`

### LAW 6 — UNPRIVILEGED-QUADLETS

Every Quadlet declares `User=`, `Group=`, `Delegate=yes`. Documented
exceptions: `mios-ceph` and `mios-k3s` are `User=root` because Ceph and
K3s require uid 0.

### LAW 3 — BOUND-IMAGES

Every Quadlet image is symlinked into `/usr/lib/bootc/bound-images.d/`
so `bootc upgrade` knows to pull/cache it alongside the OS image.
Binder loop: `automation/08-system-files-overlay.sh:74-86`.

### Service gating (defaults policy, usr/share/mios/ai/INDEX.md §5)

Every boolean ships `true`. Disablement happens via systemd
`Condition*` directives in the Quadlet/unit, not via static config:

```ini
# etc/containers/systemd/mios-ceph.container excerpt
[Unit]
ConditionPathExists=/etc/ceph/ceph.conf
ConditionVirtualization=!container

[Service]
User=root          # documented exception to LAW 6
Group=root
Delegate=yes
```

## Windows builder (`mios-build-local.ps1`)

The 5-phase Windows orchestrator creates a rootful Podman Desktop
machine named `mios-builder` with all CPU cores, all RAM, and 250 GB
disk. After `podman build` completes, the script restores the previous
default machine.

## Cross-refs

- `usr/share/doc/mios/10-build-pipeline.md`
- `usr/share/doc/mios/50-orchestrators.md`
- `usr/share/doc/mios/70-ai-surface.md` (LocalAI Quadlet at `etc/containers/systemd/mios-ai.container`)
