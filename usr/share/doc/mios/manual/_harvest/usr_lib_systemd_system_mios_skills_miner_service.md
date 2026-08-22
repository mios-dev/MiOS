<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Systemd unit that executes `mios-skills mine` to process the pgvector tool_call history into a skill catalog, automatically updating the shared catalog and reaping low-performing skills via `export-catalog` and `reap`.
AI-related: /usr/libexec/mios/mios-skills, /etc/mios/userenv.sh, mios-skills, mios-skills-miner, mios-agent-pipe, mios-ai, mios-skills-miner.timer, mios-pgvector.service, mios-agent-pipe.service
/usr/lib/systemd/system/mios-skills-miner.service
Phase C.2 of the AgentOS roadmap: scheduled Sequential Pattern
Mining over the pgvector tool_call history. Runs `mios-skills mine`
at the cadence set by mios-skills-miner.timer (default 60min;
operator overrides via [skills].mine_interval_minutes -> the
OnUnitActiveSec line in the .timer file).

Idempotent: re-running on the same tool_call population that
already has fully-attributed skill_invocation edges is a no-op
because the miner subtracts skill-emitted tool_calls from the
candidate population.

<!-- mios-src:c37a0d4ea3a5 from usr/lib/systemd/system/mios-skills-miner.service:1-13 -->

