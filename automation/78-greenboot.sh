#!/usr/bin/env bash
# MIOS_APPLY_CLASS=bake-only
# AI-hint: Enables and symlinks core greenboot systemd services (health checks, grub2 status, and auto-reboot) and sets execution bits on greenboot check scripts to ensure system health monitoring is active.
# AI-related: greenboot-healthcheck.service, greenboot-rpm-ostree-grub2-check-fallback.service, greenboot-grub2-set-counter.service, greenboot-grub2-set-success.service, greenboot-status.service, redboot-auto-reboot.service, multi-user.target
# 78-greenboot.sh - wire greenboot services; package installs via mios.toml
# [packages.updater] (greenboot, greenboot-default-health-checks).
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

# Enable core greenboot services
WANTS=/usr/lib/systemd/system/multi-user.target.wants
install -d -m 0755 "${WANTS}"

mios_log "enabling greenboot services"
for unit in \
    greenboot-healthcheck.service \
    greenboot-set-rollback-trigger.service
do
    if [[ -f "/usr/lib/systemd/system/${unit}" ]]; then
        ln -sf "../${unit}" "${WANTS}/${unit}"
        mios_ok "enabled ${unit}"
    else
        mios_warn "${unit} not installed, skipping"
    fi
done

# Make health-check scripts executable (shipped via )
# Directory creation and config installation moved to  overlay.
chmod +x /etc/greenboot/check/required.d/*.sh 2>/dev/null || true
chmod +x /etc/greenboot/check/wanted.d/*.sh   2>/dev/null || true
chmod +x /etc/greenboot/green.d/*.sh          2>/dev/null || true
chmod +x /etc/greenboot/red.d/*.sh            2>/dev/null || true

mios_ok "greenboot wired"
