#!/usr/bin/env bash
# AI-hint: MiOS' MCP server pre-flight (ExecStartPre for mios-mcp.service).
# AI-related: /usr/lib/mios/paths.sh, mios-mcp, mios-ai, mios-mcp-init, mios-owned, mios-mcp.service
# AI-functions: _log
set -euo pipefail
source /usr/lib/mios/paths.sh

_log()  { logger -t mios-mcp-init "$*" 2>/dev/null || true; echo "[mcp-init] $*" >&2; }

uid=$(id -u)
gid=$(id -g)

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
