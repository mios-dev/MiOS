#!/usr/bin/env bash
# 47-hardening.sh - enable hardening services (USBGuard, auditd).
# Package installs moved to mios.toml [packages.security].
# sysctl drop-in shipped via usr/lib/sysctl.d/99-mios-hardening.conf.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

# USBGuard config is at /usr/lib/usbguard/usbguard-daemon.conf (managed via overlay).
chmod 0600 /usr/lib/usbguard/usbguard-daemon.conf 2>/dev/null || true

# Enable hardening services using build-safe symlinks
WANTS=/usr/lib/systemd/system/multi-user.target.wants
install -d -m 0755 "${WANTS}"

log "Enabling hardening services..."
for unit in \
    usbguard.service \
    auditd.service \
    fapolicyd.service
do
    if [[ -f "/usr/lib/systemd/system/${unit}" ]]; then
        ln -sf "../${unit}" "${WANTS}/${unit}"
        log "Enabled ${unit}"
    else
        warn "${unit} not installed, skipping enablement."
    fi
done

# Pre-generate fapolicyd trust database for bootc systems
# fapolicyd config is at /usr/lib/fapolicyd/fapolicyd.conf (managed via overlay).
if command -v fagenrules &>/dev/null; then
    log "Pre-generating fapolicyd trust database..."
    # Ensure correct permissions for the fapolicyd directory
    chown -R fapolicyd:fapolicyd /etc/fapolicyd 2>/dev/null || true
    fagenrules --load 2>/dev/null || true
    fapolicyd-cli --update 2>/dev/null || true
fi

log "hardening services wired"