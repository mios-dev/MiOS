#!/bin/bash
# AI-hint: Bakes the coderun-sandbox container image during the system build. It stages the mios-codemode-api.py shim so the container has everything it needs.
# AI-related: /etc/mios/containers/coderun-sandbox/Dockerfile, mios-codemode-api.py

set -euo pipefail
source "$(dirname "$0")/lib/common.sh"

log "54-bake: Baking mios-coderun-sandbox container image"

if ! command -v podman >/dev/null 2>&1; then
    log "  [!] podman not found, skipping image bake"
    exit 0
fi

CTX="${CTX:-/ctx}"
SRC_DIR="${CTX}/etc/mios/containers/coderun-sandbox"
SHIM_SRC="${CTX}/usr/libexec/mios/mios-codemode-api.py"

if [[ ! -d "${SRC_DIR}" ]]; then
    die "Missing ${SRC_DIR}"
fi

cp "${SHIM_SRC}" "${SRC_DIR}/mios_tools.py"

log "  Building localhost/mios-coderun-sandbox:latest"
_crs_built=0
for _attempt in 1 2 3; do
    if podman build \
        --network=host \
        --cap-add all \
        --security-opt seccomp=unconfined \
        --security-opt apparmor=unconfined \
        -t localhost/mios-coderun-sandbox:latest "${SRC_DIR}"; then
        _crs_built=1
        break
    fi
    log "  [!] coderun-sandbox build attempt ${_attempt}/3 failed"
    [[ "${_attempt}" -lt 3 ]] && sleep $(( _attempt * 5 ))
done
if [[ "${_crs_built}" == 1 ]] && podman image exists localhost/mios-coderun-sandbox:latest; then
    log "  baked localhost/mios-coderun-sandbox:latest"
else
    log "  [!] coderun-sandbox bake failed after 3 attempts"
fi
exit 0
