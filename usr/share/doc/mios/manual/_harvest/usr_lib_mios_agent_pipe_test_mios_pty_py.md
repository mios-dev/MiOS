<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Stdlib offline tests for...

!/usr/bin/env python3
AI-hint: Stdlib offline tests for mios_pipe.routing.pty -- the persistent shell substrate's pure protocol (SHELL-01). No tmux, no subprocess, no filesystem. Proves the security properties the protocol exists for: a session id containing path traversal or shell metacharacters cannot escape its tmux namespace and two distinct ids never collide after truncation; a command whose OUTPUT prints a marker-shaped line, or replays an OLD nonce, does NOT read as this command completing; the last real marker wins so a replayed capture cannot terminate a command early; an unfinished command parses as None rather than as exit 0; and the idle reaper never kills a session on unparseable bookkeeping. Run: python3 test_mios_pty.py
AI-related: ./mios_pipe/routing/pty.py, usr/libexec/mios/mios-shell-session, usr/share/mios/mios.toml [shell_session]
AI-functions: main

<!-- mios-src:45db071574de from usr/lib/mios/agent-pipe/test_mios_pty.py:1-4 -->

