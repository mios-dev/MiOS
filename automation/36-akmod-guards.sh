#!/usr/bin/env bash
# ============================================================================
# automation/36-akmod-guards.sh - MiOS v0.1.4
# ----------------------------------------------------------------------------
# Install ExecCondition drop-ins that make NVIDIA systemd units exit cleanly
# (skipped, not failed) when the running kernel's nvidia module has not yet
# been registered by akmods/depmod. Build-time script; does not touch runtime.
#
# Regex widened beyond NVIDIA/nvidia-container-toolkit#1395 to match:
#   - kernel/drivers/... paths (negativo17 packaging)
#   - extra/nvidia/...    paths (RPM Fusion akmod packaging, used by ucore-hci)
#   - .ko, .ko.xz, .ko.zst compressed variants
# ============================================================================
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

log "36-akmod-guards: installing ExecCondition drop-ins"

SERVICES=(
    nvidia-persistenced
    nvidia-powerd
    nvidia-suspend
    nvidia-resume
    nvidia-hibernate
    nvidia-suspend-then-hibernate
    nvidia-cdi-refresh
)

DROPIN_NAME="10-mios-akmod-guard.conf"
count=0

for svc in "${SERVICES[@]}"; do
    dir="/usr/lib/systemd/system/${svc}.service.d"
    path="${dir}/${DROPIN_NAME}"
    install -d -m 0755 "${dir}"
    cat > "${path}" <<'EOF'
# MiOS v0.1.4 akmod-guard
# Skip unit if akmods has not yet registered the nvidia kernel module
# for the currently running kernel. ExecCondition is additive (AND
# semantics per systemd.service(5)), so this composes safely with any
# future upstream guard. Ref: NVIDIA/nvidia-container-toolkit#1395
# NOTE: \\\\ in this heredoc → \\ in file → systemd strips one backslash
# → grep sees \. (literal-dot escape). Plain \\. triggered SC "unknown
# escape sequence" warnings in systemd 259+ and could mis-match.
[Service]
ExecCondition=/bin/bash -c 'grep -Eq "(^|/)nvidia\\.ko(\\.[xz]z|\\.zst)?:" /lib/modules/$(uname -r)/modules.dep'
EOF
    chmod 0644 "${path}"
    count=$((count + 1))
    log "  installed ${path}"
done

log "36-akmod-guards: done (${count} drop-ins)"
