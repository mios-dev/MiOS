#!/usr/bin/env bash
# AI-hint: Runtime smoke test harness that boots a built MiOS container image to verify load-bearing binaries, units, and Python compilation from SSOT.
set -euo pipefail

IMAGE_REF="${1:-localhost/mios:latest}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TOML_PATH="${ROOT}/usr/share/mios/mios.toml"

echo "[bake-smoke] Running runtime smoke checks against container image: ${IMAGE_REF}"

if ! command -v podman >/dev/null 2>&1; then
    echo "ERROR: podman executable not found in PATH" >&2
    exit 1
fi

PODMAN_CMD="podman"
if [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1; then
    PODMAN_CMD="sudo podman"
fi

SHIMS=$(python3 -c "import tomllib; t = tomllib.load(open('${TOML_PATH}', 'rb')); print(' '.join(t.get('testing', {}).get('smoke_components', {}).get('shims', [])))" 2>/dev/null || echo "Usr/libexec/mios/flatpak-launch usr/libexec/mios/mios-pc-control usr/libexec/mios/mios-launcher-daemon usr/libexec/mios/mios-flatpak-icon-sanitize")
UNITS=$(python3 -c "import tomllib; t = tomllib.load(open('${TOML_PATH}', 'rb')); print(' '.join(t.get('testing', {}).get('smoke_components', {}).get('units', [])))" 2>/dev/null || echo "Usr/lib/systemd/system/mios-wsl-interop-priority.service")
PY_ENTRIES=$(python3 -c "import tomllib; t = tomllib.load(open('${TOML_PATH}', 'rb')); print(' '.join(t.get('testing', {}).get('smoke_components', {}).get('python_entries', [])))" 2>/dev/null || echo "Usr/lib/mios/agent-pipe/server.py")

${PODMAN_CMD} run --rm "${IMAGE_REF}" bash -lc "
    set -e
    for py in ${PY_ENTRIES}; do
        python3 -m py_compile \"/\${py}\" && echo \"py_compile \${py}: OK\"
    done
    for s in ${SHIMS}; do
        test -e \"/\${s}\" || { echo \"MISSING shim: /\${s}\"; exit 1; }
    done
    echo \"shims: OK\"
    for u in ${UNITS}; do
        test -f \"/\${u}\" || { echo \"MISSING unit: /\${u}\"; exit 1; }
    done
    echo \"units: OK\"
    echo \"SMOKE_RUN_PASS\"
"

echo "[bake-smoke] PASS: All smoke assertions passed clean"
exit 0
