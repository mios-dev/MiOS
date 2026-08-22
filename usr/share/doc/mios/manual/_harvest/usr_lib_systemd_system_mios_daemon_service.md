<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Systemd unit file defining the core MiOS daemon; it consolidates log watching, cron gating, and agent nudging into a single process using a local qwen3 model to update the state.json file used by the OWUI sidecar.
AI-related: /usr/libexec/mios/mios-daemon, /etc/mios/secrets.env, /etc/mios/daemon/cron.toml, mios-daemon, mios-log-watcher, mios-cron-director, mios-agent-nudger, mios-ai, mios-delegation-prefilter, mios-open-webui

<!-- mios-src:97b151c0e131 from usr/lib/systemd/system/mios-daemon.service:1-2 -->

