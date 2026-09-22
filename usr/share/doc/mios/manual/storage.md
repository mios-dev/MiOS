<!-- AI-hint: Manual pages distilled from the source comments of storage, sanitized, each passage anchored to the comment it came from. -->

# storage

### bcachefs_tier.py — T-761 WS-STRG Declarative Bcachefs...

bcachefs_tier.py — T-761 WS-STRG
Declarative Bcachefs multi-device tiering and transparent SSD caching manager.

Configures foreground NVMe and background HDD targets with zstd compression,
providing >10 GB/s burst write absorption and transparent background migration.

<!-- mios-src:2be895d56123 from usr/libexec/mios/storage/bcachefs_tier.py:4-10 -->

### Renders the bcachefs multi-device format command and its...

Renders the bcachefs multi-device format command and its fstab entry.

    The rendering half is pure: it turns a device inventory into the exact
    argv/fstab text an operator would run, so it is verifiable without touching
    a disk. The block-migration half below models the in-kernel behaviour and
    reports a fixed throughput figure -- treat those numbers as illustrative,
    not measured.

<!-- mios-src:68dcc66e5238 from usr/libexec/mios/storage/bcachefs_tier.py:28-35 -->

### ceph_mds.py — T-739 WS-STRG Active-Active CephFS MDS...

ceph_mds.py — T-739 WS-STRG
Active-Active CephFS MDS metadata clustering and dynamic subtree partitioner.

Sets max_mds=2, configures standby replay daemons, and manages dynamic subtree
directory pinning (ceph.dir.pin) across MDS ranks with <2s failover recovery.

<!-- mios-src:2887d26ce568 from usr/libexec/mios/storage/ceph_mds.py:4-10 -->

### MiOS OCI Container Image Storage LRU Garbage Collection &...

MiOS OCI Container Image Storage LRU Garbage Collection & Deduplication Daemon.

Maintains container graph storage integrity:
1. Podman Graph Inspection: Evaluates image layers, manifests, and active container bindings.
2. LRU Eviction Ordering: Sorts unreferenced dangling images by last access timestamp.
3. Automated Threshold Pruning: Prunes oldest unused images when storage exceeds high watermark (default 85%).
4. Invariant Protection: Bound production and base OS images are pinned and exempt from pruning.

<!-- mios-src:5ff0a26427e8 from usr/libexec/mios/storage/container_gc.py:4-12 -->

### Predictive S.M.A.R.T. drive health monitor and automated...

Predictive S.M.A.R.T. drive health monitor and automated CephFS evacuation manager for MiOS.

Polls NVMe and SATA drive S.M.A.R.T. telemetry, parses nvme-cli / smartctl JSON outputs,
calculates predictive health scores, detects wear indicators (percentage_used >= 95%,
available spare <= 10%, reallocated sectors > 10, temperature > 75°C), emits desktop alerts,
and executes proactive CephFS OSD drain with zero degraded object loss.

<!-- mios-src:37a486cb09d7 from usr/libexec/mios/storage/disk_health.py:4-10 -->

### Compares current manifest against baseline manifest to...

Compares current manifest against baseline manifest to determine:
    - New chunks that must be compressed and transmitted.
    - Deduped chunks that already exist on remote target.
    - Deleted files / obsolete chunks.

<!-- mios-src:b98245fa388a from usr/libexec/mios/storage/mios-backup-remote:129-134 -->

### Hardware OPAL 2.0 SED / LUKS2 Automated Disk Partitioning...

Hardware OPAL 2.0 SED / LUKS2 Automated Disk Partitioning Engine (T-549).

Discovers NVMe/SATA storage drives, detects TCG OPAL 2.0 Self-Encrypting Drive (SED)
hardware capabilities via sedutil-cli/sysfs, activates hardware Locking Range 0,
falls back to software LUKS2 AES-XTS-512 with TPM 2.0 (PCR 7+11) binding, and applies
MiOS standard GPT partitioning layouts (ESP, Root, Userspace, DB/Ceph).

<!-- mios-src:5174fc9d7b9a from usr/libexec/mios/storage/opal_luks_partition.py:4-10 -->
