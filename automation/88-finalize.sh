#!/usr/bin/env bash
# MIOS_APPLY_CLASS=bake-only
# AI-hint: Finalizes the build by applying systemd presets, setting the default boot target, scrubbing credential leaks, purging DNF caches, and generating the MiOS version metadata files in /usr/lib/mios/.
# AI-related: /usr/lib/mios/., /etc/mios/role.conf, /etc/mios/version, mios-version, graphical.target, multi-user.target
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

systemctl preset-all 2>/dev/null || true

systemctl set-default multi-user.target 2>/dev/null || true

install -d -m 0755 ${MIOS_SHARE_DIR}

mios_log "Scrubbing build-time credentials and override scripts"
rm -f /etc/containers/auth.json \
      /root/.docker/config.json \
      /root/.containers/auth.json \
      /ctx/automation/99-overrides.sh \
      /usr/local/bin/99-overrides.sh \
      /usr/bin/99-overrides.sh 2>/dev/null || true

$DNF_BIN "${DNF_SETOPT[@]}" clean all 2>/dev/null || true
rm -rf /var/cache/libdnf5 /var/cache/dnf /var/log/dnf5.log* 2>/dev/null || true

MIOS_VERSION=$(cat /ctx/VERSION 2>/dev/null || echo "Unknown")
install -d -m 0755 ${MIOS_USR_DIR}
if [[ -n "${SOURCE_DATE_EPOCH:-}" ]]; then
    MIOS_BUILT=$(date -u -d "@${SOURCE_DATE_EPOCH}" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ)
else
    MIOS_BUILT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
fi
cat > ${MIOS_USR_DIR}/version <<EOF
MIOS_VERSION=${MIOS_VERSION}
MIOS_BASE=ucore-hci-stable-nvidia
MIOS_BUILT=${MIOS_BUILT}
EOF
ln -sf ${MIOS_USR_DIR}/version ${MIOS_USR_DIR}/mios-version

OSR=/usr/lib/os-release
if command -v miosd >/dev/null 2>&1; then
    miosd finalize-osrelease --path "$OSR" --version "$MIOS_VERSION"
    mios_ok "Os-release version projected from SSOT via miosd: ${MIOS_VERSION}"
elif [[ -f "$OSR" && "$MIOS_VERSION" != "unknown" ]]; then
    for _k in VERSION VERSION_ID BUILD_ID IMAGE_VERSION OSTREE_VERSION; do
        sed -i -E "s|^${_k}=.*|${_k}=\"${MIOS_VERSION}\"|" "$OSR"
    done
    sed -i -E "s|^PRETTY_NAME=.*|PRETTY_NAME=\"MiOS ${MIOS_VERSION}\"|" "$OSR"
    sed -i -E "s|^CPE_NAME=.*|CPE_NAME=\"cpe:/o:mios-dev:mios:${MIOS_VERSION}\"|" "$OSR"
    mios_ok "Os-release version projected from SSOT: ${MIOS_VERSION}"
fi

mios_ok "Finalized"
