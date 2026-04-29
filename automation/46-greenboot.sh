#!/usr/bin/env bash
# 46-greenboot.sh - wire greenboot services; package installs via PACKAGES.md
# (packages-updater section: greenboot, greenboot-default-health-checks).
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

# Enable core greenboot services
WANTS=/usr/lib/systemd/system/multi-user.target.wants
install -d -m 0755 "${WANTS}"

log "Enabling Greenboot services..."
for unit in \
    greenboot-healthcheck.service \
    greenboot-rpm-ostree-grub2-check-fallback.service \
    greenboot-grub2-set-counter.service \
    greenboot-grub2-set-success.service \
    greenboot-status.service \
    redboot-auto-reboot.service
do
    if [[ -f "/usr/lib/systemd/system/${unit}" ]]; then
        ln -sf "../${unit}" "${WANTS}/${unit}"
        log "Enabled ${unit}"
    else
        warn "${unit} not installed, skipping enablement."
    fi
done

# Make health-check scripts executable (shipped via )
# Directory creation and config installation moved to  overlay.
chmod +x /etc/greenboot/check/required.d/*.sh 2>/dev/null || true
chmod +x /etc/greenboot/check/wanted.d/*.sh   2>/dev/null || true
chmod +x /etc/greenboot/green.d/*.sh          2>/dev/null || true
chmod +x /etc/greenboot/red.d/*.sh            2>/dev/null || true

log "greenboot wired"
