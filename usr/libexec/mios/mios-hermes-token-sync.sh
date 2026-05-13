#!/bin/bash
# /usr/libexec/mios/mios-hermes-token-sync.sh
#
# Scrape mios-hermes-dashboard's ephemeral session token (random per
# process per upstream nousresearch/hermes-agent web_server.py:86 --
# `_SESSION_TOKEN = secrets.token_urlsafe(32)`) and write it as
# HERMES_DASHBOARD_TOKEN into /etc/mios/hermes/api.env so
# mios-hermes-workspace authenticates against /api/* (sessions, tasks,
# kanban, skills, mcp, config, status).
#
# Without this sync, workspace falls back to its legacy HTML-scrape
# token flow which fails on the minimal hermes-agent gateway image and
# the operator sees "Failed to load tasks Retry" / "Sessions: 401
# Unauthorized" across every panel (operator-confirmed 2026-05-13).
#
# Per outsourc-e/hermes-workspace .env.example:
#   HERMES_DASHBOARD_URL    defaults to http://127.0.0.1:9119
#   HERMES_DASHBOARD_TOKEN  preferred over legacy HTML-scrape flow
#
# Triggered by mios-hermes-token-sync.service whenever
# mios-hermes-dashboard.service becomes active (PartOf+After binding
# in the unit), so token refresh is automatic on every dashboard
# restart.
set -euo pipefail

API_ENV=/etc/mios/hermes/api.env
DASH_URL="${MIOS_DASHBOARD_URL:-http://localhost:9119}"
WORKSPACE_UNIT=mios-hermes-workspace.service
LOG_TAG=mios-hermes-token-sync

log() { logger -t "$LOG_TAG" "$1"; echo "$1"; }

# Wait up to 30s for dashboard to start serving (it runs uvicorn; a few
# seconds of warmup after systemd reports active is normal).
for _ in $(seq 1 30); do
    code=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 1 -m 2 "$DASH_URL/" 2>/dev/null || echo 000)
    [ "$code" = "200" ] && break
    sleep 1
done
if [ "$code" != "200" ]; then
    log "ERROR: dashboard unreachable at $DASH_URL/ (last code: $code) -- skipping token sync"
    exit 0
fi

token=$(curl -s -m 5 "$DASH_URL/" \
        | grep -oE '__HERMES_SESSION_TOKEN__\s*=\s*"[^"]+"' \
        | head -1 \
        | sed -E 's/.*"([^"]+)"/\1/')
if [ -z "$token" ]; then
    log "ERROR: could not scrape __HERMES_SESSION_TOKEN__ from dashboard HTML -- skipping"
    exit 0
fi

# Compare against existing value to avoid pointless workspace restarts.
existing=$(grep -E '^HERMES_DASHBOARD_TOKEN=' "$API_ENV" 2>/dev/null | head -1 | cut -d= -f2- || echo '')
if [ "$existing" = "$token" ]; then
    log "token unchanged (${token:0:8}...) -- workspace restart skipped"
    exit 0
fi

# Strip any prior HERMES_DASHBOARD_URL / HERMES_DASHBOARD_TOKEN lines + re-append.
sed -i '/^HERMES_DASHBOARD_URL=/d; /^HERMES_DASHBOARD_TOKEN=/d' "$API_ENV"
{
    echo "HERMES_DASHBOARD_URL=$DASH_URL"
    echo "HERMES_DASHBOARD_TOKEN=$token"
} >> "$API_ENV"
chmod 0640 "$API_ENV"
log "wrote HERMES_DASHBOARD_TOKEN=${token:0:8}... + URL=$DASH_URL to $API_ENV"

# Bounce the workspace so its container picks up the new EnvironmentFile values.
# Restart instead of try-restart so a stopped workspace gets started here too
# (covers the firstboot case where the workspace failed prior token sync).
systemctl restart "$WORKSPACE_UNIT" 2>&1 | sed "s/^/  $LOG_TAG: /"
log "restarted $WORKSPACE_UNIT to pick up new dashboard token"
