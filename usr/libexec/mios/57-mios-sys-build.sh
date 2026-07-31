#!/usr/bin/env bash
# AI-hint: Unified builder script to build localhost/mios-sys and localhost/mios-cuda shared-base images into the additional containers-storage root (WS-MIOSSYS).
# AI-related: usr/share/mios/sys/Containerfile, usr/share/mios/cuda/Containerfile, C:\MiOS\Containerfile
set -euo pipefail

# This script is located at /usr/libexec/mios/57-mios-sys-build.sh on the target system
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIOS_TOML="${MIOS_TOML:-/usr/share/mios/mios.toml}"
export MIOS_VENDOR_TOML="${MIOS_VENDOR_TOML:-$MIOS_TOML}"
STORE="${STORE:-/usr/lib/containers/storage}"
SCRATCH="${SCRATCH:-/var/tmp/mios-bakescratch}"

# Load common and userenv to get base image configuration
# Sourced relative to /usr/libexec/mios/ or /tmp/build/usr/libexec/mios/
if [[ -f "/usr/lib/mios/paths.sh" ]]; then
    source "/usr/lib/mios/paths.sh"
else
    source "${SCRIPT_DIR}/../../lib/mios/paths.sh"
fi

# Ensure we have common logging functions
log() { printf '[57-mios-sys-build] %s\n' "$*"; }

# Determine BASE_IMAGE to use
BASE="${MIOS_BASE_IMAGE:-ghcr.io/ublue-os/ucore-hci:stable-nvidia}"

log "Base image configured: $BASE"
log "Target storage root: $STORE"

# Generate inner store configuration
install -d -m 0700 "$SCRATCH"
install -d -m 0700 "$SCRATCH/tmp" "$SCRATCH/run"
CONF="$SCRATCH/storage.conf"
cat > "$CONF" <<'SC'
[storage]
driver = "overlay"
[storage.options]
[storage.options.overlay]
mountopt = "nodev"
[storage.options.pull_options]
enable_partial_images = "true"
convert_images = "true"
use_hard_links = "true"
SC

# Route docker.io FROM pulls (the sys build's golang stage) through mirror.gcr.io --
# Google's public pull-through cache of Docker Hub -- to avoid anonymous rate limits
# (HTTP 429) on shared-IP CI runners; falls back to docker.io. Build-time-scoped via
# CONTAINERS_REGISTRIES_CONF; never written into the image's registries.
REG_CONF="$SCRATCH/registries.conf"
cat > "$REG_CONF" <<'RC'
short-name-mode = "permissive"
[[registry]]
location = "docker.io"
[[registry.mirror]]
location = "mirror.gcr.io"
RC

# --cap-add all + unconfined seccomp/apparmor on the INNER build: this podman build
# runs nested inside the OCI build's RUN step, and mios-sys/-cuda are multi-stage
# (their own go-builder RUN steps), so crun must set up TRIPLE-nested containers --
# it needs CAP_SYS_RESOURCE for setrlimit(RLIMIT_NOFILE) + SYS_ADMIN for mounts, etc.
# The outer .github/.forgejo build grants these to RUN; pass them down here too.
SEARXNG_REF="$(python3 -c "import mios_toml; print(mios_toml.load_merged().get('build', {}).get('bake_refs', {}).get('searxng', 'master'))" 2>/dev/null || echo "master")"

build_image_with_retry() {
    local target_tag="$1"
    local build_dir="$2"
    shift 2
    local attempt=1
    local max_attempts=3
    local backoff=5
    local success=0

    while [[ $attempt -le $max_attempts ]]; do
        log "Attempt $attempt/$max_attempts: Building $target_tag..."
        if CONTAINERS_STORAGE_CONF="$CONF" CONTAINERS_REGISTRIES_CONF="$REG_CONF" TMPDIR="$SCRATCH/tmp" \
          podman --root "$STORE" --runroot "$SCRATCH/run" build \
          --network=host \
          --cap-add all \
          --security-opt seccomp=unconfined \
          --security-opt apparmor=unconfined \
          --layers \
          -t "$target_tag" \
          "$@" \
          "$build_dir"; then
            success=1
            break
        else
            log "WARNING: Build $target_tag failed on attempt $attempt/$max_attempts"
            if [[ $attempt -lt $max_attempts ]]; then
                log "Backing off $backoff seconds before retry..."
                sleep "$backoff"
                backoff=$((backoff * 2))
            fi
        fi
        attempt=$((attempt + 1))
    done

    if [[ $success -ne 1 ]]; then
        log "ERROR: Persistent build failure for $target_tag after $max_attempts attempts."
        exit 1
    fi

    if ! CONTAINERS_STORAGE_CONF="$CONF" podman --root "$STORE" image exists "$target_tag"; then
        log "ERROR: Image verification failed: $target_tag does not exist after build!"
        exit 1
    fi
    log "Image $target_tag verified successfully."
}

# Build localhost/mios-sys
log "Building localhost/mios-sys (searxng ref: $SEARXNG_REF)..."
build_image_with_retry "localhost/mios-sys" "/usr/share/mios/sys" \
  --build-arg BASE_IMAGE="$BASE" \
  --build-arg SEARXNG_REF="$SEARXNG_REF"

# Build localhost/mios-cuda
log "Building localhost/mios-cuda..."
build_image_with_retry "localhost/mios-cuda" "/usr/share/mios/cuda" \
  --build-arg BASE_IMAGE="$BASE"

# Record to SBOM (Software Bill of Materials)
SBOM_DIR="${SBOM_DIR:-/usr/share/mios/artifacts/sbom}"
_sys_digest="$(CONTAINERS_STORAGE_CONF="$CONF" podman --root "$STORE" image inspect localhost/mios-sys --format '{{.Digest}}' 2>/dev/null || echo "local")"
_cuda_digest="$(CONTAINERS_STORAGE_CONF="$CONF" podman --root "$STORE" image inspect localhost/mios-cuda --format '{{.Digest}}' 2>/dev/null || echo "local")"
install -d -m 0755 "$SBOM_DIR"
printf '%s\t%s\t%s\n' "localhost/mios-sys:latest" "${_sys_digest:-local}" "sys" >> "$SBOM_DIR/bound-images.tsv"
printf '%s\t%s\t%s\n' "localhost/mios-cuda:latest" "${_cuda_digest:-local}" "cuda" >> "$SBOM_DIR/bound-images.tsv"

# CI DISK FIT (exit-125 "storing blob ... write" on the RUN commit): with
# `podman --layers`, the multi-stage go-/rust-/llamaswap builder images linger in
# $STORE and get captured in THIS RUN's committed layer, which buildah then writes
# ~2-3x to TMPDIR during commit -> ENOSPC on a disk-constrained runner. Drop every
# image except the two consolidated bases so the committed /usr/lib/containers/storage
# diff is minimal. Bit-for-bit safe: the builders are build-time inputs, absent from
# the runtime image; mios-sys/mios-cuda (tagged, kept) retain their shared base layers.
log "Pruning build-stage images from ${STORE} (keep only mios-sys + mios-cuda)..."
while read -r _img; do
    case "$_img" in
        localhost/mios-sys:latest|localhost/mios-cuda:latest|"<none>:<none>") continue ;;
    esac
    CONTAINERS_STORAGE_CONF="$CONF" podman --root "$STORE" --runroot "$SCRATCH/run" rmi -f "$_img" >/dev/null 2>&1 || true
done < <(CONTAINERS_STORAGE_CONF="$CONF" podman --root "$STORE" images --format '{{.Repository}}:{{.Tag}}' 2>/dev/null | sort -u)
CONTAINERS_STORAGE_CONF="$CONF" podman --root "$STORE" --runroot "$SCRATCH/run" image prune -f >/dev/null 2>&1 || true

log "Consolidated shared base images built successfully."
