#!/bin/bash
# AI-hint: Read-only health dashboard: lists systemd --failed units, prints active/enabled state for the full mios-* + hermes/ollama/owui/searxng/forge service set, tails hermes-firstboot and hermes-agent journals, and checks the canonical agent ports (8640/8642/8000/114
# AI-related: mios-agent-pipe, mios-daemon, mios-surrealdb, mios-open-webui, mios-ollama-cpu, mios-searxng, mios-forge, mios-skills-miner, mios-passport-provision, mios-hermes-firstboot
# Comprehensive service-health probe across MiOS surfaces.
set -euo pipefail

echo "═══════════════════════════════════════════════════════"
echo " 1. systemd-wide failed units"
echo "═══════════════════════════════════════════════════════"
systemctl --failed --no-pager 2>&1 || true

echo
echo "═══════════════════════════════════════════════════════"
echo " 2. All mios-* + agent services (state)"
echo "═══════════════════════════════════════════════════════"
for u in mios-agent-pipe mios-daemon mios-surrealdb hermes-agent \
         mios-open-webui ollama mios-ollama-cpu mios-searxng \
         mios-forge mios-skills-miner mios-passport-provision \
         mios-hermes-firstboot mios-ttyd-bash mios-ttyd-powershell \
         mios-delegation-prefilter hermes-dashboard mios-code-server; do
    state=$(systemctl is-active "${u}.service" 2>&1)
    enabled=$(systemctl is-enabled "${u}.service" 2>&1)
    printf '  %-32s active=%-12s enabled=%s\n' "$u" "$state" "$enabled"
done

echo
echo "═══════════════════════════════════════════════════════"
echo " 3. mios-hermes-firstboot tail (50 lines)"
echo "═══════════════════════════════════════════════════════"
journalctl -u mios-hermes-firstboot.service --no-pager -n 50 \
    --since '15 min ago' 2>&1 | tail -50

echo
echo "═══════════════════════════════════════════════════════"
echo " 4. hermes-agent tail (15 lines)"
echo "═══════════════════════════════════════════════════════"
journalctl -u hermes-agent.service --no-pager -n 15 \
    --since '15 min ago' 2>&1 | tail -15

echo
echo "═══════════════════════════════════════════════════════"
echo " 5. Listening ports (canonical agent stack)"
echo "═══════════════════════════════════════════════════════"
for p in 8640 8642 8000 11434 11435 3030 8888 7681 7682 9119; do
    if ss -ltn 2>/dev/null | grep -qE "[:.]${p}\\b"; then
        printf '  :%-5s  LISTEN\n' "$p"
    else
        printf '  :%-5s  ---\n' "$p"
    fi
done
