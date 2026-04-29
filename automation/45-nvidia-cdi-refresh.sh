#!/usr/bin/env bash
# 45-nvidia-cdi-refresh.sh - wire up NVIDIA CDI auto-refresh services.
# Package installs live in PACKAGES.md (packages-gpu-nvidia section).
#
# Key invariants:
#   - nvidia-container-toolkit ≥ 1.18 for nvidia-cdi-refresh.service/path.
#   - Avoid NCT 1.16.2: "unresolvable CDI devices" regression. Use 1.16.1 or 1.18+.
#   - Remove oci-nvidia-hook.json: dual injection with CDI causes conflicts.
#   - CDI canonical path: /var/run/cdi/nvidia.yaml (runtime) or /etc/cdi/nvidia.yaml (persistent).
#   - NVIDIA kmods blacklisted by default; 34-gpu-detect.sh removes blacklist on bare metal.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

# Remove legacy OCI hook — conflicts with CDI when both are present.
OCI_HOOK=/usr/share/containers/oci/hooks.d/oci-nvidia-hook.json
if [[ -f "$OCI_HOOK" ]]; then
    log "removing legacy OCI nvidia hook (conflicts with CDI)"
    rm -f "$OCI_HOOK"
fi

# Pin nvidia-container-toolkit version in the CDI env file.
# The systemd service reads this at boot via EnvironmentFile.
install -d -m 0755 /etc/nvidia-container-toolkit
cat >/etc/nvidia-container-toolkit/cdi-refresh.env <<'EOF'
# Managed by 45-nvidia-cdi-refresh.sh
# CDI output path — runtime location preferred by bootc (ephemeral, cleared on boot).
CDI_OUTPUT_PATH=/var/run/cdi/nvidia.yaml
# Debug logging — set to 1 for troubleshooting.
NVIDIA_CTK_DEBUG=0
EOF
chmod 0644 /etc/nvidia-container-toolkit/cdi-refresh.env

# Enable units using build-safe symlinks
WANTS=/usr/lib/systemd/system/multi-user.target.wants
install -d -m 0755 "${WANTS}"

log "Enabling NVIDIA CDI units..."
for unit in \
    nvidia-cdi-refresh.path \
    nvidia-cdi-refresh.service \
    nvidia-persistenced.service \
    mios-nvidia-cdi.service
do
    if [[ -f "/usr/lib/systemd/system/${unit}" ]]; then
        ln -sf "../${unit}" "${WANTS}/${unit}"
        log "Enabled ${unit}"
    else
        warn "${unit} not found, skipping enablement."
    fi
done

# Ensure CDI persistent dir exists; tmpfiles.d/mios-gpu.conf creates the runtime dir.
install -d -m 0755 /etc/cdi

log "CDI refresh pipeline configured"
