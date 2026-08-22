<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Systemd unit that executes /usr/libexec/mios/mios-sys-env to probe and UPSERT the current system state (apps, services, models, hardware) into the pgvector sys_env:current row for global agent synchronization.
AI-related: /usr/libexec/mios/mios-sys-env, mios-sys-env, mios-pg-query, mios-podman-ps, mios-pgvector.service, multi-user.target

<!-- mios-src:daf7f27686ce from usr/lib/systemd/system/mios-sys-env-refresh.service:1-2 -->

