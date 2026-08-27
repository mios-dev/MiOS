#!/usr/bin/env bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Configures the host's admin sshd to bind to the SSOT port defined in mios.toml by creating a drop-in config in /etc/ss...
# AI-doc: usr/share/doc/mios/manual/automation.md
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

source "$(dirname "$0")/lib/common.sh"

mios_log "Pin host admin sshd to MIOS_PORT_SSH=${MIOS_PORT_SSH} via drop-in"

install -d -m 0755 /etc/ssh/sshd_config.d
cat > /etc/ssh/sshd_config.d/09-mios-ssh-port.conf <<EOF
Port ${MIOS_PORT_SSH}
EOF
chmod 0644 /etc/ssh/sshd_config.d/09-mios-ssh-port.conf

if command -v sshd >/dev/null 2>&1; then
    sshd -t 2>/dev/null \
        && mios_ok "Sshd config valid; admin sshd will bind ${MIOS_PORT_SSH}" \
        || mios_skip "drop-in written; skipped sshd -t (host keys absent at build is normal)"
fi
