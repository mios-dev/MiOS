#!/usr/bin/env bash
# AI-hint: Build-if-missing bootstrap for the mios-webtools container images
# (crawl4ai-slim FastAPI engine and Mendable firecrawl API/worker stack).
# Runs as a pre-requisite service before the web-tools containers are started by Quadlet.
# AI-related: /usr/share/mios/crawl4ai/Containerfile, /usr/share/mios/webtools/firecrawl.Containerfile, mios-webtools-firstboot.service
set -euo pipefail

log() { logger -t mios-webtools-firstboot "$*" 2>/dev/null || true; echo "[mios-webtools-firstboot] $*" >&2; }

# 1. Build crawl4ai-slim if missing or stale
C4_IMG="localhost/mios-crawl4ai-slim:latest"
C4_CTX="/usr/share/mios/crawl4ai"
C4_CF="$C4_CTX/Containerfile"

if [ -f "$C4_CF" ]; then
    NEED_BUILD=0
    if ! podman image exists "$C4_IMG"; then
        NEED_BUILD=1; log "image $C4_IMG missing -> build"
    else
        _img_epoch="$(date -d "$(podman image inspect -f '{{.Created}}' "$C4_IMG" 2>/dev/null)" +%s 2>/dev/null || echo 0)"
        _cf_epoch="$(stat -c %Y "$C4_CF" 2>/dev/null || echo 0)"
        if [ "$_img_epoch" -gt 0 ] && [ "$_cf_epoch" -gt "$_img_epoch" ]; then
            NEED_BUILD=1; log "Containerfile newer than image ($C4_CF) -> rebuild"
        fi
    fi
    if [ "$NEED_BUILD" = 1 ]; then
        log "building $C4_IMG from $C4_CF ..."
        podman build --network=host -t "$C4_IMG" -f "$C4_CF" "$C4_CTX"
        log "built $C4_IMG"
    else
        log "image $C4_IMG current; skipping build"
    fi
else
    log "WARN: $C4_CF missing -- skipping crawl4ai build"
fi

# 2. Build firecrawl if missing or stale
FC_IMG="localhost/mios-firecrawl:v1.0.0"
FC_CTX="/usr/share/mios/webtools"
FC_CF="$FC_CTX/firecrawl.Containerfile"

if [ -f "$FC_CF" ]; then
    NEED_BUILD=0
    if ! podman image exists "$FC_IMG"; then
        NEED_BUILD=1; log "image $FC_IMG missing -> build"
    else
        _img_epoch="$(date -d "$(podman image inspect -f '{{.Created}}' "$FC_IMG" 2>/dev/null)" +%s 2>/dev/null || echo 0)"
        _cf_epoch="$(stat -c %Y "$FC_CF" 2>/dev/null || echo 0)"
        if [ "$_img_epoch" -gt 0 ] && [ "$_cf_epoch" -gt "$_img_epoch" ]; then
            NEED_BUILD=1; log "Containerfile newer than image ($FC_CF) -> rebuild"
        fi
    fi
    if [ "$NEED_BUILD" = 1 ]; then
        log "building $FC_IMG from $FC_CF ..."
        podman build --network=host -t "$FC_IMG" -f "$FC_CF" "$FC_CTX"
        log "built $FC_IMG"
    else
        log "image $FC_IMG current; skipping build"
    fi
else
    log "WARN: $FC_CF missing -- skipping firecrawl build"
fi
