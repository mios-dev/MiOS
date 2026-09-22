<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Automated pg_dump and zstd...

!/usr/bin/env python3
AI-hint: Automated pg_dump and zstd snapshot generator with rolling retention for pgvector.
AI-related: usr/lib/systemd/system/mios-backup-pgvector.service, tests/test-db.py, usr/share/doc/mios/manual/ch66-v5-authority-inversion-and-cephfs-tiering.md

<!-- mios-src:509dac5a37cc from usr/libexec/mios/db/mios-backup-pgvector.py:1-3 -->

### !/usr/bin/env python3 AI-hint: Database integrity checker...

!/usr/bin/env python3
AI-hint: Database integrity checker, corruption detector, and automated non-destructive repair engine for SQLite and PostgreSQL.
AI-related: usr/lib/greenboot/check/required.d/55-mios-db-check.sh, tests/test-db.py, usr/share/containers/systemd/mios-pgvector.container

<!-- mios-src:9668bc5814c0 from usr/libexec/mios/db/mios-db-doctor.py:1-3 -->

### !/usr/bin/env python3 AI-hint: PostgreSQL hot-standby...

!/usr/bin/env python3
AI-hint: PostgreSQL hot-standby streaming replication manager, lag monitor, fencing coordinator, and atomic failover promoter.
AI-related: usr/lib/systemd/system/mios-pg-replica.service, tests/test-db.py, usr/share/containers/systemd/mios-pgvector.container

<!-- mios-src:f2a17a187d66 from usr/libexec/mios/db/mios-pg-replica.py:1-3 -->
