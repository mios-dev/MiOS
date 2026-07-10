#!/bin/bash
# AI-hint: Executes a recovery sequence to redeploy firstboot binaries, apply environment drop-ins for hermes-agent, restart the agent, and verify the status of ttyd and skills-miner services.
# AI-related: /usr/libexec/mios/mios-hermes-firstboot, mios-hermes-firstboot, mios-paths-env, mios-ttyd-bash, mios-ttyd-powershell, mios-skills-miner, hermes-agent.service, skills-miner.timer, mios-hermes-firstboot.service, mios-skills-miner.timer
# Final heal: redeploy firstboot + env drop-in, restart hermes-agent
# to pick up the new env, re-run firstboot to enable opt-in units,
# verify everything is green.
set -euo pipefail

echo "── deploy firstboot + env drop-in ──"
cp /mnt/c/MiOS/usr/libexec/mios/mios-hermes-firstboot \
   /usr/libexec/mios/mios-hermes-firstboot
chmod +x /usr/libexec/mios/mios-hermes-firstboot
cp /mnt/c/MiOS/usr/lib/systemd/system/hermes-agent.service.d/20-mios-paths-env.conf \
   /usr/lib/systemd/system/hermes-agent.service.d/20-mios-paths-env.conf
systemctl daemon-reload

echo
echo "── restart hermes-agent to pick up env fix ──"
systemctl restart hermes-agent.service 2>&1 &
RESTART_PID=$!

echo
echo "── re-run firstboot (idempotent; enables ttyd + skills-miner.timer) ──"
systemctl reset-failed mios-hermes-firstboot.service 2>&1 || true
systemctl start --no-block mios-hermes-firstboot.service
sleep 6
journalctl -u mios-hermes-firstboot.service --since '30 sec ago' --no-pager \
    | grep -E 'enabled\+started|WARN' | tail -10

echo
echo "── opt-in service states after firstboot ──"
for u in mios-ttyd-bash mios-ttyd-powershell mios-skills-miner mios-embed-backfill; do
    state=$(systemctl is-active "${u}.service" 2>&1)
    enabled=$(systemctl is-enabled "${u}.service" 2>&1)
    printf '  %-30s active=%-10s enabled=%s\n' "$u" "$state" "$enabled"
done
for t in mios-skills-miner.timer mios-embed-backfill.timer; do
    state=$(systemctl is-active "$t" 2>&1)
    enabled=$(systemctl is-enabled "$t" 2>&1)
    printf '  %-30s active=%-10s enabled=%s\n' "$t" "$state" "$enabled"
done

echo
echo "── env drop-in parse re-check (no rejected lines) ──"
wait $RESTART_PID 2>/dev/null || true
sleep 2
journalctl -u hermes-agent.service --since '20 sec ago' --no-pager \
    | grep -E 'Invalid environment assignment' | head -3 \
    || echo "  (none -- drop-in parses cleanly)"

echo
echo "── final listening-port summary ──"
for p in 8640 8642 8000 11434 11435 3030 8888 7681 7682 9119; do
    if ss -ltn 2>/dev/null | grep -qE "[:.]${p}\\b"; then
        printf '  :%-5s  LISTEN\n' "$p"
    else
        printf '  :%-5s  ---\n' "$p"
    fi
done
