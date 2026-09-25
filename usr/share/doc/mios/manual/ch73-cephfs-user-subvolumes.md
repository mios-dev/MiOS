<!-- AI-hint: Chapter 73: Global Per-User Encrypted CephFS Subvolumes. Covers the mios-user-cephfs subvolume manager that provisions isolated, fscrypt-encrypted CephFS subvolumes for each user across bare-metal Blade clusters, enforcing tenant isolation, key escrow, and cross-blade disaster recovery. -->

# Chapter 73: Global Per-User Encrypted CephFS Subvolumes

## Overview

MiOS clusters provide distributed, persistent home directory storage across 2–6 bare-metal Blades using CephFS. To ensure strict multi-tenant isolation, data confidentiality at rest, and cross-blade disaster recovery, MiOS implements the Global Per-User Encrypted CephFS Subvolume Manager (`mios-user-cephfs`).

The subvolume manager operates under the five load-bearing architectural invariants:
1. **`/var` Persists by Default**: CephFS state descriptors, encryption keys, and subvolume mappings reside under persistent `/var/lib/mios/cephfs/`.
2. **Tenant Isolation**: Privileged accounts (`root`, system UIDs < 1000) are forbidden from owning tenant subvolumes to eliminate host privilege escalation vectors.
3. **Transparent Directory Encryption (`fscrypt`)**: User directories are encrypted with hardware-bound AES-256-XTS policies where keys are unlocked through native Linux keyrings.
4. **Hourly Delta Snapshots & Mesh Replication**: Changes are captured as atomic CephFS subvolume snapshots and replicated across the WireGuard HCI mesh cluster.

## Architecture & Subvolume Lifecycle

```
[User Login: UID >= 1000]
         │
         ▼
[mios-user-cephfs provision]
         │
         ├──► CephFS Subvolume (mode 0700, subvolume_group=users)
         ├──► fscrypt Key Descriptor (AES-256-XTS)
         └──► State Registry (/var/lib/mios/cephfs/subvolumes/<user>.json)
         │
         ▼
[Systemd Hourly Timer: mios-user-snapshot@<user>.timer]
         │
         ├──► mios-user-cephfs snapshot <user>
         └──► mios-user-cephfs replicate <user> (WireGuard HCI Mesh)
```

## CLI Usage

```bash
# Provision encrypted subvolume for tenant
mios-user-cephfs provision alice --uid 1001 --quota 100GiB

# Create point-in-time delta snapshot
mios-user-cephfs snapshot alice

# Replicate delta snapshot to peer blades
mios-user-cephfs replicate alice

# Inspect status and inventory
mios-user-cephfs list --json
mios-user-cephfs status
```

## Security & Tenant Boundary Guarantees

Any invocation targeting a UID < 1000 or system accounts (`root`, `daemon`, `nobody`, `systemd-*`) immediately fails:

```text
Security Error: Tenant isolation violation. Provisioning CephFS subvolume for privileged account 'root' (UID=0 < 1000) is strictly forbidden.
```

Subvolume directories are created with octal permissions `0700` and ownership pinned to the tenant UID/GID.

## Automated Delta Snapshots & Systemd Units

Hourly delta snapshots and mesh replications are scheduled via systemd parameterized units:
- `usr/lib/systemd/system/mios-user-snapshot@.service`: Triggered oneshot execution.
- `usr/lib/systemd/system/mios-user-snapshot@.timer`: Hourly schedule with randomized jitter to prevent cluster I/O storms.
