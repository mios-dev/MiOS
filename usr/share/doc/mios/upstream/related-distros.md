# Related Distros -- Comparison Context

## Sibling Universal Blue images

| Image | Spin | Use case | URL |
| --- | --- | --- | --- |
| Bluefin | GNOME developer workstation | conventional dev desktop, devcontainer focus | <https://github.com/ublue-os/bluefin> |
| Aurora | KDE | KDE-preferred workstation | <https://github.com/ublue-os/aurora> |
| Bazzite | Gaming/handheld | Steam Deck-class, HTPC | <https://github.com/ublue-os/bazzite> |
| ucore | Server/HCI base | self-hosted infra | <https://github.com/ublue-os/ucore> |
| **'MiOS'** | **HCI workstation+server hybrid** | **immutable workstation w/ local AI** | <https://github.com/mios-dev/'MiOS'> |

'MiOS' sits closest to ucore/ucore-hci with a workstation-server hybrid
posture (GNOME desktop + KVM passthrough + k3s + Ceph + local AI).

## Other immutable / atomic distros

| Distro | Backend | OCI image? | Notes |
| --- | --- | --- | --- |
| Fedora Silverblue | rpm-ostree | no (rpm-ostree refs) | GNOME, predecessor of bootc |
| Fedora Kinoite | rpm-ostree | no | KDE Silverblue |
| Fedora bootc | bootc | yes | The lineage 'MiOS' is in |
| CentOS Stream bootc | bootc | yes | Where BIB is published from |
| RHEL image mode | bootc | yes | Red Hat enterprise sibling |
| CoreOS Layering | rpm-ostree | yes (via `coreos.inst.image_url`) | Pre-bootc |
| NixOS | Nix | no (declarative TOML/Nix) | Different model -- declarative not image-based |
| Talos | bespoke | yes (Kubernetes-only API-driven) | No SSH, no shell |
| Flatcar | Container Linux | yes | CoreOS Linux successor |
| Vanilla OS | apx + abroot | yes | Ubuntu-based, dual-root atomic |
| openSUSE MicroOS | btrfs snapshots | no | Btrfs-snapshot-based atomic |

## Why 'MiOS' vs each

| Alt | Why 'MiOS' instead |
| --- | --- |
| Bluefin | Bluefin is dev-desktop only -- no KVM passthrough, no Ceph, no local AI surface |
| Bazzite | Gaming-tuned; not suitable for HCI workloads |
| Silverblue | Pre-bootc (rpm-ostree); harder to run as a pure container image |
| RHEL image mode | Closed source, requires subscription |
| NixOS | Different mental model (declarative); steeper learning curve |
| Talos | Kubernetes-only; no desktop; no general-purpose workstation |
| Flatcar | Server-only; no desktop; smaller package set |

## Cross-refs

- `usr/share/doc/mios/upstream/ucore-hci.md`
- `usr/share/doc/mios/upstream/fedora-bootc.md`
- `usr/share/doc/mios/upstream/bootc.md`
