#!/usr/bin/env bash
# 'MiOS' MCP server pre-flight (ExecStartPre for mios-mcp.service).
# Verifies the MCP server's runtime directories + sqlite vault paths exist
# before the long-running mcp-server-runner is launched. Fast (<100 ms),
# idempotent, no network.
#
# Lays down:
#   /var/lib/mios/mcp/             owner mios:mios mode 0750
#   /var/lib/mios/mcp/state.db     touched if missing (sqlite WAL friendly)
#   /var/log/mios/mcp/             owner mios:mios mode 0750
#   /srv/ai/mcp/                   read-only mount target for server config
set -euo pipefail
# shellcheck source=/usr/lib/mios/paths.sh
source /usr/lib/mios/paths.sh

_log()  { logger -t mios-mcp-init "$*" 2>/dev/null || true; echo "[mcp-init] $*" >&2; }

uid=$(id -u mios 2>/dev/null || echo 1000)
gid=$(id -g mios 2>/dev/null || echo 1000)

# Writable runtime dirs only. /srv/ai/mcp is the read-only config mount
# target -- it's pre-created by usr/lib/tmpfiles.d/mios.conf at boot,
# and on bootc/composefs deployments where /srv resolves into the
# read-only image surface, `install -d` fails on the chmod step. The
# mcp server reads config from there but never writes, so verification
# is enough; no mutation.
for dir in \
    "${MIOS_VAR_DIR}/mcp" \
    "/var/log/mios/mcp"
do
    install -d -m 0750 -o "$uid" -g "$gid" "$dir" 2>/dev/null || \
        install -d -m 0750 "$dir"
done

if [[ ! -d /srv/ai/mcp ]]; then
    _log "WARN: /srv/ai/mcp missing -- tmpfiles.d/mios.conf may not have run; mcp config bind-mount will be empty"
fi

DBPATH="${MIOS_VAR_DIR}/mcp/state.db"
if [[ ! -f "$DBPATH" ]]; then
    : > "$DBPATH"
    chown "$uid:$gid" "$DBPATH" 2>/dev/null || true
    chmod 0640 "$DBPATH"
    _log "  initialized $DBPATH"
fi

_log "pre-flight ok"
exit 0
