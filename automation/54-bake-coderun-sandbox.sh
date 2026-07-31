#!/bin/bash
# AI-hint: Bakes the coderun-sandbox container image during the system build. It stages the mios-codemode-api.py shim so the container has everything it needs.
# AI-related: /etc/mios/containers/coderun-sandbox/Dockerfile, mios-codemode-api.py

set -euo pipefail
source "$(dirname "$0")/lib/common.sh"

log "54-bake: Baking mios-coderun-sandbox container image..."

if ! command -v podman >/dev/null 2>&1; then
    log "  [!] podman not found, skipping image bake (OK in chroot if deferred)"
    exit 0
fi

CTX="${CTX:-/ctx}"
SRC_DIR="${CTX}/etc/mios/containers/coderun-sandbox"
SHIM_SRC="${CTX}/usr/libexec/mios/mios-codemode-api.py"

if [[ ! -d "${SRC_DIR}" ]]; then
    die "missing ${SRC_DIR}"
fi

# Stage the shim into the build directory so Dockerfile can COPY it
cp "${SHIM_SRC}" "${SRC_DIR}/mios_tools.py"

log "  Building localhost/mios-coderun-sandbox:latest..."
podman build -t localhost/mios-coderun-sandbox:latest "${SRC_DIR}"
log "  baked localhost/mios-coderun-sandbox:latest"
