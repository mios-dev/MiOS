<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Pure PTY-session protocol for the persistent shell substrate (SHELL-01). Owns the four pure decisions a stateful shell needs and nothing else: session_key normalises an arbitrary chat id into a tmux-safe name that cannot escape its namespace; tmux_argv builds the new-session/send-keys/kill-session argv; wrap_command frames one command between a per-command NONCE sentinel so completion, exit code and cwd are read back from a line the command's own output cannot forge; and parse_result extracts that frame, treating any pre-marker text as untrusted output. No subprocess, no tmux, no filesystem -- the libexec runner supplies those, so every branch here is isolation-testable.
AI-related: usr/libexec/mios/mios-shell-session, ./aci.py, usr/share/mios/mios.toml [shell_session], ../../test_mios_pty.py
AI-functions: session_key, session_path, tmux_argv, tmux_conf, new_nonce, session_init_cmd, wrap_command, parse_result, is_idle

<!-- mios-src:f59eec743233 from usr/lib/mios/agent-pipe/mios_pipe/routing/pty.py:1-3 -->

