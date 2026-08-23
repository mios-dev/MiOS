#!/usr/bin/env bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Configures the dynamic PostgreSQL-to-OS user account sync service, enabling live account mappings without the packag...
# AI-doc: usr/share/doc/mios/manual/automation.md
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

source "$(dirname "$0")/lib/common.sh"

mios_log "PostgreSQL account sync service"

install -d -m 0755 /usr/libexec/mios/
install -m 0755 "$(dirname "$0")/../usr/libexec/mios/mios-account-sync" /usr/libexec/mios/mios-account-sync
install -m 0755 "$(dirname "$0")/../usr/libexec/mios/mios-userdb-render" /usr/libexec/mios/mios-userdb-render

install -d -m 0755 /usr/lib/systemd/system/
install -m 0644 "$(dirname "$0")/../usr/lib/systemd/system/mios-account-sync.service" /usr/lib/systemd/system/mios-account-sync.service
install -m 0644 "$(dirname "$0")/../usr/lib/systemd/system/mios-userdb-render.service" /usr/lib/systemd/system/mios-userdb-render.service

rm -f /etc/nss-pgsql.conf /etc/nss-pgsql-root.conf /etc/pam_pgsql.conf

if [ -f /etc/nsswitch.conf ]; then
    sed -i 's/ pgsql//g' /etc/nsswitch.conf
fi

for f in /etc/pam.d/system-auth /etc/pam.d/password-auth; do
    if [ -f "$f" ]; then
        sed -i '/pam_pgsql.so/d' "$f"
    fi
done

if [[ "${MIOS_ACCOUNTS_DB_BACKED:-false}" =~ ^(true|1|yes)$ ]]; then
    mios_log "Enable account-sync daemon & userdb-render"
    systemctl enable mios-account-sync.service || true
    systemctl enable mios-userdb-render.service || true
else
    mios_skip "account sync flag-gated off (db_backed=false)"
    systemctl disable mios-account-sync.service || true
    systemctl disable mios-userdb-render.service || true
fi
