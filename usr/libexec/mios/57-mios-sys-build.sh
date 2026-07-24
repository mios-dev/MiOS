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
    source "$(dirname "$0")/../../lib/mios/paths.sh"
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
use_hard_links = "true"
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

# Build localhost/mios-sys
log "Building localhost/mios-sys..."
CONTAINERS_STORAGE_CONF="$CONF" CONTAINERS_REGISTRIES_CONF="$REG_CONF" TMPDIR="$SCRATCH/tmp" \
  podman --root "$STORE" --runroot "$SCRATCH/run" build \
  --network=host \
  --layers \
  -t localhost/mios-sys \
  --build-arg BASE_IMAGE="$BASE" \
  "/usr/share/mios/sys"

# Build localhost/mios-cuda
log "Building localhost/mios-cuda..."
CONTAINERS_STORAGE_CONF="$CONF" CONTAINERS_REGISTRIES_CONF="$REG_CONF" TMPDIR="$SCRATCH/tmp" \
  podman --root "$STORE" --runroot "$SCRATCH/run" build \
  --network=host \
  --layers \
  -t localhost/mios-cuda \
  --build-arg BASE_IMAGE="$BASE" \
  "/usr/share/mios/cuda"

# Record to SBOM (Software Bill of Materials)
SBOM_DIR="${SBOM_DIR:-/usr/share/mios/artifacts/sbom}"
_sys_digest="$(CONTAINERS_STORAGE_CONF="$CONF" podman --root "$STORE" image inspect localhost/mios-sys --format '{{.Digest}}' 2>/dev/null || echo "local")"
_cuda_digest="$(CONTAINERS_STORAGE_CONF="$CONF" podman --root "$STORE" image inspect localhost/mios-cuda --format '{{.Digest}}' 2>/dev/null || echo "local")"
install -d -m 0755 "$SBOM_DIR"
printf '%s\t%s\t%s\n' "localhost/mios-sys:latest" "${_sys_digest:-local}" "sys" >> "$SBOM_DIR/bound-images.tsv"
printf '%s\t%s\t%s\n' "localhost/mios-cuda:latest" "${_cuda_digest:-local}" "cuda" >> "$SBOM_DIR/bound-images.tsv"

log "Consolidated shared base images built successfully."
