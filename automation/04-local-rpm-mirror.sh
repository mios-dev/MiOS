#!/usr/bin/env bash
# AI-hint: Configures local RPM mirror repos for DNF when offline build mode is requested or vendored mirror is present.
# AI-related: usr/share/mios/mios.toml [offline], build.sh

set -euo pipefail

source "$(dirname "$0")/lib/common.sh" 2>/dev/null || {
    printf '[MiOS Offline] WARN: lib/common.sh unavailable -- skipping\n' >&2
    exit 0
}

MIRROR_DIR="${MIOS_RPM_MIRROR_DIR:-/usr/share/mios/vendored/rpm-mirror}"
OFFLINE_BUILD="${MIOS_OFFLINE_BUILD:-0}"

if [[ "$OFFLINE_BUILD" == "1" ]] || [[ -d "$MIRROR_DIR" ]]; then
    mios_log "Configuring local DNF RPM mirror from $MIRROR_DIR"
    mkdir -p /etc/yum.repos.d/
    cat > /etc/yum.repos.d/mios-local-mirror.repo <<EOF
[mios-local-mirror]
name=MiOS Local RPM Mirror
baseurl=file://${MIRROR_DIR}
enabled=1
gpgcheck=0
priority=1
EOF
    mios_ok "Local DNF RPM mirror configured"
else
    mios_log "Offline RPM mirror not active"
fi
