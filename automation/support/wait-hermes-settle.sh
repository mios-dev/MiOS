#!/bin/bash
# AI-hint: Polls the hermes-agent.service status to bypass long gateway drain timeouts and logs the Discord patch status to verify successful configur...
# AI-doc: usr/share/doc/mios/manual/_harvest/automation_support_wait_hermes_settle_sh.md
set -euo pipefail
for i in $(seq 1 30); do
    s=$(systemctl is-active hermes-agent.service)
    case "$s" in
        active|failed|inactive)
            echo "Settled: $s after $)s"
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
