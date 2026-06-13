#!/bin/bash
# AI-hint: Polls the hermes-agent.service status to bypass long gateway drain timeouts and logs the Discord patch status to verify successful configuration application during restart cycles.
# AI-related: /usr/lib/mios/agents/.venv/lib/python3.14/site-packages/gateway/platforms/discord.py, hermes-agent.service
# Poll hermes-agent.service state until it leaves activating/
# deactivating, then report the ExecStartPre patch verdict.
# Used after restart cycles where the gateway's 240s drain
# timeout can stall the unit in 'activating' for minutes.
set -euo pipefail
for i in $(seq 1 30); do
    s=$(systemctl is-active hermes-agent.service)
    case "$s" in
        active|failed|inactive)
            echo "settled: $s after $((i * 5))s"
            break
            ;;
    esac
    sleep 5
done

echo
echo "=== ExecStartPre verdict ==="
journalctl -u hermes-agent.service --since '5 min ago' --no-pager \
    | grep -E 'discord-reactions-patch|already applied|grew' | head -5

echo
echo "=== MiOS-patch marker count ==="
grep -c 'MiOS-patch' \
    /usr/lib/mios/agents/.venv/lib/python3.14/site-packages/gateway/platforms/discord.py
