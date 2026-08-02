#!/usr/bin/env bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Configures GPU passthrough by symlinking systemd unit files for NVIDIA/AMD/Intel drivers into the multi-user.target.wants directory and enabling the container_use_devices SELinux boolean.
# AI-related: mios-gpu-status, mios-gpu-nvidia, mios-gpu-amd, mios-gpu-intel, multi-user.target, mios-gpu-status.service, mios-gpu-nvidia.service, mios-gpu-amd.service, mios-gpu-intel.service
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

mios_log "Enabling GPU passthrough services"

WANTS=/usr/lib/systemd/system/multi-user.target.wants
install -d -m 0755 "${WANTS}"

for svc in mios-gpu-status.service mios-gpu-nvidia.service mios-gpu-amd.service mios-gpu-intel.service; do
  if [[ -f "/usr/lib/systemd/system/${svc}" ]]; then
    ln -sf "../${svc}" "${WANTS}/${svc}"
    mios_ok "Enabled ${svc}"
  else
    mios_warn "${svc} missing from /usr/lib/systemd/system/"
  fi
done

if [[ -f /usr/lib/systemd/system/nvidia-cdi-refresh.path ]]; then
  ln -sf ../nvidia-cdi-refresh.path "${WANTS}/nvidia-cdi-refresh.path"
  mios_ok "Enabled nvidia-cdi-refresh.path"
fi

if command -v semanage >/dev/null 2>&1 && [[ -d /etc/selinux/targeted ]]; then
  if semanage boolean -m --on container_use_devices 2>/dev/null; then
    mios_ok "SELinux boolean container_use_devices persisted"
  else
    mios_skip "semanage not operational; runtime service handles it"
  fi
fi

mios_ok "GPU passthrough units symlinked into multi-user.target.wants"
