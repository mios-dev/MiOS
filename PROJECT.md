# Project: MiOS Roadmap Workstreams Implementation (T-401 through T-412)

## Architecture
MiOS ("My OS") is an immutable bootc/OCI Fedora container workstation and local self-replicating agentic AI edge OS. The system combines:
1. Unified Agent Datastore and Database Reliability: Automated index maintenance, hot-standby clustering, SQLite/Postgres corruption recovery, and zero-downtime transactional schema migration under `usr/libexec/mios/db/`.
2. High-Assurance CephFS & Storage Infrastructure: Transactional SHA-256 block ledger synchronization, dynamic subvolume quota management, RADOS S3 object storage sidecar gateway, and LUKS2 zero-downtime key rotation under `usr/libexec/mios/storage/` and `usr/libexec/mios/sec/`.
3. Edge Node Resilience & Telemetry Pipeline: Fast zstd delta snapshot transfers for remote backups, `mios-bench-storage` IOPS/latency benchmark harness, automated PSI-driven tmpfs spill-to-NVMe manager, and journald-to-pgvector structured log aggregator.
4. Strict SSOT configuration model driven by `usr/share/mios/mios.toml`, 8-field schema task registries (`TASKS.md` / `AGY-TASKS.md`), automated test suites registered under `[ci.tiers] unit`, and 7 CI validation checks.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | T-401 | Automated VACUUM ANALYZE and HNSW vector index rebuilding timer in pgvector | M1 | survey |
| 2 | T-406 | Hot-standby PostgreSQL replica provisioning over local cluster nodes | M1 | survey |
| 3 | T-407 | Database corruption detector and automated repair script for SQLite and PostgreSQL stores | M1 | survey |
| 4 | T-412 | Zero-downtime database schema migration runner with rollback safety checks | M1 | survey |
| 5 | T-402 | Transactional ledger replication across CephFS pools with integrity hashing | M2 | survey |
| 6 | T-403 | CephFS dynamic quota enforcement per tenant subvolume | M2 | survey |
| 7 | T-404 | S3-compatible object storage gateway / radosgw sidecar for bulk model distribution | M2 | survey |
| 8 | T-405 | Encrypted volume key rotation service for LUKS2 and dm-crypt Ceph OSD drives | M2 | survey |
| 9 | T-408 | Fast delta snapshot transfer for remote off-site backup synchronization | M3 | survey |
| 10 | T-409 | Storage performance benchmark tool `mios-bench-storage` testing IOPS and latency | M3 | survey |
| 11 | T-410 | Automated tmpfs spill-to-NVMe manager under memory pressure conditions | M3 | survey |
| 12 | T-411 | Unified log aggregation pipeline streaming journald events to pgvector | M3 | survey |
| 13 | Test Suites | Authored dedicated unit tests in `tests/test-*.py`, registered under `[ci.tiers] unit` in `usr/share/mios/mios.toml` | M4 | survey |
| 14 | Registries Parity | Full 8-field schema adherence across `TASKS.md` & `AGY-TASKS.md`, metrics rollup via `tools/roadmap-index.py` | M4 | survey |
| 15 | SSOT Sync & CI | 7 SSOT machine projections sync (`tools/sync-generated.sh`), 7 CI checks pass (exit code 0), clean git commit/push | M4 | survey |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | M1: Database & Memory Operations | T-401 (pgvector optimize), T-406 (pg replica), T-407 (db doctor), T-412 (db migrate) | none | DONE |
| 2 | M2: CephFS & Storage Infrastructure | T-402 (ledger sync), T-403 (cephfs quota), T-404 (radosgw sidecar), T-405 (LUKS2 key rotation) | none | DONE |
| 3 | M3: Node Resilience & Telemetry Pipeline | T-408 (delta backup), T-409 (bench-storage), T-410 (tmpfs spillover), T-411 (log streamer) | none | DONE |
| 4 | M4: Test Suites, Registries & CI Verification | Authored unit tests, mios.toml registration, TASKS.md / AGY-TASKS.md 8-field parity, sync-generated, 7 CI gates, git commit & push | M1, M2, M3 | DONE |

## Interface Contracts

### Database & Vector Maintenance Interface (T-401, T-406, T-407, T-412)
- Maintenance script: `usr/libexec/mios/db/mios-pgvector-optimize.py` running `VACUUM (ANALYZE, PARALLEL 4)` and `REINDEX INDEX CONCURRENTLY` for vector indices.
- Service & Timer: `usr/lib/systemd/system/mios-pgvector-optimize.service`, `usr/lib/systemd/system/mios-pgvector-optimize.timer` (Weekly, Sunday 03:00).
- Replication script: `usr/libexec/mios/db/mios-pg-replica.py` orchestrating `pg_basebackup -R`, streaming replication lag monitoring, and promotion via `pg_ctl promote`.
- Doctor script: `usr/libexec/mios/db/mios-db-doctor.py` checking SQLite (`PRAGMA integrity_check`) and PostgreSQL (`pg_checksums`/`amcheck`), plus greenboot hook `usr/lib/greenboot/check/required.d/55-mios-db-check.sh`.
- Migration runner: `usr/libexec/mios/db/mios-db-migrate.py` applying transactional SQL migrations from `usr/share/mios/postgres/migrations/` inside `BEGIN ... COMMIT` with `schema_version` SHA-256 ledger and rollback.

### CephFS & Storage Infrastructure Interface (T-402, T-403, T-404, T-405)
- Ledger Sync: `usr/libexec/mios/storage/mios-ledger-sync` replicating transactions across CephFS pools with SHA-256 block hashing and sequence verification.
- Quota Manager: `usr/libexec/mios/storage/mios-cephfs-quota` enforcing soft/hard quotas via `setfattr -n ceph.quota.max_bytes` and subvolume resizing.
- RADOSGW Sidecar: `usr/share/containers/systemd/mios-radosgw.container` listening on port 8470 (`[ports.categories.cluster] radosgw = 8470`), providing local S3 endpoint for model distribution.
- LUKS2 Key Rotation: `usr/libexec/mios/sec/mios-luks-rotate` executing atomic key rotation via keyslot addition, passphrase validation, and old keyslot destruction without unmounting.

### Node Resilience & Telemetry Interface (T-408, T-409, T-410, T-411)
- Delta Backup: `usr/libexec/mios/storage/mios-backup-remote` calculating block/file deltas, compressing via `zstd`, and syncing to remote targets.
- Benchmark: `usr/libexec/mios/storage/mios-bench-storage` testing 4K random IOPS, 1M throughput, fsync latency with `--json` output.
- Memory Spill: `usr/libexec/mios/mem/mios-tmpfs-spill` monitoring `/proc/pressure/memory` (>60% PSI threshold) and moving older cache files from `/tmp` to `/var/tmp/spill`.
- Log Streamer: `usr/libexec/mios/log/mios-log-streamer` streaming filtered JSON logs from `journalctl` to pgvector `system_logs` table.

## Code Layout
- Database utilities: `usr/libexec/mios/db/`
- Storage & backup utilities: `usr/libexec/mios/storage/`
- Security & key rotation: `usr/libexec/mios/sec/`
- Memory management: `usr/libexec/mios/mem/`
- Logging & telemetry: `usr/libexec/mios/log/`
- Systemd units & timers: `usr/lib/systemd/system/`
- Quadlet container units: `usr/share/containers/systemd/`
- SQL schemas & migrations: `usr/share/mios/postgres/`
- Python unit test suites: `tests/test-*.py`
- Configuration & SSOT: `usr/share/mios/mios.toml`
- Task registries: `TASKS.md`, `AGY-TASKS.md`, `ROADMAP.md`
- Validation tools: `tools/sync-generated.sh`, `tools/drift-checks.py`, `tools/roadmap-index.py`, `tools/ci-suites.py`, `tools/check-*.py`
