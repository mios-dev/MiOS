<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Ordered-before oneshot that lets the pgvector image float across PostgreSQL majors -- it dumps an older cluster with the older image into the initdb restore slot and stashes the old data dir so the new major can initialise, and degrades open (never destructive) when it cannot.
AI-related: mios-pgvector.service, mios-pgvector-major-upgrade, /usr/lib/tmpfiles.d/mios-pgvector.conf, mios-pgvector-backup.service
/usr/lib/systemd/system/mios-pgvector-major-upgrade.service
Rationale and the full procedure: usr/share/doc/mios/upstream/pgvector.md
section "Moving the PostgreSQL major". Non-destructive on every failure path.

<!-- mios-src:0c1e4092596e from usr/lib/systemd/system/mios-pgvector-major-upgrade.service:1-5 -->

