#!/usr/bin/env bash
# AI-hint: Unit test for MiOS role-apply and mios-blade command verification.
# AI-related: usr/libexec/mios/role-apply, usr/libexec/mios/mios-blade, /etc/mios/role.conf
set -euo pipefail

TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

MOCK_BIN="$TMP_ROOT/bin"
mkdir -p "$MOCK_BIN"
export PATH="$MOCK_BIN:$PATH"

MOCK_LOG="$TMP_ROOT/mock_calls.log"
touch "$MOCK_LOG"

cat > "$MOCK_BIN/systemctl" <<EOF
echo "Systemctl \$*" >> "$MOCK_LOG"
EOF
chmod +x "$MOCK_BIN/systemctl"

cat > "$MOCK_BIN/hostnamectl" <<EOF
echo "Hostnamectl \$*" >> "$MOCK_LOG"
EOF
chmod +x "$MOCK_BIN/hostnamectl"

mkdir -p "$TMP_ROOT/etc/mios"
mkdir -p "$TMP_ROOT/usr/share/mios"
mkdir -p "$TMP_ROOT/var/lib/mios"

cat > "$TMP_ROOT/usr/share/mios/mios.toml" <<EOF
[blade]
type = "hybrid"

[blade.archetypes]
hybrid = ["gpu-serving", "controller"]
compute = ["gpu-serving"]
headless = []

[blade.requires]
mios-llm-heavy = ["gpu-serving"]
EOF

export MIOS_ETC_DIR="$TMP_ROOT/etc/mios"
export MIOS_VAR_DIR="$TMP_ROOT/var/lib/mios"
export MIOS_ROOT="$TMP_ROOT"
export MIOS_TOML="$TMP_ROOT/usr/share/mios/mios.toml"
export MIOS_VENDOR_TOML="$TMP_ROOT/usr/share/mios/mios.toml"
export MIOS_HOST_TOML="$TMP_ROOT/etc/mios/mios.toml"
export MIOS_USR_DIR="$(pwd -W)/usr/lib/mios"

echo "=== Test 1: Default role-apply resolution ==="
rm -rf "$TMP_ROOT/etc/mios/role.conf"
rm -rf "$TMP_ROOT/etc/mios/blade.d"

bash usr/libexec/mios/role-apply

if [[ ! -f "$TMP_ROOT/etc/mios/blade.d/gpu-serving" || ! -f "$TMP_ROOT/etc/mios/blade.d/controller" ]]; then
    echo "FAIL: hybrid capability markers missing"
    exit 1
fi
echo "PASS: hybrid capability markers touched"

if ! grep -q "ROLE=hybrid" "$TMP_ROOT/var/lib/mios/role.active"; then
    echo "FAIL: role.active not correct for default role"
    exit 1
fi
echo "PASS: role.active updated correctly"

echo "=== Test 2: mios blade set compute ==="
bash usr/libexec/mios/mios-blade set compute

if ! grep -q 'ROLE="compute"' "$TMP_ROOT/etc/mios/role.conf"; then
    echo "FAIL: role.conf not updated to compute"
    exit 1
fi
echo "PASS: role.conf set correctly"

if [[ ! -f "$TMP_ROOT/etc/mios/blade.d/gpu-serving" ]]; then
    echo "FAIL: compute capability markers missing"
    exit 1
fi
if [[ -f "$TMP_ROOT/etc/mios/blade.d/controller" ]]; then
    echo "FAIL: controller capability marker should be absent under compute archetype"
    exit 1
fi
echo "PASS: compute capability markers verified"

echo "=== Test 3: mios blade add-capability custom-cap ==="
bash usr/libexec/mios/mios-blade add-capability custom-cap

if [[ ! -f "$TMP_ROOT/etc/mios/blade.d/custom-cap" ]]; then
    echo "FAIL: custom-cap capability marker missing"
    exit 1
fi
echo "PASS: custom capability marker verified"

if ! grep -q 'FEATURES="custom-cap"' "$TMP_ROOT/etc/mios/role.conf"; then
    echo "FAIL: role.conf does not persist custom-cap"
    exit 1
fi
echo "PASS: persistent custom capability verified"

echo "=== Test 4: mios blade status ==="
status_out=$(bash usr/libexec/mios/mios-blade status)
if ! echo "$status_out" | grep -q "Blade Type: compute"; then
    echo "FAIL: status did not show compute role"
    exit 1
fi
if ! echo "$status_out" | grep -q "\- custom-cap"; then
    echo "FAIL: status did not show custom-cap capability marker"
    exit 1
fi
echo "PASS: status verb output verified"

echo "ALL TESTS PASSED"
