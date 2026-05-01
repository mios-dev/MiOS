#!/usr/bin/env bash
# automation/35-gpu-pv-shim.sh - MiOS v0.2.0
# ----------------------------------------------------------------------------
# Automates guest-side shimming for Hyper-V GPU-PV (dxgkrnl).
# Since dxgkrnl isn't mainlined yet, we provide the user-mode hooks
# to bridge to host drivers mounted via WSL/Hyper-V.
#
# v0.2.0: Refactored to use common logging and build-safe symlinks.
# ----------------------------------------------------------------------------
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

# 1. Create the system-standard mount points for dxgkrnl/WSL hooks
# These are the locations where Mesa D3D12 and NVIDIA CUDA look for Hyper-V host drivers.
log "Creating GPU-PV shim directory structure..."
mkdir -p /usr/lib/wsl/lib
mkdir -p /usr/lib/wsl/drivers

# 2. Add ld.so.conf entry to ensure these libraries are in the search path
# LAW 4: write to /usr/lib/ld.so.conf.d — /etc/ld.so.conf.d is for Day-2 admin overrides only
log "Configuring dynamic linker paths for GPU-PV..."
install -d -m 0755 /usr/lib/ld.so.conf.d
echo "/usr/lib/wsl/lib" > /usr/lib/ld.so.conf.d/mios-gpu-pv.conf

# 3. Create a detection script for first-boot or deployment
mkdir -p /usr/libexec/mios
cat > /usr/libexec/mios/gpu-pv-detect <<'EOF'
#!/usr/bin/bash
set -euo pipefail
log() { echo "[gpu-pv-detect] $*"; }

if [ ! -e /dev/dxg ]; then
    # log "Hyper-V /dev/dxg not found. Skipping GPU-PV library hooks."
    exit 0
fi

log "Hyper-V dxgkrnl detected!"
if [ -z "$(ls -A /usr/lib/wsl/lib)" ]; then
    log "HINT: /usr/lib/wsl/lib is empty. GPU acceleration requires host drivers."
    log "HINT: Copy drivers from Windows: C:\Windows\System32\lxss\lib -> /usr/lib/wsl/lib"
fi
EOF

chmod +x /usr/libexec/mios/gpu-pv-detect

# 4. Create a systemd service to run the detection/setup on boot
cat > /usr/lib/systemd/system/mios-gpu-pv-detect.service <<EOF
[Unit]
Description=MiOS Hyper-V GPU-PV Detection
ConditionVirtualization=microsoft
After=local-fs.target
Before=display-manager.service

[Service]
Type=oneshot
ExecStart=/usr/libexec/mios/gpu-pv-detect
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

# 5. Enable the service using a build-safe symlink
# See 35-gpu-passthrough.sh for detailed explanation.
log "Enabling GPU-PV detection service..."
WANTS=/usr/lib/systemd/system/multi-user.target.wants
install -d -m 0755 "${WANTS}"
ln -sf ../mios-gpu-pv-detect.service "${WANTS}/mios-gpu-pv-detect.service"

log "GPU-PV shim integration complete."
