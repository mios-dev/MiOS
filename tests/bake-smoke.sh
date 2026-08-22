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

_ssot_list() {
    python3 -c "
import sys, tomllib
t = tomllib.load(open('${TOML_PATH}', 'rb'))
v = t.get('testing', {}).get('smoke_components', {}).get('$1', [])
if not v:
    sys.stderr.write('empty\n'); sys.exit(1)
print(' '.join(v))
" || {
        echo "ERROR: mios.toml [testing.smoke_components].$1 is missing or empty --" \
             "refusing to report PASS without assertions" >&2
        exit 1
    }
}

SHIMS=$(_ssot_list shims)
UNITS=$(_ssot_list units)
PY_ENTRIES=$(_ssot_list python_entries)

# Counts are passed into the container so it can prove it ran every assertion,
# rather than trusting that the loops iterated.
N_SHIMS=$(printf '%s\n' ${SHIMS} | grep -c .)
N_UNITS=$(printf '%s\n' ${UNITS} | grep -c .)
N_PY=$(printf '%s\n' ${PY_ENTRIES} | grep -c .)
echo "[bake-smoke] SSOT components: ${N_PY} python, ${N_SHIMS} shims, ${N_UNITS} units"

# errexit would abort ON this pipeline, so the FAIL branches below could never report.
set +e
${PODMAN_CMD} run --rm "${IMAGE_REF}" bash -lc "
    set -e
    n=0
    for py in ${PY_ENTRIES}; do
        python3 -m py_compile \"/\${py}\" && echo \"py_compile \${py}: OK\"
        n=\$((n+1))
    done
    [ \"\$n\" -eq ${N_PY} ] || { echo \"ASSERTION COUNT MISMATCH: python \$n != ${N_PY}\"; exit 1; }

    n=0
    for s in ${SHIMS}; do
        test -e \"/\${s}\" || { echo \"MISSING shim: /\${s}\"; exit 1; }
        n=\$((n+1))
    done
    [ \"\$n\" -eq ${N_SHIMS} ] || { echo \"ASSERTION COUNT MISMATCH: shims \$n != ${N_SHIMS}\"; exit 1; }
    echo \"shims: OK (\$n)\"

    n=0
    for u in ${UNITS}; do
        test -f \"/\${u}\" || { echo \"MISSING unit: /\${u}\"; exit 1; }
        n=\$((n+1))
    done
    [ \"\$n\" -eq ${N_UNITS} ] || { echo \"ASSERTION COUNT MISMATCH: units \$n != ${N_UNITS}\"; exit 1; }
    echo \"units: OK (\$n)\"

    echo \"SMOKE_RUN_PASS\"
" 2> >(sed 's/^/[bake-smoke][podman-stderr] /' >&2) | tee /tmp/mios-bake-smoke.$$.log

# The container's own exit status is what matters -- `| tee` would otherwise
# hand us tee's. And the marker must actually appear: a run that dies after the
# last echo but before exiting non-zero would otherwise read as a pass.
run_rc=${PIPESTATUS[0]}
set -e
if [ "${run_rc}" -ne 0 ]; then
    rm -f "/tmp/mios-bake-smoke.$$.log"
    echo "[bake-smoke] FAIL: container assertions exited ${run_rc}" >&2
    exit 1
fi
if ! grep -q '^SMOKE_RUN_PASS$' "/tmp/mios-bake-smoke.$$.log"; then
    rm -f "/tmp/mios-bake-smoke.$$.log"
    echo "[bake-smoke] FAIL: SMOKE_RUN_PASS marker absent -- assertions did not complete" >&2
    exit 1
fi
rm -f "/tmp/mios-bake-smoke.$$.log"

echo "[bake-smoke] PASS: ${N_PY} python + ${N_SHIMS} shim + ${N_UNITS} unit assertions verified in ${IMAGE_REF}"
exit 0
