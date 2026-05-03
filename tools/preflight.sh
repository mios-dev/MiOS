#!/usr/bin/env bash
# 'MiOS' preflight check — verifies build prerequisites
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { printf "${GREEN}[OK]${NC}  %s\n" "$*"; }
fail() { printf "${RED}[FAIL]${NC} %s\n" "$*" >&2; }
warn() { printf "${YELLOW}[WARN]${NC} %s\n" "$*"; }

ERRORS=0

echo "'MiOS' v$(cat "$(dirname "$0")/../VERSION" 2>/dev/null || echo '?') — Pre-flight Check"

for cmd in podman git just; do
    if command -v "$cmd" >/dev/null 2>&1; then ok "$cmd found"; else fail "$cmd not found"; ERRORS=$((ERRORS+1)); fi
done

# Disk space (need at least 20G free)
AVAIL_GB=$(df -BG . | awk 'NR==2 {gsub("G",""); print $4}')
if [[ "${AVAIL_GB:-0}" -ge 20 ]]; then
    ok "Disk space: ${AVAIL_GB}G available"
else
    warn "Disk space: ${AVAIL_GB}G available (recommend 20G+ for OCI build cache)"
fi

# Containerfile present
if [[ -f "$(dirname "$0")/../Containerfile" ]]; then ok "Containerfile present"; else fail "Containerfile missing"; ERRORS=$((ERRORS+1)); fi

if [[ "$ERRORS" -gt 0 ]]; then
    echo ""
    fail "Pre-flight failed with $ERRORS error(s). Resolve above before building."
    exit 1
fi

echo ""
ok "All pre-flight checks passed."
