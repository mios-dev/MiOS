<!--
AI-hint: Guides engineering reference documentation for the CephFS + XDG Unified Storage Fabric, documenting cache isolation rules, OCI bootstrap quickstarts, and multi-tenant extension paths.
AI-related: /usr/share/doc/mios/guides/cephfs-xdg-storage.md, mios-cephfs-provision, mios-xdg-cephfs.sh, [storage.cephfs]
-->
# CephFS & XDG Unified Storage Fabric Guide

This guide documents the architecture, configuration, and operation of the **CephFS + XDG Unified Storage Fabric** implemented in MiOS.

---

## 1. Architecture Diagram

The storage fabric dynamically segments hot/metadata directories from cold/bulk data directories, routing all user-session reads and writes to either local high-speed tmpfs or remote path-scoped CephFS subvolumes:

```
                  +----------------------------------------------+
                  |               User Session (GUI)             |
                  +----------------------------------------------+
                                  |              |
           XDG_CACHE_HOME         |              |        XDG_CONFIG_HOME
           (Local tmpfs)          |              |        (Network CephFS)
                  v               v              v
           +--------------+   +----------------------+   +--------------+
           | /run/user/ID |   |    /home/operator    |   | $HOME/.config|
           +--------------+   +----------------------+   +--------------+
                  |                      |                      |
             Local tmpfs                 |                Path-scoped Caps
            (No MDS load)                v                 (MDS Hot Pool)
                                  [systemd.automount]
                                         |
                                         v
                             +------------------------+
                             | CephFS Network Storage |
                             |   (cephadm Orchestrated)|
                             +------------------------+
```

---

## 2. Cache Isolation Rule

To prevent MDS (Metadata Server) metadata storms and file-lock deadlock conditions:
- **Rule**: `XDG_CACHE_HOME` must **NEVER** map to a CephFS directory.
- **Problem**: Desktop environment indexers (e.g., Tracker, GVfs, Flatpak portals) walk `$XDG_DATA_HOME` and write heavily to `$XDG_CACHE_HOME` on login. If cache folders are remote, this generates 2,000–8,000 MDS ops/s, triggering client capability recalls and freezing GUI desktops.
- **Remedy**: `XDG_CACHE_HOME` is dynamically isolated to `/run/user/<uid>/.cache` (a local tmpfs layer) at login via [mios-xdg-cephfs.sh](file:///usr/share/mios/profile.d/mios-xdg-cephfs.sh).

---

## 3. Single-Operator Quickstart

To initialize the storage fabric on a fresh workstation:

1. **Bootstrap the Ceph Cluster**:
   Run the OCI bootstrap script to stand up the single-host MON and OSD storage services:
   ```bash
   sudo /usr/libexec/mios/ceph-bootstrap.sh
   ```

2. **Enable CephFS Integration**:
   Edit `/etc/mios/mios.toml` to activate the storage fabric:
   ```toml
   [storage.cephfs]
   enable                          = true
   monitors                        = ["192.168.1.50:6789"] # Configure actual MON IPs
   ```

3. **Re-run firstboot orchestration**:
   Trigger the firstboot handler to apply configurations, reload units, and enable automount targets:
   ```bash
   sudo /usr/libexec/mios/mios-hermes-firstboot
   ```

---

## 4. Multi-Tenant Extension Path

To provision subvolumes for additional tenant profiles:
1. Call `mios-cephfs-provision` directly:
   ```bash
   sudo /usr/libexec/mios/mios-cephfs-provision validate <uid> <gid>
   ```
2. This creates:
   - Path-scoped CephX keyring `/etc/ceph/keyring.d/client.<uid>` restricting OSD/MDS access exclusively to `/tenants/mios/users/<uid>`.
   - Idempotently loads the systemd automount file linking access to `/home/<username>`.

---

## 5. Known Caveats

- **systemd-homed Conflict**: Do not enable `systemd-homed` alongside CephFS automounting. systemd-homed expects local LUKS container loopbacks, which conflict with network-layer mounts.
- **fscache + LUKS interaction**: When fscache is enabled (`fsc` mount option), cache files are written to `/var/cache/fscache`. Ensure `/var` is encrypted via LUKS on the host workstation to preserve data confidentiality.
