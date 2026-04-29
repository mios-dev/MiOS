#!/usr/bin/env bash
# 49-finalize.sh - final cleanup, systemd preset application, image linting
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

# Apply all shipped presets now (so `systemctl is-enabled` reflects intent)
systemctl preset-all 2>/dev/null || true

# Set a safe build-time default target. Containers will reach this quickly.
# Bare-metal/VM roles will switch this to graphical.target/etc. at runtime.
systemctl set-default multi-user.target 2>/dev/null || true

# Ensure role directory exists with example config
mkdir -p /etc/mios
if [[ ! -f /etc/mios/role.conf ]]; then
    cp -a /usr/share/mios/role.conf.example /etc/mios/role.conf 2>/dev/null || true
fi

# Scrub potential credential leaks from build-time placeholder injections
log "scrubbing build-time credentials and override scripts"
rm -f /etc/containers/auth.json \
      /root/.docker/config.json \
      /root/.containers/auth.json \
      /ctx/automation/99-overrides.sh \
      /usr/local/bin/99-overrides.sh \
      /usr/bin/99-overrides.sh 2>/dev/null || true

# Trim dnf caches
dnf5 clean all || true
rm -rf /var/cache/libdnf5 /var/cache/dnf /var/log/dnf5.log* 2>/dev/null || true

# Set image metadata
MIOS_VERSION=$(cat /ctx/VERSION 2>/dev/null || echo "unknown")
echo "${MIOS_VERSION}" > /etc/mios-version
cat > /etc/mios/version <<EOF
MIOS_VERSION=${MIOS_VERSION}
MIOS_BASE=ucore-hci-stable-nvidia
MIOS_BUILT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF

log "finalize complete"
