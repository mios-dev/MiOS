#!/usr/bin/env bash
# AI-hint: Automated CI test suite for NUMA memory interleaving, bandwidth scaling (>400 GB/s), and core affinity pinning.
# AI-related: usr/libexec/mios/mios-numa-alloc, tests/test-numa-interleave-bandwidth.sh, usr/share/mios/mios.toml

set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
ALLOC_BIN="${ROOT_DIR}/usr/libexec/mios/mios-numa-alloc"

pass=0
fail=0

assert_pass() {
    echo "  PASS: $1"
    pass=$((pass + 1))
}

assert_fail() {
    echo "  FAIL: $1" >&2
    fail=$((fail + 1))
}

echo "[test-numa-interleave-bandwidth] === MiOS NUMA Memory Interleaver & Bandwidth Test Suite ==="

# 1. Verify mios-numa-alloc binary exists and is executable
if [[ -x "$ALLOC_BIN" ]]; then
    assert_pass "mios-numa-alloc exists and is executable at $ALLOC_BIN"
else
    assert_fail "mios-numa-alloc is missing or not executable"
fi

# 2. Test NUMA topology discovery
info_json="$("$ALLOC_BIN" --info 2>/dev/null)"
num_nodes="$(echo "$info_json" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('num_nodes', 0))")"
if [[ "$num_nodes" -ge 1 ]]; then
    assert_pass "Discovered valid NUMA topology (nodes: $num_nodes)"
else
    assert_fail "Failed to discover NUMA topology"
fi

# 3. Test dry-run execution with interleave and pinning
dry_run_out="$("$ALLOC_BIN" --interleave --pin-node=0 --dry-run /bin/true 2>&1)"
if echo "$dry_run_out" | grep -q "interleave=True"; then
    assert_pass "Dry-run validates interleave policy configuration"
else
    assert_fail "Dry-run did not show interleave=True"
fi

# 4. Run memory bandwidth scaling benchmark
echo "[test-numa-interleave-bandwidth] Executing multi-threaded NUMA bandwidth benchmark..."
bench_output="$("$ALLOC_BIN" --benchmark 2>/dev/null)"

speedup="$(echo "$bench_output" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('speedup_ratio', 0.0))")"
scaling_achieved="$(echo "$bench_output" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('scaling_achieved', False))")"
interleaved_bw="$(echo "$bench_output" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('interleaved', {}).get('aggregate_bandwidth_gbps', 0.0))")"
zero_migrations="$(echo "$bench_output" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('zero_migrations', False))")"

# 5. Assert bandwidth scaling ratio >= 1.8x
if python3 -c "import sys; sys.exit(0 if float('$speedup') >= 1.8 else 1)"; then
    assert_pass "NUMA interleaving achieved >= 1.8x speedup (measured: ${speedup}x)"
else
    assert_fail "NUMA interleaving speedup < 1.8x (measured: ${speedup}x)"
fi

# 6. Assert aggregate memory read throughput > 400.0 GB/s on composite channels
if python3 -c "import sys; sys.exit(0 if float('$interleaved_bw') >= 400.0 else 1)"; then
    assert_pass "Aggregate composite memory throughput >= 400.0 GB/s (measured: ${interleaved_bw} GB/s)"
else
    assert_fail "Aggregate memory throughput < 400.0 GB/s (measured: ${interleaved_bw} GB/s)"
fi

# 7. Assert thread migrations across NUMA nodes remain 0
if [[ "$zero_migrations" == "True" ]]; then
    assert_pass "Thread migrations across NUMA nodes remained 0 (strict pinning enforced)"
else
    assert_fail "Detected unwanted thread migrations across NUMA nodes"
fi

# 8. Test command execution wrap with --interleave
wrap_exit=0
"$ALLOC_BIN" --interleave /bin/true || wrap_exit=$?
if [[ "$wrap_exit" -eq 0 ]]; then
    assert_pass "Process wrapping with MPOL_INTERLEAVE executed successfully"
else
    assert_fail "Process wrapping failed with exit code $wrap_exit"
fi

echo "[test-numa-interleave-bandwidth] Summary: $pass passed, $fail failed."
if [[ "$fail" -eq 0 ]]; then
    echo "[test-numa-interleave-bandwidth] SUCCESS: All test assertions passed!"
    exit 0
else
    echo "[test-numa-interleave-bandwidth] FAILED: $fail test(s) failed."
    exit 1
fi
