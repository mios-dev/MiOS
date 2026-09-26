#!/bin/bash
# AI-hint: ADR-0025 lane L3 -- install_packages* skip a [packages] section outside the build profile (BUILD_PROFILE_SECTIONS from miosd build --sections) and install it when the profile selects it or no profile is set.
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
for b in dnf dnf5; do printf '#!/bin/sh\necho "$*" >> "%s/dnf.log"\n' "$TMP" > "$TMP/bin/$b"; chmod +x "$TMP/bin/$b"; done

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
