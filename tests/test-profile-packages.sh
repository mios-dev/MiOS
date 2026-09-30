#!/bin/bash
# AI-hint: Verifies package profile filtering, shared section dependency closures, strict retry failures and default toolchain retention without installing or removing host packages.
# AI-related: automation/lib/packages.sh, automation/build.sh, src/mios-rs/mios-build/src/lib.rs, usr/share/mios/mios.toml
# AI-functions: main

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d /tmp/test-profile-packages.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT
fails=0
pass() { echo "  [PASS] $*"; }
fail() { echo "  [FAIL] $*"; fails=$((fails + 1)); }

# dnf is stubbed: every call is logged, nothing is installed.
mkdir -p "$TMP/bin"
for b in dnf dnf5; do printf '#!/bin/sh\necho "$*" >> "%s/dnf.log"\nexit "${MIOS_TEST_DNF_RC:-0}"\n' "$TMP" > "$TMP/bin/$b"; chmod +x "$TMP/bin/$b"; done

dependency_checks() {
    local fixture="$TMP/fixture" got rc
    mkdir -p "$fixture/lib"
    cp "$ROOT/automation/lib/packages.sh" "$fixture/lib/packages.sh"
    cp "$ROOT/automation/91-strip-build-toolchain.sh" "$fixture/91-strip-build-toolchain.sh"
    # Isolated library context: no real package manager or resolver runs.
    cat > "$fixture/lib/common.sh" <<'EOF'
DNF_BIN=dnf5
DNF_SETOPT=()
DNF_OPTS=()
mios_log() { echo "$*"; }
mios_ok() { echo "$*"; }
mios_warn() { echo "$*" >&2; }
mios_err() { echo "$*" >&2; }
EOF
    printf '#!/bin/sh\nexit 0\n' > "$TMP/bin/sleep"
    chmod +x "$TMP/bin/sleep"
    cat > "$fixture/packages.toml" <<'EOF'
[packages.child]
enable = true
pkgs = ["shared", "compiler"]
[packages.parent]
enable = true
requires_sections = ["child"]
pkgs = ["shared", "runtime"]
[packages.self-build]
enable = true
retain_toolchain = true
requires_sections = ["parent"]
pkgs = ["builder"]
EOF
    resolve() (
        source "$fixture/lib/packages.sh"
        export MIOS_TOML="$fixture/packages.toml"
        "$@"
    )
    got="$(resolve get_packages parent)"
    [[ "$got" == "shared compiler runtime " ]] && pass "section dependencies are ordered and deduplicated" || fail "unexpected closure: $got"
    got="$(resolve get_packages_from_toml parent "$fixture/packages.toml")"
    [[ "$got" == "shared compiler runtime " ]] && pass "explicit TOML reader resolves the same dependency closure" || fail "explicit TOML bypassed closure: $got"
    got="$(resolve get_packages optional-absent)"
    [[ -z "$got" ]] && pass "absent optional root retains its empty-reader contract" || fail "absent optional root unexpectedly resolved"
    cp "$fixture/packages.toml" "$fixture/valid.toml"
    sed -i 's/requires_sections = \["child"\]/requires_sections = ["missing-child"]/' "$fixture/packages.toml"
    if resolve get_packages parent > "$TMP/resolved.log" 2> "$TMP/err.log"; then
        fail "missing dependency was accepted"
    else
        [[ ! -s "$TMP/resolved.log" ]] && grep -q 'missing-child' "$TMP/err.log" && pass "missing dependency fails without partial output" || fail "missing dependency was not named"
    fi
    cp "$fixture/valid.toml" "$fixture/packages.toml"
    sed -i '0,/enable = true/s//enable = false/' "$fixture/packages.toml"
    if resolve get_packages parent > "$TMP/resolved.log" 2> "$TMP/err.log"; then
        fail "disabled dependency was accepted"
    else
        grep -q 'requires disabled.*child' "$TMP/err.log" && pass "disabled required section fails explicitly" || fail "disabled dependency failure was not explicit"
    fi
    cp "$fixture/valid.toml" "$fixture/packages.toml"
    sed -i '/\[packages.child\]/a requires_sections = ["parent"]' "$fixture/packages.toml"
    if resolve get_packages parent > "$TMP/resolved.log" 2> "$TMP/err.log"; then
        fail "cyclic dependency was accepted"
    else
        grep -q 'cyclic.*parent.*child.*parent' "$TMP/err.log" && pass "cyclic section dependency fails with the chain" || fail "cycle was not diagnosed"
    fi
    cp "$fixture/valid.toml" "$fixture/packages.toml"
    printf '\nbuild_catalog_authoritative = true\n' >> "$fixture/packages.toml"
    # Match the real global catalog switch; it may occur anywhere in TOML.
    printf '[{"name":"child","pkgs":["catalog-compiler"]},{"name":"parent","pkgs":["catalog-runtime"]}]\n' > "$fixture/package_sets.json"
    got="$(resolve get_packages parent)"
    [[ "$got" == "catalog-compiler catalog-runtime " ]] && pass "authoritative catalog retains declared dependency closure" || fail "catalog bypassed dependencies: $got"
    cp "$fixture/valid.toml" "$fixture/packages.toml"
    : > "$TMP/dnf.log"
    (
        export PATH="$TMP/bin:$PATH" MIOS_TOML="$fixture/packages.toml"
        bash "$fixture/91-strip-build-toolchain.sh"
    ) > "$TMP/out.log" 2>&1
    [[ ! -s "$TMP/dnf.log" ]] && grep -q 'Retaining build dependencies' "$TMP/out.log" && pass "retain_toolchain=true never invokes package removal" || fail "retention removed dependencies"
    sed -i '/retain_toolchain = true/d' "$fixture/packages.toml"
    if (export PATH="$TMP/bin:$PATH" MIOS_TOML="$fixture/packages.toml"; bash "$fixture/91-strip-build-toolchain.sh") > "$TMP/out.log" 2>&1; then
        fail "missing retention policy was accepted"
    else
        [[ ! -s "$TMP/dnf.log" ]] && pass "missing retention policy refuses destructive removal" || fail "missing policy removed packages"
    fi
    cp "$fixture/valid.toml" "$fixture/packages.toml"
    : > "$TMP/dnf.log"
    if (export PATH="$TMP/bin:$PATH" MIOS_TEST_DNF_RC=42; resolve install_packages_strict parent) > "$TMP/out.log" 2>&1; then
        fail "strict install hid the package manager failure"
    else
        [[ "$(wc -l < "$TMP/dnf.log" | tr -d ' ')" == 3 ]] && pass "strict install retries and propagates the final failure" || fail "strict retry count differs"
    fi
    if grep -Eq 'strict=0|skip-unavailable' "$TMP/dnf.log"; then fail "strict install permits missing dependencies"; else pass "strict install requires every requested package"; fi
    # Verify the actual MiOS closures, including the transitive developer image.
    for group in self-build devcontainer; do
        got="$(resolve get_packages_from_toml "$group" "$ROOT/usr/share/mios/mios.toml")"
        for pkg in rust cargo rustup clippy rustfmt musl-devel musl-gcc musl-libc-static just python3-pytest python3-jsonschema python3-pyflakes; do
            [[ " $got" == *" $pkg "* ]] || fail "$group lacks $pkg"
        done
        pass "$group includes the native compiler, static linker and development-check dependency closure"
    done
    unset -f resolve
}

# $1 = BUILD_PROFILE_SECTIONS (or "unset"), $2 = install function, $3 = section; prints dnf call count.
calls() {
    : > "$TMP/dnf.log"
    (
        export PATH="$TMP/bin:$PATH"
        if [[ "$1" == "unset" ]]; then unset BUILD_PROFILE_SECTIONS; else export BUILD_PROFILE_SECTIONS="$1"; fi
        # shellcheck source=/dev/null
        source "$ROOT/automation/lib/packages.sh" >/dev/null 2>&1
        # Sourcing exports the resolved environment, whose MIOS_TOML is the image path; read this checkout.
        export MIOS_TOML="$ROOT/usr/share/mios/mios.toml"
        "$2" "$3" > "$TMP/out.log" 2>&1
    ) || { echo "rc!=0"; return 0; }
    wc -l < "$TMP/dnf.log" | tr -d ' '
}

main() {
    dependency_checks
    if [[ "${1:-}" == --dependency-only ]]; then
        echo "[test-profile-packages] dependency failures: $fails"
        (( fails == 0 ))
        return
    fi
    local miosd="${MIOS_MIOSD_BIN:-$ROOT/src/mios-rs/target/debug/miosd}"
    if [[ ! -x "$miosd" ]]; then
        (cd "$ROOT/src/mios-rs" && cargo build -q -p miosd) || { echo "[test-profile-packages] ERROR: cannot build miosd" >&2; exit 1; }
    fi
    local core
    core="$(MIOS_ROOT="$ROOT" "$miosd" build --sections --profile core | tr '\n' ' ')"
    [[ " $core " == *" utils "* && " $core " != *" gaming "* ]] \
        && pass "miosd build --sections --profile core selects utils, not gaming: $core" \
        || fail "core sections unexpected: $core"
    [[ "$(MIOS_ROOT="$ROOT" "$miosd" build --sections --profile full)" == "*" ]] \
        && pass "the full profile selects every section (*)" || fail "full profile did not print *"

    local n
    n="$(calls "$core" install_packages gaming)"
    [[ "$n" == "0" ]] && grep -q "outside the build profile" "$TMP/out.log" \
        && pass "core: install_packages gaming is skipped, dnf never called" || fail "core: gaming made $n dnf call(s)"
    n="$(calls "$core" install_packages_strict hyprland)"
    [[ "$n" == "0" ]] && pass "core: install_packages_strict hyprland is a skip, not a failure" || fail "core: strict hyprland gave '$n'"
    n="$(calls "$core" install_packages utils)"
    [[ "$n" == "1" ]] && pass "core: install_packages utils installs (1 dnf call)" || fail "core: utils made $n dnf call(s)"
    n="$(calls "*" install_packages gaming)"
    [[ "$n" == "1" ]] && pass "*: install_packages gaming installs" || fail "*: gaming made $n dnf call(s)"
    n="$(calls unset install_packages gaming)"
    [[ "$n" == "1" ]] && pass "no profile set: install_packages gaming installs (today's behaviour)" || fail "unset: gaming made $n dnf call(s)"

    # build.sh itself, truncated before any stage runs: the caller's profile must survive common.sh re-exporting the SSOT env.
    local n_end probe out
    n_end="$(grep -n "^TOTAL_SCRIPTS=" "$ROOT/automation/build.sh" | cut -d: -f1)"
    probe="$TMP/build-head.sh"
    head -n "$n_end" "$ROOT/automation/build.sh" \
        | sed "s|^SCRIPT_DIR=.*|SCRIPT_DIR=\"$ROOT/automation\"|" \
        | awk -v t="$ROOT/usr/share/mios/mios.toml" '{print} /^source "\$\{SCRIPT_DIR\}\/lib\/packages.sh"/{print "export MIOS_TOML=\"" t "\""}' > "$probe"
    echo 'echo "PHASES=${#ALL_SCRIPTS[@]} SECTIONS=[${BUILD_PROFILE_SECTIONS:-}]"' >> "$probe"
    out="$(MIOS_MIOSD_BIN="$miosd" MIOS_PROFILES_DEFAULT=core bash "$probe" 2>&1 | grep "^PHASES=" || true)"
    [[ "$out" == *"SECTIONS=[ai base"* && "$out" != *"SECTIONS=[*"* ]] \
        && pass "build.sh honours MIOS_PROFILES_DEFAULT=core: $out" || fail "build.sh ignored the requested profile: ${out:-no output}"
    out="$(MIOS_MIOSD_BIN="$miosd" MIOS_PROFILES_DEFAULT=zz-planted-profile bash "$probe" 2>&1 || true)"
    [[ "$out" == *"FATAL"*"zz-planted-profile"* ]] \
        && pass "build.sh refuses an undeclared profile, naming it" || fail "build.sh accepted an undeclared profile"

    echo "[test-profile-packages] failures: $fails"
    (( fails == 0 ))
}

main "$@"
