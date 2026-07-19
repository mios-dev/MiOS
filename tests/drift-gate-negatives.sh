#!/usr/bin/env bash
# AI-hint: Negative-test harness for the new drift gates (AGY-54). Inject violations, assert they fail, restore, and assert pass.
# AI-related: /usr/lib/mios/userenv.sh, /usr/libexec/mios/mios-test-temp-eval, /usr/share/mios/referenced_names.txt, mios-test-temp-eval
# AI-functions: log, die, test_version_ssot, test_resolver_equivalence, test_eval_safety, test_shellcheck_failure, test_names_registry_closure, test_root_toml_subset, main
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Ensure we use the correct path variables for drift checks
export PATH="${ROOT}/.gemini/antigravity-ide/brain/65e96314-c09e-454f-843e-7baf8bdd3df7/scratch:${PATH}"

log() {
    echo -e "\033[1;34m[drift-gate-negatives]\033[0m $1"
}

die() {
    echo -e "\033[1;31m[drift-gate-negatives] ERROR:\033[0m $1" >&2
    exit 1
}

# 1. Test check_version_ssot
test_version_ssot() {
    log "Testing check_version_ssot..."
    local version_file="${ROOT}/VERSION"
    local orig_val
    orig_val="$(cat "$version_file")"

    # Inject violation
    echo "9.9.9" > "$version_file"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/38-drift-checks.sh" check_version_ssot >/dev/null 2>&1; then
        echo "$orig_val" > "$version_file"
        die "check_version_ssot passed despite version drift violation!"
    fi

    # Restore and verify green
    echo "$orig_val" > "$version_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/38-drift-checks.sh" check_version_ssot >/dev/null 2>&1 \
        || die "check_version_ssot failed after restoration!"
    log "check_version_ssot negative test passed."
}

# 2. Test check_resolver_twin_equivalence
test_resolver_equivalence() {
    log "Testing check_resolver_twin_equivalence..."
    local userenv_file="${ROOT}/usr/lib/mios/userenv.sh"
    local orig_val
    orig_val="$(cat "$userenv_file")"

    # Inject violation
    echo 'export MIOS_AI_TEST_TEMP="invalid-drift-val"' >> "$userenv_file"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/38-drift-checks.sh" check_resolver_twin_equivalence >/dev/null 2>&1; then
        echo "$orig_val" > "$userenv_file"
        die "check_resolver_twin_equivalence passed despite mismatch!"
    fi

    # Restore and verify green
    echo "$orig_val" > "$userenv_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/38-drift-checks.sh" check_resolver_twin_equivalence >/dev/null 2>&1 \
        || die "check_resolver_twin_equivalence failed after restoration!"
    log "check_resolver_twin_equivalence negative test passed."
}

# 3. Test check_cli_eval_safety
test_eval_safety() {
    log "Testing check_cli_eval_safety..."
    local temp_verb="${ROOT}/usr/libexec/mios/mios-test-temp-eval"

    # Clean up any leftover
    rm -f "$temp_verb"

    # Inject violation: add eval "$1" to a verb script
    cat << 'EOF' > "$temp_verb"
#!/usr/bin/env bash
eval "$1"
EOF
    chmod +x "$temp_verb"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/38-drift-checks.sh" check_cli_eval_safety >/dev/null 2>&1; then
        rm -f "$temp_verb"
        die "check_cli_eval_safety passed despite eval injection!"
    fi

    # Restore and verify green
    rm -f "$temp_verb"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/38-drift-checks.sh" check_cli_eval_safety >/dev/null 2>&1 \
        || die "check_cli_eval_safety failed after restoration!"
    log "check_cli_eval_safety negative test passed."
}

# 4. Test check_shellcheck
test_shellcheck_failure() {
    log "Testing check_shellcheck..."
    
    # We set up a temporary directory with a mock shellcheck binary to simulate a lint failure
    local tmp_bin_dir
    tmp_bin_dir="$(mktemp -d)"
    cat << 'EOF' > "${tmp_bin_dir}/shellcheck"
#!/bin/sh
echo "Injected shellcheck failure"
exit 1
EOF
    chmod +x "${tmp_bin_dir}/shellcheck"

    # Run linter with mock shellcheck in PATH
    local old_path="$PATH"
    export PATH="${tmp_bin_dir}:${PATH}"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/38-drift-checks.sh" check_shellcheck >/dev/null 2>&1; then
        export PATH="$old_path"
        rm -rf "$tmp_bin_dir"
        die "check_shellcheck passed despite shellcheck failure!"
    fi

    # Restore and verify green (degrades to skipped or passes on clean)
    export PATH="$old_path"
    rm -rf "$tmp_bin_dir"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/38-drift-checks.sh" check_shellcheck >/dev/null 2>&1 \
        || die "check_shellcheck failed after restoration!"
    log "check_shellcheck negative test passed."
}

# 5. Test check_names_registry (names registry / closure)
test_names_registry_closure() {
    log "Testing check_names_registry..."
    local ref_file="${ROOT}/usr/share/mios/referenced_names.txt"
    local orig_val
    orig_val="$(cat "$ref_file")"

    # Inject violation: add a dummy fake environment variable reference
    echo "MIOS_FAKE_TEST_VARIABLE_DRIP" >> "$ref_file"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/38-drift-checks.sh" check_names_registry >/dev/null 2>&1; then
        echo "$orig_val" > "$ref_file"
        die "check_names_registry passed despite stale referenced_names.txt!"
    fi

    # Restore and verify green
    echo "$orig_val" > "$ref_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/38-drift-checks.sh" check_names_registry >/dev/null 2>&1 \
        || die "check_names_registry failed after restoration!"
    log "check_names_registry negative test passed."
}

# 6. Test check_root_toml_subset
test_root_toml_subset() {
    log "Testing check_root_toml_subset..."
    local root_toml="${ROOT}/mios.toml"
    local orig_val
    orig_val="$(cat "$root_toml")"

    # Inject violation: add a new unrecognized key not in canonical toml
    cat << 'EOF' >> "$root_toml"
[meta.nonexistent_drift_test_section]
fake_key_drift_assertion = "drift"
EOF

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/38-drift-checks.sh" check_root_toml_subset >/dev/null 2>&1; then
        echo "$orig_val" > "$root_toml"
        die "check_root_toml_subset passed despite invalid key injection!"
    fi

    # Restore and verify green
    echo "$orig_val" > "$root_toml"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/38-drift-checks.sh" check_root_toml_subset >/dev/null 2>&1 \
        || die "check_root_toml_subset failed after restoration!"
    log "check_root_toml_subset negative test passed."
}

# 7. Test check_toml_projection
test_toml_projection() {
    log "Testing check_toml_projection..."
    local root_toml="${ROOT}/mios.toml"
    if [[ ! -f "$root_toml" ]]; then
        log "root mios.toml absent -- skipping check_toml_projection negative test."
        return 0
    fi
    local bak="${root_toml}.projtest.bak"
    cp "$root_toml" "$bak"

    # Inject drift into a PROJECTED section: mutate a [colors] value so the block no longer
    # matches the canonical SSOT (mios-sync-toml --check must then report drift).
    python3 - "$root_toml" << 'EOF'
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
new = t.replace('accent      = "#1A407F"', 'accent      = "#DEAD00"', 1)
if new == t:
    new = t.replace('#1A407F', '#DEAD00', 1)   # fallback if spacing differs
open(p, "w", encoding="utf-8").write(new)
EOF

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/38-drift-checks.sh" check_toml_projection >/dev/null 2>&1; then
        mv "$bak" "$root_toml"
        die "check_toml_projection passed despite injected [colors] drift!"
    fi

    # Restore and verify green.
    mv "$bak" "$root_toml"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/38-drift-checks.sh" check_toml_projection >/dev/null 2>&1 \
        || die "check_toml_projection failed after restoration!"
    log "check_toml_projection negative test passed."
}

main() {
    log "Starting negative-test suite..."
    test_version_ssot
    test_resolver_equivalence
    test_eval_safety
    test_shellcheck_failure
    test_names_registry_closure
    test_root_toml_subset
    test_toml_projection
    log "All negative tests completed successfully!"
}

main "$@"
