#!/usr/bin/env bash
# MIOS_APPLY_CLASS=bake-only
# AI-hint: Enables and symlinks core greenboot systemd services (health checks, grub2 status, and auto-reboot) and sets execution...
# AI-doc: usr/share/doc/mios/manual/_harvest/automation_78_greenboot_sh.md
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

WANTS=/usr/lib/systemd/system/multi-user.target.wants
install -d -m 0755 "${WANTS}"

mios_log "Enabling greenboot services"
for unit in \
    greenboot-healthcheck.service \
    greenboot-set-rollback-trigger.service
do
    if [[ -f "/usr/lib/systemd/system/${unit}" ]]; then
        ln -sf "../${unit}" "${WANTS}/${unit}"
        mios_ok "Enabled ${unit}"
    else
        mios_warn "${unit} not installed, skipping"
    fi
done

chmod +x /etc/greenboot/check/required.d/*.sh 2>/dev/null || true
chmod +x /etc/greenboot/check/wanted.d/*.sh   2>/dev/null || true
chmod +x /etc/greenboot/green.d/*.sh          2>/dev/null || true
chmod +x /etc/greenboot/red.d/*.sh            2>/dev/null || true

mios_ok "Greenboot wired"
