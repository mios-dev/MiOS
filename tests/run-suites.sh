#!/usr/bin/env bash
# AI-hint: Runs one registered suite tier to completion and reports every failure, so a single run says everything that is wrong.
# AI-related: tools/ci-suites.py, usr/share/mios/mios.toml
#
# Sequential steps stop at the first failure, so each red run taught exactly one
# thing and the next failure cost another round trip. This runs the whole tier
# and reports all of it. Suites come from [ci] in the SSOT, which is also what
# check_ci_suite_coverage enforces, so a publisher cannot quietly run a
# different set from its sibling.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TIER="${1:-}"

if [[ -z "$TIER" ]]; then
    echo "usage: run-suites.sh <tier>   (tiers: $(python3 "${ROOT}/tools/ci-suites.py" --tier '' 2>&1 | sed -n 's/^unknown tier.*//p'))" >&2
    echo "       registered tiers are the keys of [ci.tiers] in usr/share/mios/mios.toml" >&2
    exit 2
fi

mapfile -t SUITES < <(cd "$ROOT" && MIOS_DRIFT_ROOT="$ROOT" python3 tools/ci-suites.py --tier "$TIER")
if [[ ${#SUITES[@]} -eq 0 ]]; then
    # An empty tier is a runner that reports success having done nothing, which
    # is the failure mode this whole registry exists to prevent.
    echo "::error::tier '${TIER}' resolved to zero suites" >&2
    exit 1
fi

echo "[run-suites] tier=${TIER} suites=${#SUITES[@]} root=${ROOT}"
FAILED=()
PASSED=0
for entry in "${SUITES[@]}"; do
    runner="${entry%%	*}"
    path="${entry#*	}"
    [[ -n "$path" ]] || continue
    start=$SECONDS
    if out="$(cd "$ROOT" && MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" \
              MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" \
              "$runner" "$path" 2>&1)"; then
        PASSED=$((PASSED + 1))
        echo "::group::[ OK ] ${path} ($((SECONDS - start))s)"
        printf '%s\n' "$out"
        echo "::endgroup::"
    else
        rc=$?
        FAILED+=("$path")
        echo "[FAIL] ${path} (exit ${rc}, $((SECONDS - start))s)"
        printf '%s\n' "$out"
        echo "::error file=${path}::${path} failed with exit ${rc}"
    fi
done

echo "[run-suites] tier=${TIER}: ${PASSED} passed, ${#FAILED[@]} failed"
if [[ ${#FAILED[@]} -gt 0 ]]; then
    printf '[run-suites]   failed: %s\n' "${FAILED[@]}" >&2
    exit 1
fi
