#!/usr/bin/env bash
# AI-hint: Self-contained test harness for automation/38-ssot-lint.sh -- builds throwaway fixture trees (a fully-wired key, a both-sides orphan, a userenv-only and a render-only half-orphan) to assert the lint's PASS/FAIL exit codes and orphan detection, then asserts it flags the real known dead key (MIOS_SGLANG_TOOL_PARSER) in the live repo tree.
# AI-related: ../38-ssot-lint.sh, ../15-render-quadlets.sh, ../../tools/lib/userenv.sh, ../../usr/share/containers/systemd
# AI-functions: _mk_fixture, _expect, main
# automation/tests/test-38-ssot-lint.sh
# ----------------------------------------------------------------------------
# No deps beyond bash + grep + mktemp. Exits 0 if all assertions pass, 1 on
# the first failure. Run standalone:  automation/tests/test-38-ssot-lint.sh
# ----------------------------------------------------------------------------
set -euo pipefail

_self_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$_self_dir/../.." && pwd)"
LINT="$REPO_ROOT/automation/38-ssot-lint.sh"

pass=0
fail=0
tmp=""
trap '[[ -n "$tmp" ]] && rm -rf "$tmp"' EXIT

_ok()  { echo "  PASS: $1"; pass=$((pass + 1)); }
_bad() { echo "  FAIL: $1" >&2; fail=$((fail + 1)); }

# Build a fixture root: userenv.sh + 15-render-quadlets.sh + one .container.
# Args: <root> <userenv-content> <render-content> <container-exec-line>
_mk_fixture() {
    local root="$1" ue="$2" rq="$3" exec_line="$4"
    mkdir -p "$root/tools/lib" "$root/automation" "$root/usr/share/containers/systemd"
    printf '%s\n' "$ue" > "$root/tools/lib/userenv.sh"
    printf '%s\n' "$rq" > "$root/automation/15-render-quadlets.sh"
    cat > "$root/usr/share/containers/systemd/fixture.container" <<EOF
[Container]
Image=localhost/fixture:latest
$exec_line
EOF
}

# Run the lint against a fixture root; echo exit code (never aborts the test
# script even when the lint exits non-zero).
_run_lint() {
    local root="$1"
    MIOS_SSOT_LINT_ROOT="$root" bash "$LINT" >/dev/null 2>&1 && echo 0 || echo $?
}

# _expect <label> <expected-exit> <actual-exit>
_expect() {
    local label="$1" want="$2" got="$3"
    if [[ "$got" == "$want" ]]; then _ok "$label (exit $got)"; else _bad "$label: want exit $want, got $got"; fi
}

main() {
    echo "[test-38-ssot-lint] fixture cases"
    tmp="$(mktemp -d)"

    local UE_GOOD RQ_GOOD UE_EMPTY RQ_EMPTY
    UE_GOOD='slots=(
    ("foo.bar", "MIOS_FIXTURE_OK"),
)'
    RQ_GOOD='envsubst "${MIOS_FIXTURE_OK}"
for var in MIOS_FIXTURE_OK; do :; done'
    UE_EMPTY='# no slots here'
    RQ_EMPTY='# no allowlist here'

    # Case 1: fully wired -> PASS (exit 0)
    _mk_fixture "$tmp/c1" "$UE_GOOD" "$RQ_GOOD" 'Exec=run --x ${MIOS_FIXTURE_OK:-d}'
    _expect "fully-wired key passes" 0 "$(_run_lint "$tmp/c1")"

    # Case 2: orphan on BOTH ends -> FAIL (exit 1)
    _mk_fixture "$tmp/c2" "$UE_EMPTY" "$RQ_EMPTY" 'Exec=run --x ${MIOS_FIXTURE_DEAD:-d}'
    _expect "both-sides orphan fails" 1 "$(_run_lint "$tmp/c2")"

    # Case 3: userenv-only (missing render allowlist) -> FAIL
    _mk_fixture "$tmp/c3" "$UE_GOOD" "$RQ_EMPTY" 'Exec=run --x ${MIOS_FIXTURE_OK:-d}'
    _expect "render-allowlist half-orphan fails" 1 "$(_run_lint "$tmp/c3")"

    # Case 4: render-only (missing userenv slot) -> FAIL
    _mk_fixture "$tmp/c4" "$UE_EMPTY" "$RQ_GOOD" 'Exec=run --x ${MIOS_FIXTURE_OK:-d}'
    _expect "userenv half-orphan fails" 1 "$(_run_lint "$tmp/c4")"

    # Case 5: a var only MENTIONED in a userenv comment must NOT count as wired
    _mk_fixture "$tmp/c5" '# MIOS_FIXTURE_OK is great' "$RQ_GOOD" 'Exec=run ${MIOS_FIXTURE_OK:-d}'
    _expect "comment-only mention does not satisfy userenv" 1 "$(_run_lint "$tmp/c5")"

    # Case 6: the Environment=LHS literal name is NOT a placeholder reference.
    # Here MIOS_FIXTURE_OK appears only as the LHS being SET; the RHS uses an
    # unrelated, fully-wired var, so there is no orphan -> PASS.
    _mk_fixture "$tmp/c6" "$UE_GOOD" "$RQ_GOOD" 'Environment=MIOS_FIXTURE_OK=${MIOS_FIXTURE_OK:-d}'
    _expect "Environment= LHS literal is not double-counted" 0 "$(_run_lint "$tmp/c6")"

    # Case 7: soft mode reports orphans but exits 0
    _mk_fixture "$tmp/c7" "$UE_EMPTY" "$RQ_EMPTY" 'Exec=run ${MIOS_FIXTURE_DEAD:-d}'
    local soft
    soft="$(MIOS_SSOT_LINT_ROOT="$tmp/c7" MIOS_SSOT_LINT_SOFT=1 bash "$LINT" >/dev/null 2>&1 && echo 0 || echo $?)"
    _expect "soft mode exits 0 despite orphan" 0 "$soft"

    # Case 8: live repo tree -- must flag the real known dead key.
    echo "[test-38-ssot-lint] live-tree case"
    local live_out
    live_out="$(MIOS_SSOT_LINT_ROOT="$REPO_ROOT" bash "$LINT" 2>&1 || true)"
    if printf '%s' "$live_out" | grep -q 'MIOS_SGLANG_TOOL_PARSER'; then
        _ok "live tree flags known dead key MIOS_SGLANG_TOOL_PARSER"
    else
        _bad "live tree did NOT flag MIOS_SGLANG_TOOL_PARSER"
    fi

    echo "[test-38-ssot-lint] ---------------------------------------"
    echo "[test-38-ssot-lint] $pass passed, $fail failed."
    [[ "$fail" -eq 0 ]]
}

main "$@"
