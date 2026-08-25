<!-- AI-hint: Chapter 66: V5 Database Authority Inversion, CephFS Storage Tiering & Disaster Recovery. -->
# <a name="66_v5_authority_inversion_and_cephfs_tiering"></a>Chapter 66: V5 Database Authority Inversion, CephFS Storage Tiering & Disaster Recovery

> Part III: Storage & Database Fabric of the [MiOS manual](../manual.md).
> Path Reference: `/usr/share/doc/mios/manual.md#66_v5_authority_inversion_and_cephfs_tiering`

#### Overview

The MiOS persistence plane reconciles declarative configuration with live runtime state through **V5 SSOT Authority Inversion**, **CephFS Multi-Tenant Storage**, and **Automated Disaster Recovery** (`WS-DURA` / `WS-STRG`).

#### <a name="66_v5_authority_inversion"></a>66.1 V5 SSOT Authority Inversion

In early architectures, static `mios.toml` on disk was the sole authority. Under V5:
* **PostgreSQL `config_kv` is the Live Runtime Authority**: Runtime API mutations and Portal edits update the database immediately.
* **Transactional Materialization**: `usr/libexec/mios/materialize-config-toml.py` writes database updates back to `mios.toml` with atomic rename.
* **Boot-Time Reconciliation**: On system boot, if `mios.toml` carries a newer timestamp than the database (e.g. from offline editing), the seeder transactionally imports diffs with full audit logging before re-materializing.

#### <a name="66_cephfs_storage_tiering"></a>66.2 Tiered Storage & CephFS Quotas

* **Local NVMe Fast Tier**: High-IOPS transient data (`/var/tmp/mios`, `/var/lib/mios/scratch`, `/var/lib/mios/llamacpp/slots/`).
* **Distributed CephFS Persistent Tier**: Persistent state (`pgvector` data directories, model weight pools, user home directories).
* **Tenant Directory Quotas**: Extended attributes (`ceph.quota.max_bytes`) enforce subvolume storage boundaries per tenant automatically.

#### <a name="66_disaster_recovery"></a>66.3 Automated Disaster Recovery & Safe Migrations

* **Automated `zstd` Snapshotting**: `mios-backup-pgvector.timer` generates compressed database snapshots before upgrades and daily at midnight.
* **Transactional Migrations**: All schema updates run inside explicit transaction blocks (`BEGIN ... COMMIT`) with automatic rollback on error.
