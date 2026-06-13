#!/bin/bash
# AI-hint: Restarts core MiOS agent and daemon services to clear stale state and regenerate day-0 credentials/keys after a system wipe or configuration reset.
# AI-related: mios-agent-pipe, mios-daemon, mios-open-webui, mios-agent-pipe.service, mios-daemon.service
# Restart MiOS agent services post-wipe so they regenerate their
# day-0 state cleanly (passport keys, satisfaction loop baseline,
# session dirs, etc.).
set -euo pipefail
systemctl restart mios-agent-pipe.service mios-daemon.service 2>&1
sleep 2
for s in mios-agent-pipe mios-daemon hermes-agent mios-open-webui; do
    state=$(systemctl is-active "${s}.service" 2>&1)
    printf '%-22s %s\n' "$s" "$state"
done
