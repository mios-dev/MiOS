<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Injects sibling-agent activities (Sys-Agent, nudger, log-watcher, cron-director) into the OWUI chat stream by polling state files and emitting status events to provide the operator visibility into the full MiOS federation.
AI-related: mios-agent-nudger, mios-log-watcher, mios-cron-director, mios-hermes-tail, mios-delegation-prefilter, mios-daemon, mios-sys-agent
AI-functions: __init__, _cache_path, _load_cache, _save_cache, _format_hermes_tail, _format_nudger, _format_log_watcher, _format_cron, _format_daemon_classify, _format_daemon_refusal, _format_daemon_cron, _format_sys_agent

<!-- mios-src:bd093eb542dd from usr/share/mios/owui/pipes/mios_sidecar_filter.py:1-3 -->

