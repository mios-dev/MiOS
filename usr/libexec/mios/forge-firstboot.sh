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
#
# --user 816 matches the in-container UID we configured via USER_UID=816
# in the Quadlet. The container's internal username is 'git' (the Forgejo
# image's convention), not 'mios-forge'; we pass the numeric UID so the
# podman exec lookup succeeds against the container's /etc/passwd.
if podman exec --user 816:816 mios-forge \
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

# ── Initial repository for the deployed root ────────────────────────────────
# MiOS's defining feature: the live `/` is a git working tree, and the
# Forgejo container hosts the bare repo it tracks. For `git -C / push
# http://localhost:3000/<admin>/mios` to work on first run, the repo
# has to already exist on the forge. Create it via the admin API.
#
# Idempotent: 409 Conflict (already exists) is treated as success.
INITIAL_REPO_NAME="${MIOS_FORGE_INITIAL_REPO:-mios}"
_log "creating initial repo '${admin_user}/${INITIAL_REPO_NAME}' for the deployed root"
_repo_status=$(curl -sS -o /tmp/forge-repo-create.json -w '%{http_code}' \
    -u "${admin_user}:${admin_password}" \
    -H 'Content-Type: application/json' \
    -X POST "http://localhost:${http_port}/api/v1/user/repos" \
    -d "{\"name\":\"${INITIAL_REPO_NAME}\",\"description\":\"MiOS deployed root (live working tree of /).\",\"private\":false,\"auto_init\":false,\"default_branch\":\"main\"}" \
    || echo "000")
case "$_repo_status" in
    201) _log "initial repo created: http://localhost:${http_port}/${admin_user}/${INITIAL_REPO_NAME}" ;;
    409) _log "initial repo already exists -- skipping" ;;
    *)   _log "WARN: repo create returned HTTP ${_repo_status}; manual step needed:"
         _log "      curl -u ${admin_user}:<password> -X POST http://localhost:${http_port}/api/v1/user/repos -d '{\"name\":\"${INITIAL_REPO_NAME}\"}'" ;;
esac
rm -f /tmp/forge-repo-create.json

# ── Forgejo Runner registration token ──────────────────────────────────────
# The Runner Quadlet (mios-forgejo-runner.container) reads this file via
# EnvironmentFile= and self-registers on first start. Stored at root-only
# permissions; never tracked in git (whitelist .gitignore excludes
# /etc/mios/forge/ entirely except for files we explicitly allow).
RUNNER_TOKEN_FILE=/etc/mios/forge/runner-token
install -d -m 0750 -o root -g mios-forge /etc/mios/forge

# Try the in-container Forgejo CLI first -- most reliable across versions.
# `forgejo actions generate-runner-token` prints the token on stdout.
runner_token=""
if runner_token=$(podman exec --user 816:816 mios-forge \
        forgejo --config /data/gitea/conf/app.ini actions generate-runner-token 2>/dev/null \
        | tr -d '[:space:]'); then
    [[ -n "$runner_token" ]] && _log "minted runner token via forgejo CLI"
fi

# Fallback: admin API. Some Forgejo versions return a wrapper object,
# others return the bare string; sed handles either shape.
if [[ -z "$runner_token" ]]; then
    runner_token=$(curl -sS -u "${admin_user}:${admin_password}" \
        "http://localhost:${http_port}/api/v1/admin/runners/registration-token" 2>/dev/null \
        | sed -nE 's/.*"token"\s*:\s*"([^"]+)".*/\1/p' \
        | tr -d '[:space:]')
    [[ -n "$runner_token" ]] && _log "minted runner token via admin API"
fi

if [[ -n "$runner_token" ]]; then
    umask 077
    {
        echo "# /etc/mios/forge/runner-token -- generated by mios-forge-firstboot.service"
        echo "# EnvironmentFile= consumed by mios-forgejo-runner.container Quadlet."
        echo "FORGEJO_RUNNER_REGISTRATION_TOKEN=${runner_token}"
        echo "FORGEJO_INSTANCE_URL=http://mios-forge:3000/"
    } > "$RUNNER_TOKEN_FILE"
    chmod 0600 "$RUNNER_TOKEN_FILE"
    chown root:root "$RUNNER_TOKEN_FILE"
    _log "wrote runner token to ${RUNNER_TOKEN_FILE} (mode 0600, root-only)"
    # Trigger the runner Quadlet so it registers immediately rather than
    # waiting for next boot. systemctl is a no-op if the unit isn't
    # available on this host.
    systemctl start mios-forgejo-runner.service 2>/dev/null || \
        _log "(mios-forgejo-runner.service not yet active; will start on next boot)"
else
    _log "WARN: could not mint runner token -- self-replication CI is offline."
    _log "      Generate manually: 'sudo podman exec --user 816:816 mios-forge forgejo \\"
    _log "         --config /data/gitea/conf/app.ini actions generate-runner-token'"
fi

install -d -m 0755 -o root -g root "$(dirname "$SENTINEL")"
date -u +%FT%TZ > "$SENTINEL"
chmod 0644 "$SENTINEL"
_log "firstboot complete; sentinel at $SENTINEL"

# One-line operator hint, dropped into the system journal.
_log "Forgejo URL:  http://localhost:${http_port}/"
_log "Admin user:   ${admin_user}"
_log "Admin email:  ${admin_email}"
_log "Initial repo: http://localhost:${http_port}/${admin_user}/${INITIAL_REPO_NAME}"
_log "Push pattern: git -C / remote add origin http://${admin_user}@localhost:${http_port}/${admin_user}/${INITIAL_REPO_NAME}.git && git -C / push -u origin main"
if [[ -f "$PASSWORD_FILE" ]]; then
    _log "Initial password: 'sudo cat ${PASSWORD_FILE}' (must change on first login)"
fi

exit 0
