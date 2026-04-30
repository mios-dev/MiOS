#!/usr/bin/env bash
# ============================================================================
# MiOS v0.2.0 - 35-gpu-passthrough.sh
# ----------------------------------------------------------------------------
# Manages systemd unit enablement and SELinux for GPU passthrough.
#
# v0.2.0: ARCHITECTURAL PURITY FIX. All files (systemd units, udev rules,
#         sysusers, kargs.d) are now delivered via the system_files overlay.
#         This script no longer performs 'install' commands; it only handles
#         symlinking and SELinux booleans.
#
# Runs AFTER 34-gpu-detect.sh and 08-system-files-overlay.sh.
# ============================================================================
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

log "Enabling GPU passthrough services"

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
    log "Enabled ${svc}"
  else
    log "WARN: ${svc} missing from /usr/lib/systemd/system/ — skipping"
  fi
done

# Enable the upstream NVIDIA path unit where the toolkit shipped it.
if [[ -f /usr/lib/systemd/system/nvidia-cdi-refresh.path ]]; then
  ln -sf ../nvidia-cdi-refresh.path "${WANTS}/nvidia-cdi-refresh.path"
  log "Enabled nvidia-cdi-refresh.path"
fi

# ----------------------------------------------------------------------------
# SELinux: enable container_use_devices boolean so containers can touch
# /dev/kfd and /dev/dri with the default container_t domain. This is the
# minimal-privilege path for AMD/Intel compute - NOT container_runtime_t.
# ----------------------------------------------------------------------------
if command -v semanage >/dev/null 2>&1 && [[ -d /etc/selinux/targeted ]]; then
  if semanage boolean -m --on container_use_devices 2>/dev/null; then
    log "SELinux boolean container_use_devices persisted at build time"
  else
    log "semanage not operational in build; runtime service will handle it"
  fi
fi

log "GPU passthrough services enabled successfully"
