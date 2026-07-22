#!/usr/bin/env bash
# AI-hint: First-boot admin-bootstrap for the mios-forge Quadlet (Forgejo).
# AI-related: /usr/libexec/mios/forge-firstboot.sh, /etc/mios/install.env, /etc/mios/forge/admin-password, /etc/mios/forge, /etc/mios/forge/admin-password., /etc/mios/forge/, /etc/mios/forge/runner-token, mios-forge, mios-forge-firstboot, mios-bootstrap
# AI-functions: _log
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

# Ensure host data volume has correct user ownership (UID 1000 git user)
mkdir -p /srv/mios/forge 2>/dev/null || true
chown -R 1000:1000 /srv/mios/forge 2>/dev/null || true

# Source install.env if present; tolerate absence (operator may run this
# script manually with env-vars set inline).
if [[ -r "$ENV_FILE" ]]; then
    # shellcheck source=/dev/null
    # Guard set -u: a value with shell-metachars must not abort under set -u.
    _mios_had_u=0; case "$-" in *u*) _mios_had_u=1;; esac
    set +u; set -a; source "$ENV_FILE" 2>/dev/null || true; set +a
    [ "$_mios_had_u" = 1 ] && set -u
fi

# Resolution: explicit MIOS_FORGE_* wins; otherwise fall back to the
# linux user identity that bootstrap captured. Final fallback to 'mios'.
admin_user="${MIOS_FORGE_ADMIN_USER:-${MIOS_LINUX_USER:-${MIOS_USER:-mios}}}"
admin_host="${MIOS_HOSTNAME:-mios}"
admin_email="${MIOS_FORGE_ADMIN_EMAIL:-${admin_user}@${admin_host}.local}"
# Default to the global MiOS password (mios.toml [identity].default_password).
# Operators can override per-service via MIOS_FORGE_ADMIN_PASSWORD, or set
# MIOS_FORGE_ADMIN_PASSWORD=__random__ to force a generated value.
admin_password="${MIOS_FORGE_ADMIN_PASSWORD:-${MIOS_DEFAULT_PASSWORD:-mios}}"
if [[ "$admin_password" == "__random__" ]]; then
    admin_password=""
fi

# Wait for mios-forge to come up. Forgejo's HTTP listener is the canonical
# readiness probe.
http_port="${MIOS_FORGE_HTTP_PORT:-3000}"
deadline=$(( $(date +%s) + 300 ))
while (( $(date +%s) < deadline )); do
    if curl -fsS -o /dev/null "http://localhost:${http_port}/api/v1/version" 2>/dev/null; then
        _log "Forgejo is up on :${http_port}"
        break
    fi
    sleep 2
done

if ! curl -fsS -o /dev/null "http://localhost:${http_port}/api/v1/version" 2>/dev/null; then
    _log "ERROR: Forgejo did not become ready; exiting with error for systemd retry"
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
# --must-change-password=false: TOML-first invariant. The admin
# password is resolved from mios.toml [identity] (default_password /
# MIOS_FORGE_ADMIN_PASSWORD) -- it IS the operator's intended
# credential, not a throwaway. With =true Forgejo locks every
# basic-auth API call behind a "you must change your password" 403,
# which breaks the very next steps in THIS script (repo-create,
# runner-token mint) and every downstream automation that authbenticates
# as the admin (the self-replication push loop, CI). The dashboard
# even advertises `forge mios/mios` as working credentials. Operators
# who want a forced rotation can set MIOS_FORGE_ADMIN_PASSWORD=__random__
# (handled above) -- that path still leaves the password usable, just
# unknown until read from /etc/mios/forge/admin-password.
if podman exec --user 816:816 mios-forge \
        forgejo --config /data/gitea/conf/app.ini admin user create \
        --admin --must-change-password=false \
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

# ── Wire the deployed root `/` to this forge (Day-0 self-host loop) ──────────
# code-server bind-mounts `/` at /mnt/mios-root and the Forgejo Runner builds
# /Containerfile on push, so the only missing link for "dev from INSIDE
# MiOS-DEV" is making `/` a git working tree pointed at this forge. The image
# build (Containerfile) excludes ./.git, so a fresh deploy has none -- create
# it here. The root is a PROPER, deliberately-curated git working tree:
# /.gitignore is a whitelist that tracks exactly the MiOS-owned surface
# (etc/, usr/, var/lib/mios, the Quadlets, the verbs) and nothing else -- it is
# the complete, intentional manifest of what MiOS owns, by design. `git add -A`
# stages that curated tree cleanly; it is not a defensive filter against the
# kernel's runtime mounts. We wire config only -- the operator (or code-server)
# drives the first commit + push. Idempotent; never fatal to firstboot.
# Forgejo is the loop HUB: point `origin` at the local Forgejo repo so a push
# from code-server (or `git -C / push`) triggers .forgejo/workflows/build-mios.yml
# on the Runner. The chain the operator wants is: .git=/ -> Forgejo -> code-server
# edits /mnt/mios-root. Password is embedded so the push is frictionless on this
# single-user self-host box; /.git/config is never committed (git ignores .git/).
# Any pre-existing non-Forgejo origin is preserved as 'local-bare'.
_forge_remote_url="http://${admin_user}:${admin_password}@localhost:${http_port}/${admin_user}/${INITIAL_REPO_NAME}.git"
if command -v git >/dev/null 2>&1; then
    git config --global --add safe.directory / 2>/dev/null || true
    if [[ ! -d /.git ]]; then
        if git -C / init -q -b main 2>/dev/null; then
            _log "initialised git working tree at / (whitelist /.gitignore -> only MiOS paths tracked)"
        else
            _log "WARN: 'git -C / init' failed -- self-host push loop not wired"
        fi
    fi
    if [[ -d /.git ]]; then
        _cur_origin=$(git -C / remote get-url origin 2>/dev/null || true)
        if [[ -n "$_cur_origin" && "$_cur_origin" != *"localhost:${http_port}"* ]]; then
            git -C / remote rename origin local-bare 2>/dev/null || true
        fi
        if git -C / remote get-url origin >/dev/null 2>&1; then
            git -C / remote set-url origin "$_forge_remote_url" 2>/dev/null || _log "WARN: 'git -C / remote set-url' failed (read-only / -- self-host push loop unavailable on this deployment; non-fatal)"
        else
            git -C / remote add origin "$_forge_remote_url" 2>/dev/null || true
        fi
        _log "root '/' origin -> Forgejo (${admin_user}/${INITIAL_REPO_NAME}); a push triggers the Runner"
        _log "self-host loop: edit in code-server (/mnt/mios-root) -> 'git -C / add -A && git -C / commit -m ... && git -C / push -u origin main' -> Runner builds /Containerfile -> bootc-switch stages next boot"
    fi
else
    _log "WARN: git not found in image -- cannot wire root '/' to forge"
fi

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

# The runner registers with -- and the daemon then connects to --
# whatever network mios-forge is actually on. On bridge shapes (real
# MiOS OCI builds) forge runs on mios.network and is reachable by
# container DNS as mios-forge:<port>. On the WSL / dev-VM testbed,
# build-mios.ps1 drops BOTH forge and the runner to Network=host via
# Quadlet drop-ins -- there container DNS does not exist, and the
# host-published PublishPort=3000:3000 means localhost:<port> is the
# only address that resolves for both. mios-forge is up by now (this
# script polled its HTTP listener above), so inspect its live network
# and write the URL the runner daemon will actually be able to reach.
# Falls back to the container-DNS form if inspect yields nothing.
forge_net=$(podman inspect mios-forge \
    --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}' 2>/dev/null \
    | awk '{print $1}')
if [[ "$forge_net" == "host" ]]; then
    runner_instance_url="http://localhost:${http_port}/"
else
    runner_instance_url="http://mios-forge:${http_port}/"
fi
_log "runner instance URL: ${runner_instance_url} (forge network: ${forge_net:-unknown})"

if [[ -n "$runner_token" ]]; then
    umask 077
    {
        echo "# /etc/mios/forge/runner-token -- generated by mios-forge-firstboot.service"
        echo "# EnvironmentFile= consumed by mios-forgejo-runner.container Quadlet."
        echo "FORGEJO_RUNNER_REGISTRATION_TOKEN=${runner_token}"
        echo "FORGEJO_INSTANCE_URL=${runner_instance_url}"
    } > "$RUNNER_TOKEN_FILE"
    chmod 0600 "$RUNNER_TOKEN_FILE"
    chown root:root "$RUNNER_TOKEN_FILE"
    _log "wrote runner token to ${RUNNER_TOKEN_FILE} (mode 0600, root-only)"
    # Trigger the runner chain so it registers immediately rather than
    # waiting for next boot. --no-block is LOAD-BEARING: this script is
    # the ExecStart of mios-forge-firstboot.service, and the runner
    # chain is ordered After=mios-forge-firstboot.service. A *blocking*
    # `systemctl start` here would wait for a job (mios-forgejo-runner.
    # service) that is itself queued behind this very unit finishing
    # activation -- a hard ordering deadlock (operator-confirmed
    # forge-firstboot stuck "activating", runner jobs stuck
    # "waiting"). --no-block enqueues the chain and returns immediately
    # so this unit can reach "active", which then unblocks the queue.
    # mios-forgejo-runner.service Wants= the runner-firstboot
    # registration unit, so starting it pulls the whole chain.
    systemctl start --no-block mios-forgejo-runner.service 2>/dev/null || \
        _log "(mios-forgejo-runner.service not yet available; will start on next boot)"
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
