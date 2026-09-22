#!/usr/bin/env bash
# AI-hint: Build-if-missing bootstrap for the mios-agents A2O super-container image
# AI-related: /usr/share/mios/agents/Containerfile, /usr/share/mios/agents/mios-a2o, mios-agents.service, mios-code-server.service, mios-forge-firstboot
set -euo pipefail

IMG="${MIOS_AGENTS_IMAGE:-localhost/mios-agents:latest}"
CTX="/usr/share/mios/agents"
CF="$CTX/Containerfile"
SETTINGS_SOURCE="$CTX/code-server-mobile-settings.json"
SETTINGS_TARGET="/var/lib/mios/agents/.local/share/code-server/User/settings.json"

log() { logger -t mios-agents-firstboot "$*" 2>/dev/null || true; echo "[mios-agents-firstboot] $*" >&2; }

seed_code_server_settings() {
    [ -f "$SETTINGS_SOURCE" ] || return 0

    install -d -m 0755 "$(dirname "$SETTINGS_TARGET")"
    if [ ! -e "$SETTINGS_TARGET" ]; then
        install -m 0644 "$SETTINGS_SOURCE" "$SETTINGS_TARGET"
        log "Seeded portrait code-server settings"
        return 0
    fi

    python3 - "$SETTINGS_SOURCE" "$SETTINGS_TARGET" <<'PY'
import json
import sys
from pathlib import Path

source = Path(sys.argv[1])
target = Path(sys.argv[2])
defaults = json.loads(source.read_text(encoding="utf-8"))
settings = json.loads(target.read_text(encoding="utf-8"))
if not isinstance(settings, dict):
    raise ValueError(f"{target} must contain a JSON object")

updated = False
for key, value in defaults.items():
    if key not in settings:
        settings[key] = value
        updated = True

if updated:
    target.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
PY
    log "Merged missing portrait code-server defaults"
}

seed_code_server_settings

if command -v miosd >/dev/null 2>&1; then
    miosd build-if-missing agents
    exit 0
fi

[ -f "$CF" ] || { log "ERROR: $CF missing"; exit 1; }

NEED_BUILD=0
if ! podman image exists "$IMG"; then
    NEED_BUILD=1; log "Image $IMG missing -> build"
else
    _img_epoch="$(date -d "$(podman image inspect -f '{{.Created}}' "$IMG" 2>/dev/null)" +%s 2>/dev/null || echo 0)"
    _cf_epoch="$(stat -c %Y "$CF" 2>/dev/null || echo 0)"
    if [ "$_img_epoch" -gt 0 ] && [ "$_cf_epoch" -gt "$_img_epoch" ]; then
        NEED_BUILD=1; log "Containerfile newer than image -> rebuild"
    else
        log "Image $IMG current; nothing to build"
    fi
fi
[ "$NEED_BUILD" = 1 ] || exit 0

log "Building $IMG from $CF "
if ! podman build --network=host -t "$IMG" -f "$CF" "$CTX"; then
    log "ERROR: $IMG build failed. Cleaning up intermediate containers/images"
    podman image prune --force >/dev/null 2>&1 || true
    exit 1
fi
log "Built $IMG"
