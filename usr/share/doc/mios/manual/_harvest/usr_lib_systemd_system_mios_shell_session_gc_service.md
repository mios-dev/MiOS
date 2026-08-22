<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: SHELL-01 idle reaper for the persistent PTY substrate -- kills tmux sessions idle past [shell_session].idle_s so a long-lived shell plane cannot accumulate unbounded state.
AI-related: /usr/libexec/mios/mios-shell-session, mios-shell-session-gc.timer, /usr/share/mios/mios.toml [shell_session]

<!-- mios-src:42fea3757a83 from usr/lib/systemd/system/mios-shell-session-gc.service:1-2 -->

