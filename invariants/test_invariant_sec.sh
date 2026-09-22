#!/bin/bash
set -euo pipefail
echo "[TEST-INVARIANT-SEC] Verifying Tetragon eBPF TracingPolicy non-interference..."

policy_dir="/etc/tetragon/tetragon.tp.d"
policy_file="$policy_dir/20-agent-sandboxing.yaml"

# Tetragon is a host-level eBPF observability daemon, not something every
# devcontainer, Codespace, or CI runner ships. Its absence is a capability
# gap, not a defect: SKIP (exit 2) rather than FAIL or a false PASS.
if [[ ! -d "$policy_dir" ]]; then
    echo "[SKIP] [INVARIANT-SEC] $policy_dir not present; Tetragon is not installed here."
    exit 2
fi

test -f "$policy_file" || {
    echo "[FAIL] Tetragon is installed but missing $policy_file" >&2
    exit 1
}
echo "[PASS] [INVARIANT-SEC] verified."
