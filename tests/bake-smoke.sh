#!/usr/bin/env bash
# AI-hint: Runtime smoke test harness that boots a built MiOS container image to verify load-bearing binaries, units, and Python compilation.
# Usage: tests/bake-smoke.sh [image-ref] (default: localhost/mios:latest)
set -euo pipefail

IMAGE_REF="${1:-localhost/mios:latest}"

echo "[bake-smoke] Running runtime smoke checks against container image: ${IMAGE_REF}"

if ! command -v podman >/dev/null 2>&1; then
    echo "ERROR: podman executable not found in PATH" >&2
    exit 1
fi

PODMAN_CMD="podman"
if [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1; then
    PODMAN_CMD="sudo podman"
fi

${PODMAN_CMD} run --rm "${IMAGE_REF}" bash -lc '
    set -e
    python3 -m py_compile /usr/lib/mios/agent-pipe/server.py && echo "agent-pipe compile: OK"
    for b in flatpak-launch mios-pc-control mios-launcher-daemon \
             mios-flatpak-icon-sanitize; do
      test -e "/usr/libexec/mios/$b" || { echo "MISSING: /usr/libexec/mios/$b"; exit 1; }
    done
    echo "libexec shims: OK"
    test -f /usr/lib/systemd/system/mios-wsl-interop-priority.service \
      && echo "interop-priority svc: OK" || { echo "MISSING interop svc"; exit 1; }
    echo "SMOKE_RUN_PASS"
'

echo "[bake-smoke] PASS: All smoke assertions passed clean."
exit 0
