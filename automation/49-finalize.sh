#!/usr/bin/env bash
# 49-finalize.sh - final cleanup, systemd preset application, image linting
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

# Apply all shipped presets now (so `systemctl is-enabled` reflects intent)
systemctl preset-all 2>/dev/null || true

# Set a safe build-time default target. Containers will reach this quickly.
# Bare-metal/VM roles will switch this to graphical.target/etc. at runtime.
systemctl set-default multi-user.target 2>/dev/null || true

# LAW 4: /etc/mios is for Day-2 admin overrides and is created by tmpfiles.d at boot.
# Stage the example role.conf in /usr/share/mios/ so tmpfiles.d can seed it
# to /etc/mios/role.conf on first boot via the C (copy-if-missing) directive.
install -d -m 0755 ${MIOS_SHARE_DIR}

# Scrub potential credential leaks from build-time placeholder injections
log "scrubbing build-time credentials and override scripts"
rm -f /etc/containers/auth.json \
      /root/.docker/config.json \
      /root/.containers/auth.json \
      /ctx/automation/99-overrides.sh \
      /usr/local/bin/99-overrides.sh \
      /usr/bin/99-overrides.sh 2>/dev/null || true

# Trim dnf caches
$DNF_BIN "${DNF_SETOPT[@]}" clean all 2>/dev/null || true
rm -rf /var/cache/libdnf5 /var/cache/dnf /var/log/dnf5.log* 2>/dev/null || true

# Set image metadata — LAW 4: write to /usr/lib/mios/, not /etc/
# /etc/mios-version and /etc/mios/version are Day-2 admin paths.
MIOS_VERSION=$(cat /ctx/VERSION 2>/dev/null || echo "unknown")
install -d -m 0755 ${MIOS_USR_DIR}
cat > ${MIOS_USR_DIR}/version <<EOF
MIOS_VERSION=${MIOS_VERSION}
MIOS_BASE=ucore-hci-stable-nvidia
MIOS_BUILT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF
ln -sf ${MIOS_USR_DIR}/version ${MIOS_USR_DIR}/mios-version

log "finalize complete"
