#!/usr/bin/env bash
# MIOS_APPLY_CLASS=dev-only
# AI-hint: Configures Hyper-V GPU-PV (dxgkrnl) support by creating mount points, ld.so.conf entries, and a systemd service to detect and bridge host-side GPU drivers for Mesa D3D12 and NVIDIA CUDA.
# AI-related: mios-gpu-pv, mios-gpu-pv-detect, mios-gpu-pv-detect.service, display-manager.service, local-fs.target, multi-user.target
# AI-functions: log
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

mios_log "GPU-PV shim dirs"
mkdir -p /usr/lib/wsl/lib
mkdir -p /usr/lib/wsl/drivers

mios_log "Ld.so.conf paths"
install -d -m 0755 /usr/lib/ld.so.conf.d
echo "/usr/lib/wsl/lib" > /usr/lib/ld.so.conf.d/mios-gpu-pv.conf

mkdir -p ${MIOS_LIBEXEC_DIR}
cat > ${MIOS_LIBEXEC_DIR}/gpu-pv-detect <<'EOF'
set -euo pipefail
log() { echo "[gpu-pv-detect] $*"; }

if [ ! -e /dev/dxg ]; then
    exit 0
fi

log "/dev/dxg present"
if [ -z "$(ls -A /usr/lib/wsl/lib)" ]; then
    log "HINT: /usr/lib/wsl/lib is empty. GPU acceleration requires host drivers"
    log "HINT: Copy drivers from Windows: C:\Windows\System32\lxss\lib -> /usr/lib/wsl/lib"
fi
EOF

chmod +x ${MIOS_LIBEXEC_DIR}/gpu-pv-detect

cat > /usr/lib/systemd/system/mios-gpu-pv-detect.service <<EOF
[Unit]
Description='MiOS' Hyper-V GPU-PV Detection
ConditionVirtualization=microsoft
After=local-fs.target
Before=display-manager.service

[Service]
Type=oneshot
ExecStart=${MIOS_LIBEXEC_DIR}/gpu-pv-detect
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

mios_log "Enable gpu-pv-detect service"
WANTS=/usr/lib/systemd/system/multi-user.target.wants
install -d -m 0755 "${WANTS}"
ln -sf ../mios-gpu-pv-detect.service "${WANTS}/mios-gpu-pv-detect.service"

mios_ok "GPU-PV shim installed: /usr/lib/wsl/{lib,drivers}, ld.so.conf.d/mios-gpu-pv.conf, mios-gpu-pv-detect.service enabled"
