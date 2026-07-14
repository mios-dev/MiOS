#!/usr/bin/env bash
# AI-hint: Build-if-missing bootstrap for the mios-agents A2O super-container image
# (code-server IDE + tmux war room + Claude CLI + agy/Gemini + the mios-a2o muxer).
# Runs as ExecStartPre of mios-agents.service; idempotent no-op when the image exists.
# AI-related: /usr/share/mios/agents/Containerfile, /usr/share/mios/agents/mios-a2o, mios-agents.service, mios-code-server.service, mios-forge-firstboot
# /usr/libexec/mios/mios-agents-firstboot.sh
set -euo pipefail

IMG="${MIOS_AGENTS_IMAGE:-localhost/mios-agents:latest}"
CTX="/usr/share/mios/agents"
CF="$CTX/Containerfile"

log() { logger -t mios-agents-firstboot "$*" 2>/dev/null || true; echo "[mios-agents-firstboot] $*" >&2; }

[ -f "$CF" ] || { log "ERROR: $CF missing -- cannot build $IMG"; exit 1; }

# Rebuild when the image is MISSING or the Containerfile is NEWER than the image.
# Build-if-missing alone pins a stale image forever after a Containerfile change
# (operator-flagged: mios-frontier missing inside a stale mios-agents container).
# The mios-a2o / mios-frontier SCRIPTS do NOT force a rebuild -- they are read LIVE
# from the bind-mounted /mnt/mios-root via the image's profile.d PATH self-heal, so
# only dependency / Containerfile changes need an image refresh.
NEED_BUILD=0
if ! podman image exists "$IMG"; then
    NEED_BUILD=1; log "image $IMG missing -> build (first deploy)"
else
    _img_epoch="$(date -d "$(podman image inspect -f '{{.Created}}' "$IMG" 2>/dev/null)" +%s 2>/dev/null || echo 0)"
    _cf_epoch="$(stat -c %Y "$CF" 2>/dev/null || echo 0)"
    if [ "$_img_epoch" -gt 0 ] && [ "$_cf_epoch" -gt "$_img_epoch" ]; then
        NEED_BUILD=1; log "Containerfile newer than image ($_cf_epoch > $_img_epoch) -> rebuild"
    else
        log "image $IMG current; nothing to build"
    fi
fi
[ "$NEED_BUILD" = 1 ] || exit 0

log "building $IMG from $CF ..."
# --network=host: the build's apt/npm/agy fetches need working egress; the podman
# build netns otherwise attempts unroutable IPv6 on some substrates (WSL testbed).
if ! podman build --network=host -t "$IMG" -f "$CF" "$CTX"; then
    log "ERROR: $IMG build failed. Cleaning up intermediate containers/images..."
    podman image prune --force >/dev/null 2>&1 || true
    exit 1
fi
log "built $IMG"
