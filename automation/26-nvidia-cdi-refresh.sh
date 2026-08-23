#!/usr/bin/env bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Configures and enables systemd units for NVIDIA CDI (Container Device Interface) auto-refresh, removes legacy...
# AI-doc: usr/share/doc/mios/manual/_harvest/automation_26_nvidia_cdi_refresh_sh.md
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

OCI_HOOK=/usr/share/containers/oci/hooks.d/oci-nvidia-hook.json
if [[ -f "$OCI_HOOK" ]]; then
    mios_log "Removing legacy OCI nvidia hook"
    rm -f "$OCI_HOOK"
fi


WANTS=/usr/lib/systemd/system/multi-user.target.wants
install -d -m 0755 "${WANTS}"

mios_log "Symlinking nvidia-cdi-refresh.path, nvidia-cdi-refresh.service, nvidia-persistenced.service into multi-user.target.wants"
for unit in \
    nvidia-cdi-refresh.path \
    nvidia-cdi-refresh.service \
    nvidia-persistenced.service
do
    if [[ -f "/usr/lib/systemd/system/${unit}" ]]; then
        ln -sf "../${unit}" "${WANTS}/${unit}"
        mios_ok "Enabled ${unit}"
    else
        mios_warn "${unit} not found, skipping enablement"
    fi
done


mios_ok "CDI refresh pipeline configured"
