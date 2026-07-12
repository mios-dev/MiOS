#!/bin/bash
# AI-hint: Executes targeted Day-0 cleanup of PostgreSQL/pgvector tables, daemon states, skills catalogs, agent passports, and audit logs to purge persistent state when standard cache clearing is insufficient.
# AI-related: mios-cache-clear, mios-daemon, mios-skills-miner, mios-passport-provision, mios-skills-miner.timer, mios-passport-provision.service
# AI-functions: pgvector, daemon, skills, passports, agentpipe, audit, ttyd, pycache
# Day-0 readiness: surfaces NOT covered by mios-cache-clear.
# Run via: wsl.exe ... bash /mnt/c/MiOS/automation/support/day0-extras.sh <section>
# Sections: pgvector | daemon | skills | passports | agentpipe | audit | ttyd | pycache | all
set -euo pipefail
SECTION="${1:-all}"

pgvector() {
    echo "── PostgreSQL/pgvector row-level wipe (schema preserved) ──"
    local TABLES="knowledge agent_memory event tool_call session skill skill_invocation sys_env pending_action run_template scratch kanban app_install alias resolves_to directory_entry log_digest person agent_keypair mios_rag"
    for t in $TABLES; do
        if /usr/libexec/mios/mios-db --pg "TRUNCATE TABLE $t RESTART IDENTITY CASCADE;" >/dev/null 2>&1; then
            printf '  200  TRUNCATE %s\n' "$t"
        else
            printf '  500  TRUNCATE %s FAILED\n' "$t"
        fi
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
    pgvector)   pgvector ;;
    daemon)     daemon ;;
    skills)     skills ;;
    passports)  passports ;;
    agentpipe)  agentpipe ;;
    audit)      audit ;;
    ttyd)       ttyd ;;
    pycache)    pycache ;;
    all)
        pgvector
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
