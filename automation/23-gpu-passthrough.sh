#!/usr/bin/env bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Configures GPU passthrough by symlinking systemd unit files for NVIDIA/AMD/Intel drivers into the multi-user.target.wants directory and enabling the container_use_devices SELinux boolean.
# AI-related: mios-gpu-status, mios-gpu-nvidia, mios-gpu-amd, mios-gpu-intel, multi-user.target, mios-gpu-status.service, mios-gpu-nvidia.service, mios-gpu-amd.service, mios-gpu-intel.service
# ============================================================================
# 'MiOS' - 23-gpu-passthrough.sh
# ----------------------------------------------------------------------------
# Manages systemd unit enablement and SELinux for GPU passthrough.
#
# : ARCHITECTURAL PURITY FIX. All files (systemd units, udev rules,
#         sysusers, kargs.d) are now delivered via the system_files overlay.
#         This script no longer performs 'install' commands; it only handles
#         symlinking and SELinux booleans.
#
# Runs AFTER 34-gpu-detect.sh and 01-system-files-overlay.sh.
# ============================================================================
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

mios_log "enabling GPU passthrough services"

# ----------------------------------------------------------------------------
# Enable units via symlink (Containerfile-safe; `systemctl enable` cannot run
# in a bootc build because there is no PID 1 / dbus during image assembly).
# ----------------------------------------------------------------------------
WANTS=/usr/lib/systemd/system/multi-user.target.wants
install -d -m 0755 "${WANTS}"

# These files are already installed in /usr/lib/systemd/system/ via overlay
for svc in mios-gpu-status.service mios-gpu-nvidia.service mios-gpu-amd.service mios-gpu-intel.service; do
  if [[ -f "/usr/lib/systemd/system/${svc}" ]]; then
    ln -sf "../${svc}" "${WANTS}/${svc}"
    mios_ok "enabled ${svc}"
  else
    mios_warn "${svc} missing from /usr/lib/systemd/system/ -- skipping"
  fi
done

# Enable the upstream NVIDIA path unit where the toolkit shipped it.
if [[ -f /usr/lib/systemd/system/nvidia-cdi-refresh.path ]]; then
  ln -sf ../nvidia-cdi-refresh.path "${WANTS}/nvidia-cdi-refresh.path"
  mios_ok "enabled nvidia-cdi-refresh.path"
fi

# ----------------------------------------------------------------------------
# SELinux: enable container_use_devices boolean so containers can touch
# /dev/kfd and /dev/dri with the default container_t domain. This is the
# minimal-privilege path for AMD/Intel compute - NOT container_runtime_t.
# ----------------------------------------------------------------------------
if command -v semanage >/dev/null 2>&1 && [[ -d /etc/selinux/targeted ]]; then
  if semanage boolean -m --on container_use_devices 2>/dev/null; then
    mios_ok "SELinux boolean container_use_devices persisted"
  else
    mios_skip "semanage not operational; runtime service handles it"
  fi
fi

mios_ok "GPU passthrough units symlinked into multi-user.target.wants"
