#!/usr/bin/env bash
# AI-hint: Proves placement failover ladder against fixtures, running the REAL functions from blade.sh.
# AI-doc: usr/share/doc/mios/manual/tests.md
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT}/usr/libexec/mios/role-apply"
LIB="${ROOT}/usr/lib/mios/blade.sh"
PASS=0

log() { printf '[placement-failover] %s\n' "$*"; }
die() { printf '[placement-failover] ERROR: %s\n' "$*" >&2; exit 1; }
ok()  { PASS=$((PASS + 1)); log "ok: $*"; }

[[ -r "$SCRIPT" ]] || die "role-apply missing: $SCRIPT"
[[ -r "$LIB" ]]    || die "blade.sh missing: $LIB"
grep -q '_resolve_placement_failover' "$SCRIPT" || die "role-apply must call _resolve_placement_failover"

FIXTURE="$(mktemp -d)"
trap 'rm -rf "$FIXTURE"' EXIT

export FAILOVER_STATE_DIR="${FIXTURE}/failover"
mkdir -p "$FAILOVER_STATE_DIR"
export MIOS_USR_DIR="${ROOT}/usr/lib/mios"
export MIOS_VENDOR_TOML="${FIXTURE}/mios.toml"
export MIOS_HOST_TOML="/dev/null"
export MIOS_USER_TOML="/dev/null"
export MIOS_VENDOR_TOML_D="${FIXTURE}/empty.d"
export MIOS_HOST_TOML_D="${FIXTURE}/empty.d"
export MIOS_USER_TOML_D="${FIXTURE}/empty.d"
mkdir -p "${FIXTURE}/empty.d"

# shellcheck source=/dev/null
source "$LIB"

resolve() { _resolve_placement_failover "$@" | cut -f1; }
verdict() { _resolve_placement_failover "$@" | cut -f2; }
detail()  { _resolve_placement_failover "$@" | cut -f3; }

# --- Test 1: Real SSOT order (local -> localhost -> cluster) at fail_checks boundaries ---
cat > "$MIOS_VENDOR_TOML" <<'EOF'
[blade.placement]
failover_order = ["local", "localhost", "cluster"]

[blade.collapse]
fail_checks = 3
dwell_s = 30
recover_dwell_s = 120
EOF

export NOW_OVERRIDE=1000
[[ "$(resolve guest failed)" == "local" ]] || die "first check must resolve local"
export NOW_OVERRIDE=1001
[[ "$(resolve guest failed)" == "local" ]] || die "second check must resolve local"
export NOW_OVERRIDE=1002
[[ "$(resolve guest failed)" == "localhost" ]] || die "third check (fail_checks boundary) must transition to localhost"
ok "fail_checks boundary (3 fails) transitions local -> localhost"

# --- Test 2: Flapping inside recover_dwell_s is suppressed ---
export NOW_OVERRIDE=1010
[[ "$(resolve guest failed)" == "localhost" ]] || die "check 4 must stay localhost"
export NOW_OVERRIDE=1011
[[ "$(resolve guest failed)" == "localhost" ]] || die "check 5 must stay localhost"
export NOW_OVERRIDE=1012
res="$(_resolve_placement_failover guest failed)"
tier="$(printf '%s\n' "$res" | cut -f1)"
v="$(printf '%s\n' "$res" | cut -f2)"
[[ "$tier" == "localhost" ]] || die "check 6 inside recover_dwell_s must stay localhost, got '$tier'"
[[ "$v" == "flapping_suppressed" ]] || die "check 6 must report flapping_suppressed, got '$v'"
ok "flapping inside recover_dwell_s is suppressed (flapping_suppressed)"

# --- Test 3: Advance past recover_dwell_s transitions to cluster ---
export NOW_OVERRIDE=1200
[[ "$(resolve guest failed)" == "cluster" ]] || die "check 7 after recover_dwell_s must transition to cluster, got '$(resolve guest failed)'"
ok "transition to cluster after recover_dwell_s elapses"

# --- Test 4: Reordered fixture produces a different sequence ---
cat > "$MIOS_VENDOR_TOML" <<'EOF'
[blade.placement]
failover_order = ["localhost", "local", "cluster"]

[blade.collapse]
fail_checks = 3
dwell_s = 30
recover_dwell_s = 120
EOF

rm -rf "${FAILOVER_STATE_DIR:?}"/*
export NOW_OVERRIDE=2000
[[ "$(resolve guest failed)" == "localhost" ]] || die "reordered check 1 must be localhost"
export NOW_OVERRIDE=2001
[[ "$(resolve guest failed)" == "localhost" ]] || die "reordered check 2 must be localhost"
export NOW_OVERRIDE=2002
[[ "$(resolve guest failed)" == "local" ]] || die "reordered check 3 must transition to local"
ok "reordered fixture produces localhost -> local -> cluster"

# --- Test 5: Negative control - unknown tier ("cloud") fails naming the bad value ---
cat > "$MIOS_VENDOR_TOML" <<'EOF'
[blade.placement]
failover_order = ["local", "cloud"]
EOF

rm -rf "${FAILOVER_STATE_DIR:?}"/*
out="$(_resolve_placement_failover guest failed 2>&1 || true)"
[[ "$out" == *"cloud"* ]] || die "unknown tier 'cloud' must fail naming the bad value, got: $out"
ok "unknown tier 'cloud' is refused naming the bad value"

# --- Test 6: Negative control - empty failover_order fails ---
cat > "$MIOS_VENDOR_TOML" <<'EOF'
[blade.placement]
failover_order = []
EOF

rm -rf "${FAILOVER_STATE_DIR:?}"/*
out="$(_resolve_placement_failover guest failed 2>&1 || true)"
[[ "$out" == *"empty failover_order"* ]] || die "empty failover_order must fail, got: $out"
ok "empty failover_order is refused"

# --- Test 7: Healthy check resets fail_count before boundary ---
cat > "$MIOS_VENDOR_TOML" <<'EOF'
[blade.placement]
failover_order = ["local", "localhost", "cluster"]

[blade.collapse]
fail_checks = 3
dwell_s = 30
recover_dwell_s = 120
EOF

rm -rf "${FAILOVER_STATE_DIR:?}"/*
export NOW_OVERRIDE=3000
[[ "$(resolve guest failed)" == "local" ]] || die "reset check 1 failed"
export NOW_OVERRIDE=3001
[[ "$(resolve guest failed)" == "local" ]] || die "reset check 2 failed"
export NOW_OVERRIDE=3002
[[ "$(resolve guest ok)" == "local" ]] || die "healthy check must stay local"
export NOW_OVERRIDE=3003
[[ "$(resolve guest failed)" == "local" ]] || die "check after reset must stay local (fail_count was 0)"
export NOW_OVERRIDE=3004
[[ "$(resolve guest failed)" == "local" ]] || die "second fail check after reset must stay local"
export NOW_OVERRIDE=3005
[[ "$(resolve guest failed)" == "localhost" ]] || die "third fail check after reset must transition to localhost"
ok "healthy status resets fail_count before boundary"

log "PASS: ${PASS}/7 assertions"
