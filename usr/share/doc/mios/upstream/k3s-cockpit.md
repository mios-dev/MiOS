# K3s + Cockpit on 'MiOS'

> K3s baked into the image as a single-node workstation cluster.
> Cockpit (inherited from ucore) provides browser-based admin.
> K3s Quadlet documented exception to LAW 6 (UNPRIVILEGED-QUADLETS):
> `User=root` because K3s requires uid 0.

## K3s

- Project: <https://k3s.io/>
- Repo: <https://github.com/k3s-io/k3s>
- 'MiOS' gating: `mios-k3s.container` Quadlet has
  `ConditionVirtualization=!wsl,!container` (skips on WSL2 and inside
  containers -- INDEX.md §5)
- SELinux integration: `automation/19-k3s-selinux.sh` (custom policy)

### Why baked, not Quadlet-only

K3s is a single binary that wants to manage cgroups, iptables, and
overlay filesystems directly. Running it inside a Quadlet sidecar
adds a redundant container layer. 'MiOS' instead ships the binary plus
a systemd unit that gates on
`ConditionPathIsDirectory=/etc/rancher/k3s` so admins explicitly opt
in by populating that directory.

## Cockpit

- Project: <https://cockpit-project.org/>
- Inherited from ucore base
- Port: 9090/tcp (firewalld allowed in default zone)
- Modules 'MiOS' uses:
  - `cockpit-podman` -- manage Quadlet sidecars from the browser
  - `cockpit-machines` -- libvirt/KVM VM dashboard
  - `cockpit-storaged` -- disk/LVM/Btrfs management (not ZFS -- Cockpit doesn't speak ZFS)
  - `cockpit-networkmanager` -- network interface admin
  - `cockpit-selinux` -- view denials, toggle booleans

### Verification

```bash
sudo systemctl status cockpit.socket
firewall-cmd --list-services | grep -q cockpit
# Then browse https://<host>:9090 (uses host PAM auth)
```

## Ceph (referenced; not in default workstation profile)

- Project: <https://ceph.io/>
- cephadm: <https://docs.ceph.com/en/latest/cephadm/>
- 'MiOS' gating: `mios-ceph.container` requires `/etc/ceph/ceph.conf`
  to exist and `!container`; otherwise the Quadlet's `Condition*` no-ops
- Documented exception to LAW 6: `User=root` (Ceph requires uid 0)
- Path: multi-node deployments use cephadm; single-node 'MiOS' workstations
  typically use BlueStore on a dedicated disk via a separate
  bootstrap step

## libvirt / QEMU

- libvirt: <https://libvirt.org/>
- QEMU: <https://www.qemu.org/>
- Inherited from ucore-hci (not added by 'MiOS'); used for KVM VMs and
  VFIO passthrough. Wired to Cockpit's `machines` module.

## Cross-refs

- `usr/share/doc/mios/70-ai-surface.md`
- `usr/share/doc/mios/upstream/podman.md` (Quadlets)
- `usr/share/doc/mios/upstream/looking-glass-kvmfr.md` (VFIO + display)
