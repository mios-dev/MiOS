#!/bin/bash
set -u
echo "=== FINAL service state ==="
for u in mios-agent-pipe mios-daemon mios-surrealdb hermes-agent \
         mios-open-webui ollama mios-ollama-igpu mios-searxng \
         mios-forge mios-skills-miner.timer mios-passport-provision \
         mios-hermes-firstboot mios-ttyd-bash mios-ttyd-powershell \
         mios-delegation-prefilter hermes-dashboard mios-code-server; do
    printf '  %-30s %s\n' "$u" "$(systemctl is-active "$u" 2>/dev/null)"
done

echo
echo "=== FAILED ==="
out=$(systemctl --failed --no-pager 2>&1 | head -8)
echo "$out"

echo
echo "=== port listeners ==="
for p in 8640 8642 8000 11434 11435 3030 8888 7681 7682 9119; do
    if ss -ltn 2>/dev/null | grep -qE "[:.]${p}\\b"; then
        printf '  :%-5s LISTEN\n' "$p"
    else
        printf '  :%-5s ---\n' "$p"
    fi
done
