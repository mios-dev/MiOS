#!/usr/bin/env bash
# AI-hint: CI suite for NUMA interleave policy, measured bandwidth (scaling asserted only on >1 node), and command wrapping.
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

# 4. Run the bandwidth benchmark; it reports measured numbers only
echo "[test-numa-interleave-bandwidth] Executing multi-threaded NUMA bandwidth benchmark..."
bench_output="$("$ALLOC_BIN" --benchmark 2>/dev/null)"
field() { echo "$bench_output" | python3 -c "import sys, json
d = json.load(sys.stdin)
try:
    v = d$1
except (KeyError, TypeError):
    v = None
print('' if v is None else v)"; }
base_bw="$(field "['baseline']['aggregate_bandwidth_gbps']")"
inter_bw="$(field "['interleaved']['aggregate_bandwidth_gbps']")"
measurable="$(field "['scaling_measurable']")"
speedup="$(field "['speedup_ratio']")"

# 5. Both runs measured a positive bandwidth
if python3 -c "import sys; sys.exit(0 if float('$base_bw') > 0 and float('$inter_bw') > 0 else 1)"; then
    assert_pass "Benchmark measured bandwidth (baseline ${base_bw} GB/s, interleaved ${inter_bw} GB/s)"
else
    assert_fail "Benchmark produced no measured bandwidth (baseline '${base_bw}', interleaved '${inter_bw}')"
fi

# 6. Scaling is asserted only where it can be measured (>1 node); a single node must not claim one
if [[ "$num_nodes" -gt 1 ]]; then
    if [[ "$measurable" == "True" ]] && python3 -c "import sys; sys.exit(0 if float('$speedup') >= 1.8 else 1)"; then
        assert_pass "NUMA interleaving achieved >= 1.8x speedup across $num_nodes nodes (measured: ${speedup}x)"
    else
        assert_fail "NUMA interleaving speedup < 1.8x across $num_nodes nodes (measured: '${speedup}')"
    fi
elif [[ "$measurable" == "False" && -z "$speedup" ]]; then
    assert_pass "Single NUMA node: no speedup claimed (interleave scaling not measurable here)"
else
    assert_fail "Single NUMA node reported a speedup it cannot measure (measurable=${measurable}, speedup=${speedup})"
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
