<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines filesystem permissions and setgid bits for mios-cron-director state and prompt storage, ensuring the mios-ai daemon and launcher-broker can share and access per-minute deduplication data and prompt text.
AI-related: mios-cron-director, mios-ai
/usr/lib/tmpfiles.d/mios-cron-director.conf
'MiOS' cron-director runtime dirs. The daemon (mios-ai) writes its per-minute
dedup state here; the schedule shim drops each rule's prompt text in prompts/
(kept out of the shell `do` line to avoid any injection). Owner mios-ai (uid
850) matches the service User=.
0770 (group-writable): the daemon runs as mios-ai, but the `schedule` verb's
shim runs as the launcher-broker user `mios` (uid 1000), who is a member of
the mios-ai group -- so it can write user-rules.toml + prompts/ here without
touching root-owned /etc/mios. setgid (2) so new files inherit the mios-ai
group and the mios-ai daemon can always read them.

<!-- mios-src:c8fe64c4baeb from usr/lib/tmpfiles.d/mios-cron-director.conf:1-12 -->

