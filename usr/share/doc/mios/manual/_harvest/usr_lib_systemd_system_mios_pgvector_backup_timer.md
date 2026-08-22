<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Daily systemd timer that fires mios-pgvector-backup.service to snapshot the unified agent-plane Postgres+pgvector datastore, with Persistent=true so a missed run (machine off) executes at next boot.
AI-related: mios-pgvector-backup.service, timers.target
/usr/lib/systemd/system/mios-pgvector-backup.timer
WS-0 pgvector durability: schedules the daily logical backup of the unified
agent-plane datastore. The service itself is degrade-open + gated on
MIOS_PG_BACKUP_ENABLE, so the timer can stay enabled unconditionally.

<!-- mios-src:814e75d3e117 from usr/lib/systemd/system/mios-pgvector-backup.timer:1-6 -->

