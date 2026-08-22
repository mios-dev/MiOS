<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Declares the persistent /var/lib/mios/backups directory (owned by the pgvector sysuser, uid/gid 826) where the daily pg_dump retention job writes timestamped database snapshots.
AI-related: mios-pgvector-backup.service, mios-pgvector-backup.timer, mios-pgvector, mios-services
/usr/lib/tmpfiles.d/mios-backups.conf
Persistent backup dir for the unified agent-plane datastore (WS-0 pgvector
durability). The daily mios-pgvector-backup.service pg_dumps the `mios` DB
here and prunes to MIOS_PG_BACKUP_KEEP newest. Architectural Law 2
(NO-MKDIR-IN-VAR): the /var path is DECLARED here, never mkdir'd at build.

Owned by the canonical mios-pgvector uid/gid (826, declared in
usr/lib/sysusers.d/50-mios-services.conf) so the UNPRIVILEGED backup unit
(User=mios-pgvector) can write dumps without root. 0750 keeps the dumps
(which contain DB contents) off other local users; the mios-pgvector group
owns them (dump files are chmod 0640 by the backup unit).

SSOT: the dir path mirrors mios.toml [pgvector].backup_dir
(MIOS_PG_BACKUP_DIR). If the operator overrides backup_dir to a different
/var path, add a matching drop-in under /etc/tmpfiles.d so that path exists.

<!-- mios-src:7720ee0f93dc from usr/lib/tmpfiles.d/mios-backups.conf:1-17 -->

