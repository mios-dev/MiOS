#!/usr/bin/env bash
# AI-hint: Build-if-missing bootstrap for the mios-webtools container images
# (crawl4ai-slim FastAPI engine and Mendable firecrawl API/worker stack). Runs as
# a prerequisite service before the web-tools containers are started by Quadlet.
# WS-DEPLOY: each image build is INDEPENDENT (one failure never aborts the other),
# RETRIED with backoff (a transient network blip under install-time contention no
# longer leaves an image unbuilt so the consumer Quadlet can't start), and VERIFIED
# to exist after the build. Exits non-zero if any needed image is still missing so
# the .service's Restart=on-failure re-attempts instead of leaving webtools down.
# AI-related: /usr/share/mios/crawl4ai/Containerfile, /usr/share/mios/webtools/firecrawl.Containerfile, mios-webtools-firstboot.service
#
# NOTE: intentionally NOT `set -e` -- a failed crawl4ai build must not skip the
# firecrawl build. Errors are handled explicitly per image and aggregated into $_rc.
set -uo pipefail

log() { logger -t mios-webtools-firstboot "$*" 2>/dev/null || true; echo "[mios-webtools-firstboot] $*" >&2; }

# ─── firstboot idempotency sentinel (AGY-38) ────────────────────────────────
# Once both webtools images are built + verified, skip re-running on every boot.
# The sentinel lives under /var/lib/mios (persists across bootc upgrades). It is
# written ONLY on a fully-successful run (_rc==0) below, so a partial/failed
# build still retries. Delete it to force a rebuild:
#   rm -f /var/lib/mios/.webtools-firstboot.done && systemctl restart mios-webtools-firstboot
_FIRSTBOOT_SENTINEL="/var/lib/mios/.webtools-firstboot.done"
if [ -f "$_FIRSTBOOT_SENTINEL" ]; then
    log "sentinel $_FIRSTBOOT_SENTINEL present -- webtools firstboot already completed, skipping"
    exit 0
fi

# need_build <image> <containerfile> -> echoes 1 if a (re)build is needed, else 0.
# Rebuild when the image is absent OR the Containerfile is newer than the image.
need_build() {
    local img="$1" cf="$2"
    if ! podman image exists "$img"; then echo 1; return; fi
    local _img_epoch _cf_epoch
    _img_epoch="$(date -d "$(podman image inspect -f '{{.Created}}' "$img" 2>/dev/null)" +%s 2>/dev/null || echo 0)"
    _cf_epoch="$(stat -c %Y "$cf" 2>/dev/null || echo 0)"
    if [ "$_img_epoch" -gt 0 ] && [ "$_cf_epoch" -gt "$_img_epoch" ]; then echo 1; else echo 0; fi
}

# build_image_retry <image> <containerfile> <context> -> 0 on success (image
# present + verified), 1 after exhausting retries. Backoff: 10s, 20s.
build_image_retry() {
    local img="$1" cf="$2" ctx="$3" attempts=3 a
    for a in $(seq 1 "$attempts"); do
        log "building $img from $cf (attempt $a/$attempts) ..."
        if podman build --network=host -t "$img" -f "$cf" "$ctx" && podman image exists "$img"; then
            log "built + verified $img"
            return 0
        fi
        if [ "$a" -lt "$attempts" ]; then
            log "WARN: $img build attempt $a/$attempts failed (transient network under install load?) -- retrying in $((a*10))s"
            sleep $((a*10))
        fi
    done
    log "ERROR: $img build failed after $attempts attempts -- webtools consumer will stay down until the next retry"
    return 1
}

# maybe_build <image> <containerfile> <context> <label> -> respects need_build,
# never aborts the caller; returns the build result (0 ok / 1 failed / 0 skipped).
maybe_build() {
    local img="$1" cf="$2" ctx="$3" label="$4"
    if [ ! -f "$cf" ]; then
        log "WARN: $cf missing -- skipping $label build"
        return 0
    fi
    if [ "$(need_build "$img" "$cf")" = 1 ]; then
        build_image_retry "$img" "$cf" "$ctx"
        return $?
    fi
    log "image $img current; skipping $label build"
    return 0
}

_rc=0

# 1. crawl4ai-slim FastAPI engine
maybe_build "localhost/mios-crawl4ai-slim:latest" \
            "/usr/share/mios/crawl4ai/Containerfile" \
            "/usr/share/mios/crawl4ai" "crawl4ai" || _rc=1

# 2. firecrawl API/worker stack (independent -- runs even if crawl4ai failed)
maybe_build "localhost/mios-firecrawl:v1.0.0" \
            "/usr/share/mios/webtools/firecrawl.Containerfile" \
            "/usr/share/mios/webtools" "firecrawl" || _rc=1

if [ "$_rc" -eq 0 ]; then
    # sentinel: all images built + verified -- gate re-runs on later boots (AGY-38).
    # Degrade-open: the touch never changes the exit status.
    install -d -m 0755 /var/lib/mios 2>/dev/null || true
    touch "$_FIRSTBOOT_SENTINEL" 2>/dev/null || true
    log "all webtools images present -- wrote sentinel $_FIRSTBOOT_SENTINEL"
else
    log "one or more webtools images missing -- exiting non-zero for Restart=on-failure retry"
fi
exit "$_rc"
