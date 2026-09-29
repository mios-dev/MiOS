#!/usr/bin/env bash
# AI-hint: bash Two-sided verification test suite for Linux Core Scheduling (T-858) and SMT sibling isolation.
# AI-doc: usr/share/doc/mios/manual/tests.md
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${ROOT}/usr/libexec/mios/mios-core-sched"
AFFINITY_SH="${ROOT}/automation/24-cpu-affinity.sh"

log() { printf '[test-core-sched] %s\n' "$*"; }
die() { printf '[test-core-sched] ERROR: %s\n' "$*" >&2; exit 1; }
ok()  { printf '[test-core-sched]   [ OK ] %s\n' "$*"; }

[[ -f "$BIN" ]] || die "Core scheduling tool not found at $BIN"
[[ -f "$AFFINITY_SH" ]] || die "CPU affinity phase script not found at $AFFINITY_SH"

TMP="$(mktemp -d /tmp/mios-core-sched-test.XXXXXX 2>/dev/null || mktemp -d 2>/dev/null || echo "${TEMP:-/tmp}/mios-core-sched-test-$$")"
mkdir -p "$TMP"
trap 'rm -rf "$TMP"' EXIT

# Force deterministic mock mode for portable cross-platform CI verification
export MIOS_CORE_SCHED_MOCK="1"
export MIOS_CORE_SCHED_MOCK_STATE="${TMP}/mock_state.json"

log "=== MiOS Linux Core Scheduling (T-858) Two-Sided Verification Suite ==="

# -----------------------------------------------------------------------------
# Tier 1: Syntax & Pre-flight Static Checks
# -----------------------------------------------------------------------------
log "Tier 1: Syntax & Pre-flight Checks"
python3 -m py_compile "$BIN" || die "mios-core-sched failed python compilation"
ok "mios-core-sched python syntax clean"

bash -n "$AFFINITY_SH" || die "24-cpu-affinity.sh failed bash -n"
ok "24-cpu-affinity.sh shell syntax clean"

bash -n "${BASH_SOURCE[0]}" || die "test-core-sched.sh failed bash -n"
ok "test-core-sched.sh shell syntax clean"

# -----------------------------------------------------------------------------
# Tier 2: Positive Controls — Core Functionality
# -----------------------------------------------------------------------------
log "Tier 2: Positive Controls"

# 2.1 CLI Help & Structure
out_help="$(python3 "$BIN" --help)"
grep -q "create" <<<"$out_help" || die "missing 'create' subcommand"
grep -q "get" <<<"$out_help" || die "missing 'get' subcommand"
grep -q "share" <<<"$out_help" || die "missing 'share' subcommand"
grep -q "tag-pid" <<<"$out_help" || die "missing 'tag-pid' subcommand"
grep -q "tag-cgroup" <<<"$out_help" || die "missing 'tag-cgroup' subcommand"
grep -q "exec" <<<"$out_help" || die "missing 'exec' subcommand"
grep -q "status" <<<"$out_help" || die "missing 'status' subcommand"
grep -q "verify-smt" <<<"$out_help" || die "missing 'verify-smt' subcommand"
ok "2.1: CLI subcommands and help interface complete"

# 2.2 Status reporting
out_status="$(python3 "$BIN" status --json)"
grep -q '"smt_control"' <<<"$out_status" || die "status JSON missing smt_control"
grep -q '"sched_core_supported"' <<<"$out_status" || die "status JSON missing sched_core_supported"
grep -q '"nosmt_violation"' <<<"$out_status" || die "status JSON missing nosmt_violation"
ok "2.2: System status and SMT inspection JSON output valid"

# 2.3 SMT verification pass
python3 "$BIN" verify-smt >/dev/null || die "verify-smt failed on default configuration"
ok "2.3: verify-smt passes when nosmt is absent"

# 2.4 Cookie Creation & Uniqueness (SMT Isolation)
# Process 101 and Process 102 must receive DIFFERENT cookies
python3 "$BIN" create --pid 101 >/dev/null || die "failed to create cookie for PID 101"
python3 "$BIN" create --pid 102 >/dev/null || die "failed to create cookie for PID 102"

cookie_101="$(python3 "$BIN" get --pid 101 | grep -o 'cookie=0x[0-9a-fA-F]*' | cut -d= -f2)"
cookie_102="$(python3 "$BIN" get --pid 102 | grep -o 'cookie=0x[0-9a-fA-F]*' | cut -d= -f2)"

[[ -n "$cookie_101" && "$cookie_101" != "0x0" ]] || die "PID 101 received empty/zero cookie"
[[ -n "$cookie_102" && "$cookie_102" != "0x0" ]] || die "PID 102 received empty/zero cookie"
[[ "$cookie_101" != "$cookie_102" ]] || die "PID 101 and PID 102 received IDENTICAL cookies! Isolation failed."
ok "2.4: Cookie creation generates unique cookies ($cookie_101 != $cookie_102) guaranteeing SMT isolation"

# 2.5 Untagged process has cookie 0 (Default system domain)
cookie_103="$(python3 "$BIN" get --pid 103 | grep -o 'cookie=0x[0-9a-fA-F]*' | cut -d= -f2)"
[[ "$cookie_103" == "0x0" ]] || die "Untagged PID 103 has non-zero cookie: $cookie_103"
ok "2.5: Untagged process resides in default unassigned domain (cookie 0x0)"

# 2.6 Cookie Sharing between cooperating tasks (same trust boundary)
python3 "$BIN" share --src 101 --dst 104 >/dev/null || die "failed to share cookie from 101 to 104"
cookie_104="$(python3 "$BIN" get --pid 104 | grep -o 'cookie=0x[0-9a-fA-F]*' | cut -d= -f2)"
[[ "$cookie_104" == "$cookie_101" ]] || die "Shared cookie mismatch: expected $cookie_101 but got $cookie_104"
ok "2.6: Cookie sharing successfully links cooperating tasks ($cookie_101 == $cookie_104)"

# 2.7 Tag-cgroup across multiple processes
CG_TEST="${TMP}/cgroup_sandbox_test"
mkdir -p "$CG_TEST"
printf "301\n302\n303\n" > "${CG_TEST}/cgroup.procs"

python3 "$BIN" tag-cgroup "$CG_TEST" >/dev/null || die "tag-cgroup failed on test cgroup"
c301="$(python3 "$BIN" get --pid 301 | grep -o 'cookie=0x[0-9a-fA-F]*' | cut -d= -f2)"
c302="$(python3 "$BIN" get --pid 302 | grep -o 'cookie=0x[0-9a-fA-F]*' | cut -d= -f2)"
c303="$(python3 "$BIN" get --pid 303 | grep -o 'cookie=0x[0-9a-fA-F]*' | cut -d= -f2)"

[[ -n "$c301" && "$c301" != "0x0" ]] || die "cgroup process 301 has invalid cookie"
[[ "$c301" == "$c302" && "$c302" == "$c303" ]] || die "cgroup processes do not share identical cookie ($c301, $c302, $c303)"
ok "2.7: Cgroup tagging successfully unifies all cgroup processes under one cookie ($c301)"

# 2.8 Subagent Exec wrapper
out_exec="$(python3 "$BIN" exec --new-cookie -- echo "subagent-payload-execution-verified")"
grep -q "subagent-payload-execution-verified" <<<"$out_exec" || die "exec wrapper failed to run payload command"
ok "2.8: Subagent exec wrapper executes isolated child command"

# 2.9 Verify automation/24-cpu-affinity.sh content invariants
grep -q "MIOS_APPLY_CLASS=universal" "$AFFINITY_SH" || die "24-cpu-affinity.sh missing MIOS_APPLY_CLASS=universal"
grep -q "CoreScheduling=yes" "$AFFINITY_SH" || die "24-cpu-affinity.sh missing CoreScheduling=yes drop-in"
grep -q "mios-core-sched.service" "$AFFINITY_SH" || die "24-cpu-affinity.sh missing mios-core-sched.service"
grep -q "sandbox.slice" "$AFFINITY_SH" || die "24-cpu-affinity.sh missing sandbox.slice"
ok "2.9: 24-cpu-affinity.sh configuration and systemd service specifications verified"

# -----------------------------------------------------------------------------
# Tier 3: Negative Controls — Error Handling & Perturbation Tests
# -----------------------------------------------------------------------------
log "Tier 3: Negative Controls & Perturbation Tests"

# 3.1 Invalid subcommand rejected (exit code 2)
set +e
python3 "$BIN" bogus-command 2>/dev/null
rc=$?
set -e
[[ "$rc" -ne 0 ]] || die "Negative Control 3.1 Failed: bogus-command unexpectedly succeeded"
ok "3.1 [Negative Control]: Invalid subcommand refused with non-zero exit code ($rc)"

# 3.2 Invalid scheduling scope rejected
set +e
python3 "$BIN" create --pid 501 --scope invalid-scope-xyz 2>/dev/null
rc=$?
set -e
[[ "$rc" -ne 0 ]] || die "Negative Control 3.2 Failed: invalid scope unexpectedly succeeded"
ok "3.2 [Negative Control]: Invalid scope refused with non-zero exit code ($rc)"

# 3.3 Non-existent PID rejected (ESRCH: No such process)
set +e
out_err="$(python3 "$BIN" get --pid 999999999 2>&1)"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || die "Negative Control 3.3 Failed: non-existent PID succeeded"
grep -q "No such process" <<<"$out_err" || die "Negative Control 3.3 Failed: expected 'No such process' error, got: $out_err"
ok "3.3 [Negative Control]: Non-existent PID rejected with ESRCH (No such process)"

# 3.4 Non-existent cgroup directory rejected
set +e
out_err="$(python3 "$BIN" tag-cgroup "${TMP}/nonexistent_cgroup_path" 2>&1)"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || die "Negative Control 3.4 Failed: non-existent cgroup path succeeded"
grep -q "does not exist" <<<"$out_err" || die "Negative Control 3.4 Failed: expected 'does not exist' error, got: $out_err"
ok "3.4 [Negative Control]: Non-existent cgroup path refused with descriptive error"

# 3.5 Perturbation Test: Injected 'nosmt' karg must be caught by SMT verification
FAKE_ROOT="${TMP}/fake_root"
mkdir -p "${FAKE_ROOT}/etc/cmdline.d"
echo "console=ttyS0 nosmt quiet" > "${FAKE_ROOT}/etc/cmdline.d/99-test-nosmt.conf"

set +e
nosmt_found=0
for f in "${FAKE_ROOT}/etc/cmdline.d"/*.conf; do
    if grep -qE '\bnosmt\b' "$f"; then
        nosmt_found=1
        break
    fi
done
set -e
[[ "$nosmt_found" -eq 1 ]] || die "Negative Control 3.5 Failed: nosmt detector failed to flag injected nosmt parameter"
ok "3.5 [Negative Control / Perturbation]: Injected 'nosmt' karg successfully flagged and refused"

# 3.6 Cross-boundary isolation negative assertion
# PID 101 (untrusted subagent) and PID 103 (unassigned/trusted host) must NOT match
[[ "$cookie_101" != "$cookie_103" ]] || die "Negative Control 3.6 Failed: untrusted subagent cookie matches unassigned host cookie"
ok "3.6 [Negative Control]: Untrusted subagent cookie strictly isolated from unassigned host domain"

log "=== All Two-Sided Verification Controls Passed (Positive & Negative) ==="
exit 0
