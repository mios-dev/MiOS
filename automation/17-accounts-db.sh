#!/usr/bin/env bash
# AI-hint: Configures libnss-pgsql2 and pam_pgsql when [accounts].db_backed is enabled, enabling live PostgreSQL-backed system accounts with dynamic PAM system-auth and password-auth overrides.
# AI-related: 31-user.sh, schema-init.sql, /etc/nsswitch.conf
# 'MiOS' v0.2.4 -- 17-accounts-db: PostgreSQL NSS + PAM account system
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

log "Configuring PostgreSQL NSS + PAM account system"

# NSS-pgsql configuration files
cat <<'EOF' > /etc/nss-pgsql.conf
connectionstring = host=127.0.0.1 port=@PGPORT@ dbname=mios user=mios connect_timeout=2
getpwnam = SELECT name, 'x', uid, gid, display, '/var/home/' || name, '/bin/bash' FROM account WHERE name = $1 AND enabled = true AND (os_targets = 'both' OR os_targets = 'linux')
getpwuid = SELECT name, 'x', uid, gid, display, '/var/home/' || name, '/bin/bash' FROM account WHERE uid = $1 AND enabled = true AND (os_targets = 'both' OR os_targets = 'linux')
getpwent = SELECT name, 'x', uid, gid, display, '/var/home/' || name, '/bin/bash' FROM account WHERE enabled = true AND (os_targets = 'both' OR os_targets = 'linux')
getgrnam = SELECT name, '*', gid FROM account WHERE name = $1 AND enabled = true
getgrgid = SELECT name, '*', gid FROM account WHERE gid = $1 AND enabled = true
getgrent = SELECT name, '*', gid FROM account WHERE enabled = true
getgroupmembersbygid = SELECT name FROM account WHERE gid = $1 AND enabled = true
EOF

cat <<'EOF' > /etc/nss-pgsql-root.conf
shadowconnectionstring = host=127.0.0.1 port=@PGPORT@ dbname=mios user=mios connect_timeout=2
shadowbyname = SELECT name, password_hash, -1, -1, -1, -1, -1, -1, 0 FROM account WHERE name = $1 AND enabled = true AND (os_targets = 'both' OR os_targets = 'linux')
shadowbyuid = SELECT name, password_hash, -1, -1, -1, -1, -1, -1, 0 FROM account WHERE uid = $1 AND enabled = true AND (os_targets = 'both' OR os_targets = 'linux')
shadowent = SELECT name, password_hash, -1, -1, -1, -1, -1, -1, 0 FROM account WHERE enabled = true AND (os_targets = 'both' OR os_targets = 'linux')
EOF

# PAM-pgsql configuration file
cat <<'EOF' > /etc/pam_pgsql.conf
connect = host=127.0.0.1 port=@PGPORT@ dbname=mios user=mios connect_timeout=2
table = account
user_column = name
pwd_column = password_hash
expired_column = (CASE WHEN enabled = true THEN 0 ELSE 1 END)
debug = 1
EOF

# Resolve the pgvector port from the SSOT ([ports].pgvector, bridged to
# MIOS_PORT_PGVECTOR by userenv.sh). The connection strings above are written
# with an @PGPORT@ placeholder because the heredocs are single-quoted (no
# expansion, so the SQL's $1 / || survive). Without this, libpq defaults to
# 5432 while MiOS runs postgres on 8432 -> every DB-backed getent/login stalls
# on connect_timeout and silently falls through to files.
_pgport="${MIOS_PORT_PGVECTOR:-8432}"
sed -i "s/@PGPORT@/${_pgport}/g" /etc/nss-pgsql.conf /etc/nss-pgsql-root.conf /etc/pam_pgsql.conf

# Set secure permissions
chmod 600 /etc/nss-pgsql.conf /etc/nss-pgsql-root.conf /etc/pam_pgsql.conf || true

# If accounts.db_backed is enabled in the runtime/system configuration,
# we apply the NSS and PAM system changes.
if [[ "${MIOS_ACCOUNTS_DB_BACKED:-false}" =~ ^(true|1|yes)$ ]]; then
    log "Enabling live PostgreSQL database NSS and PAM account mappings"
    
    # Opt-out of authselect so our manual changes are preserved
    if command -v authselect &>/dev/null; then
        authselect opt-out || true
    fi

    # Edit /etc/nsswitch.conf if not already modified
    if ! grep -q "pgsql" /etc/nsswitch.conf; then
        sed -i 's/^passwd:.*/passwd:     files systemd pgsql/' /etc/nsswitch.conf
        sed -i 's/^shadow:.*/shadow:     files systemd pgsql/' /etc/nsswitch.conf
        sed -i 's/^group:.*/group:      files [SUCCESS=merge] systemd pgsql/' /etc/nsswitch.conf
        log "Updated /etc/nsswitch.conf with pgsql"
    fi

    # Modify PAM system-auth and password-auth files to insert pam_pgsql.so
    for f in /etc/pam.d/system-auth /etc/pam.d/password-auth; do
        if [ -f "$f" ] && ! grep -q "pam_pgsql.so" "$f"; then
            # Insert auth pgsql after pam_unix.so auth
            sed -i '/pam_unix.so try_first_pass/a auth        sufficient    pam_pgsql.so use_first_pass' "$f"
            # Insert account pgsql after pam_unix.so account
            sed -i '/pam_unix.so/a account     required      pam_pgsql.so' "$f"
            # Insert password pgsql after pam_unix.so password
            sed -i '/pam_unix.so try_first_pass/a password    sufficient    pam_pgsql.so use_authtok' "$f"
            # Insert pam_mkhomedir.so at the end of session if missing
            if ! grep -q "pam_mkhomedir.so" "$f"; then
                echo "session     optional      pam_mkhomedir.so umask=0077" >> "$f"
            fi
            log "Configured PAM pgsql + mkhomedir for $f"
        fi
    done
else
    log "PostgreSQL NSS + PAM integration is flag-gated off (db_backed = false)"
fi
