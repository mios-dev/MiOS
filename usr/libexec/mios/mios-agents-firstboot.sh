#!/usr/bin/env bash
# AI-hint: Build-if-missing bootstrap for the mios-agents A2O super-container image
# AI-related: /usr/share/mios/agents/Containerfile, /usr/share/mios/agents/mios-a2o, mios-agents.service, mios-code-server.service, mios-forge-firstboot
set -euo pipefail

IMG="${MIOS_AGENTS_IMAGE:-localhost/mios-agents:latest}"
CTX="/usr/share/mios/agents"
CF="$CTX/Containerfile"

log() { logger -t mios-agents-firstboot "$*" 2>/dev/null || true; echo "[mios-agents-firstboot] $*" >&2; }

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
