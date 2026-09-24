#!/usr/bin/env bash
# AI-hint: Automated unit test suite verifying hardware target matrix profiling, dynamic inference memory limits, and mesh enrollment latency.
# AI-related: usr/libexec/mios/mios-hardware-profile, automation/20-hardware.sh, usr/share/mios/mios.toml

set -euo pipefail

PASS=0
FAIL=0

assert_eq() {
    local label="$1"
    local expected="$2"
    local actual="$3"
    if [[ "$expected" == "$actual" ]]; then
        echo "PASS: $label == $expected"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $label expected '$expected', got '$actual'"
        FAIL=$((FAIL + 1))
    fi
}

assert_le() {
    local label="$1"
    local val="$2"
    local ceiling="$3"
    if (( val <= ceiling )); then
        echo "PASS: $label ($val) <= $ceiling"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $label ($val) exceeded ceiling $ceiling"
        FAIL=$((FAIL + 1))
    fi
}

assert_ge() {
    local label="$1"
    local val="$2"
    local floor="$3"
    if (( val >= floor )); then
        echo "PASS: $label ($val) >= $floor"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $label ($val) below floor $floor"
        FAIL=$((FAIL + 1))
    fi
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BIN="${REPO_ROOT}/usr/libexec/mios/mios-hardware-profile"

if [[ ! -x "$BIN" ]]; then
    echo "FAIL: $BIN is missing or not executable"
    exit 1
fi

echo "=== 1. Native Detection Sanity Test ==="
NATIVE_TIER=$("$BIN" --tier)
echo "Native detected tier: $NATIVE_TIER"
if [[ "$NATIVE_TIER" =~ ^(prosumer-server|consumer-pc|laptop|nas|smartphone)$ ]]; then
    echo "PASS: Native tier is valid canonical target tier"
    PASS=$((PASS + 1))
else
    echo "FAIL: Unknown native tier '$NATIVE_TIER'"
    FAIL=$((FAIL + 1))
fi

echo "=== 2. Prosumer Server Emulation Test ==="
SERVER_JSON=$("$BIN" --emulate prosumer-server --json)
SERVER_TIER=$(echo "$SERVER_JSON" | jq -r '.tier')
SERVER_MODEL=$(echo "$SERVER_JSON" | jq -r '.recommended_model')
SERVER_ROLE=$(echo "$SERVER_JSON" | jq -r '.mesh_role')
SERVER_MEM=$(echo "$SERVER_JSON" | jq -r '.inference_memory_limit_mb')

assert_eq "server.tier" "prosumer-server" "$SERVER_TIER"
assert_eq "server.recommended_model" "70B" "$SERVER_MODEL"
assert_eq "server.mesh_role" "wan-gateway" "$SERVER_ROLE"
assert_ge "server.inference_memory_limit_mb" "$SERVER_MEM" 16384

echo "=== 3. Consumer PC Emulation Test ==="
PC_JSON=$("$BIN" --emulate consumer-pc --json)
PC_TIER=$(echo "$PC_JSON" | jq -r '.tier')
PC_MODEL=$(echo "$PC_JSON" | jq -r '.recommended_model')
PC_SHELL=$(echo "$PC_JSON" | jq -r '.display.desktop_shell')
PC_FRAMELESS=$(echo "$PC_JSON" | jq -r '.display.frameless')

assert_eq "pc.tier" "consumer-pc" "$PC_TIER"
assert_eq "pc.recommended_model" "8B" "$PC_MODEL"
assert_eq "pc.desktop_shell" "quickshell-wayland" "$PC_SHELL"
assert_eq "pc.frameless" "false" "$PC_FRAMELESS"

echo "=== 4. Laptop Emulation Test ==="
LAPTOP_JSON=$("$BIN" --emulate laptop --json)
LAPTOP_TIER=$(echo "$LAPTOP_JSON" | jq -r '.tier')
LAPTOP_MODEL=$(echo "$LAPTOP_JSON" | jq -r '.recommended_model')
LAPTOP_POWER=$(echo "$LAPTOP_JSON" | jq -r '.power_profile')

assert_eq "laptop.tier" "laptop" "$LAPTOP_TIER"
assert_eq "laptop.recommended_model" "3B" "$LAPTOP_MODEL"
assert_eq "laptop.power_profile" "battery-saver" "$LAPTOP_POWER"

echo "=== 5. NAS Storage Tier Emulation Test ==="
NAS_JSON=$("$BIN" --emulate nas --json)
NAS_TIER=$(echo "$NAS_JSON" | jq -r '.tier')
NAS_MODEL=$(echo "$NAS_JSON" | jq -r '.recommended_model')
NAS_SHELL=$(echo "$NAS_JSON" | jq -r '.display.desktop_shell')
NAS_BACKEND=$(echo "$NAS_JSON" | jq -r '.inference_backend')

assert_eq "nas.tier" "nas" "$NAS_TIER"
assert_eq "nas.recommended_model" "1.5B" "$NAS_MODEL"
assert_eq "nas.desktop_shell" "headless" "$NAS_SHELL"
assert_eq "nas.inference_backend" "llama-swap-cpu" "$NAS_BACKEND"

echo "=== 6. Smartphone Edge Tier Emulation Test (Strict <= 3GB Invariant) ==="
PHONE_JSON=$("$BIN" --emulate smartphone --json)
PHONE_TIER=$(echo "$PHONE_JSON" | jq -r '.tier')
PHONE_MODEL=$(echo "$PHONE_JSON" | jq -r '.recommended_model')
PHONE_ROLE=$(echo "$PHONE_JSON" | jq -r '.mesh_role')
PHONE_SHELL=$(echo "$PHONE_JSON" | jq -r '.display.desktop_shell')
PHONE_FRAMELESS=$(echo "$PHONE_JSON" | jq -r '.display.frameless')
PHONE_MEM=$(echo "$PHONE_JSON" | jq -r '.inference_memory_limit_mb')

assert_eq "smartphone.tier" "smartphone" "$PHONE_TIER"
assert_eq "smartphone.recommended_model" "1.5B" "$PHONE_MODEL"
assert_eq "smartphone.mesh_role" "edge-client" "$PHONE_ROLE"
assert_eq "smartphone.desktop_shell" "mobile-pwa" "$PHONE_SHELL"
assert_eq "smartphone.frameless" "true" "$PHONE_FRAMELESS"
# Strict verification: mobile memory pool MUST be <= 3GB (3072 MB)
assert_le "smartphone.inference_memory_limit_mb" "$PHONE_MEM" 3072

echo "=== 7. Rapid Mesh Enrollment Latency Benchmark (< 200ms) ==="
PHONE_BENCH=$("$BIN" --emulate smartphone --enroll-test)
PHONE_LATENCY=$(echo "$PHONE_BENCH" | jq -r '.enrollment_latency_ms')
PHONE_PASS=$(echo "$PHONE_BENCH" | jq -r '.passed')
assert_eq "phone.enroll_passed" "true" "$PHONE_PASS"
echo "Smartphone simulated enrollment latency: ${PHONE_LATENCY}ms (budget: <200ms)"

NAS_BENCH=$("$BIN" --emulate nas --enroll-test)
NAS_LATENCY=$(echo "$NAS_BENCH" | jq -r '.enrollment_latency_ms')
NAS_PASS=$(echo "$NAS_BENCH" | jq -r '.passed')
assert_eq "nas.enroll_passed" "true" "$NAS_PASS"
echo "NAS simulated enrollment latency: ${NAS_LATENCY}ms (budget: <200ms)"

echo "=== 8. Shell Environment Export Test ==="
ENV_OUT=$("$BIN" --emulate smartphone --env)
if echo "$ENV_OUT" | grep -q "export MIOS_HARDWARE_TIER='smartphone'" && \
   echo "$ENV_OUT" | grep -q "export MIOS_FRAMELESS_UI='true'" && \
   echo "$ENV_OUT" | grep -q "export MIOS_INFERENCE_MEM_LIMIT_MB="; then
    echo "PASS: Shell environment exports formatted correctly"
    PASS=$((PASS + 1))
else
    echo "FAIL: Shell environment exports missing required keys"
    FAIL=$((FAIL + 1))
fi

echo "=== 9. Negative Control: Invalid Emulation Tier ==="
set +e
"$BIN" --emulate invalid-tier-xyz 2>/dev/null
NEG_RC=$?
set -e
if [[ $NEG_RC -ne 0 ]]; then
    echo "PASS: Invalid emulation tier rejected with non-zero exit code ($NEG_RC)"
    PASS=$((PASS + 1))
else
    echo "FAIL: Invalid emulation tier unexpectedly succeeded"
    FAIL=$((FAIL + 1))
fi

echo "========================================="
echo "Hardware Profiling Test Results: PASS=$PASS FAIL=$FAIL"
echo "========================================="

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
exit 0
