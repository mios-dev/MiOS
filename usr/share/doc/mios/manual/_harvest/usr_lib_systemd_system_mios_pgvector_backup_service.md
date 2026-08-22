<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Unprivileged daily oneshot that pg_dumps the unified agent-plane Postgres+pgvector database to /var/lib/mios/backups over loopback-trust and prunes to the newest MIOS_PG_BACKUP_KEEP snapshots; degrade-open so a backup failure never blocks the DB.
AI-related: mios-pgvector-backup.timer, mios-pgvector.service, /usr/lib/tmpfiles.d/mios-backups.conf, /etc/mios/userenv.sh, mios-pg-query
/usr/lib/systemd/system/mios-pgvector-backup.service
WS-0 pgvector durability: periodic logical backup of the unified agent-plane
datastore (tiered memory / knowledge / skills / sessions / scratch / sys_env /
kanban / ...). Losing pgvector is expensive, so this snapshots it daily.

UNPRIVILEGED (Architectural Law 6 spirit): runs as the pgvector sysuser
(mios-pgvector, uid 826) -- it owns /var/lib/mios/backups (tmpfiles) and
reaches Postgres over the pg_hba loopback-trust line (host all all 127.0.0.1/32
trust), so NO password and NO podman/root are needed.

DEGRADE-OPEN: every failure path (gate off, no pg_dump client, dump error)
logs and exits 0. A backup miss must NEVER fault the boot/timer or affect the
live DB. backup_enable ships TRUE; flip MIOS_PG_BACKUP_ENABLE=false (mios.toml
[pgvector].backup_enable) to disable. Real dumps require a `pg_dump` client on
PATH (the `postgresql` package); without it the unit logs a one-line hint and
no-ops -- still safe, just no snapshot until the client is provisioned.

<!-- mios-src:46fcd1eb9c7c from usr/lib/systemd/system/mios-pgvector-backup.service:1-18 -->

