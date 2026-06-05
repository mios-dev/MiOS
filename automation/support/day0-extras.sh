#!/bin/bash
# Day-0 readiness: surfaces NOT covered by mios-cache-clear.
# Run via: wsl.exe ... bash /mnt/c/MiOS/automation/support/day0-extras.sh <section>
# Sections: surreal | daemon | skills | passports | agentpipe | audit | ttyd | pycache | all
set -euo pipefail
SECTION="${1:-all}"

surreal() {
    echo "── SurrealDB row-level wipe (schema preserved) ──"
    local TABLES="session tool_call event kanban_shadow scratch agent_metric skill skill_invocation agent_keypair emitted includes message memory_event verdict"
    for t in $TABLES; do
        local resp
        resp=$(curl -s -o /dev/null -w "%{http_code}" \
            -u root:root -H "ns: mios" -H "db: agent" \
            -H "Accept: application/json" -H "Content-Type: text/plain" \
            --data "DELETE $t;" http://127.0.0.1:8000/sql)
        printf '  %s  DELETE %s\n' "$resp" "$t"
    done
}

daemon() {
    echo "── mios-daemon state ──"
    rm -fv /var/lib/mios/daemon/state.json \
           /var/lib/mios/daemon/launch_failures.json 2>&1
    rm -fv /var/lib/mios/scratch/agent-nudges.md \
           /var/lib/mios/scratch/agent-nudges.json 2>&1
}

skills() {
    echo "── skills catalog + mined patterns (regen via mios-skills-miner.timer) ──"
    if [[ -d /var/lib/mios/skills ]]; then
        find /var/lib/mios/skills -type f \
            \( -name '*.json' -o -name '*.jsonl' \) -print -delete
    fi
    if [[ -d /var/lib/mios/skills/mined ]]; then
        rm -rfv /var/lib/mios/skills/mined/* 2>&1 | tail -5
    fi
}

passports() {
    # SSOT: [passport].dir in mios.toml -> /var/lib/mios/agent-passports/
    # (NOT /var/lib/mios/passports/ -- that's a typo trap that has
    # caught me before).
    echo "── passport keys (regen via mios-passport-provision.service) ──"
    local DIR=/var/lib/mios/agent-passports
    if [[ -d $DIR ]]; then
        find "$DIR" -mindepth 1 -print -delete
        echo "  -> systemctl restart mios-passport-provision.service"
        systemctl restart mios-passport-provision.service 2>&1 | tail -3
    else
        echo "  (no $DIR yet)"
    fi
}

agentpipe() {
    echo "── agent-pipe local state ──"
    if [[ -d /var/lib/mios/agent-pipe ]]; then
        find /var/lib/mios/agent-pipe -type f -print -delete
    else
        echo "  (no /var/lib/mios/agent-pipe/)"
    fi
}

audit() {
    echo "── audit + gui logs ──"
    [[ -d /var/log/mios/ai/audit ]] && \
        find /var/log/mios/ai/audit -type f -print -delete || \
        echo "  (no audit logs)"
    [[ -d /var/log/mios/gui ]] && \
        find /var/log/mios/gui -type f -print -delete || \
        echo "  (no gui logs)"
}

ttyd() {
    echo "── ttyd shell histories ──"
    if [[ -d /var/lib/mios/ttyd ]]; then
        find /var/lib/mios/ttyd -type f \
            \( -name '.bash_history' -o -name '.psreadline_history' \
               -o -name '*.history' \) -print -delete
    else
        echo "  (no /var/lib/mios/ttyd/)"
    fi
}

pycache() {
    echo "── __pycache__ trees under /usr/lib/mios ──"
    find /usr/lib/mios -type d -name __pycache__ -print -exec rm -rf {} + 2>/dev/null
    echo "  done"
}

case "$SECTION" in
    surreal)    surreal ;;
    daemon)     daemon ;;
    skills)     skills ;;
    passports)  passports ;;
    agentpipe)  agentpipe ;;
    audit)      audit ;;
    ttyd)       ttyd ;;
    pycache)    pycache ;;
    all)
        surreal
        daemon
        skills
        passports
        agentpipe
        audit
        ttyd
        pycache
        ;;
    *)  echo "unknown section: $SECTION" >&2; exit 64 ;;
esac
