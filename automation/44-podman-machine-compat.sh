#!/usr/bin/env bash
# 44-podman-machine-compat.sh - Podman-machine backend compatibility.
# Package installs moved to mios.toml [packages.containers] / [packages.utils].
# This script only does the runtime config that cannot be expressed as packages:
#   - create the 'core' user (Podman machine convention)
#   - enable services needed for machine backend operation
#
# v0.2.0 fix:
#   - Pre-create the `video`, `render`, `kvm`, `libvirt` groups if missing so
#     useradd -G doesn't die with "group does not exist". The ucore-hci base
#     ships udev rules that create these groups dynamically at runtime, but
#     during the image build they're absent.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

log "Hardware groups are pre-created globally by 31-user.sh"

# Create the 'core' user if missing (Podman machine convention).
# Managed via /usr/lib/sysusers.d/20-podman-machine.conf (declarative).
# We apply sysusers here to ensure 'core' exists for any subsequent operations.
systemd-sysusers --root=/ 2>/dev/null || true

if id -u core >/dev/null 2>&1; then
    passwd -l core 2>/dev/null || true
    log "user 'core' initialized (declarative; key-auth only)"
else
    warn "Failed to initialize 'core' user via sysusers"
fi

# Enable core services for Podman-machine and cloud-init entry
WANTS=/usr/lib/systemd/system/multi-user.target.wants
install -d -m 0755 "${WANTS}"

log "Enabling Podman Machine and cloud-init services..."
for unit in \
    sshd.service \
    podman.socket \
    qemu-guest-agent.service \
    cloud-init.service \
    cloud-final.service
do
    if [[ -f "/usr/lib/systemd/system/${unit}" ]]; then
        ln -sf "../${unit}" "${WANTS}/${unit}"
        log "Enabled ${unit}"
    else
        warn "${unit} not found, skipping enablement."
    fi
done

log "podman-machine compatibility wired"
