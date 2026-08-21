<!-- AI-hint: Chapter 24: CephFS Local Storage Cluster. Covers Ceph Quadlet definitions and storage config. Details block device access exemptions. Maps user directories onto CephFS mounts for auto-backups. -->

# Chapter 24: CephFS Local Storage Cluster

> Part VI: Storage, Network & Web Planes of the [MiOS manual](../manual.md).

This chapter covers the documentation for **CephFS Local Storage Cluster** under MiOS.

### <a name="24_containerized_ceph_deployments"></a>24.Containerized Ceph Deployments: Containerized Ceph Deployments

> Path Reference: `/usr/share/doc/mios/manual.md#24_containerized_ceph_deployments`

#### Overview

Ceph storage daemons are orchestrated inside unprivileged containers.

## Orchestration
- **Service**: Managed via `mios-ceph.service` Quadlet.
- **Containers**: Includes Ceph monitors and OSD engines.
- **Mounts**: Exposes storage block paths.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="24_storage_daemon_permissions"></a>24.Storage Daemon Permissions: Storage Daemon Permissions

> Path Reference: `/usr/share/doc/mios/manual.md#24_storage_daemon_permissions`

#### Overview

Ceph requires block access permissions, making it one of the few root exemptions.

## Details
- **Exceptions**: Documented inside systemd templates.
- **Permissions**: Runs with permissions required to interact with hardware blocks.
- **Hardening**: Limits network execution boundaries to loopback interfaces.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="24_xdg_directory_integrations"></a>24.XDG Directory Integrations: XDG Directory Integrations

> Path Reference: `/usr/share/doc/mios/manual.md#24_xdg_directory_integrations`

#### Overview

Desktop directories are synced to CephFS mounts for automatic backups.

## Setup
- **Integrations**: Mounts local directories (e.g. `~/Documents`) directly on CephFS.
- **Backups**: Saves changes across the local storage network.
- **Config**: Settings are stored inside XDG configuration files.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
