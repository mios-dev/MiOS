<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Systemd unit file defining the mios-cron-director service, which executes the LLM-gated task scheduler as the mios-ai user to process rules from /etc/mios/cron-rules.toml.
AI-related: /etc/mios/cron-rules.toml., /etc/mios/cron-rules.toml, /usr/libexec/mios/mios-cron-director, mios-cron-director, mios-ai, mios-agent-pipe, mios-agent-pipe.service, network-online.target, multi-user.target
/usr/lib/systemd/system/mios-cron-director.service
'MiOS' cron-director -- LLM-gated recurring-task scheduler. Reads
/etc/mios/cron-rules.toml and fires each rule's `do` when its 5-field cron
matches (optional micro-LLM gate). Runs as the agent-plane user (mios-ai) so
scheduled research/Discord tasks have the right context + network, with less
privilege than root. Already enabled in 90-mios.preset.

<!-- mios-src:6e86b0432570 from usr/lib/systemd/system/mios-cron-director.service:1-8 -->

