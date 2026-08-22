#!/usr/bin/env bash
# AI-hint: bash Unified builder script to build localhost/mios-sys and localhost/mios-cuda shared-base images into the additional containers-storage r...
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_libexec_mios_57_mios_sys_build_sh.md
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIOS_TOML="${MIOS_TOML:-/usr/share/mios/mios.toml}"
export MIOS_VENDOR_TOML="${MIOS_VENDOR_TOML:-$MIOS_TOML}"
STORE="${STORE:-/usr/lib/containers/storage}"
SCRATCH="${SCRATCH:-/var/tmp/mios-bakescratch}"

if [[ -f "/usr/lib/mios/paths.sh" ]]; then
    source "/usr/lib/mios/paths.sh"
else
    source "${SCRIPT_DIR}/../../lib/mios/paths.sh"
fi

log() { printf '[57-mios-sys-build] %s\n' "$*"; }

if [ "${MIOS_BAKE_BOUND_IMAGES:-1}" != "1" ]; then
    log "SKIP bound-images bake for mios-sys and mios-cuda"
    exit 0
fi

BASE="${MIOS_BASE_IMAGE:-ghcr.io/ublue-os/ucore-hci:stable-nvidia}"

log "Base image configured: $BASE"
log "Target storage root: $STORE"

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

REG_CONF="$SCRATCH/registries.conf"
cat > "$REG_CONF" <<'RC'
short-name-mode = "permissive"
[[registry]]
location = "docker.io"
[[registry.mirror]]
location = "mirror.gcr.io"
RC

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
        log "Attempt $attempt/$max_attempts: Building $target_tag"
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
                log "Backing off $backoff seconds before retry"
                sleep "$backoff"
                backoff=$((backoff * 2))
            fi
        fi
        attempt=$((attempt + 1))
    done

    if [[ $success -ne 1 ]]; then
        log "ERROR: Persistent build failure for $target_tag after $max_attempts attempts"
        exit 1
    fi

    if ! CONTAINERS_STORAGE_CONF="$CONF" podman --root "$STORE" image exists "$target_tag"; then
        log "ERROR: Image verification failed: $target_tag does not exist after build"
        exit 1
    fi
    log "Image $target_tag verified successfully"
}

log "Building localhost/mios-sys"
build_image_with_retry "localhost/mios-sys" "/usr/share/mios/sys" \
  --build-arg BASE_IMAGE="$BASE" \
  --build-arg SEARXNG_REF="$SEARXNG_REF"

log "Building localhost/mios-cuda"
build_image_with_retry "localhost/mios-cuda" "/usr/share/mios/cuda" \
  --build-arg BASE_IMAGE="$BASE"

SBOM_DIR="${SBOM_DIR:-/usr/share/mios/artifacts/sbom}"
_sys_digest="$(CONTAINERS_STORAGE_CONF="$CONF" podman --root "$STORE" image inspect localhost/mios-sys --format '{{.Digest}}' 2>/dev/null || echo "Local")"
_cuda_digest="$(CONTAINERS_STORAGE_CONF="$CONF" podman --root "$STORE" image inspect localhost/mios-cuda --format '{{.Digest}}' 2>/dev/null || echo "Local")"
install -d -m 0755 "$SBOM_DIR"
printf '%s\t%s\t%s\n' "localhost/mios-sys:latest" "${_sys_digest:-local}" "sys" >> "$SBOM_DIR/bound-images.tsv"
printf '%s\t%s\t%s\n' "localhost/mios-cuda:latest" "${_cuda_digest:-local}" "cuda" >> "$SBOM_DIR/bound-images.tsv"

log "Pruning build-stage images from ${STORE}"
while read -r _img; do
    case "$_img" in
        localhost/mios-sys:latest|localhost/mios-cuda:latest|"<none>:<none>") continue ;;
    esac
    CONTAINERS_STORAGE_CONF="$CONF" podman --root "$STORE" --runroot "$SCRATCH/run" rmi -f "$_img" >/dev/null 2>&1 || true
done < <(CONTAINERS_STORAGE_CONF="$CONF" podman --root "$STORE" images --format '{{.Repository}}:{{.Tag}}' 2>/dev/null | sort -u)
CONTAINERS_STORAGE_CONF="$CONF" podman --root "$STORE" --runroot "$SCRATCH/run" image prune -f >/dev/null 2>&1 || true

log "Consolidated shared base images built successfully"
