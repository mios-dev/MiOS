<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines the persistent storage path, permissions, and ownership (UID/GID 826) for the pgvector database directory used by the unified agent-plane Postgres container.
AI-related: mios-pgvector, mios-services
/usr/lib/tmpfiles.d/mios-pgvector.conf
Persistent PGDATA dir for the unified agent-plane Postgres+pgvector container
(WS-9), owned by the canonical mios-pgvector uid/gid (826, declared in
usr/lib/sysusers.d/50-mios-services.conf). bootc-immutable code path; mutable
state stays under /var. The postgres entrypoint creates the `pgdata` subdir
under this (so a non-root uid can own its own PGDATA).

<!-- mios-src:b17b0d899458 from usr/lib/tmpfiles.d/mios-pgvector.conf:1-8 -->

