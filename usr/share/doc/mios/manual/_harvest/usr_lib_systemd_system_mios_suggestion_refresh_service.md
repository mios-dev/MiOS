<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Systemd unit that triggers a one-shot script to refresh MiOS-aware starter chips in webui.db by querying pgvector and the refine endpoint, ensuring the UI prompt suggestions stay current.
AI-related: /usr/libexec/mios/mios-suggestion-refresh., /usr/libexec/mios/mios-suggestion-refresh, mios-suggestion-refresh, mios-agent-pipe, mios-agent-pipe.service, mios-pgvector.service, mios-llm-light.service, multi-user.target
/usr/lib/systemd/system/mios-suggestion-refresh.service
One-shot wrapper around /usr/libexec/mios/mios-suggestion-refresh.
Generates fresh MiOS-aware starter chips + writes them into
webui.db ui.prompt_suggestions. Fired by the matching .timer
on a 10-min cadence (operator-tunable). Safe to run any time;
on failure the previous chips remain in place.

<!-- mios-src:8b344bc53ce1 from usr/lib/systemd/system/mios-suggestion-refresh.service:1-8 -->

