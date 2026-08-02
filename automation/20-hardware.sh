#!/bin/bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Configures GPU drivers by installing Mesa, AMD ROCm, and Intel compute runtimes, while performing a multi-stage check and fallback logic for NVIDIA kernel modules based on the current kernel version.
# AI-related: mios-kver
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/packages.sh"

KVER=$(cat /tmp/mios-kver 2>/dev/null || find /lib/modules/ -mindepth 1 -maxdepth 1 -printf "%f\n" | sort -V | tail -1)

mios_log "Install Mesa GPU stack"
install_packages_strict "gpu-mesa"

mios_log "Install ROCm"
install_packages "gpu-amd-compute"

mios_log "Install Intel compute runtime"
install_packages "gpu-intel-compute" || true

mios_log "Check NVIDIA modules from ucore base"

NVIDIA_PRESENT=0
if [[ -d "/lib/modules/$KVER/extra/nvidia" ]] || \
   [[ -d "/lib/modules/$KVER/extra/nvidia-open" ]] || \
   modinfo nvidia -k "$KVER" &>/dev/null; then
    mios_ok "NVIDIA kmod present for kernel $KVER"
    NVIDIA_PRESENT=1
fi

if [[ $NVIDIA_PRESENT -eq 0 ]]; then
    mios_log "Fallback: akmod-nvidia build against $KVER"
    if install_packages "gpu-nvidia"; then
        if command -v akmods &>/dev/null; then
            akmods --force --kernels "$KVER" 2>&1 | tail -10 || true
            if modinfo nvidia -k "$KVER" &>/dev/null; then
                mios_ok "NVIDIA kmod rebuilt via akmods for $KVER"
                NVIDIA_PRESENT=1
            fi
        fi
    fi
fi

if [[ $NVIDIA_PRESENT -eq 0 ]]; then
    mios_warn "No NVIDIA kmod for $KVER after all fallback attempts"
    mios_warn "Image will ship without NVIDIA acceleration. Users with"
    mios_warn "NVIDIA hardware can rebuild the kmod at runtime:"
    mios_warn "Sudo dnf install kernel-devel-\$ akmod-nvidia"
    mios_warn "Sudo akmods"
fi

if command -v nvidia-ctk &>/dev/null; then
    nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml 2>/dev/null || true
    mios_ok "NVIDIA CDI spec generated"
fi


mios_ok "GPU stack: Mesa + AMD ROCm + Intel installed; NVIDIA kmod present=$NVIDIA_PRESENT"
