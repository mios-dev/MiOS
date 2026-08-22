<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/bin/bash AI-hint: Automates the deployment of the...

!/bin/bash
AI-hint: Automates the deployment of the agent-pipe service by copying source files, stripping CRLF, performing a pre-restart import check in the service venv, and rolling back to backups if the import fails.
AI-related: /usr/lib/mios/agent-pipe, /usr/lib/mios/agents/.venv/bin/python3, /usr/lib/mios/agent-pipe/, /usr/share/mios/mios.toml, /usr/share/mios/mios.toml.bak-, mios-agent-pipe, mios-agent-pipe.service

<!-- mios-src:4261f116cf36 from automation/support/deploy-agent-pipe.sh:1-3 -->

