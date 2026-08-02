#!/usr/bin/env bash
# MIOS_APPLY_CLASS=dev-only
# AI-hint: Configures Podman machine backend compatibility by ensuring the 'core' user exists via sysusers and symlinking essential systemd units like podman.socket and qemu-guest-agent.service for container runtime support.
# AI-related: podman.socket, qemu-guest-agent.service, sshd.service, cloud-init.service, cloud-final.service, multi-user.target
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

mios_log "Hardware groups pre-created globally by 11-user.sh"

systemd-sysusers --root=/ 2>/dev/null || true

if id -u core >/dev/null 2>&1; then
    passwd -l core 2>/dev/null || true
    mios_ok "User 'core' initialized"
else
    mios_warn "Failed to initialize 'core' user via sysusers"
fi

WANTS=/usr/lib/systemd/system/multi-user.target.wants
install -d -m 0755 "${WANTS}"

mios_log "Symlink units into multi-user.target.wants"
for unit in \
    sshd.service \
    podman.socket \
    qemu-guest-agent.service \
    cloud-init.service \
    cloud-final.service
do
    if [[ -f "/usr/lib/systemd/system/${unit}" ]]; then
        ln -sf "../${unit}" "${WANTS}/${unit}"
        mios_ok "Enabled ${unit}"
    else
        mios_warn "${unit} not found, skipping"
    fi
done

mios_ok "Podman-machine compatibility wired"
