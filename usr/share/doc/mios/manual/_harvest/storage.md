<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Remote delta backup...

!/usr/bin/env python3
AI-hint: Remote delta backup synchronizer utilizing chunk hashing, zstd compression, and rsync/rclone transports.
AI-related: usr/lib/systemd/system/mios-backup-remote.service, usr/lib/systemd/system/mios-backup-remote.timer, tests/test-storage.py
AI-functions: hash_file_chunk, create_snapshot_manifest, compute_delta_plan, compress_chunk_zstd, sync_delta_payload, verify_remote_manifest, main

<!-- mios-src:4fc47a8a4af4 from usr/libexec/mios/storage/mios-backup-remote:1-4 -->

### !/usr/bin/env python3 AI-hint: Storage benchmark harness...

!/usr/bin/env python3
AI-hint: Storage benchmark harness measuring 4K random IOPS, 1M sequential throughput, and fsync latency against AI model inference floors.
AI-related: usr/bin/mios-bench-storage, tests/test-storage.py
AI-functions: run_random_4k_read_benchmark, run_random_4k_write_benchmark, run_seq_1m_read_benchmark, run_seq_1m_write_benchmark, run_fsync_latency_benchmark, evaluate_inference_floors, main

<!-- mios-src:a20bf11cad90 from usr/libexec/mios/storage/mios-bench-storage:1-4 -->

### !/usr/bin/env python3 AI-hint: Dynamic quota enforcement...

!/usr/bin/env python3
AI-hint: Dynamic quota enforcement per tenant subvolume via CephFS extended attributes and subvolume resizing.
AI-related: usr/lib/systemd/system/mios-cephfs-quota.service, usr/lib/systemd/system/mios-cephfs-quota.timer, tests/test-storage.py, usr/share/mios/mios.toml
AI-functions: parse_size_bytes, format_size_bytes, parse_count, CephFSQuotaManager, main

<!-- mios-src:39f73ffaf4a3 from usr/libexec/mios/storage/mios-cephfs-quota:1-4 -->

### !/usr/bin/env python3 AI-hint: Transactional ledger...

!/usr/bin/env python3
AI-hint: Transactional ledger replication across CephFS pools with SHA-256 integrity verification.
AI-related: usr/lib/systemd/system/mios-ledger-sync.service, tests/test-storage.py, usr/share/mios/mios.toml
AI-functions: canonical_json, compute_hash, compute_hmac, Block, LedgerChain, LedgerSyncEngine, main

<!-- mios-src:125f69f6d6e6 from usr/libexec/mios/storage/mios-ledger-sync:1-4 -->
