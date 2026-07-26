#!/usr/bin/env bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Configures the dynamic PostgreSQL-to-OS user account sync service, enabling live account mappings without the packaging-restricted NSS/PAM pgsql modules.
# AI-related: 11-user.sh, schema-init.sql, mios-account-sync.service
# 'MiOS' - 17-accounts-db: PostgreSQL account synchronization setup
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

mios_log "PostgreSQL account sync service"

# Install account-sync executable to system path
install -d -m 0755 /usr/libexec/mios/
install -m 0755 "$(dirname "$0")/../usr/libexec/mios/mios-account-sync" /usr/libexec/mios/mios-account-sync

# Install systemd service unit
install -d -m 0755 /usr/lib/systemd/system/
install -m 0644 "$(dirname "$0")/../usr/lib/systemd/system/mios-account-sync.service" /usr/lib/systemd/system/mios-account-sync.service

# Clean up legacy libnss-pgsql and pam_pgsql configs if they exist
rm -f /etc/nss-pgsql.conf /etc/nss-pgsql-root.conf /etc/pam_pgsql.conf

# Revert nsswitch.conf changes if they were previously written
if [ -f /etc/nsswitch.conf ]; then
    sed -i 's/ pgsql//g' /etc/nsswitch.conf
fi

# Revert PAM system-auth/password-auth pgsql inserts if previously written
for f in /etc/pam.d/system-auth /etc/pam.d/password-auth; do
    if [ -f "$f" ]; then
        sed -i '/pam_pgsql.so/d' "$f"
    fi
done

if [[ "${MIOS_ACCOUNTS_DB_BACKED:-false}" =~ ^(true|1|yes)$ ]]; then
    mios_log "enable account-sync daemon"
    systemctl enable mios-account-sync.service || true
else
    mios_skip "account sync flag-gated off (db_backed=false)"
    systemctl disable mios-account-sync.service || true
fi
