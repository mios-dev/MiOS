#!/usr/bin/env bash
# /usr/libexec/mios/forge-firstboot.sh
#
# First-boot admin-bootstrap for the mios-forge Quadlet (Forgejo).
# Runs once via mios-forge-firstboot.service after mios-forge.service is
# healthy. Creates the operator's admin user using values that
# mios-bootstrap install.sh wrote to /etc/mios/install.env, which were
# themselves resolved from mios-bootstrap.git/mios.toml at install time:
#
#   MIOS_FORGE_ADMIN_USER     defaults to MIOS_LINUX_USER ([identity].username)
#   MIOS_FORGE_ADMIN_EMAIL    defaults to <user>@<hostname>.local
#   MIOS_FORGE_ADMIN_PASSWORD if empty, a 24-byte URL-safe random
#                             password is generated and written to
#                             /etc/mios/forge/admin-password (root-owned,
#                             mode 0600); operator reads it once and
#                             changes it via the web UI on first login.
#
# Idempotent: marks completion via /var/lib/mios/forge/.firstboot-done
# and short-circuits on every subsequent boot. To re-trigger (e.g. after
# wiping the SQLite DB), delete that sentinel file and restart the
# mios-forge-firstboot.service.

set -euo pipefail

SENTINEL=/var/lib/mios/forge/.firstboot-done
ENV_FILE=/etc/mios/install.env
PASSWORD_FILE=/etc/mios/forge/admin-password

_log() {
    logger -t mios-forge-firstboot "$*" 2>/dev/null || true
    echo "[forge-firstboot] $*" >&2
}

if [[ -f "$SENTINEL" ]]; then
    _log "sentinel present, nothing to do"
    exit 0
fi

# Source install.env if present; tolerate absence (operator may run this
# script manually with env-vars set inline).
if [[ -r "$ENV_FILE" ]]; then
    # shellcheck source=/dev/null
    set -a; source "$ENV_FILE"; set +a
fi

# Resolution: explicit MIOS_FORGE_* wins; otherwise fall back to the
# linux user identity that bootstrap captured. Final fallback to 'mios'.
admin_user="${MIOS_FORGE_ADMIN_USER:-${MIOS_LINUX_USER:-${MIOS_USER:-mios}}}"
admin_host="${MIOS_HOSTNAME:-mios}"
admin_email="${MIOS_FORGE_ADMIN_EMAIL:-${admin_user}@${admin_host}.local}"
admin_password="${MIOS_FORGE_ADMIN_PASSWORD:-}"

# Wait for mios-forge to come up. The Quadlet sets TimeoutStartSec=300s;
# we mirror that ceiling. Forgejo's HTTP listener is the canonical
# readiness probe.
http_port="${MIOS_FORGE_HTTP_PORT:-3000}"
deadline=$(( $(date +%s) + 300 ))
while (( $(date +%s) < deadline )); do
    if curl -fsS -o /dev/null "http://localhost:${http_port}/api/v1/version"; then
        _log "Forgejo is up on :${http_port}"
        break
    fi
    sleep 2
done

if ! curl -fsS -o /dev/null "http://localhost:${http_port}/api/v1/version"; then
    _log "ERROR: Forgejo did not become ready within 300s; aborting"
    exit 1
fi

# Generate a password if none was supplied. 24 bytes -> 32 base64 chars.
if [[ -z "$admin_password" ]]; then
    admin_password="$(openssl rand -base64 24 | tr -d '\n')"
    install -d -m 0750 -o root -g mios-forge /etc/mios/forge
    umask 077
    printf '%s\n' "$admin_password" > "$PASSWORD_FILE"
    chmod 0600 "$PASSWORD_FILE"
    chown root:root "$PASSWORD_FILE"
    _log "generated initial admin password; wrote $PASSWORD_FILE (mode 0600, root-only)"
fi

# Create the admin via the in-container forgejo CLI. Idempotency: if the
# user already exists (e.g. someone created one via the web UI before
# this service ran), 'forgejo admin user create' returns non-zero and
# we accept that as a soft success.
if podman exec --user mios-forge mios-forge \
        forgejo --config /data/gitea/conf/app.ini admin user create \
        --admin --must-change-password=true \
        --username "$admin_user" \
        --email "$admin_email" \
        --password "$admin_password" 2>&1 | tee -a /var/log/mios/forge/firstboot.log; then
    _log "admin user '${admin_user}' (${admin_email}) created"
else
    rc=$?
    _log "admin create returned ${rc}; treating as 'already exists' (set MIOS_FORGE_FORCE_FIRSTBOOT=1 to override)"
    if [[ "${MIOS_FORGE_FORCE_FIRSTBOOT:-}" == "1" ]]; then
        exit "$rc"
    fi
fi

install -d -m 0755 -o root -g root "$(dirname "$SENTINEL")"
date -u +%FT%TZ > "$SENTINEL"
chmod 0644 "$SENTINEL"
_log "firstboot complete; sentinel at $SENTINEL"

# One-line operator hint, dropped into the system journal.
_log "Forgejo URL: http://localhost:${http_port}/"
_log "Admin user:  ${admin_user}"
_log "Admin email: ${admin_email}"
if [[ -f "$PASSWORD_FILE" ]]; then
    _log "Initial password: 'sudo cat ${PASSWORD_FILE}' (must change on first login)"
fi

exit 0
