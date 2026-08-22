<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### In-place patch of hermes_cli/web_server.py so the /api/pty...

In-place patch of hermes_cli/web_server.py so the /api/pty endpoint
honors HERMES_PTY_SHELL env var.

Upstream hermes-agent hardcodes `_resolve_chat_argv` to spawn
`hermes --tui` (the Node-built TUI chat). MiOS-DEV wants a plain bash
shell in the dashboard's /chat tab (operator directive
"do we have a react window for terminal(s)?" -> chose "plain bash").
Setting `HERMES_PTY_SHELL=/bin/bash` (or any shell binary) replaces
the hardcoded TUI spawn with the requested shell.

Idempotent: rerunning is a no-op once the marker comment is present.
Safe: leaves the upstream fallback when HERMES_PTY_SHELL is unset.

Usage:
    hermes-dashboard-shell-patch.py /path/to/hermes_cli/web_server.py

<!-- mios-src:89f7c843cfc6 from automation/support/hermes-dashboard-shell-patch.py:4-19 -->
