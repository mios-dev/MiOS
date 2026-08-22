<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Systemd unit that runs the mios_pipe.memory.embed_backfill worker to periodically re-embed database rows with stale or missing vector versions.
AI-related: /usr/lib/mios/agent-pipe/mios_pipe/memory/embed_backfill.py, mios-embed-backfill.timer, mios-pgvector.service, mios-llm-light.service
/usr/lib/systemd/system/mios-embed-backfill.service

<!-- mios-src:769034b0da1d from usr/lib/systemd/system/mios-embed-backfill.service:1-3 -->

