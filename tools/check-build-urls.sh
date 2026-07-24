#!/usr/bin/env bash
# AI-hint: Non-build-blocking pre-flight URL liveness probe for build-time assets.
# ============================================================================
# tools/check-build-urls.sh
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "[check-build-urls] Starting pre-flight build asset URL liveness probe..."

urls=(
    "https://raw.githubusercontent.com/anchore/syft/main/install.sh"
    "https://raw.githubusercontent.com/MiOS-DEV/MiOS-bootstrap/main/bootstrap.sh"
    "https://github.com"
)

failed=0
for url in "${urls[@]}"; do
    printf "  Probing %s ... " "$url"
    status="$(curl -sI --retry 3 --connect-timeout 10 -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")"
    if [[ "$status" =~ ^[23] ]]; then
        echo "OK (HTTP $status)"
    else
        echo "FAIL (HTTP $status)"
        failed=$((failed + 1))
    fi
done

if [[ "$failed" -gt 0 ]]; then
    echo "[check-build-urls] WARN: $failed URL(s) returned non-2xx/3xx status." >&2
    exit 1
else
    echo "[check-build-urls] PASS: All build URLs active and responsive."
    exit 0
fi
