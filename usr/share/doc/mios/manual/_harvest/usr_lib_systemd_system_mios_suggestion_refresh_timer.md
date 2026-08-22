<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Systemd timer that triggers mios-suggestion-refresh.service every 10 minutes to update OWUI starter chips based on current system state, kanban data, and recent user intents.
AI-related: /usr/libexec/mios/mios-suggestion-refresh, mios-suggestion-refresh, mios-suggestion-refresh.service, timers.target
/usr/lib/systemd/system/mios-suggestion-refresh.timer
Fires mios-suggestion-refresh.service every 10 minutes so the
OWUI starter chips revolve based on current MiOS state (recent
kanban, daemon nudges, recent refine intents). Operators tune
the cadence with:
  sudo systemctl edit mios-suggestion-refresh.timer
  [Timer]
  OnUnitActiveSec=30min

<!-- mios-src:12e4fffe8a14 from usr/lib/systemd/system/mios-suggestion-refresh.timer:1-10 -->

