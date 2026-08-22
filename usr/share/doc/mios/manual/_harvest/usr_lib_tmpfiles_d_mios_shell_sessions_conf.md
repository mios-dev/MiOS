<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Declares the writable state directory for the SHELL-01 persistent PTY substrate, owned by the agent-plane user so mios-shell-session can record per-session activity for the idle reaper.
AI-related: /usr/libexec/mios/mios-shell-session, usr/share/mios/mios.toml [shell_session], mios-shell-session-gc.service
/usr/lib/tmpfiles.d/mios-shell-sessions.conf
Declared, never mkdir'd by the runner (Architectural Law 2). Holds one dir per
live session with its last-activity stamp, plus the generated tmux.conf that
carries history-limit (which tmux applies only to panes created after it).

<!-- mios-src:7c03d9fc5783 from usr/lib/tmpfiles.d/mios-shell-sessions.conf:1-6 -->

