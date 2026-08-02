#!/usr/bin/env bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Enables core MiOS systemd units (mios-role.service and mios-podman-gc.timer) by creating symlinks in multi-user.target.wants to ensure the Unified Role Engine and podman garbage collection are active.
# AI-related: /usr/libexec/mios/role-apply, mios-role, mios-podman-gc, mios-role.service, mios-podman-gc.timer, multi-user.target
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

mios_log "Symlinking mios-role.service, mios-podman-gc.timer, mios-webtools-firstboot.service into multi-user.target.wants"

WANTS=/usr/lib/systemd/system/multi-user.target.wants
install -d -m 0755 "${WANTS}"

for unit in \
    mios-role.service \
    mios-podman-gc.timer \
    mios-webtools-firstboot.service
do
    if [[ -f "/usr/lib/systemd/system/${unit}" ]]; then
        ln -sf "../${unit}" "${WANTS}/${unit}"
        mios_ok "Enabled ${unit}"
    else
        mios_warn "${unit} not found, skipping enablement"
    fi
done

mios_ok "Mios-role/podman-gc/webtools-firstboot units enabled via multi-user.target.wants symlinks"
