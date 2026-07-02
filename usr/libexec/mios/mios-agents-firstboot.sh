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

if podman image exists "$IMG"; then
    log "image $IMG already present; nothing to build"
    exit 0
fi
[ -f "$CF" ] || { log "ERROR: $CF missing -- cannot build $IMG"; exit 1; }

log "building $IMG from $CF (first deploy) ..."
# --network=host: the build's apt/npm/agy fetches need working egress; the podman
# build netns otherwise attempts unroutable IPv6 on some substrates (WSL testbed).
podman build --network=host -t "$IMG" -f "$CF" "$CTX"
log "built $IMG"
